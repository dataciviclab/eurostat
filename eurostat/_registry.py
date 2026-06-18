"""Shared dataset registry for Eurostat CLI.

Central place for GCS paths and dataset definitions.
"""

from __future__ import annotations

GCS_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_CURRENT_YEAR = "2024"

DATASETS: dict[str, str] = {
    "eurostat_gdp_nuts3": (
        f"{GCS_BASE}/eurostat_gdp_nuts3/{_CURRENT_YEAR}"
        f"/eurostat_gdp_nuts3_{_CURRENT_YEAR}_clean.parquet"
    ),
    "eurostat_gva_nuts3": (
        f"{GCS_BASE}/eurostat_gva_nuts3/{_CURRENT_YEAR}"
        f"/eurostat_gva_nuts3_{_CURRENT_YEAR}_clean.parquet"
    ),
    "eurostat_crime_nuts3": (
        f"{GCS_BASE}/eurostat_crime_nuts3/{_CURRENT_YEAR}"
        f"/eurostat_crime_nuts3_{_CURRENT_YEAR}_clean.parquet"
    ),
    "eurostat_pop_nuts3": (
        f"{GCS_BASE}/eurostat_pop_nuts3/{_CURRENT_YEAR}"
        f"/eurostat_pop_nuts3_{_CURRENT_YEAR}_clean.parquet"
    ),
}
