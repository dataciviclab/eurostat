"""DuckDB client for Eurostat data on GCS.

Reads parquet from GCS via lab_connectors.duckdb.gcs_connect.
Results are cached with TtlCache (TTL 120s).

Input validation: slug allowlist, SQL guard (no read_*, filesystem, DDL),
limit capping (max 500 rows), no multi-statement.
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date
from typing import Any

from lab_connectors.duckdb import gcs_connect
from lab_connectors.mcp.cache import TtlCache

# ── GCS paths (multi-year parquet, no year in path) ─────────────────────────

GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_FALLBACK_YEAR: str | None = None


def _parquet_url(slug: str) -> str:
    """Build the GCS URL for a dataset slug.

    Prefers the no-year path (multi-year parquet). Falls back to
    year-based path for backward compat during migration.
    """
    url = f"{GCS_BASE}/{slug}/{slug}_clean.parquet"
    # Probe the no-year URL; if probing fails (slow GCS), still use the
    # no-year URL — that's where the current data lives.
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=2)
        if resp.status == 200:
            return url
    except Exception:
        pass
    # Probing timed out — no-year URL is the only valid one after migration
    return url


# ── Registry ─────────────────────────────────────────────────────────────────

DATASETS: dict[str, dict[str, Any]] = {
    "eurostat_gdp_nuts3": {
        "dataflow": "NAMA_10R_3GDP",
        "theme": "Economy / GDP per capita",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "geo"],
        "description": "GDP at current market prices by NUTS 3 region",
    },
    "eurostat_gva_nuts3": {
        "dataflow": "NAMA_10R_3GVA",
        "theme": "Economy / Gross Value Added",
        "nuts_level": 3,
        "dimensions": ["freq", "nace_r2", "unit", "geo"],
        "description": "Gross Value Added by NUTS 3 region and NACE sector",
    },
    "eurostat_crime_nuts3": {
        "dataflow": "CRIM_GEN",
        "theme": "Crime / Recorded offences",
        "nuts_level": 3,
        "dimensions": ["freq", "iccs", "unit", "geo"],
        "description": "Recorded crimes by NUTS 3 region and ICCS category",
    },
    "eurostat_pop_nuts3": {
        "dataflow": "DEMO_R_D2JAN",
        "theme": "Demography / Population",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "sex", "age", "geo"],
        "description": "Population on 1 January by NUTS 3 region, sex and age",
    },
}

# Each dataset also carries a parquet_url (computed, can be overridden for tests)
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

# ── Codelists (embedded, no GCS dependency) ──────────────────────────────────

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

NUTS_ITALY: dict[str, str] = {
    "ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria",
    "ITC4": "Lombardia",
    "ITH1": "Bolzano", "ITH2": "Trento", "ITH3": "Veneto",
    "ITH4": "Friuli-Venezia Giulia", "ITH5": "Emilia-Romagna",
    "ITI1": "Toscana", "ITI2": "Umbria", "ITI3": "Marche", "ITI4": "Lazio",
    "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania",
    "ITF4": "Puglia", "ITF5": "Basilicata", "ITF6": "Calabria",
    "ITG1": "Sicilia", "ITG2": "Sardegna",
}

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
    sql = re.sub(r'^--.*$', '', sql, flags=re.MULTILINE)
    # Remove block comments (/* ... */)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
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


# ── Tool implementations ─────────────────────────────────────────────────────


def list_datasets() -> list[dict[str, Any]]:
    """Return the list of available datasets with metadata."""
    result = []
    for slug, meta in sorted(DATASETS.items()):
        result.append({
            "slug": slug,
            "dataflow": meta["dataflow"],
            "theme": meta["theme"],
            "nuts_level": meta["nuts_level"],
            "dimensions": meta["dimensions"],
            "description": meta["description"],
        })
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

    resolved_sql = from_data.sub(
        f"FROM read_parquet('{path}') AS data", sql, count=1
    )

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
            {"name": r[0], "type": r[1], "nullable": r[2] == "YES"}
            for r in schema
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
                    f"SELECT DISTINCT \"{dim}\" AS code, \"{label_col}\" AS label "
                    f"FROM read_parquet('{path}') "
                    f"WHERE \"{dim}\" IS NOT NULL ORDER BY 1"
                ).fetchall()
                total = len(rows)
                limit = dimension_limit if dimension_limit > 0 else total
                truncated = total > limit
                items = [
                    {"code": r[0], "label": r[1]} for r in rows[:limit]
                ]
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
                        f"WHERE \"{dim}\" IS NOT NULL ORDER BY 1"
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
