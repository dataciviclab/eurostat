#!/usr/bin/env python3
"""
Assess a Eurostat dataflow as a candidate for the pipeline.

Probes the Eurostat SDMX API, detects dimensions, years, and size,
then generates a ready-to-edit dataset.yml + clean.sql + mart.sql.

Usage:
    python scripts/assess_candidate.py --flow TOUR_OCC_ARN2
    python scripts/assess_candidate.py --flow LFST_R_LFE2EMPRT --slug emp_rates

Output:
    datasets/{slug}/dataset.yml
    datasets/{slug}/sql/clean.sql
    datasets/{slug}/sql/mart.sql
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

API_DATa = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
API_META = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT"
REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 30

# ── Helpers ───────────────────────────────────────────────────────────────────


def _fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    return json.loads(resp.read())  # type: ignore[no-any-return]


def _slugify(flow: str) -> str:
    """Convert dataflow ID to dataset directory name (hyphens only).

    Convention: all dataset directories start with ``eurostat-``.
    """
    base = flow.lower().replace("_", "-")
    if not base.startswith("eurostat-"):
        base = "eurostat-" + base
    if "nuts3" not in base and "nuts2" not in base:
        base += "-nuts3"
    return base


def _ds_name(slug: str) -> str:
    """Dataset name for dataset.yml (underscores for GCS path compat)."""
    return slug.replace("-", "_")


# ── Probe ─────────────────────────────────────────────────────────────────────


def _probe_header(flow: str) -> tuple[list[str], list[str], int | None]:
    """Download first bytes of the TSV and detect dimensions and years.

    Returns (dimensions, year_columns, estimated_bytes).
    """
    url = f"{API_DATa}/{flow}?format=TSV"
    req = urllib.request.Request(url, headers={"Range": "bytes=0-51200"})
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        data = resp.read()
    except urllib.error.HTTPError as e:
        # Fallback: full download if Range not supported
        if e.code == 416:
            req2 = urllib.request.Request(url)
            resp2 = urllib.request.urlopen(req2, timeout=TIMEOUT)
            data = resp2.read(51200)
        else:
            raise

    # Get full size from Content-Range or Content-Length
    size: int | None = None
    cr = resp.headers.get("Content-Range") if hasattr(resp, "headers") else None
    cl = resp.headers.get("Content-Length") if hasattr(resp, "headers") else None
    if cr:
        match = re.search(r"/\s*(\d+)", cr)
        if match:
            size = int(match.group(1))
    elif cl:
        size = int(cl)

    text = data.decode("utf-8")
    first_line = text.split("\n", 1)[0].strip()

    # Detect dimensions: everything before \TIME_PERIOD
    parts = first_line.split("\t")
    first_col = parts[0]
    backslash_pos = first_col.find("\\")
    dims_raw = first_col[:backslash_pos] if backslash_pos > 0 else first_col
    dims = [d.strip() for d in dims_raw.split(",") if d.strip()]

    # Year columns
    year_cols = [y.strip() for y in parts[1:] if y.strip()]

    return dims, year_cols, size


def _probe_metadata(flow: str) -> dict[str, Any]:
    """Fetch dataflow metadata from the Eurostat catalog."""
    catalog = _fetch_json(f"{API_META}?format=json&limit=10000")
    items = catalog.get("link", {}).get("item", [])

    for item in items:
        ext = item.get("extension", {})
        if ext.get("id") == flow:
            ann = {a.get("type"): a for a in ext.get("annotation", [])}
            return {
                "label": item.get("label", flow),
                "obs": ann.get("OBS_COUNT", {}).get("title"),
                "oldest": ann.get("OBS_PERIOD_OVERALL_OLDEST", {}).get("title"),
                "latest": ann.get("OBS_PERIOD_OVERALL_LATEST", {}).get("title"),
            }
    return {"label": flow, "obs": None, "oldest": None, "latest": None}


# ── Known codelists ───────────────────────────────────────────────────────────
# Map from dimension name to codelist file (if one exists)

_KNOWN_CODELISTS: dict[str, str] = {
    "freq": "freq.csv",
    "unit": "units.csv",
    "geo": "geo.csv",
    "nace_r2": "nace_r2.csv",
    "iccs": None,  # no codelist yet
}

# Dimensions that need special handling (CASE WHEN labels)
_KNOWN_DIM_LABELS: dict[str, list[tuple[str, str]]] = {
    "sex": [
        ("'M'", "'Male'"),
        ("'F'", "'Female'"),
        ("'T'", "'Total'"),
    ],
    "wstatus": [
        ("'TOTAL'", "'Total employment'"),
        ("'EMP'", "'Employed'"),
        ("'UNE'", "'Unemployed'"),
        ("'INACT'", "'Inactive'"),
        ("'SAL'", "'Salaried'"),
        ("'SELF'", "'Self-employed'"),
        ("'EMPL'", "'Employees'"),
    ],
}


# ── Template generators ───────────────────────────────────────────────────────


def _dim_comment(dim: str) -> str:
    """Generate a clean.sql dimension-enrichment template."""
    if dim in _KNOWN_CODELISTS:
        cl = _KNOWN_CODELISTS[dim]
        if cl:
            return (
                f"    -- LEFT JOIN read_csv('codelists/{cl}', "
                "auto_detect=true, delim=',', header=true) d "
                f"ON r.{dim} = d.code"
            )
    elif dim in _KNOWN_DIM_LABELS:
        lines = [f"    -- {dim}: enrich with label_en"]
        for val, label in _KNOWN_DIM_LABELS[dim]:
            lines.append(f"    -- WHEN {val} THEN {label}")
        lines.append(f"    -- END AS {dim}_label_en,")
        return "\n".join(lines) + "\n"
    return f"    -- DIMENSION {dim}: add codelist or CASE WHEN for label_en"


def _generate_clean_sql(dims: list[str]) -> str:
    """Generate clean.sql with proper JOINs and comments."""
    cols = [f"    r.{d}" for d in dims]

    lines = [
        f"-- clean.sql: auto-generated for {', '.join(dims)}",
        "SELECT",
    ]
    lines.extend(c + "," for c in cols)
    lines.append("    CAST(r.year AS INTEGER) AS year,")
    lines.append("    f.label_en AS freq_label_en,")
    lines.append("    u.label_en AS unit_label_en,")

    # Known codelist labels to include in SELECT
    if "nace_r2" in dims:
        lines.append("    n.label_en AS nace_label_en,")

    # Add enrichment hints for extra dimensions
    extra_dims = [d for d in dims if d not in ("freq", "unit", "nace_r2", "geo")]
    for d in extra_dims:
        hint = _dim_comment(d)
        if "\n" in hint:
            lines.append(hint.rstrip(","))
        else:
            lines.append(hint + ",")

    if "geo" in dims:
        lines.append("    g.label_en AS geo_label_en,")
        lines.append("    g.nuts_level,")
        lines.append("    g.parent_code AS nuts_parent_code,")
        lines.append("    gp.label_en AS nuts_parent_label_en,")

    lines.append("    CAST(r.value AS DOUBLE) AS value,")
    lines.append("    r.flag,")
    lines.append("    fl.description_en AS flag_desc_en")

    # FROM
    lines.append("FROM raw_input r")

    # JOINs
    lines.append(
        "LEFT JOIN read_csv('codelists/freq.csv', "
        "auto_detect=true, delim=',', header=true) f "
        "ON r.freq = f.freq"
    )
    lines.append(
        "LEFT JOIN read_csv('codelists/units.csv', "
        "auto_detect=true, delim=',', header=true) u "
        "ON r.unit = u.unit"
    )
    if "nace_r2" in dims:
        lines.append(
            "LEFT JOIN read_csv('codelists/nace_r2.csv', "
            "auto_detect=true, delim=',', header=true) n "
            "ON r.nace_r2 = n.code"
        )
    if "geo" in dims:
        lines.append(
            "LEFT JOIN read_csv('codelists/geo.csv', "
            "auto_detect=true, delim=',', header=true) g "
            "ON r.geo = g.code"
        )
        lines.append(
            "LEFT JOIN read_csv('codelists/geo.csv', "
            "auto_detect=true, delim=',', header=true) gp "
            "ON g.parent_code = gp.code"
        )
    lines.append(
        "LEFT JOIN read_csv('codelists/flags.csv', "
        "auto_detect=true, delim=',', header=true) fl "
        "ON r.flag = fl.flag"
    )

    return "\n".join(lines) + "\n"


def _generate_mart_sql() -> str:
    """Generate a standard Italy-filtered mart.sql."""
    return (
        "-- mart.sql: Italy-filtered view on clean data\n"
        "SELECT\n"
        "    year,\n"
        "    geo,\n"
        "    geo_label_en,\n"
        "    nuts_level,\n"
        "    value,\n"
        "    flag\n"
        "FROM clean_input\n"
        "WHERE geo LIKE 'IT%'\n"
        "  AND value IS NOT NULL\n"
        "ORDER BY year DESC, geo\n"
    )


def _generate_dataset_yml(
    slug: str,
    flow: str,
    dims: list[str],
    year_cols: list[str],
    label: str,
) -> str:
    """Generate dataset.yml.

    slug = directory name (hyphens), ds_name = underscored (GCS compat).
    years = current year (repo convention), time_coverage = actual range.
    """
    ds_name = _ds_name(slug)
    oldest = year_cols[0] if year_cols else "2000"
    end_year = year_cols[-1] if year_cols else "2026"
    curr_year = str(date.today().year)

    return (
        f'root: "../../out"\n'
        f"schema_version: 1\n"
        f"\n"
        f"dataset:\n"
        f'  name: "{ds_name}"\n'
        f'  source_id: "eurostat"\n'
        f"  years: [{curr_year}]\n"
        f"  time_coverage:\n"
        f"    start_year: {oldest}\n"
        f"    end_year: {end_year}\n"
        f"\n"
        f"raw:\n"
        f"  output_policy: overwrite\n"
        f"  sources:\n"
        f'    - name: "eurostat_{flow.lower()}"\n'
        f'      type: "script"\n'
        f"      args:\n"
        f'        command: "../../connectors/tsv_normalize.py'
        f" --flow {flow}"
        f' --output {flow.lower()}_normalized.parquet"\n'
        f'        output: "{flow.lower()}_normalized.parquet"\n'
        f'        filename: "{flow.lower()}_normalized.parquet"\n'
        f"      primary: true\n"
        f"\n"
        f"clean:\n"
        f'  sql: "sql/clean.sql"\n'
        f"  read:\n"
        f"    source: auto\n"
        f"    mode: latest\n"
        f'    delim: ","\n'
        f"    encoding: utf-8\n"
        f"    header: true\n"
        f"  validate:\n"
        f"    min_rows: 100\n"
        f"\n"
        f"mart:\n"
        f"  tables:\n"
        f'    - name: "mart_{ds_name}"\n'
        f'      sql: "sql/mart.sql"\n'
        f"  required_tables:\n"
        f'    - "mart_{ds_name}"\n'
        f"\n"
        f"validation:\n"
        f"  fail_on_error: true\n"
        f"\n"
        f"registry:\n"
        f'  dataflow: "{flow}"\n'
        f'  theme: "{label}"\n'
        f"  nuts_level: 3\n"
        f"  dimensions: {json.dumps(dims)}\n"
        f'  description: "{label}"\n'
    )


# ── List mode ─────────────────────────────────────────────────────────────────


def _list_candidates(
    filter_keyword: str | None = None, min_obs: int = 0, json_output: bool = False
):
    """Fetch the Eurostat catalog and print NUTS3-related dataflows."""
    catalog = _fetch_json(f"{API_META}?format=json&limit=10000")
    items = catalog.get("link", {}).get("item", [])

    candidates: list[dict[str, Any]] = []
    for item in items:
        ext = item.get("extension", {})
        flow_id = ext.get("id", "")
        label = item.get("label", "")
        annotations = {a.get("type"): a for a in ext.get("annotation", [])}

        # Detect NUTS level from label patterns and ID conventions
        label_lower = label.lower()
        id_lower = flow_id.lower()
        is_nuts3 = any(
            k in label_lower or k in id_lower for k in ["nuts 3", "nuts3", "_r3", "n3"]
        )
        if not is_nuts3:
            continue

        obs_str = annotations.get("OBS_COUNT", {}).get("title", "0")
        try:
            obs = int(obs_str) if obs_str.isdigit() else 0
        except (ValueError, TypeError):
            obs = 0

        if obs < min_obs:
            continue
        if filter_keyword and filter_keyword.lower() not in label_lower:
            continue

        candidates.append(
            {
                "id": flow_id,
                "label": label[:120],
                "obs": obs,
                "oldest": annotations.get("OBS_PERIOD_OVERALL_OLDEST", {}).get(
                    "title", "?"
                ),
                "latest": annotations.get("OBS_PERIOD_OVERALL_LATEST", {}).get(
                    "title", "?"
                ),
            }
        )

    if not candidates:
        print("No matching NUTS3 dataflows found.")
        return

    candidates.sort(key=lambda x: x["obs"], reverse=True)

    if json_output:
        print(json.dumps(candidates, indent=2))
        return

    print(f"\n{'ID':35s} {'Obs':>10s} {'Period':18s}  Label")
    print("-" * 100)
    for c in candidates:
        period = f"{c['oldest']} - {c['latest']}"
        print(f"{c['id']:35s} {c['obs']:>10,} {period:18s}  {c['label'][:70]}")
    print(f"\n{len(candidates)} candidates")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Eurostat dataset tools: probe a candidate or list available ones"
    )
    parser.add_argument(
        "--flow", default=None, help="Eurostat dataflow ID (e.g. TOUR_OCC_ARN2)"
    )
    parser.add_argument(
        "--slug", default=None, help="Output slug for generated dataset"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all NUTS3 candidates from catalog"
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="Filter list by theme keyword (e.g. tourism, transport)",
    )
    parser.add_argument(
        "--min-obs",
        type=int,
        default=100000,
        help="Minimum observations (default: 100K)",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="JSON output (for --list mode)"
    )
    args = parser.parse_args()

    if args.list or not args.flow:
        _list_candidates(
            filter_keyword=args.theme,
            min_obs=args.min_obs,
            json_output=args.json_output,
        )
        return

    flow = args.flow.upper()
    slug = args.slug or _slugify(flow)

    print(f"🔍 Probing {flow}...")
    dims, year_cols, size = _probe_header(flow)
    meta = _probe_metadata(flow)

    print(f"   Dimensions: {', '.join(dims)}")
    print(
        f"   Years: {year_cols[0] if year_cols else '?'}..{year_cols[-1] if year_cols else '?'} ({len(year_cols)} years)"
    )
    print(
        f"   Size: {size:,} bytes ({size / 1024 / 1024:.1f} MB)"
        if size
        else "   Size: unknown"
    )
    print(f"   Observations: {meta.get('obs', '?')}")
    print(f"   Label: {meta.get('label', '?')[:80]}")
    print()

    # Create output directory
    out_dir = REPO_ROOT / "datasets" / slug
    sql_dir = out_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    (out_dir / "dataset.yml").write_text(
        _generate_dataset_yml(slug, flow, dims, year_cols, meta.get("label", flow)),
        encoding="utf-8",
    )
    (sql_dir / "clean.sql").write_text(
        _generate_clean_sql(dims),
        encoding="utf-8",
    )
    (sql_dir / "mart.sql").write_text(
        _generate_mart_sql(),
        encoding="utf-8",
    )

    print(f"✅ Generated datasets/{slug}/")
    print("   ├── dataset.yml")
    print("   ├── sql/clean.sql")
    print("   └── sql/mart.sql")
    print()
    print("Next steps:")
    print(
        f"   1. Review and edit clean.sql (add dimension labels for: "
        f"{', '.join(d for d in dims if d not in ('freq', 'unit', 'geo') and d not in _KNOWN_CODELISTS)})"
    )
    print(
        f"   2. Run: TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run raw --config datasets/{slug}/dataset.yml --years {year_cols[-1] if year_cols else '2026'}"
    )
    print(
        f"   3. Run: TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run full --config datasets/{slug}/dataset.yml --years {year_cols[-1] if year_cols else '2026'}"
    )
    print("   4. Update docs/dataset-registry.md")


if __name__ == "__main__":
    main()
