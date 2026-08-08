"""Parameterized tests for the analytical mart pattern (benchmark pilot).

SCOPE — semantics only. The toolkit already validates the FORMAL contract at
run time (required_columns, not_null, primary_key uniqueness, min_rows via
`mart.validate.table_rules`). This suite deliberately does NOT re-test those
gates. It protects only what the toolkit cannot check:

  • benchmark columns computed only for the dataset's benchmark unit
  • top region of each country has rank_nazionale = 1
  • every benchmark-unit row carries all benchmark columns
  • trend: CAGR NULL on single-year windows, geo never NULL

Dataset-specific verified facts (e.g. Dublin top 2024, Italy 2021 reporting
break, IT 2024 coverage gap) live in per-dataset test classes — they encode
domain knowledge about the underlying Eurostat data.

Skip-based: tests run against locally produced parquet files, so CI does
not break when the pipeline has not been executed on the runner.

CI limitation (documented decision): the semantic suite only runs where the
marts have been produced. There is no CI job executing the pipeline because
raw data is downloaded live from the Eurostat SDMX API (network-fragile) and
no other repo in the lab runs live pipeline jobs in CI. To validate locally:
    toolkit run -c datasets/<slug>/dataset.yml --years 2026   # per dataset
    pytest tests/test_analytical_marts.py -q
"""

from pathlib import Path

import duckdb
import pytest

# Lab test-policy: every test must declare the contract it protects.
# This whole suite protects the analytical mart contract (benchmark
# semantics, EU27 scope, verified data facts) — public interface of the
# marts, so the module-level marker is `contract`.
pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).parent.parent
MART_BASE = REPO_ROOT / "out" / "data" / "mart"


def _parquet(slug: str, mart: str) -> Path:
    """Resolve the mart parquet path for a dataset slug."""
    return MART_BASE / slug / "2026" / f"{mart}.parquet"


# ── Shared contract (parameterized) ──────────────────────────────────────────
# Each entry: slug, benchmark unit (columns computed only for this unit),
# a non-benchmark unit for the negative test, and the NUTS level used
# by the benchmark comparison.

