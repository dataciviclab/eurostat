#!/usr/bin/env python3
"""
Fetch Eurostat SDMX codelists and regenerate codelists/*.csv.

Fetches ALL codelists from the Eurostat JSON API (GEO, NACE_R2, FREQ,
UNIT, OBS_FLAG). GEO includes NUTS hierarchy (nuts_level, parent_code)
deduced from code length. All CSVs are written with canonical columns.

Uso:  python scripts/update_codelists.py

Run this when Eurostat updates its classifications (NUTS ~every 3 years,
NACE rarely). Called automatically by publish.yml before processing
datasets, so codelists are always fresh on GCS pushes.
"""

from __future__ import annotations

import csv
import urllib.request
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CODELISTS_DIR = REPO_ROOT / "codelists"
API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT"
TIMEOUT = 30


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fetch_raw(url: str) -> dict[str, Any]:
    """Fetch a URL and return parsed JSON."""
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    return json.loads(resp.read())  # type: ignore[no-any-return]


def _fetch_codelist(codelist_id: str) -> dict[str, str]:
    """Fetch a codelist from Eurostat JSON API, return {code: label_en}."""
    data = _fetch_raw(f"{API_BASE}/{codelist_id}?format=json")
    return data.get("category", {}).get("label", {}) or {}


def _write_csv(filename: str, header: list[str], rows: list[tuple]) -> Path:
    """Write rows to codelists/{filename}, return path."""
    path = CODELISTS_DIR / filename
    CODELISTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


# ── GEO helpers (NUTS level from API annotations) ────────────────────────────

# Mapping from API LEVEL annotation values to geo.csv nuts_level strings.
_LEVEL_MAP: dict[str, str] = {
    "0": "country",
    "1": "NUTS1",
    "2": "NUTS2",
    "3": "NUTS3",
}


def _parent_code(code: str) -> str:
    """Derive NUTS parent code by truncating the last character."""
    c = code.strip()
    return c[:-1] if len(c) > 2 else ""


# ── Codelist generators ───────────────────────────────────────────────────────


def update_geo() -> int:
    """Fetch GEO codelist and write geo.csv with NUTS hierarchy.

    Uses the API's code annotations (LEVEL, IS_STANDARD_CODE) instead
    of heuristic code-length sniffing, avoiding false NUTS levels on
    EU aggregates like EU27_2020, ACP_*, etc.
    """
    data = _fetch_raw(f"{API_BASE}/GEO/latest?format=json")
    labels: dict[str, str] = data.get("category", {}).get("label", {}) or {}
    annotations: dict[str, list[dict[str, Any]]] = (
        data.get("extension", {}).get("code-annotation", {}) or {}
    )

    def _get_attrib(code: str, attr: str) -> str | None:
        """Extract a single annotation attribute by type."""
        ann_list = annotations.get(code, [])
        for ann in ann_list:
            if ann.get("type") == attr:
                val = ann.get("title")
                if val is not None:
                    return str(val)
        return None

    rows: list[tuple[str, str, str, str]] = []
    obsolete = 0

    for code in sorted(labels):
        label = labels[code]

        # Obsolete codes: keep (data may reference them) but no nuts_level
        is_std = _get_attrib(code, "IS_STANDARD_CODE")
        if is_std == "O":
            rows.append((code, label, "", ""))
            obsolete += 1
            continue

        # Resolve NUTS level from API annotation
        level_raw = _get_attrib(code, "LEVEL")
        if level_raw and level_raw in _LEVEL_MAP:
            nuts = _LEVEL_MAP[level_raw]
            parent = _parent_code(code) if nuts.startswith("NUTS") else ""
        else:
            nuts = ""
            parent = ""

        rows.append((code, label, nuts, parent))

    _write_csv("geo.csv", ["code", "label_en", "nuts_level", "parent_code"], rows)
    print(f"  ✅ geo.csv: {len(rows)} entries ({obsolete} obsolete kept)")
    return len(rows)


