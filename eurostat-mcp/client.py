"""DuckDB client for Eurostat data on GCS.

Reads parquet from GCS via lab_connectors.duckdb.gcs_connect.
Results are cached with TtlCache (TTL 120s).

Input validation: slug allowlist, SQL guard (no read_*, filesystem, DDL),
limit capping (max 500 rows), no multi-statement.
"""

from __future__ import annotations

import csv
import logging
import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from lab_connectors.duckdb.core import gcs_connect
from lab_connectors.mcp.cache import TtlCache

logger = logging.getLogger(__name__)

# ── GCS paths (multi-year parquet, no year in path) ─────────────────────────

GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_FALLBACK_YEAR: str | None = None


_YEAR_CACHE: str | None = None


def _parquet_url(slug: str) -> str:
    """Build the GCS URL for a dataset slug.

    The toolkit produces files named {slug}_{year}_clean.parquet.
    We probe for the current year, then previous years as fallback.
    """
    global _YEAR_CACHE
    if _YEAR_CACHE:
        year = _YEAR_CACHE
    else:
        this_year = date.today().year
        for y in range(this_year, this_year - 3, -1):
            probe = f"{GCS_BASE}/{slug}/{slug}_{y}_clean.parquet"
            try:
                req = urllib.request.Request(probe, method="HEAD")
                resp = urllib.request.urlopen(req, timeout=2)
                if resp.status == 200:
                    _YEAR_CACHE = str(y)
                    year = str(y)
                    break
            except Exception:
                continue
        else:
            year = str(this_year)
    return f"{GCS_BASE}/{slug}/{slug}_{year}_clean.parquet"


# ── Registry (auto-discovered from datasets/*/dataset.yml) ───────────────────

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATASETS_DIR = _REPO_ROOT / "datasets"

DATASETS: dict[str, dict[str, Any]] = {}
for _entry in sorted(_DATASETS_DIR.iterdir()):
    _yml = _entry / "dataset.yml"
    if not _yml.exists():
        continue
    _data = yaml.safe_load(_yml.read_text())
    _slug = ((_data or {}).get("dataset", {}) or {}).get("name", "")
    if not _slug:
        continue
    _reg = (_data or {}).get("registry", {}) or {}
    DATASETS[_slug] = {
        "dataflow": _reg.get("dataflow", ""),
        "theme": _reg.get("theme", ""),
        "nuts_level": _reg.get("nuts_level", 3),
        "dimensions": list(_reg.get("dimensions", [])),
        "description": _reg.get("description", _slug),
    }

# Add computed parquet_url to each dataset (can be overridden for tests)
for _slug in list(DATASETS):
    DATASETS[_slug]["parquet_url"] = _parquet_url(_slug)

VALID_SLUGS: set[str] = set(DATASETS.keys())

# ── SQL guard — blocked keywords (case-insensitive match) ────────────────────

_BLOCKED_KEYWORDS = re.compile(
    r"\b(read_csv|read_csv_auto|read_parquet|read_json|read_text|"
    r"copy|import|export|"
    r"create|drop|alter|insert|update|delete|"
    r"attach|detach|call|load|install)\b",
    re.IGNORECASE,
)

_FILESYSTEM_PATTERNS = re.compile(
    r"['\"]/(etc|tmp|var|home|dev|proc|usr|bin|sbin|boot|root|opt|run)/|"
    r"['\"][a-zA-Z]:\\|"
    r"file://",
    re.IGNORECASE,
)

# ── Codelists ────────────────────────────────────────────────────────────────
# Small codelists are embedded for speed and zero-dependency operation.
# For larger datasets (geo, nace_r2), the CSV files in codelists/ are the
# canonical source — data is loaded at import time to avoid file-based drift.

