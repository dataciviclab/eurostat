"""DuckDB client for Eurostat data on GCS.

Reads parquet from GCS via lab_connectors.duckdb.gcs_connect.
Results are cached with TtlCache (TTL 120s).

Input validation on slugs, limits, and SQL to prevent injection.
"""

from __future__ import annotations

from typing import Any

from lab_connectors.duckdb import gcs_connect
from lab_connectors.mcp.cache import TtlCache

# ── Registry ─────────────────────────────────────────────────────────────────

GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
GCS_MART = "https://storage.googleapis.com/dataciviclab-mart/eurostat"

DATASETS: dict[str, dict[str, Any]] = {
    "eurostat_gdp_nuts3": {
        "dataflow": "NAMA_10R_3GDP",
        "theme": "Economy / GDP per capita",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "geo"],
        "clean_path": f"{GCS_BASE}/eurostat_gdp_nuts3/*/*.parquet",
        "mart_path": f"{GCS_MART}/eurostat_gdp_nuts3/*/mart_gdp_nuts3.parquet",
        "description": "GDP at current market prices by NUTS 3 region",
    },
    "eurostat_gva_nuts3": {
        "dataflow": "NAMA_10R_3GVA",
        "theme": "Economy / Gross Value Added",
        "nuts_level": 3,
        "dimensions": ["freq", "nace_r2", "unit", "geo"],
        "clean_path": f"{GCS_BASE}/eurostat_gva_nuts3/*/*.parquet",
        "mart_path": f"{GCS_MART}/eurostat_gva_nuts3/*/mart_gva_nuts3.parquet",
        "description": "Gross Value Added by NUTS 3 region and NACE sector",
    },
    "eurostat_crime_nuts3": {
        "dataflow": "CRIM_GEN",
        "theme": "Crime / Recorded offences",
        "nuts_level": 3,
        "dimensions": ["freq", "iccs", "unit", "geo"],
        "clean_path": f"{GCS_BASE}/eurostat_crime_nuts3/*/*.parquet",
        "mart_path": f"{GCS_MART}/eurostat_crime_nuts3/*/mart_crime_nuts3.parquet",
        "description": "Recorded crimes by NUTS 3 region and ICCS category",
    },
    "eurostat_pop_nuts3": {
        "dataflow": "DEMO_R_D2JAN",
        "theme": "Demography / Population",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "sex", "age", "geo"],
        "clean_path": f"{GCS_BASE}/eurostat_pop_nuts3/*/*.parquet",
        "mart_path": f"{GCS_MART}/eurostat_pop_nuts3/*/mart_pop_nuts3.parquet",
        "description": "Population on 1 January by NUTS 3 region, sex and age",
    },
}

VALID_SLUGS: set[str] = set(DATASETS.keys())

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
    "ITC1": "Piemonte",
    "ITC2": "Valle d'Aosta",
    "ITC3": "Liguria",
    "ITC4": "Lombardia",
    "ITH1": "Bolzano",
    "ITH2": "Trento",
    "ITH3": "Veneto",
    "ITH4": "Friuli-Venezia Giulia",
    "ITH5": "Emilia-Romagna",
    "ITI1": "Toscana",
    "ITI2": "Umbria",
    "ITI3": "Marche",
    "ITI4": "Lazio",
    "ITF1": "Abruzzo",
    "ITF2": "Molise",
    "ITF3": "Campania",
    "ITF4": "Puglia",
    "ITF5": "Basilicata",
    "ITF6": "Calabria",
    "ITG1": "Sicilia",
    "ITG2": "Sardegna",
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

    The SQL should be a SELECT statement. The parquet file is aliased
    as 'data' — reference it in FROM data or FROM read_parquet('...').

    Examples:
      SELECT year, geo, value FROM data WHERE geo LIKE 'IT%' LIMIT 10
      SELECT geo, AVG(value) FROM data WHERE unit='EUR_HAB' GROUP BY geo
      SELECT COUNT(*) AS total_rows FROM data

    Warning: SQL is not fully sanitized beyond basic guards.
    This tool is designed for trusted users only.
    """
    slug = _validate_slug(slug)
    limit = _validate_limit(limit)
    path = DATASETS[slug]["clean_path"]

    # Guards
    sql_stripped = sql.strip()
    if not sql_stripped.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    if ";" in sql_stripped:
        raise ValueError("Multi-statement queries are not supported")

    # Inject parquet path: replace FROM data with the actual read
    full_sql = sql_stripped.replace(
        "FROM data",
        f"FROM read_parquet('{path}') AS data",
        1,
    )
    full_sql = f"{full_sql.rstrip(';')} LIMIT {limit}"

    columns, rows = _query(full_sql, path)
    return [dict(zip(columns, row)) for row in rows]


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