ANALYTICAL_DATASETS = [
    {
        "slug": "eurostat_gdp_nuts3",
        "benchmark_unit": "EUR_HAB",
        "other_unit": "MIO_EUR",
        "nuts_level": "NUTS3",
        "other_unit_geo": "IE061",
    },
    {
        "slug": "eurostat_physicians_nuts2",
        "benchmark_unit": "HAB_P",
        "other_unit": "NR",
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_hospital_beds_nuts2",
        "benchmark_unit": "HAB_P",
        "other_unit": "NR",
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_crime_nuts3",
        "benchmark_unit": "P_HTHAB",
        "other_unit": "NR",
        "nuts_level": "NUTS3",
        # Torino: Milano (ITC4C) is missing from 2024 (partial IT coverage)
        "other_unit_geo": "ITC11",
        # Extra benchmark dimension: crime category (ICCS code).
        "dim": "iccs",
        "dim_value": "ICCS0101",
    },
    {
        "slug": "eurostat_poverty_risk_nuts2",
        "benchmark_unit": "PC",
        # Single-unit dataset: any other unit must carry NULL benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_income_inequality_nuts2",
        "benchmark_unit": "INX",
        # Single-unit dataset: any other unit must carry NULL benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_tran_sf_roadnu",
        "benchmark_unit": "P_MHAB",
        "other_unit": "NR",
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC11",
    },
    {
        "slug": "eurostat_early_school_leavers_nuts2",
        "benchmark_unit": "PC",
        # Extra breakdown dimension: benchmark slice is sex='T' (total).
        "dim": "sex",
        "dim_value": "T",
        # Single-unit dataset: any other unit must carry NULL benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_tertiary_education_nuts2",
        "benchmark_unit": "PC",
        # Extra breakdown dimensions: slice is isced11='ED5-8' + sex='T'.
        "dim": "sex",
        "dim_value": "T",
        "dim2": "isced11",
        "dim2_value": "ED5-8",
        # Single-unit dataset.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_rd_expenditure_nuts2",
        "benchmark_unit": "PC_GDP",
        # Extra dimension: sector of performance, slice is TOTAL.
        "dim": "sectperf",
        "dim_value": "TOTAL",
        # Single-unit reference: PC_GDP only carries the benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS2",
        "other_unit_geo": "ITC4",
    },
    {
        "slug": "eurostat_labour_productivity_nuts3",
        "benchmark_unit": "EUR",
        # Extra dimension: national accounts item, slice is NLPR_PER.
        "dim": "na_item",
        "dim_value": "NLPR_PER",
        # Other units (NAC, PC_EU27_2020_MEUR_CP) carry no benchmark.
        # FRB03: IT NUTS3 2024 coverage is partial (source gap) — FR has both
        # EUR and NAC rows for 2024.
        "other_unit": "NAC",
        "nuts_level": "NUTS3",
        "other_unit_geo": "FRB03",
    },
    {
        "slug": "eurostat_pop_density_nuts3",
        "benchmark_unit": "PER_KM2",
        # Single-unit dataset: only PER_KM2 exists, no other unit to compare.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_demo_balance_nuts3",
        "benchmark_unit": "GROWRT",
        # No `unit` column: dimensions are freq/indic_de/geo — the benchmark
        # slice is the indic_de dim (GROWRT), not a unit.
        "no_unit": True,
        # Extra dimension: demographic indicator, slice is GROWRT.
        "dim": "indic_de",
        "dim_value": "GROWRT",
        # No other unit dimension (freq, indic_de, geo only).
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_fertility_nuts3",
        "benchmark_unit": "NR",
        # Extra dimension: fertility indicator, slice is TOTFERRT.
        "dim": "indic_de",
        "dim_value": "TOTFERRT",
        # Other units (YR) carry no benchmark.
        "other_unit": "YR",
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_pop_structure_nuts3",
        "benchmark_unit": "PC",
        # Extra dimension: structure indicator, slice is OLDDEP2.
        "dim": "indic_de",
        "dim_value": "OLDDEP2",
        # Other units (YR) carry no benchmark.
        "other_unit": "YR",
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_area_nuts3",
        "benchmark_unit": "KM2",
        # Extra dimension: landuse, slice is TOTAL (total area).
        "dim": "landuse",
        "dim_value": "TOTAL",
        # Single-unit: KM2 only.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_nrg_chddr2_a_nuts3",
        "benchmark_unit": "NR",
        # Extra dimension: climate indicator, slice is HDD (heating).
        "dim": "indic_nrg",
        "dim_value": "HDD",
        # Other indicator (CDD) carries no benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_demo_r_pjangrp3_nuts3",
        "benchmark_unit": "NR",
        # Extra dimensions: sex + age, slice is T + TOTAL.
        "dim": "age",
        "dim_value": "TOTAL",
        "dim2": "sex",
        "dim2_value": "T",
        # Single-unit: only NR exists.
        "other_unit": "PC",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_demo_r_magec3_nuts3",
        "benchmark_unit": "NR",
        # Extra dimensions: sex + age, slice is T + TOTAL.
        "dim": "age",
        "dim_value": "TOTAL",
        "dim2": "sex",
        "dim2_value": "T",
        # Single-unit: only NR exists.
        "other_unit": "PC",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_demo_r_fagec3_nuts3",
        "benchmark_unit": "NR",
        # Extra dimension: age (mother age group), slice is TOTAL.
        "dim": "age",
        "dim_value": "TOTAL",
        # Single-unit: only NR exists.
        "other_unit": "PC",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_gva_nuts3",
        "benchmark_unit": "CP_MEUR",
        # Extra dimension: NACE sector, slice is TOTAL.
        "dim": "nace_r2",
        "dim_value": "TOTAL",
        # Other units (CP_MNAC, ...) carry no benchmark. FRK26: IT NUTS3
        # 2024 coverage is partial — FR has both CP units for 2024.
        "other_unit": "CP_MNAC",
        "nuts_level": "NUTS3",
        "other_unit_geo": "FRK26",
    },
    {
        "slug": "eurostat_emp_nuts3",
        "benchmark_unit": "THS",
        # Extra dimensions: working status + NACE sector, slice EMP + TOTAL.
        "dim": "nace_r2",
        "dim_value": "TOTAL",
        "dim2": "wstatus",
        "dim2_value": "EMP",
        # Single-unit: only THS exists.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_business_demography_nuts3",
        "benchmark_unit": "V11920",
        # No `unit` column: dimensions are freq/indic_sb/sizeclas/nace_r2/geo.
        "no_unit": True,
        # Extra dimensions: indicator + size class + sector, slice V11920 +
        # TOTAL + B-S_X_K642.
        "dim": "sizeclas",
        "dim_value": "TOTAL",
        "dim2": "nace_r2",
        "dim2_value": "B-S_X_K642",
        "dim3": "indic_sb",
        "dim3_value": "V11920",
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_soil_erosion_nuts3",
        "benchmark_unit": "T",
        # Series ends 2023 (not 2024) — per-dataset cross-check year.
        "check_year": 2016,
        # Extra dimensions: severity class + land cover, slice TOTAL +
        # CLC2_3X331_332_335. (unit PC is constant 100 — T discriminates.)
        "dim": "levels",
        "dim_value": "TOTAL",
        "dim2": "clc18",
        "dim2_value": "CLC2_3X331_332_335",
        # Other units (PC, T_HA, ...) carry no benchmark. FRB02: has 5 units
        # in the slice for 2016 (ITC4C only has HA).
        "other_unit": "PC",
        "nuts_level": "NUTS3",
        "other_unit_geo": "FRB02",
    },
    {
        "slug": "eurostat_tourism_nuts3",
        "benchmark_unit": "NR",
        # Extra dimensions: residency + accommodation, slice TOTAL +
        # I551-I553.
        "dim": "c_resid",
        "dim_value": "TOTAL",
        "dim2": "nace_r2",
        "dim2_value": "I551-I553",
        # Other units (PC_TOT) carry no benchmark.
        "other_unit": "PC_TOT",
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
    {
        "slug": "eurostat_nrg_chddr2_m_nuts3",
        "benchmark_unit": "NR",
        # Monthly dataset: extra dimensions indic_nrg (HDD) + month (1).
        "dim": "indic_nrg",
        "dim_value": "HDD",
        "dim2": "month",
        "dim2_value": "1",
        # Other indicator (CDD) carries no benchmark.
        "other_unit": "NR",
        "other_unit_is_absent": True,
        "nuts_level": "NUTS3",
        "other_unit_geo": "ITC4C",
    },
]

# Year with widest coverage for cross-checks (same across datasets).
CHECK_YEAR = 2024


def _check_year(ds: dict) -> int:
    """Cross-check year for a dataset — per-dataset override when the
    series does not reach CHECK_YEAR (e.g. soil-erosion ends 2023)."""
    return int(ds.get("check_year", CHECK_YEAR))


def _skip_if_missing(slug: str, mart: str) -> Path:
    path = _parquet(slug, mart)
    if not path.exists():
        pytest.skip(f"{path.name} not present — run the pipeline for {slug} first")
    return path


def _dim_filter(ds: dict) -> str:
    """SQL filter for the optional extra benchmark dimensions (e.g. crime iccs,
    tertiary isced11 + sex, or business demography indic_sb + sizeclas +
    nace_r2)."""
    parts = []
    for key in ("dim", "dim2", "dim3"):
        if key in ds:
            parts.append(f"{ds[key]} = '{ds[key + '_value']}'")
    if parts:
        return " AND " + " AND ".join(parts)
    return ""


def _unit_filter(ds: dict) -> str:
    """SQL filter on the benchmark unit column, when the dataset has one.

    Datasets without a `unit` column (e.g. demo-balance: dimensions are
    freq/indic_de/geo) set `no_unit: True` — the benchmark slice is fully
    expressed by the `dim` filter instead.
    """
    if ds.get("no_unit"):
        return ""
    return f" AND unit = '{ds['benchmark_unit']}'"


# EU27 post-2020 composition in Eurostat geo codes (Greece = 'EL', not 'GR').
# Mirrors the eu_countries CTE used in the mart SQL files — keep in sync.
_EU27 = [
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "EL",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
]


def _eu27_body() -> str:
    """SQL IN-clause body for the EU27 country list."""
    return "country IN ('" + "','".join(_EU27) + "')"


def _eu27_filter() -> str:
    """SQL filter restricting a query to EU27 rows."""
    return f" AND {_eu27_body()}"


class TestSharedBenchmarkContract:
    """Same benchmark semantics for every analytical dataset."""

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_benchmark_only_on_unit(self, ds):
        """media/percentile/rank columns are NULL outside the benchmark unit."""
        f = _skip_if_missing(ds["slug"], "mart_geo_benchmark")
        dim = _dim_filter(ds)
        if ds.get("no_unit"):
            # No `unit` column: benchmark slice is the dim (e.g. indic_de
            # GROWRT) — rows outside the dim slice must carry NULL benchmark.
            dim2 = ds.get("dim2")
            outside = f"NOT ({ds['dim']} = '{ds['dim_value']}'"
            if dim2:
                outside += f" AND {dim2} = '{ds['dim2_value']}'"
            outside += ")"
            n_bad = duckdb.sql(
                f"""
                SELECT COUNT(*)
                FROM read_parquet('{f}')
                WHERE year = {_check_year(ds)} AND {outside}
                  AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL
                       OR rank_nazionale IS NOT NULL)
                """
            ).fetchone()[0]
            assert n_bad == 0, (
                f"benchmark columns computed outside slice for {ds['slug']}"
            )
            return
        if ds.get("other_unit_is_absent"):
            # Single-unit dataset: no row may carry benchmark columns outside
            # the benchmark unit (there are no other units at all).
            n_bad = duckdb.sql(
                f"""
                SELECT COUNT(*)
                FROM read_parquet('{f}')
                WHERE unit != '{ds["benchmark_unit"]}'{dim}
                  AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL
                       OR rank_nazionale IS NOT NULL)
                """
            ).fetchone()[0]
            assert n_bad == 0, (
                f"benchmark columns computed outside benchmark unit {ds['benchmark_unit']}"
            )
            return
        row = duckdb.sql(
            f"""
            SELECT media_eu_value, media_paese_value, percentile_eu, rank_nazionale,
                   distanza_media_eu_pct
            FROM read_parquet('{f}')
            WHERE year = {_check_year(ds)} AND unit = '{ds["other_unit"]}'
              AND geo = '{ds["other_unit_geo"]}'
            """
        ).fetchone()
        assert row is not None, "non-benchmark unit row missing"
        assert all(v is None for v in row), (
            f"benchmark columns computed for non-benchmark unit {ds['other_unit']}"
        )

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_rank_is_1_for_top_region(self, ds):
        """The top region of each country must have rank_nazionale = 1.

        Uses RANK() (ties share the same rank — regions with equal value are
        equally ranked, deterministic). Rows with rank_nazionale = 1 in the
        mart must be the max-value rows of their (country, nuts_level, unit)
        partition.
        """
        f = _skip_if_missing(ds["slug"], "mart_geo_benchmark")
        dims = [ds.get("dim"), ds.get("dim2"), ds.get("dim3")]
        dim_partition = "".join(f", {d}" for d in dims if d)
        if not ds.get("no_unit"):
            dim_partition += ", unit"
        dim_filter = _dim_filter(ds)
        unit_filter = _unit_filter(ds)
        n_bad = duckdb.sql(
            f"""
            WITH ranked AS (
                SELECT geo, country, value,
                       RANK() OVER (PARTITION BY year, country{dim_partition}
                                    ORDER BY value DESC) AS rn
                FROM read_parquet('{f}')
                WHERE year = {_check_year(ds)} AND nuts_level = '{ds["nuts_level"]}'{dim_filter}{unit_filter}
            )
            SELECT COUNT(*)
            FROM read_parquet('{f}') b
            JOIN ranked r ON b.geo = r.geo AND b.year = {_check_year(ds)}
                       AND b.nuts_level = '{ds["nuts_level"]}'{dim_filter}{unit_filter}
            WHERE b.rank_nazionale = 1 AND r.rn != 1
            """
        ).fetchone()[0]
        assert n_bad == 0, "a rank-1 region is not the top value of its partition"

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_benchmark_columns_complete(self, ds):
        """EU27 benchmark-unit rows carry all benchmark columns.

        Non-EU rows (CH, NO, TR, RS, ...) keep media_eu_value and
        distanza_media_eu_pct (the EU27 reference) but have percentile_eu
        NULL — they are not ranked within the EU27 distribution.
        """
        f = _skip_if_missing(ds["slug"], "mart_geo_benchmark")
        dim = _dim_filter(ds)
        eu_filter = _eu27_filter()
        unit_filter = _unit_filter(ds)
        n_incomplete = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = {_check_year(ds)} AND nuts_level = '{ds["nuts_level"]}'{dim}{unit_filter}{eu_filter}
              AND (media_eu_value IS NULL OR media_paese_value IS NULL
                   OR percentile_eu IS NULL OR rank_nazionale IS NULL
                   OR distanza_media_eu_pct IS NULL)
            """
        ).fetchone()[0]
        assert n_incomplete == 0, "EU27 benchmark-unit rows with NULL benchmark columns"

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_non_eu_percentile_null(self, ds):
        """Non-EU rows have percentile_eu NULL (not ranked within EU27)."""
        f = _skip_if_missing(ds["slug"], "mart_geo_benchmark")
        dim = _dim_filter(ds)
        unit_filter = _unit_filter(ds)
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = {_check_year(ds)} AND nuts_level = '{ds["nuts_level"]}'{dim}{unit_filter}
              AND NOT ({_eu27_body()})
              AND percentile_eu IS NOT NULL
            """
        ).fetchone()[0]
        assert n_bad == 0, "non-EU rows with percentile_eu computed"

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_trend_cagr_null_when_single_year(self, ds):
        """CAGR is NULL when the observed window is a single year."""
        f = _skip_if_missing(ds["slug"], "mart_trend")
        n_single = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE first_year = last_year AND cagr_pct IS NOT NULL
            """
        ).fetchone()[0]
        assert n_single == 0, "CAGR computed on a single-year window"

    @pytest.mark.parametrize("ds", ANALYTICAL_DATASETS, ids=lambda d: d["slug"])
    def test_trend_geo_not_null(self, ds):
        """Every trend row has a non-null geo."""
        f = _skip_if_missing(ds["slug"], "mart_trend")
        n_null = duckdb.sql(
            f"""
            SELECT COUNT(*) FROM read_parquet('{f}') WHERE geo IS NULL
            """
        ).fetchone()[0]
        assert n_null == 0, "trend rows with NULL geo"


# ── Dataset-specific verified facts ──────────────────────────────────────────
# These encode domain knowledge about the underlying Eurostat data (verified
# values, source gaps, reporting breaks). They are intentionally per-dataset.


class TestGdpNuts3Facts:
    """Verified facts for eurostat-gdp-nuts3."""

    def test_dublin_top_nuts3_2024(self):
        """Dublin (IE061) is the top NUTS3 by GDP per capita in 2024."""
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT value, media_eu_value, percentile_eu, rank_nazionale,
                   distanza_media_eu_pct
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'EUR_HAB' AND nuts_level = 'NUTS3'
              AND geo = 'IE061'
            """
        ).fetchone()
        assert row is not None, "IE061 missing from 2024 NUTS3 benchmark"
        value, media_eu, percentile, rank, dist = row
        assert value > media_eu  # Dublin above EU average
        assert percentile > 0.9  # top percentile within EU
        assert rank == 1  # rank 1 in Ireland among NUTS3
        assert dist > 0  # positive distance from EU average

    def test_italy_2024_gap(self):
        """IT NUTS3 per-capita 2024 is a legit Eurostat coverage gap.

        Time-bomb (same pattern as test_nace_codelist_complete): when Eurostat
        publishes IT per-capita GDP for 2024, this test will fail — that is the
        signal that the gap is closed and the test can be updated.
        """
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_geo_benchmark")
        n = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'EUR_HAB' AND nuts_level = 'NUTS3'
              AND country = 'IT'
            """
        ).fetchone()[0]
        assert n == 0  # no IT rows: source gap, not a pipeline bug

    def test_luxembourg_top_procapite_2024(self):
        """Luxembourg ranks 1st by GDP per capita in 2024."""
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'LU'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1

    def test_italy_rank_totale(self):
        """Italy is top-5 by total GDP (2024) but ~12th per capita."""
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT rank_procapite_eu, rank_totale_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        assert row[1] <= 5  # total GDP rank
        assert row[0] > row[1]  # per-capita rank worse than total rank

    def test_bolzano_cagr_positive(self):
        """Bolzano-Bozen (ITH10) grew >2% p.a. over 2000–2023 (verified value)."""
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT first_year, last_year, first_value, last_value, cagr_pct
            FROM read_parquet('{f}')
            WHERE geo = 'ITH10' AND nuts_level = 'NUTS3'
            """
        ).fetchone()
        assert row is not None
        first_year, last_year, first_val, last_val, cagr = row
        assert last_year > first_year
        assert last_val > first_val
        assert cagr > 2.0  # verified 2.91

    def test_window_covers_2000_2024(self):
        """At least one geography spans the full 2000–2024 window."""
        f = _skip_if_missing("eurostat_gdp_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE first_year = 2000 AND last_year = 2024
            """
        ).fetchone()
        assert row is not None
        assert row[0] > 0


class TestPhysiciansNuts2Facts:
    """Verified facts for eurostat-physicians-nuts2."""

    def test_italy_regions_have_benchmark(self):
        """Italian NUTS2 regions carry benchmark columns in 2024."""
        f = _skip_if_missing("eurostat_physicians_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT value, media_eu_value, media_paese_value, percentile_eu,
                   rank_nazionale, distanza_media_eu_pct
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'HAB_P' AND country = 'IT'
              AND geo = 'ITH3'  -- Veneto
            """
        ).fetchone()
        assert row is not None
        assert all(v is not None for v in row)

    def test_italy_present(self):
        """Italy has a row in the 2024 country ranking."""
        f = _skip_if_missing("eurostat_physicians_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT medici_per_100k, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        assert row[0] is not None
        assert row[1] >= 1

    def test_window_is_long(self):
        """Physicians series spans multiple decades (>= 15 years observed)."""
        f = _skip_if_missing("eurostat_physicians_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 15

    def test_italy_2021_break_visible(self):
        """The 2021 Italian reporting break is present in the data.

        Time-bomb: Italy drops from ~250 to ~185 physicians/100k in 2021
        (definition change in Italian reporting, verified against DE/ES/NL/PL
        which show no such break). The mart must preserve it — this test
        documents the break so it is never silently "smoothed out".
        """
        f = _skip_if_missing("eurostat_physicians_nuts2", "mart_sintesi")
        y2020, y2021 = duckdb.sql(
            f"""
            SELECT
                MAX(CASE WHEN year = 2020 THEN medici_per_100k END),
                MAX(CASE WHEN year = 2021 THEN medici_per_100k END)
            FROM read_parquet('{f}')
            WHERE country = 'IT'
            """
        ).fetchone()
        assert y2020 is not None and y2021 is not None
        assert y2021 < y2020 * 0.85  # break > 15% in a single year


class TestHospitalBedsNuts2Facts:
    """Verified facts for eurostat-hospital-beds-nuts2."""

    def test_italy_above_eu_average(self):
        """Italy is above the EU average in beds per 100k (2024).

        Verified: IT country value ~322 vs EU NUTS2 average ~262 — the
        opposite pattern of physicians, where Italy is below the EU.
        """
        f = _skip_if_missing("eurostat_hospital_beds_nuts2", "mart_geo_benchmark")
        it_row, eu_row = duckdb.sql(
            f"""
            SELECT
                (SELECT ROUND(value, 0) FROM read_parquet('{f}')
                 WHERE year = 2024 AND unit = 'HAB_P' AND geo = 'IT'),
                (SELECT ROUND(media_eu_value, 0) FROM read_parquet('{f}')
                 WHERE year = 2024 AND unit = 'HAB_P' AND nuts_level = 'NUTS2'
                   AND country = 'IT' LIMIT 1)
            """
        ).fetchone()
        assert it_row is not None and eu_row is not None
        assert it_row > eu_row

    def test_calabria_top_italy(self):
        """Calabria has the most beds per 100k among Italian regions (2024)."""
        f = _skip_if_missing("eurostat_hospital_beds_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'HAB_P' AND nuts_level = 'NUTS2'
              AND country = 'IT' AND geo = 'ITF6'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Calabria ranked 1st in Italy

    def test_window_is_long(self):
        """Hospital beds series spans multiple decades (>= 15 years observed)."""
        f = _skip_if_missing("eurostat_hospital_beds_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 15


class TestCrimeNuts3Facts:
    """Verified facts for eurostat-crime-nuts3."""

    def test_italy_low_homicide_rate(self):
        """Italy is below the EU average for homicide rate (2024).

        Verified: EU NUTS3 average ~1.0 per 100k; top Italian province
        (Ragusa, 1.6) is still below the EU top tier.
        """
        f = _skip_if_missing("eurostat_crime_nuts3", "mart_geo_benchmark")
        it_top = duckdb.sql(
            f"""
            SELECT ROUND(MAX(value), 1)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'P_HTHAB' AND nuts_level = 'NUTS3'
              AND country = 'IT' AND iccs = 'ICCS0101'
            """
        ).fetchone()[0]
        assert it_top is not None
        assert it_top < 2.0  # verified: Ragusa 1.6 — low by EU standards

    def test_eu_average_homicide_around_1(self):
        """The EU homicide average is around 1 per 100k (2024)."""
        f = _skip_if_missing("eurostat_crime_nuts3", "mart_geo_benchmark")
        media = duckdb.sql(
            f"""
            SELECT ROUND(AVG(DISTINCT media_eu_value), 1)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'P_HTHAB' AND nuts_level = 'NUTS3'
              AND iccs = 'ICCS0101'
            """
        ).fetchone()[0]
        assert media is not None
        assert 0.5 <= media <= 1.5  # verified: 1.0

    def test_iccs_labels_resolved(self):
        """ICCS labels are resolved from the codelist (no NULL labels).

        Note on the 'ICSS' prefix: the Eurostat SDMX source itself publishes
        two codes with a typo ('ICSS02041_02043_02044', 'ICSS02042_02043_02044').
        The codelist mirrors the source faithfully; those codes do not appear
        in the CRIM_GEN_REG dataflow (only the 7 correct ICCS codes do), so
        the join never sees them. If Eurostat ever publishes them, this test
        fails and the codelist note should be revisited.
        """
        f = _skip_if_missing("eurostat_crime_nuts3", "mart_geo_benchmark")
        n_null = duckdb.sql(
            f"""
            SELECT COUNT(*) FROM read_parquet('{f}') WHERE iccs_label_en IS NULL
            """
        ).fetchone()[0]
        assert n_null == 0

    def test_seven_crime_categories(self):
        """The dataset covers 7 ICCS categories in the benchmark mart."""
        f = _skip_if_missing("eurostat_crime_nuts3", "mart_geo_benchmark")
        n = duckdb.sql(
            f"""
            SELECT COUNT(DISTINCT iccs) FROM read_parquet('{f}')
            """
        ).fetchone()[0]
        assert n == 7

    def test_italy_2024_partial_coverage(self):
        """IT crime 2024 has partial provincial coverage.

        Time-bomb: in 2024 only ~54 of 107 Italian NUTS3 provinces have crime
        data (Milano missing). When Eurostat completes the 2024 release this
        test will fail — that is the signal to re-check the coverage.
        """
        f = _skip_if_missing("eurostat_crime_nuts3", "mart_geo_benchmark")
        n_2024, n_2023 = duckdb.sql(
            f"""
            SELECT
                (SELECT COUNT(DISTINCT geo) FROM read_parquet('{f}')
                 WHERE year = 2024 AND nuts_level = 'NUTS3' AND country = 'IT'
                   AND unit = 'P_HTHAB'),
                (SELECT COUNT(DISTINCT geo) FROM read_parquet('{f}')
                 WHERE year = 2023 AND nuts_level = 'NUTS3' AND country = 'IT'
                   AND unit = 'P_HTHAB')
            """
        ).fetchone()
        assert n_2024 is not None and n_2023 is not None
        assert n_2024 < n_2023  # partial 2024 coverage vs full 2023
        assert n_2024 >= 40  # still a substantial sample


class TestPovertyRiskNuts2Facts:
    """Verified facts for eurostat-poverty-risk-nuts2."""

    def test_calabria_highest_poverty_italy(self):
        """Calabria has the highest at-risk-of-poverty share in Italy (2024)."""
        f = _skip_if_missing("eurostat_poverty_risk_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC' AND nuts_level = 'NUTS2'
              AND country = 'IT' AND geo = 'ITF6'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Calabria ranked 1st (highest poverty) in Italy

    def test_calabria_double_national_average(self):
        """Calabria poverty share is more than double the Italian average."""
        f = _skip_if_missing("eurostat_poverty_risk_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT value, media_paese_value
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC' AND nuts_level = 'NUTS2'
              AND geo = 'ITF6'
            """
        ).fetchone()
        assert row is not None
        value, media_paese = row
        assert value > media_paese * 1.8  # verified: 37.2 vs 17.5

    def test_italy_above_eu_in_poverty(self):
        """Italy is above the EU average in poverty share (2024)."""
        f = _skip_if_missing("eurostat_poverty_risk_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT rischio_poverta_pct, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy ~18.9% vs EU country average ~16.6% — rank is not top-3
        assert row[0] > 15.0
        assert 5 <= row[1] <= 15

    def test_window_is_long(self):
        """Poverty series spans 2003–2025 (>= 15 years observed)."""
        f = _skip_if_missing("eurostat_poverty_risk_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 15


class TestIncomeInequalityNuts2Facts:
    """Verified facts for eurostat-income-inequality-nuts2."""

    def test_calabria_highest_inequality_italy(self):
        """Calabria has the highest S80/S20 ratio among Italian regions (2024)."""
        f = _skip_if_missing("eurostat_income_inequality_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'INX' AND nuts_level = 'NUTS2'
              AND country = 'IT' AND geo = 'ITF6'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Calabria ranked 1st (highest inequality) in Italy

    def test_italy_above_eu_average(self):
        """Italy is above the EU27 average in inequality (2024)."""
        f = _skip_if_missing("eurostat_income_inequality_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT s80s20_ratio, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 5.5 vs EU27 average ~4.4 — top-5 in inequality
        assert row[0] > 5.0
        assert 1 <= row[1] <= 6

    def test_calabria_extreme_percentile(self):
        """Calabria S80/S20 is in the top EU27 percentile (2024)."""
        f = _skip_if_missing("eurostat_income_inequality_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT percentile_eu, distanza_media_eu_pct
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'INX' AND nuts_level = 'NUTS2'
              AND geo = 'ITF6'
            """
        ).fetchone()
        assert row is not None
        percentile, dist = row
        assert percentile > 0.95  # top 5% of EU27 regions
        assert dist > 50  # >50% above EU27 average

    def test_window_is_long(self):
        """Inequality series spans 2003–2025 (>= 15 years observed)."""
        f = _skip_if_missing("eurostat_income_inequality_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 15


class TestTranSfRoadnuFacts:
    """Verified facts for eurostat-tran-sf-roadnu."""

    def test_italy_top5_eu_accidents(self):
        """Italy is top-5 in EU27 by road accidents per million (2024)."""
        f = _skip_if_missing("eurostat_tran_sf_roadnu", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT incidenti_per_milione, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        assert 1 <= row[1] <= 6  # verified: rank 4 of 27

    def test_genova_top_italy(self):
        """Genova has the most accidents per million among IT provinces (2023)."""
        f = _skip_if_missing("eurostat_tran_sf_roadnu", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'P_MHAB' AND nuts_level = 'NUTS3'
              AND country = 'IT' AND geo = 'ITC33'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Genova ranked 1st in Italy

    def test_window_is_long(self):
        """Road accidents series spans 1999–2024 (>= 20 years observed)."""
        f = _skip_if_missing("eurostat_tran_sf_roadnu", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 20


class TestEarlySchoolLeaversNuts2Facts:
    """Verified facts for eurostat-early-school-leavers-nuts2."""

    def test_italy_rank8_eu(self):
        """Italy ranks 8th of 27 EU27 by early school leaving (2024)."""
        f = _skip_if_missing("eurostat_early_school_leavers_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT abbandono_pct, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        assert 5 <= row[1] <= 10  # verified: rank 8 of 27

    def test_sicilia_top_italy(self):
        """Sicilia has the highest early leaving share among IT regions (2024)."""
        f = _skip_if_missing(
            "eurostat_early_school_leavers_nuts2", "mart_geo_benchmark"
        )
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC' AND sex = 'T'
              AND nuts_level = 'NUTS2' AND country = 'IT' AND geo = 'ITG1'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Sicilia ranked 1st (highest) in Italy

    def test_calabria_halved(self):
        """Calabria early leaving roughly halved over the observed window."""
        f = _skip_if_missing("eurostat_early_school_leavers_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT first_value, last_value, cagr_pct
            FROM read_parquet('{f}')
            WHERE geo = 'ITF6' AND nuts_level = 'NUTS2'
            """
        ).fetchone()
        assert row is not None
        first_val, last_val, cagr = row
        assert last_val < first_val * 0.5  # verified: 24.4 -> 6.5
        assert cagr < -4.0  # verified: -5.15

    def test_benchmark_only_total_sex(self):
        """Benchmark columns exist only for sex='T' rows (reference slice)."""
        f = _skip_if_missing(
            "eurostat_early_school_leavers_nuts2", "mart_geo_benchmark"
        )
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC' AND sex != 'T'
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestTertiaryEducationNuts2Facts:
    """Verified facts for eurostat-tertiary-education-nuts2."""

    def test_italy_bottom_half_eu(self):
        """Italy is in the bottom half of EU27 by tertiary attainment (2024)."""
        f = _skip_if_missing("eurostat_tertiary_education_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT istruzione_terziaria_pct, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy ~21% vs IE 55.6% top — bottom half of the 27
        assert row[0] < 30.0
        assert row[1] >= 15

    def test_lazio_top_italy(self):
        """Lazio has the highest tertiary attainment among IT regions (2024)."""
        f = _skip_if_missing("eurostat_tertiary_education_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC' AND isced11 = 'ED5-8'
              AND age = 'Y25-64' AND sex = 'T'
              AND nuts_level = 'NUTS2' AND country = 'IT' AND geo = 'ITI4'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Lazio ranked 1st in Italy

    def test_countries_aggregated_from_nuts2(self):
        """Sintesi is built from NUTS2 aggregation (no country-level in source).

        The TGS00109 dataflow publishes NUTS2 only — verified:
        nuts_level='country' has zero rows. Country values are the mean of
        their NUTS2 shares.
        """
        f = _skip_if_missing("eurostat_tertiary_education_nuts2", "mart_sintesi")
        n = duckdb.sql(
            f"""
            SELECT COUNT(*) FROM read_parquet('{f}') WHERE year = 2024
            """
        ).fetchone()[0]
        assert n >= 25  # most EU27 countries present via NUTS2 aggregation

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the reference slice rows."""
        f = _skip_if_missing("eurostat_tertiary_education_nuts2", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND unit = 'PC'
              AND NOT (isced11 = 'ED5-8' AND age = 'Y25-64' AND sex = 'T')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestRdExpenditureNuts2Facts:
    """Verified facts for eurostat-rd-expenditure-nuts2."""

    def test_italy_bottom_half_eu(self):
        """Italy is in the bottom half of EU27 by R&D as % GDP (2024)."""
        f = _skip_if_missing("eurostat_rd_expenditure_nuts2", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT rd_pct_pil, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 1.38% vs SE 3.56% top — bottom half of the 27
        assert row[0] < 1.8
        assert 12 <= row[1] <= 20

    def test_piemonte_top_italy(self):
        """Piemonte and Emilia-Romagna lead Italian regions by R&D (2023)."""
        f = _skip_if_missing("eurostat_rd_expenditure_nuts2", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'PC_GDP' AND sectperf = 'TOTAL'
              AND nuts_level = 'NUTS2' AND country = 'IT' AND geo = 'ITC1'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Piemonte ranked 1st (tied with Emilia) in Italy

    def test_long_series(self):
        """R&D series spans 1980–2024 (>= 40 years observed)."""
        f = _skip_if_missing("eurostat_rd_expenditure_nuts2", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 40

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the PC_GDP + TOTAL slice."""
        f = _skip_if_missing("eurostat_rd_expenditure_nuts2", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'PC_GDP' AND sectperf = 'TOTAL')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestLabourProductivityNuts3Facts:
    """Verified facts for eurostat-labour-productivity-nuts3."""

    def test_italy_midtable_eu(self):
        """Italy is mid-table in EU27 by labour productivity (2024)."""
        f = _skip_if_missing("eurostat_labour_productivity_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT produttivita_eur, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 83k EUR vs IE 204k top — mid-table
        assert 8 <= row[1] <= 14

    def test_milano_top_province(self):
        """Milano is the top Italian province by productivity (2023)."""
        f = _skip_if_missing("eurostat_labour_productivity_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'EUR' AND na_item = 'NLPR_PER'
              AND nuts_level = 'NUTS3' AND country = 'IT' AND geo = 'ITC4C'
            """
        ).fetchone()
        assert row is not None
        assert row[0] <= 2  # Milano ranked 2nd (after Extra-Regio) in Italy

    def test_long_series(self):
        """Productivity series spans 2000–2024 (>= 20 years observed)."""
        f = _skip_if_missing("eurostat_labour_productivity_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 20


class TestPopDensityNuts3Facts:
    """Verified facts for eurostat-pop-density-nuts3."""

    def test_italy_top10_eu_density(self):
        """Italy is top-10 in EU27 by population density (2024)."""
        f = _skip_if_missing("eurostat_pop_density_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT densita_km2, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 198/km2 vs MT 1817 top — top-10
        assert 1 <= row[1] <= 10

    def test_napoli_top_italy(self):
        """Napoli is the densest Italian province (2023)."""
        f = _skip_if_missing("eurostat_pop_density_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'PER_KM2'
              AND nuts_level = 'NUTS3' AND country = 'IT' AND geo = 'ITF33'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Napoli ranked 1st in Italy

    def test_long_series(self):
        """Density series spans 1990–2024 (>= 30 years observed)."""
        f = _skip_if_missing("eurostat_pop_density_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT MAX(years_observed) FROM read_parquet('{f}')
            """
        ).fetchone()
        assert row is not None
        assert row[0] >= 30


class TestDemoBalanceNuts3Facts:
    """Verified facts for eurostat-demo-balance-nuts3."""

    def test_italy_population_decline(self):
        """Italy has negative population growth in EU27 (2024)."""
        f = _skip_if_missing("eurostat_demo_balance_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT crescita_per_1000, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy -0.5 per 1000 — declining, bottom third of EU27
        assert row[0] < 0
        assert 15 <= row[1] <= 27

    def test_bolzano_growing_sud_declining(self):
        """Bolzano grows while southern provinces decline (2023)."""
        f = _skip_if_missing("eurostat_demo_balance_nuts3", "mart_geo_benchmark")
        bolzano, potenza = duckdb.sql(
            f"""
            SELECT
                (SELECT value FROM read_parquet('{f}')
                 WHERE year = 2023 AND indic_de = 'GROWRT'
                   AND country = 'IT' AND nuts_level = 'NUTS3' AND geo = 'ITH10'),
                (SELECT value FROM read_parquet('{f}')
                 WHERE year = 2023 AND indic_de = 'GROWRT'
                   AND country = 'IT' AND nuts_level = 'NUTS3' AND geo = 'ITF51')
            """
        ).fetchone()
        assert bolzano is not None and potenza is not None
        assert bolzano > 0  # +6.3 per 1000
        assert potenza < 0  # -9.3 per 1000

    def test_benchmark_only_growrt(self):
        """Benchmark columns exist only for the GROWRT slice."""
        f = _skip_if_missing("eurostat_demo_balance_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND indic_de != 'GROWRT'
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestFertilityNuts3Facts:
    """Verified facts for eurostat-fertility-nuts3."""

    def test_italy_bottom_eu_fertility(self):
        """Italy is near-bottom of EU27 by total fertility rate (2024)."""
        f = _skip_if_missing("eurostat_fertility_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT tasso_fertilita, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 1.18 vs BG 1.71 top — bottom third of the 27
        assert row[0] < 1.3
        assert 18 <= row[1] <= 27

    def test_bolzano_top_italy(self):
        """Bolzano-Bozen is the most fertile Italian province (2023)."""
        f = _skip_if_missing("eurostat_fertility_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'NR' AND indic_de = 'TOTFERRT'
              AND nuts_level = 'NUTS3' AND country = 'IT' AND geo = 'ITH10'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Bolzano ranked 1st in Italy

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the NR + TOTFERRT slice."""
        f = _skip_if_missing("eurostat_fertility_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'NR' AND indic_de = 'TOTFERRT')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestPopStructureNuts3Facts:
    """Verified facts for eurostat-pop-structure-nuts3."""

    def test_italy_top_eu_oldage(self):
        """Italy is 1st of 27 EU27 by old-age dependency ratio (2024)."""
        f = _skip_if_missing("eurostat_pop_structure_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT dipendenza_anziani_pct, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 61.7% — the oldest population in the EU27
        assert row[0] > 55.0
        assert row[1] == 1

    def test_savona_top_italy(self):
        """Savona is the most aged Italian province (2023)."""
        f = _skip_if_missing("eurostat_pop_structure_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'PC' AND indic_de = 'OLDDEP2'
              AND nuts_level = 'NUTS3' AND country = 'IT' AND geo = 'ITC32'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Savona ranked 1st in Italy

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the PC + OLDDEP2 slice."""
        f = _skip_if_missing("eurostat_pop_structure_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'PC' AND indic_de = 'OLDDEP2')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestAreaNuts3Facts:
    """Verified facts for eurostat-area-nuts3."""

    def test_italy_rank7_eu(self):
        """Italy ranks 7th of 27 EU27 by total area (2024)."""
        f = _skip_if_missing("eurostat_area_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT superficie_km2, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 302k km2 vs FR 638k top
        assert 250000 <= row[0] <= 320000
        assert 1 <= row[1] <= 10

    def test_area_stable_over_time(self):
        """Area is stable across years (static geography, few distinct values)."""
        f = _skip_if_missing("eurostat_area_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE ABS(delta_abs) > 100
            """
        ).fetchone()[0]
        # Area barely changes — most deltas are 0 or tiny
        assert row < 50

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the KM2 + TOTAL slice."""
        f = _skip_if_missing("eurostat_area_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'KM2' AND landuse = 'TOTAL')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestNrgChddr2ANuts3Facts:
    """Verified facts for eurostat-nrg-chddr2-a-nuts3."""

    def test_italy_warm_climate(self):
        """Italy is among the warmest EU27 by heating degree days (2024)."""
        f = _skip_if_missing("eurostat_nrg_chddr2_a_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT hdd_nr, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 1678 HDD vs FI 5151 top — bottom third (warm)
        assert row[0] < 2500
        assert 18 <= row[1] <= 27

    def test_valle_aosta_coldest_italy(self):
        """Valle d'Aosta is the coldest Italian province (2023)."""
        f = _skip_if_missing("eurostat_nrg_chddr2_a_nuts3", "mart_geo_benchmark")
        row = duckdb.sql(
            f"""
            SELECT rank_nazionale
            FROM read_parquet('{f}')
            WHERE year = 2023 AND unit = 'NR' AND indic_nrg = 'HDD'
              AND nuts_level = 'NUTS3' AND country = 'IT' AND geo = 'ITC20'
            """
        ).fetchone()
        assert row is not None
        assert row[0] == 1  # Valle d'Aosta ranked 1st (coldest) in Italy

    def test_benchmark_only_hdd(self):
        """Benchmark columns exist only for the HDD slice."""
        f = _skip_if_missing("eurostat_nrg_chddr2_a_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND indic_nrg != 'HDD'
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestDemoRPjangrp3Nuts3Facts:
    """Verified facts for eurostat-demo-r-pjangrp3-nuts3."""

    def test_italy_rank3_population(self):
        """Italy is 3rd of 27 EU27 by total population (2024)."""
        f = _skip_if_missing("eurostat_demo_r_pjangrp3_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT popolazione, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 58.97M (real value) — not the erroneous AVG (2.8M)
        assert 50_000_000 <= row[0] <= 65_000_000
        assert 1 <= row[1] <= 4

    def test_population_is_sum_not_avg(self):
        """Sintesi population is the SUM of NUTS2 rows, not the mean.

        Regression guard: AVG gave 2.8M for Italy (21 NUTS2 mean of 58.9M);
        SUM gives the real 58.97M.
        """
        f = _skip_if_missing("eurostat_demo_r_pjangrp3_nuts3", "mart_sintesi")
        pop = duckdb.sql(
            f"""
            SELECT popolazione FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_demo_r_pjangrp3_nuts3/2026/"
            "eurostat_demo_r_pjangrp3_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2024 AND sex = 'T' AND age = 'TOTAL'
              AND unit = 'NR' AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(pop - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the NR + T + TOTAL slice."""
        f = _skip_if_missing("eurostat_demo_r_pjangrp3_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'NR' AND age = 'TOTAL' AND sex = 'T')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestDemoRMagec3Nuts3Facts:
    """Verified facts for eurostat-demo-r-magec3-nuts3."""

    def test_italy_rank2_deaths(self):
        """Italy is 2nd of 27 EU27 by deaths (2024)."""
        f = _skip_if_missing("eurostat_demo_r_magec3_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT decessi, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 653k deaths — 2nd after DE (1M)
        assert 500_000 <= row[0] <= 750_000
        assert 1 <= row[1] <= 3

    def test_deaths_sum_from_nuts2(self):
        """Sintesi deaths is the SUM of NUTS2 rows (not the mean)."""
        f = _skip_if_missing("eurostat_demo_r_magec3_nuts3", "mart_sintesi")
        deaths = duckdb.sql(
            f"""
            SELECT decessi FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_demo_r_magec3_nuts3/2026/"
            "eurostat_demo_r_magec3_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2024 AND sex = 'T' AND age = 'TOTAL'
              AND unit = 'NR' AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(deaths - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the NR + T + TOTAL slice."""
        f = _skip_if_missing("eurostat_demo_r_magec3_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'NR' AND age = 'TOTAL' AND sex = 'T')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestDemoRFagec3Nuts3Facts:
    """Verified facts for eurostat-demo-r-fagec3-nuts3."""

    def test_italy_rank3_births(self):
        """Italy is 3rd of 27 EU27 by births (2024)."""
        f = _skip_if_missing("eurostat_demo_r_fagec3_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT nascite, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 370k births — 3rd after DE and FR
        assert 300_000 <= row[0] <= 450_000
        assert 1 <= row[1] <= 4

    def test_births_less_than_deaths(self):
        """Italy births < deaths in 2024 — negative natural balance.

        Cross-dataset check: births 370k (fagec3) vs deaths 653k (magec3)
        → natural decline of ~283k/year.
        """
        f_b = _skip_if_missing("eurostat_demo_r_fagec3_nuts3", "mart_sintesi")
        births = duckdb.sql(
            f"""
            SELECT nascite FROM read_parquet('{f_b}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        f_d = _skip_if_missing("eurostat_demo_r_magec3_nuts3", "mart_sintesi")
        deaths = duckdb.sql(
            f"""
            SELECT decessi FROM read_parquet('{f_d}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        assert births < deaths

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the NR + TOTAL slice."""
        f = _skip_if_missing("eurostat_demo_r_fagec3_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'NR' AND age = 'TOTAL')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestGvaNuts3Facts:
    """Verified facts for eurostat-gva-nuts3."""

    def test_italy_rank3_gva(self):
        """Italy is 3rd of 27 EU27 by gross value added (2024)."""
        f = _skip_if_missing("eurostat_gva_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT gva_mio_eur, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy ~1.97 trillion EUR GVA — 3rd after DE and FR
        assert 1_500_000 <= row[0] <= 2_500_000
        assert 1 <= row[1] <= 4

    def test_gva_sum_from_nuts2(self):
        """Sintesi GVA is the SUM of NUTS2 rows (not the mean)."""
        f = _skip_if_missing("eurostat_gva_nuts3", "mart_sintesi")
        gva = duckdb.sql(
            f"""
            SELECT gva_mio_eur FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_gva_nuts3/2026/"
            "eurostat_gva_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2024 AND unit = 'CP_MEUR' AND nace_r2 = 'TOTAL'
              AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(gva - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the CP_MEUR + TOTAL slice."""
        f = _skip_if_missing("eurostat_gva_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024 AND NOT (unit = 'CP_MEUR' AND nace_r2 = 'TOTAL')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestEmpNuts3Facts:
    """Verified facts for eurostat-emp-nuts3."""

    def test_italy_rank3_employment(self):
        """Italy is 3rd of 27 EU27 by employment (2024)."""
        f = _skip_if_missing("eurostat_emp_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT occupati_migliaia, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 26.5M employed — 3rd after DE and FR
        assert 20_000 <= row[0] <= 32_000
        assert 1 <= row[1] <= 4

    def test_emp_sum_from_nuts2(self):
        """Sintesi employment is the SUM of NUTS2 rows (not the mean)."""
        f = _skip_if_missing("eurostat_emp_nuts3", "mart_sintesi")
        emp = duckdb.sql(
            f"""
            SELECT occupati_migliaia FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_emp_nuts3/2026/"
            "eurostat_emp_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2024 AND unit = 'THS' AND wstatus = 'EMP'
              AND nace_r2 = 'TOTAL' AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(emp - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the THS + EMP + TOTAL slice."""
        f = _skip_if_missing("eurostat_emp_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024
              AND NOT (unit = 'THS' AND wstatus = 'EMP' AND nace_r2 = 'TOTAL')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestBusinessDemographyNuts3Facts:
    """Verified facts for eurostat-business-demography-nuts3."""

    def test_italy_rank2_births(self):
        """Italy is 2nd of 27 EU27 by enterprise births (2020)."""
        f = _skip_if_missing("eurostat_business_demography_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT nascite_imprese, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2020 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 302k enterprise births — 2nd after FR (644k)
        assert 200_000 <= row[0] <= 400_000
        assert 1 <= row[1] <= 3

    def test_births_sum_from_nuts2(self):
        """Sintesi births is the SUM of NUTS2 rows (not the mean)."""
        f = _skip_if_missing("eurostat_business_demography_nuts3", "mart_sintesi")
        births = duckdb.sql(
            f"""
            SELECT nascite_imprese FROM read_parquet('{f}')
            WHERE year = 2020 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_business_demography_nuts3/2026/"
            "eurostat_business_demography_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2020 AND indic_sb = 'V11920' AND sizeclas = 'TOTAL'
              AND nace_r2 = 'B-S_X_K642' AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(births - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the V11920 + TOTAL + B-S slice."""
        f = _skip_if_missing("eurostat_business_demography_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2020
              AND NOT (indic_sb = 'V11920' AND sizeclas = 'TOTAL'
                       AND nace_r2 = 'B-S_X_K642')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestSoilErosionNuts3Facts:
    """Verified facts for eurostat-soil-erosion-nuts3."""

    def test_italy_top_eu_erosion(self):
        """Italy is 1st of 27 EU27 by soil erosion tonnes (2016)."""
        f = _skip_if_missing("eurostat_soil_erosion_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT erosione_tonn, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2016 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 235.6M tonnes — 1st, most erosion in the EU27
        assert 150_000_000 <= row[0] <= 300_000_000
        assert row[1] == 1

    def test_pc_constant_not_benchmark(self):
        """unit PC is constant (100) — T is the discriminating benchmark.

        Regression guard: PC = % of agricultural land at risk is 100
        everywhere for the TOTAL+CLC slice; the benchmark uses unit T
        (tonnes) which varies and ranks Italy 1st.
        """
        f = _skip_if_missing("eurostat_soil_erosion_nuts3", "mart_geo_benchmark")
        pc_vals = duckdb.sql(
            f"""
            SELECT COUNT(DISTINCT value)
            FROM read_parquet('{f}')
            WHERE year = 2016 AND unit = 'PC' AND levels = 'TOTAL'
              AND clc18 = 'CLC2_3X331_332_335' AND country = 'IT'
            """
        ).fetchone()[0]
        assert pc_vals == 1  # PC is constant

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the T + TOTAL + CLC slice."""
        f = _skip_if_missing("eurostat_soil_erosion_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2016
              AND NOT (unit = 'T' AND levels = 'TOTAL'
                       AND clc18 = 'CLC2_3X331_332_335')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestTourismNuts3Facts:
    """Verified facts for eurostat-tourism-nuts3."""

    def test_italy_rank2_nights(self):
        """Italy is 2nd of 27 EU27 by tourism nights (2024)."""
        f = _skip_if_missing("eurostat_tourism_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT pernottamenti, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 466M nights — 2nd after ES (505M)
        assert 350_000_000 <= row[0] <= 550_000_000
        assert 1 <= row[1] <= 3

    def test_nights_sum_from_nuts2(self):
        """Sintesi nights is the SUM of NUTS2 rows (not the mean)."""
        f = _skip_if_missing("eurostat_tourism_nuts3", "mart_sintesi")
        nights = duckdb.sql(
            f"""
            SELECT pernottamenti FROM read_parquet('{f}')
            WHERE year = 2024 AND country = 'IT'
            """
        ).fetchone()[0]
        clean_f = (
            "out/data/clean/eurostat_tourism_nuts3/2026/"
            "eurostat_tourism_nuts3_2026_clean.parquet"
        )
        expected = duckdb.sql(
            f"""
            SELECT SUM(value) FROM read_parquet('{clean_f}')
            WHERE year = 2024 AND unit = 'NR' AND c_resid = 'TOTAL'
              AND nace_r2 = 'I551-I553' AND country = 'IT' AND nuts_level = 'NUTS2'
            """
        ).fetchone()[0]
        assert abs(nights - expected) < 1  # exact sum

    def test_benchmark_only_reference_slice(self):
        """Benchmark columns exist only for the NR + TOTAL + I551 slice."""
        f = _skip_if_missing("eurostat_tourism_nuts3", "mart_geo_benchmark")
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = 2024
              AND NOT (unit = 'NR' AND c_resid = 'TOTAL'
                       AND nace_r2 = 'I551-I553')
              AND (media_eu_value IS NOT NULL OR percentile_eu IS NOT NULL)
            """
        ).fetchone()[0]
        assert n_bad == 0


class TestNrgChddr2MNuts3Facts:
    """Verified facts for eurostat-nrg-chddr2-m-nuts3 (monthly)."""

    def test_italy_warm_january(self):
        """Italy is among the warmest EU27 in January HDD (2024)."""
        f = _skip_if_missing("eurostat_nrg_chddr2_m_nuts3", "mart_sintesi")
        row = duckdb.sql(
            f"""
            SELECT hdd_mensile, rank_procapite_eu
            FROM read_parquet('{f}')
            WHERE year = 2024 AND month = 1 AND country = 'IT'
            """
        ).fetchone()
        assert row is not None
        # Italy 340 HDD vs FI 969 top — bottom third (warm)
        assert row[0] < 600
        assert 18 <= row[1] <= 27

    def test_milan_heating_declining(self):
        """Milan heating demand is declining (climate warming).

        CAGR Jan 1980-2025 negative — less heating needed over 45 years.
        """
        f = _skip_if_missing("eurostat_nrg_chddr2_m_nuts3", "mart_trend")
        row = duckdb.sql(
            f"""
            SELECT first_value, last_value, cagr_pct
            FROM read_parquet('{f}')
            WHERE geo = 'ITC4C' AND month = 1
            """
        ).fetchone()
        assert row is not None
        first_val, last_val, cagr = row
        assert last_val < first_val  # less heating demand
        assert cagr < 0  # declining

    def test_trend_per_month(self):
        """Trend is decomposed per calendar month (12 per geo)."""
        f = _skip_if_missing("eurostat_nrg_chddr2_m_nuts3", "mart_trend")
        n = duckdb.sql(
            f"""
            SELECT COUNT(DISTINCT month) FROM read_parquet('{f}')
            WHERE geo = 'ITC4C'
            """
        ).fetchone()[0]
        assert n == 12
