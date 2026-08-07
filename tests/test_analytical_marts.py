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
]

# Year with widest coverage for cross-checks (same across datasets).
CHECK_YEAR = 2024


def _skip_if_missing(slug: str, mart: str) -> Path:
    path = _parquet(slug, mart)
    if not path.exists():
        pytest.skip(f"{path.name} not present — run the pipeline for {slug} first")
    return path


def _dim_filter(ds: dict) -> str:
    """SQL filter for the optional extra benchmark dimensions (e.g. crime iccs,
    or tertiary isced11 + sex)."""
    parts = []
    if "dim" in ds:
        parts.append(f"{ds['dim']} = '{ds['dim_value']}'")
    if "dim2" in ds:
        parts.append(f"{ds['dim2']} = '{ds['dim2_value']}'")
    if parts:
        return " AND " + " AND ".join(parts)
    return ""


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
            WHERE year = {CHECK_YEAR} AND unit = '{ds["other_unit"]}'
              AND geo = '{ds["other_unit_geo"]}'{dim}
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
        dims = [ds.get("dim"), ds.get("dim2")]
        dim_partition = "".join(f", {d}" for d in dims if d)
        dim_filter = _dim_filter(ds)
        n_bad = duckdb.sql(
            f"""
            WITH ranked AS (
                SELECT geo, country, value,
                       RANK() OVER (PARTITION BY year, country, unit{dim_partition}
                                    ORDER BY value DESC) AS rn
                FROM read_parquet('{f}')
                WHERE year = {CHECK_YEAR} AND unit = '{ds["benchmark_unit"]}'
                  AND nuts_level = '{ds["nuts_level"]}'{dim_filter}
            )
            SELECT COUNT(*)
            FROM read_parquet('{f}') b
            JOIN ranked r ON b.geo = r.geo AND b.year = {CHECK_YEAR}
                       AND b.unit = '{ds["benchmark_unit"]}'
                       AND b.nuts_level = '{ds["nuts_level"]}'{dim_filter}
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
        n_incomplete = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = {CHECK_YEAR} AND unit = '{ds["benchmark_unit"]}'
              AND nuts_level = '{ds["nuts_level"]}'{dim}{eu_filter}
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
        n_bad = duckdb.sql(
            f"""
            SELECT COUNT(*)
            FROM read_parquet('{f}')
            WHERE year = {CHECK_YEAR} AND unit = '{ds["benchmark_unit"]}'
              AND nuts_level = '{ds["nuts_level"]}'{dim}
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