CODELISTS: dict[str, dict[str, str]] = {
    "freq": {
        "A": "Annual",
        "M": "Monthly",
        "Q": "Quarterly",
        "S": "Half-yearly",
    },
    "unit": {
        "EUR_HAB": "EUR per inhabitant",
        "MIO_EUR": "Million EUR",
        "CP_MEUR": "Current prices (million EUR)",
        "NR": "Number",
        "PPS_HAB": "PPS per inhabitant",
    },
    "flag": {
        "b": "Break in time series",
        "d": "Definition differs",
        "e": "Estimated",
        "p": "Provisional",
        "u": "Low reliability",
    },
}


def _load_nuts_italy() -> dict[str, str]:
    """Load Italian NUTS2 regions from codelists/geo.csv (canonical source).

    Filters for Italian NUTS2 entries and excludes the ITZZ placeholder
    (special 'outside' code not corresponding to an actual region).
    """
    geo_path = _REPO_ROOT / "codelists" / "geo.csv"
    if not geo_path.exists():
        return {}  # graceful fallback — tests may run from a non-repo env
    result: dict[str, str] = {}
    with open(geo_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row.get("code", "")
            level = row.get("nuts_level", "")
            if code.startswith("IT") and level == "NUTS2" and code != "ITZZ":
                result[code] = row.get("label_en", code)
    return result


NUTS_ITALY: dict[str, str] = _load_nuts_italy()

_cache = TtlCache(ttl_seconds=120)

# ── Input validation ─────────────────────────────────────────────────────────


def _validate_slug(slug: str) -> str:
    if slug not in VALID_SLUGS:
        raise ValueError(
            f"Unknown dataset slug: '{slug}'. "
            f"Available: {', '.join(sorted(VALID_SLUGS))}"
        )
    return slug


def _validate_limit(limit: int) -> int:
    limit = int(limit)
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500
    return limit


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments (-- and /* */) from the start of a query."""
    # Remove single-line comments (-- ...)
    sql = re.sub(r"^--.*$", "", sql, flags=re.MULTILINE)
    # Remove block comments (/* ... */)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def _validate_sql_safe(sql: str) -> None:
    """Reject SQL containing dangerous functions or filesystem paths."""
    # Strip comments before checking the starting keyword
    stripped = _strip_sql_comments(sql).upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        raise ValueError(
            "Only SELECT queries (or WITH...SELECT CTEs) are allowed. "
            "Your query must start with SELECT or WITH."
        )
    if ";" in sql:
        raise ValueError("Multi-statement queries are not allowed")
    if _BLOCKED_KEYWORDS.search(sql):
        raise ValueError(
            "SQL contains blocked keywords (read_*, DDL, DML, filesystem I/O). "
            "Only simple SELECT queries referencing 'data' are allowed."
        )
    if _FILESYSTEM_PATTERNS.search(sql):
        raise ValueError("SQL contains filesystem path references")


# ── Query execution ──────────────────────────────────────────────────────────


def _query(sql: str, path: str) -> tuple[list[str], list[tuple]]:
    """Execute SQL against a parquet file on GCS, return (columns, rows)."""
    cache_key = f"{path}:::{sql}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    with gcs_connect(path) as con:
        rel = con.sql(sql)
        columns = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        result = (columns, rows)
        _cache.set(cache_key, result)
        return result


# ── Facts generation ─────────────────────────────────────────────────────────

# Dimension patterns: column suffixes that indicate categorical breakdowns
_SYMBOLS: dict[str, str] = {
    "EUR_HAB": "€",
    "MIO_EUR": "€",
    "CP_MEUR": "€",
    "PYP_MEUR": "€",
    "MIO_NAC": "€",
    "PPS_EU27_2020": "€",
    "PPS_EU27_2020_HAB": "€",
    "PPS_HAB_EU27_2020": "€",
    "PER_KM2": "ab./km²",
}
_NUTS_RANKING_LEVELS = "('NUTS2', 'NUTS3')"
_NUTS_TREND_LEVEL = "'NUTS2'"  # single level for consistent year-over-year trends

# Extra dimension defaults: when a dataset has categorical columns beyond
# the primary filter (unit/indic_de), we add WHERE clauses to avoid
# averaging across unrelated categories (e.g. mixing NACE sectors, sexes).
_EXTRA_DIM_DEFAULTS: dict[str, str] = {
    "sex": "'T'",
    "age": "'TOTAL'",
    "nace_r2": "'TOTAL'",
    "wstatus": "'EMP'",
    "iccs": "'TOTAL'",
    "indic_de": None,  # handled separately via primary_indicator
}


@dataclass
class _ParquetStats:
    """Summary stats read from a parquet in a single GCS connection."""

    columns: list[dict[str, str]]
    col_names: set[str]
    row_count: int | None
    year_min: int | None
    year_max: int | None
    units: list[str]
    indicators: list[str]


def _get_parquet_stats(path: str) -> _ParquetStats | None:
    """Read schema + summary stats from a parquet (single connection).

    Consolidates DESCRIBE, COUNT, MIN/MAX year, DISTINCT unit/indic_de
    into one GCS call instead of 5 separate connections.
    """
    try:
        with gcs_connect(path) as con:
            # Schema
            schema = con.sql(
                "DESCRIBE SELECT * FROM read_parquet(?::VARCHAR)",
                params=[path],
            ).fetchall()
            columns = [{"name": r[0], "type": r[1]} for r in schema]
            col_names = {c["name"] for c in columns}

            # Row count
            row = con.sql(
                "SELECT COUNT(*) FROM read_parquet(?::VARCHAR)",
                params=[path],
            ).fetchone()
            row_count = int(row[0]) if row else None

            # Year range
            year_min, year_max = None, None
            if "year" in col_names:
                r = con.sql(
                    "SELECT MIN(year), MAX(year) FROM read_parquet(?::VARCHAR)",
                    params=[path],
                ).fetchone()
                if r and r[0] is not None:
                    year_min, year_max = int(r[0]), int(r[1])

            # Available units
            units: list[str] = []
            if "unit" in col_names:
                rows = con.sql(
                    "SELECT DISTINCT unit FROM read_parquet(?::VARCHAR) "
                    "WHERE unit IS NOT NULL ORDER BY 1 LIMIT 10",
                    params=[path],
                ).fetchall()
                units = [r[0] for r in rows]

            # Available indicators (demographic balance)
            indicators: list[str] = []
            if "indic_de" in col_names:
                rows = con.sql(
                    "SELECT DISTINCT indic_de FROM read_parquet(?::VARCHAR) "
                    "WHERE indic_de IS NOT NULL ORDER BY 1 LIMIT 15",
                    params=[path],
                ).fetchall()
                indicators = [r[0] for r in rows]

            return _ParquetStats(
                columns=columns,
                col_names=col_names,
                row_count=row_count,
                year_min=year_min,
                year_max=year_max,
                units=units,
                indicators=indicators,
            )
    except Exception as exc:
        logger.warning("parquet stats query failed: %s", exc)
        return None


def _pick_primary_unit(stats: _ParquetStats) -> str | None:
    """Pick the best unit for facts from available units.

    Prefers per-capita measures (EUR_HAB, PPS_*) over aggregates (MIO_EUR, NR).
    Returns None if no unit column exists.
    """
    if not stats.units:
        return None
    preferences = [
        "EUR_HAB",
        "PPS_EU27_2020_HAB",
        "PPS_HAB_EU27_2020",
        "PER_KM2",
        "CP_MEUR",
        "PYP_MEUR",
        "MIO_EUR",
        "THS",
        "NR",
    ]
    for pref in preferences:
        if pref in stats.units:
            return pref
    return stats.units[0]


def _pick_primary_indicator(stats: _ParquetStats) -> str | None:
    """Pick the headline indicator for demographic datasets."""
    if not stats.indicators:
        return None
    preferences = ["NATGROWRT", "GROWRT", "CNMIGRATRT", "JAN", "GROW"]
    for pref in preferences:
        if pref in stats.indicators:
            return pref
    return stats.indicators[0]


def _build_extra_dim_where(col_names: set[str], primary_dim_col: str | None) -> str:
    """Build AND ... clauses to filter extra dimensions to their default values.

    Skips the column used as primary filter (unit/indic_de) and any column
    not present in the dataset schema.
    Returns empty string when no extra dims need filtering.
    """
    parts: list[str] = []
    for dim_col, default_val in _EXTRA_DIM_DEFAULTS.items():
        if dim_col == primary_dim_col:
            continue  # already filtered by primary_dim_filter
        if default_val is None:
            continue  # handled separately
        if dim_col in col_names:
            parts.append(f"{dim_col} = {default_val}")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _format_value(val: float, unit: str | None = None) -> str:
    """Format a numeric value with appropriate symbol based on unit."""
    symbol = _SYMBOLS.get(unit, "") if unit else ""
    if symbol:
        return f"{symbol} {val:,.0f}"
    # Plain number — no symbol prefix
    return f"{val:,.0f}"


_FACT_CATEGORY_DIMS: dict[str, str] = {
    "sex": "Sex",
    "nace_r2": "NACE sector",
    "iccs": "ICCS crime category",
    "indic_de": "Demographic indicator",
    "wstatus": "Working status",
}


def _schema_facts(col_names: set[str], meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate facts from schema inspection only (no data queries)."""
    facts_list: list[dict[str, Any]] = []

    facts_list.append(
        {
            "label": "Data type",
            "value": "NUTS{} regional".format(meta.get("nuts_level", "?")),
        }
    )

    if "year" in col_names:
        facts_list.append(
            {
                "label": "Temporal coverage",
                "value": "yes — query BY year column for trends",
            }
        )

    if "geo" in col_names:
        facts_list.append(
            {
                "label": "Regional coverage",
                "value": "multi-country EU (filter BY geo code, use geo_label_en for names)",
            }
        )

    if "unit" in col_names:
        facts_list.append(
            {
                "label": "Units available",
                "value": "multiple — specify unit= in WHERE clause",
            }
        )

    if "sex" in col_names:
        facts_list.append(
            {
                "label": "Sex breakdown",
                "value": "M, F, T (Male, Female, Total)",
            }
        )

    # Identify categorical dimensions from column names
    for dim_col, dim_label in _FACT_CATEGORY_DIMS.items():
        if dim_col in col_names:
            facts_list.append(
                {
                    "label": f"Breakdown by {dim_label}",
                    "value": f"available — filter/split BY {dim_col} column",
                }
            )

    if "flag" in col_names:
        facts_list.append(
            {
                "label": "Quality flags",
                "value": "yes — use flag_desc_en for meaning",
            }
        )

    return facts_list


def _build_trend_facts(
    con: Any,  # duckdb.DuckDBPyConnection
    path: str,
    unit_filter: str | None,
    unit_col: str | None,
    limit: int,
    extra_dim_where: str = "",
) -> list[dict[str, Any]]:
    """Build facts showing year-over-year trend."""
    facts_list: list[dict[str, Any]] = []
    try:
        # Detect columns to build the right query
        cols = con.sql(
            "DESCRIBE SELECT * FROM read_parquet(?::VARCHAR)",
            params=[path],
        ).fetchall()
        col_names = {r[0] for r in cols}

        unit_filter_escaped = unit_filter.replace("'", "''") if unit_filter else None
        unit_where = (
            f"AND {unit_col} = '{unit_filter_escaped}'"
            if (unit_filter and unit_col)
            else ""
        )

        # Trend level: single NUTS level for consistent year-over-year trends
        nuts_trend_where = f"AND nuts_level = {_NUTS_TREND_LEVEL}"

        if "nuts_parent_label_en" in col_names:
            # Italy average (NUTS2 only, consistent level across all years)
            it_sql = f"""
                SELECT year, ROUND(AVG(value), 0) AS avg_val
                FROM read_parquet(?::VARCHAR)
                WHERE geo LIKE 'IT%' AND value IS NOT NULL {nuts_trend_where} {unit_where} {extra_dim_where}
                GROUP BY year ORDER BY year DESC LIMIT {limit}
            """
            it_rows = con.sql(it_sql, params=[path]).fetchall()
            if it_rows:
                years_vals = [
                    f"{r[0]}: {_format_value(float(r[1]), unit_filter)}"
                    for r in reversed(it_rows)
                ]
                facts_list.append(
                    {
                        "label": "Italy average (latest years)",
                        "value": " → ".join(years_vals),
                        "italy_only": True,
                    }
                )

            # EU average (NUTS2 only, consistent level across all years)
            eu_sql = f"""
                SELECT year, ROUND(AVG(value), 0) AS avg_val
                FROM read_parquet(?::VARCHAR)
                WHERE nuts_level = {_NUTS_TREND_LEVEL} AND value IS NOT NULL {unit_where} {extra_dim_where}
                GROUP BY year ORDER BY year DESC LIMIT {limit}
            """
            eu_rows = con.sql(eu_sql, params=[path]).fetchall()
            if eu_rows:
                years_vals = [
                    f"{r[0]}: {_format_value(float(r[1]), unit_filter)}"
                    for r in reversed(eu_rows)
                ]
                facts_list.append(
                    {
                        "label": "EU NUTS2 average (latest years)",
                        "value": " → ".join(years_vals),
                    }
                )
    except Exception as exc:
        logger.warning("trend facts query failed: %s", exc)
    return facts_list


def _build_ranking_facts(
    con: Any,
    path: str,
    unit_filter: str | None,
    unit_col: str | None,
    limit: int,
    year: int | None = None,
    extra_dim_where: str = "",
) -> list[dict[str, Any]]:
    """Build facts ranking regions by value (top and bottom).

    Filters to NUTS2/NUTS3 level only (avoids mixing countries with regions).
    Applies extra_dim_where to avoid duplicating regions across categories.
    """
    facts_list: list[dict[str, Any]] = []
    try:
        unit_filter_escaped = unit_filter.replace("'", "''") if unit_filter else None
        unit_where = (
            f"AND {unit_col} = '{unit_filter_escaped}'"
            if (unit_filter and unit_col)
            else ""
        )

        year_where = f"AND year = {year}" if year else ""
        nuts_ranking_where = f"AND nuts_level IN {_NUTS_RANKING_LEVELS}"

        top_sql = f"""
            SELECT geo_label_en, ROUND(value, 0) AS val
            FROM read_parquet(?::VARCHAR)
            WHERE value IS NOT NULL AND geo_label_en IS NOT NULL
              {nuts_ranking_where} {unit_where} {extra_dim_where} {year_where}
            ORDER BY value DESC LIMIT {limit}
        """
        top_rows = con.sql(top_sql, params=[path]).fetchall()
        if top_rows:
            items = ", ".join(
                f"{r[0]}: {_format_value(float(r[1]), unit_filter)}" for r in top_rows
            )
            facts_list.append(
                {
                    "label": f"Top {limit} regions",
                    "value": items,
                    "year": year,
                }
            )

        bottom_sql = f"""
            SELECT geo_label_en, ROUND(value, 0) AS val
            FROM read_parquet(?::VARCHAR)
            WHERE value IS NOT NULL AND geo_label_en IS NOT NULL
              {nuts_ranking_where} {unit_where} {extra_dim_where} {year_where}
            ORDER BY value ASC LIMIT {limit}
        """
        bottom_rows = con.sql(bottom_sql, params=[path]).fetchall()
        if bottom_rows:
            items = ", ".join(
                f"{r[0]}: {_format_value(float(r[1]), unit_filter)}"
                for r in bottom_rows
            )
            facts_list.append(
                {
                    "label": f"Bottom {limit} regions",
                    "value": items,
                    "year": year,
                }
            )
    except Exception as exc:
        logger.warning("ranking facts query failed: %s", exc)
    return facts_list


def _collect_detail_facts(
    con: Any,
    path: str,
    col_names: set[str],
    primary_dim_filter: str | None,
    primary_dim_col: str | None,
    limit: int,
    latest_year: int | None,
    year_max: int | None,
) -> list[dict[str, Any]]:
    """Run data queries for rankings and trends (detail mode).

    Uses the already-open connection *con* — no additional GCS calls.
    Returns (facts_list, extra_dim_where, has_analysis) where has_analysis
    is True only when there are actual ranking or trend facts.
    """
    facts_list: list[dict[str, Any]] = []
    has_analysis = False

    if latest_year:
        facts_list.append(
            {
                "label": "Latest year",
                "value": str(latest_year),
            }
        )

    # Build extra dimension filters (sex='T', nace_r2='TOTAL', etc.)
    extra_dim_where = _build_extra_dim_where(col_names, primary_dim_col)

    if "geo" in col_names:
        ranking_year = latest_year or year_max
        ranking_facts = _build_ranking_facts(
            con,
            path,
            primary_dim_filter,
            primary_dim_col,
            limit,
            ranking_year,
            extra_dim_where,
        )
        facts_list.extend(ranking_facts)
        if ranking_facts:
            has_analysis = True

        if "year" in col_names:
            trend_facts = _build_trend_facts(
                con,
                path,
                primary_dim_filter,
                primary_dim_col,
                limit,
                extra_dim_where,
            )
            facts_list.extend(trend_facts)
            if trend_facts:
                has_analysis = True

    return facts_list, extra_dim_where, has_analysis


def facts(
    dataset: str | None = None,
    detail: bool = False,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Generate facts from datasets by inspecting schemas and running queries.

    Consolidates parquet stats into a single GCS connection per dataset,
    then opens a second connection only when detail=True for ranking/trend queries.

    Args:
        dataset: Optional slug to filter a single dataset.
        detail: If True, runs actual data queries for trends and rankings.
        limit: Max items per fact list (top/bottom regions, years, etc.).
    """
    limit = _validate_limit(limit)
    slugs = [dataset] if dataset else sorted(DATASETS.keys())
    _validate_slug(slugs[0]) if dataset else None

    results: list[dict[str, Any]] = []

    for slug in slugs:
        meta = DATASETS.get(slug, {})
        path = meta.get("parquet_url")
        if not path:
            continue

        entry: dict[str, Any] = {
            "dataset": slug,
            "theme": meta.get("theme", ""),
            "description": meta.get("description", ""),
            "dimensions": meta.get("dimensions", []),
            "nuts_level": meta.get("nuts_level", 3),
            "dataflow": meta.get("dataflow", ""),
            "summary": {},
            "facts": [],
        }

        try:
            # Single GCS call for all parquet stats
            stats = _get_parquet_stats(path)
            if stats is None:
                continue

            entry["columns"] = stats.columns
            entry["schema_facts"] = _schema_facts(stats.col_names, meta)

            # Summary
            year_str = (
                f"{stats.year_min}–{stats.year_max}" if stats.year_min else "unknown"
            )
            row_str = f"{stats.row_count:,}" if stats.row_count else "unknown"
            entry["summary"] = {
                "rows": row_str,
                "years": year_str,
                "dimensions": meta.get("dimensions", []),
            }
            if stats.units:
                entry["summary"]["units"] = stats.units
            if stats.indicators:
                entry["summary"]["indicators"] = stats.indicators

            entry["facts"].append({"label": "Total rows", "value": row_str})
            entry["facts"].append({"label": "Years covered", "value": year_str})

            # Detect primary unit/indicator
            unit_col = "unit" if "unit" in stats.col_names else None
            primary_dim_col: str | None = None
            primary_dim_filter: str | None = None

            if unit_col:
                pu = _pick_primary_unit(stats)
                if pu:
                    primary_dim_filter = pu
                    primary_dim_col = unit_col
                    entry["facts"].append({"label": "Primary unit", "value": pu})

            if not primary_dim_filter and "indic_de" in stats.col_names:
                pi = _pick_primary_indicator(stats)
                if pi:
                    primary_dim_filter = pi
                    primary_dim_col = "indic_de"

            # Indicator list fact
            if stats.indicators:
                entry["facts"].append(
                    {
                        "label": "Available indicators",
                        "value": ", ".join(stats.indicators),
                    }
                )

            # Data queries (detail mode only) — second GCS connection
            if detail and primary_dim_filter and primary_dim_col:
                with gcs_connect(path) as con:
                    detail_facts, extra_dim_where, has_analysis = _collect_detail_facts(
                        con,
                        path,
                        stats.col_names,
                        primary_dim_filter,
                        primary_dim_col,
                        limit,
                        stats.year_max,
                        stats.year_max,
                    )
                    if extra_dim_where:
                        entry["summary"]["extra_dim_filters"] = extra_dim_where.strip(
                            " AND "
                        )
                    if detail_facts:
                        entry["facts"].extend(detail_facts)
                    if has_analysis:
                        entry["summary"]["has_trend"] = True

        except Exception as exc:
            entry["error"] = str(exc)

        results.append(entry)

    return results


# ── Tool implementations ─────────────────────────────────────────────────────


def list_datasets() -> list[dict[str, Any]]:
    """Return the list of available datasets with metadata."""
    result = []
    for slug, meta in sorted(DATASETS.items()):
        result.append(
            {
                "slug": slug,
                "dataflow": meta["dataflow"],
                "theme": meta["theme"],
                "nuts_level": meta["nuts_level"],
                "dimensions": meta["dimensions"],
                "description": meta["description"],
            }
        )
    return result


def query(
    slug: str,
    sql: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Run a SQL query on a specific dataset.

    The SQL must be a SELECT referencing 'data' as the source table.
    The parquet file is injected as 'data' automatically.

    Examples:
      SELECT year, geo, value FROM data WHERE geo LIKE 'IT%' ORDER BY value DESC
      SELECT geo, AVG(value) AS avg_gdp FROM data WHERE unit='EUR_HAB' GROUP BY geo
      SELECT COUNT(*) AS total FROM data

    Forbidden: read_* functions, filesystem paths, DDL/DML, multi-statement.
    """
    slug = _validate_slug(slug)
    _validate_sql_safe(sql)

    path = DATASETS[slug].get("parquet_url") or _parquet_url(slug)
    limit = _validate_limit(limit)

    # Replace FROM data (case-insensitive) with parquet read, first occurence only
    from_data = re.compile(r"\bfrom\s+data\b", re.IGNORECASE)
    if not from_data.search(sql):
        raise ValueError(
            "SQL must reference 'FROM data'. "
            "Example: SELECT year, value FROM data WHERE geo LIKE 'IT%'"
        )

    resolved_sql = from_data.sub(f"FROM read_parquet('{path}') AS data", sql, count=1)

    # Remove user's LIMIT if present — we apply our own
    resolved_sql = re.sub(r"\s+LIMIT\s+\d+(\s*;?\s*)$", "", resolved_sql, count=1)

    full_sql = f"SELECT * FROM ({resolved_sql}) AS _q LIMIT {limit}"

    columns, rows = _query(full_sql, path)
    return [dict(zip(columns, row)) for row in rows]


def describe_dataset(slug: str, dimension_limit: int = 20) -> dict[str, Any]:
    """Return schema, row count, year range and dimension values for a dataset.

    Args:
        slug: Dataset slug (e.g. eurostat_gdp_nuts3).
        dimension_limit: Max distinct values shown per dimension (default 20).
                         Use 0 for no limit (may return large responses).
    """
    slug = _validate_slug(slug)
    path = DATASETS[slug].get("parquet_url") or _parquet_url(slug)
    meta = DATASETS[slug]

    with gcs_connect(path) as con:
        # Schema
        schema = con.sql(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
        columns_def = [
            {"name": r[0], "type": r[1], "nullable": r[2] == "YES"} for r in schema
        ]

        # Row count
        count = con.sql(f"SELECT COUNT(*) FROM read_parquet('{path}')").fetchone()[0]

        # Year range
        year_range: dict[str, int | None] = {"min": None, "max": None}
        try:
            r = con.sql(
                f"SELECT MIN(year), MAX(year) FROM read_parquet('{path}')"
            ).fetchone()
            year_range = {"min": r[0], "max": r[1]}
        except Exception:
            pass

        # Dimension values (from registry dimensions)
        dimensions: dict[str, dict[str, Any]] = {}
        for dim in meta.get("dimensions", []):
            label_col = f"{dim}_label_en"
            try:
                rows = con.sql(
                    f'SELECT DISTINCT "{dim}" AS code, "{label_col}" AS label '
                    f"FROM read_parquet('{path}') "
                    f'WHERE "{dim}" IS NOT NULL ORDER BY 1'
                ).fetchall()
                total = len(rows)
                limit = dimension_limit if dimension_limit > 0 else total
                truncated = total > limit
                items = [{"code": r[0], "label": r[1]} for r in rows[:limit]]
                dimensions[dim] = {
                    "values": items,
                    "total_count": total,
                    "truncated": truncated,
                    "limit": limit,
                }
            except Exception:
                # Fallback: code only (no label column)
                try:
                    rows = con.sql(
                        f"SELECT DISTINCT \"{dim}\" FROM read_parquet('{path}') "
                        f'WHERE "{dim}" IS NOT NULL ORDER BY 1'
                    ).fetchall()
                    total = len(rows)
                    limit = dimension_limit if dimension_limit > 0 else total
                    truncated = total > limit
                    items = [{"code": r[0]} for r in rows[:limit]]
                    dimensions[dim] = {
                        "values": items,
                        "total_count": total,
                        "truncated": truncated,
                        "limit": limit,
                    }
                except Exception:
                    dimensions[dim] = {
                        "values": [],
                        "total_count": 0,
                        "truncated": False,
                        "limit": dimension_limit,
                    }

    return {
        "slug": slug,
        "dataflow": meta["dataflow"],
        "theme": meta["theme"],
        "nuts_level": meta["nuts_level"],
        "description": meta["description"],
        "columns": columns_def,
        "row_count": count,
        "year_range": year_range,
        "dimensions": dimensions,
    }


def get_codelist(codelist_id: str) -> dict[str, Any]:
    """Resolve a codelist by ID (freq, unit, flag, nuts_italy)."""
    codelist_id = codelist_id.lower().strip()

    if codelist_id == "nuts_italy":
        return {
            "codelist": "nuts_italy",
            "description": "Italian NUTS2 regions",
            "entries": NUTS_ITALY,
        }

    cl = CODELISTS.get(codelist_id)
    if cl is None:
        raise ValueError(
            f"Unknown codelist: '{codelist_id}'. "
            f"Available: freq, unit, flag, nuts_italy"
        )
    return {
        "codelist": codelist_id,
        "description": {
            "freq": "Frequency (A=Annual, M=Monthly, Q=Quarterly)",
            "unit": "Unit of measure",
            "flag": "SDMX quality flags",
        }.get(codelist_id, ""),
        "entries": cl,
    }