def update_nace() -> int:
    """Fetch NACE_R2 codelist and write nace_r2.csv (all codes)."""
    labels = _fetch_codelist("NACE_R2")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("nace_r2.csv", ["code", "label_en"], rows)
    print(f"  ✅ nace_r2.csv: {len(rows)} entries")
    return len(rows)


def update_freq() -> int:
    """Fetch FREQ codelist and write freq.csv."""
    labels = _fetch_codelist("FREQ")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("freq.csv", ["freq", "label_en"], rows)
    print(f"  ✅ freq.csv: {len(rows)} entries")
    return len(rows)


def update_units() -> int:
    """Fetch UNIT codelist and write units.csv."""
    labels = _fetch_codelist("UNIT")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("units.csv", ["unit", "label_en"], rows)
    print(f"  ✅ units.csv: {len(rows)} entries")
    return len(rows)


def update_indic_de() -> int:
    """Fetch INDIC_DE codelist and write indic_de.csv."""
    labels = _fetch_codelist("INDIC_DE")
    # Filter to codes that actually appear in demo-balance data
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("indic_de.csv", ["code", "label_en"], rows)
    print(f"  ✅ indic_de.csv: {len(rows)} entries")
    return len(rows)


def update_c_resid() -> int:
    """Fetch C_RESID codelist and write c_resid.csv."""
    labels = _fetch_codelist("C_RESID")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("c_resid.csv", ["code", "label_en"], rows)
    print(f"  ✅ c_resid.csv: {len(rows)} entries")
    return len(rows)


def update_indic_nrg() -> int:
    """Fetch INDIC_NRG codelist and write indic_nrg.csv."""
    labels = _fetch_codelist("INDIC_NRG")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("indic_nrg.csv", ["code", "label_en"], rows)
    print(f"  ✅ indic_nrg.csv: {len(rows)} entries")
    return len(rows)


def update_indic_sb() -> int:
    """Fetch INDIC_SB codelist and write indic_sb.csv."""
    labels = _fetch_codelist("INDIC_SB")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("indic_sb.csv", ["code", "label_en"], rows)
    print(f"  ✅ indic_sb.csv: {len(rows)} entries")
    return len(rows)


def update_levels() -> int:
    """Fetch LEVELS codelist and write levels.csv."""
    labels = _fetch_codelist("LEVELS")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("levels.csv", ["code", "label_en"], rows)
    print(f"  ✅ levels.csv: {len(rows)} entries")
    return len(rows)


def update_clc18() -> int:
    """Fetch CLC18 codelist and write clc18.csv."""
    labels = _fetch_codelist("CLC18")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("clc18.csv", ["code", "label_en"], rows)
    print(f"  ✅ clc18.csv: {len(rows)} entries")
    return len(rows)


def update_na_item() -> int:
    """Fetch NA_ITEM codelist and write na_item.csv."""
    labels = _fetch_codelist("NA_ITEM")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("na_item.csv", ["code", "label_en"], rows)
    print(f"  ✅ na_item.csv: {len(rows)} entries")
    return len(rows)


def update_flags() -> int:
    """Fetch OBS_FLAG codelist and write flags.csv."""
    labels = _fetch_codelist("OBS_FLAG")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("flags.csv", ["flag", "description_en"], rows)
    print(f"  ✅ flags.csv: {len(rows)} entries")
    return len(rows)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("Updating Eurostat codelists from SDMX API...")
    total = 0
    total += update_geo()
    total += update_nace()
    total += update_freq()
    total += update_units()
    total += update_indic_de()
    total += update_c_resid()
    total += update_indic_nrg()
    total += update_indic_sb()
    total += update_levels()
    total += update_clc18()
    total += update_na_item()
    total += update_flags()
    print(f"✔ Done: {total} total entries across 11 codelists")


if __name__ == "__main__":
    main()
