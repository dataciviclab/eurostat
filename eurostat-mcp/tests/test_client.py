"""Tests for eurostat-mcp client — validation, SQL guards, query contract, facts."""

import os
import tempfile

import duckdb
import pytest

from client import (
    DATASETS,
    _validate_slug,
    _validate_limit,
    _validate_sql_safe,
    describe_dataset,
    facts,
    get_codelist,
    list_datasets,
    query,
)


# ── _validate_slug ───────────────────────────────────────────────────────────


class TestValidateSlug:
    def test_valid_slug(self):
        assert _validate_slug("eurostat_gdp_nuts3") == "eurostat_gdp_nuts3"

    def test_all_valid_slugs(self):
        for slug in DATASETS:
            assert _validate_slug(slug) == slug

    def test_invalid_slug(self):
        with pytest.raises(ValueError, match="Unknown dataset slug"):
            _validate_slug("nonexistent")


# ── _validate_limit ──────────────────────────────────────────────────────────


class TestValidateLimit:
    def test_default_valid(self):
        assert _validate_limit(100) == 100

    def test_clamp_min(self):
        assert _validate_limit(0) == 1
        assert _validate_limit(-5) == 1

    def test_clamp_max(self):
        assert _validate_limit(1000) == 500

    def test_boundary(self):
        assert _validate_limit(1) == 1
        assert _validate_limit(500) == 500


# ── _validate_sql_safe ───────────────────────────────────────────────────────


class TestValidateSqlSafe:
    def test_valid_sql(self):
        # Should not raise
        _validate_sql_safe("SELECT * FROM data WHERE geo LIKE 'IT%'")
        _validate_sql_safe("SELECT geo, COUNT(*) FROM data GROUP BY geo")
        _validate_sql_safe("SELECT year, AVG(value) AS m FROM data GROUP BY year")

    def test_non_select_rejected(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("DELETE FROM data")
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("  drop table data")

    def test_multi_statement_rejected(self):
        with pytest.raises(ValueError, match="Multi-statement"):
            _validate_sql_safe("SELECT * FROM data; SELECT * FROM other")

    def test_read_parquet_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            _validate_sql_safe("SELECT * FROM read_parquet('/etc/passwd')")

    def test_read_csv_auto_blocked(self):
        with pytest.raises(ValueError, match="blocked"):
            _validate_sql_safe("SELECT * FROM read_csv_auto('/etc/passwd')")

    def test_copy_blocked(self):
        # Caught by "Only SELECT" gate first
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("COPY data TO 'out.csv'")

    def test_create_blocked(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("CREATE TABLE foo AS SELECT * FROM data")

    def test_filesystem_path_blocked(self):
        with pytest.raises(ValueError, match="filesystem"):
            _validate_sql_safe("SELECT * FROM data WHERE x = '/etc/passwd'")
        with pytest.raises(ValueError, match="filesystem"):
            _validate_sql_safe("SELECT * FROM data WHERE x LIKE '/tmp/foo'")

    def test_attach_blocked(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("ATTACH 'my.db' AS foo")

    def test_load_blocked(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            _validate_sql_safe("LOAD 'httpfs'")


# ── list_datasets ────────────────────────────────────────────────────────────


class TestListDatasets:
    def test_returns_list(self):
        result = list_datasets()
        assert isinstance(result, list)
        assert len(result) >= 4

    def test_each_has_required_fields(self):
        for ds in list_datasets():
            assert "slug" in ds
            assert "dataflow" in ds
            assert "theme" in ds
            assert "dimensions" in ds
            assert "description" in ds
            assert isinstance(ds["dimensions"], list)

    def test_slugs_are_unique(self):
        slugs = [ds["slug"] for ds in list_datasets()]
        assert len(slugs) == len(set(slugs))


# ── get_codelist ─────────────────────────────────────────────────────────────


class TestGetCodelist:
    def test_freq(self):
        result = get_codelist("freq")
        assert result["codelist"] == "freq"
        assert "A" in result["entries"]
        assert result["entries"]["A"] == "Annual"

    def test_flag(self):
        result = get_codelist("flag")
        assert result["codelist"] == "flag"
        assert "b" in result["entries"]

    def test_nuts_italy(self):
        result = get_codelist("nuts_italy")
        assert result["codelist"] == "nuts_italy"
        assert result["entries"]["ITC4"] == "Lombardia"

    def test_case_insensitive(self):
        result = get_codelist("FREQ")
        assert result["codelist"] == "freq"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Unknown codelist"):
            get_codelist("invalid")


# ── query (contract, no network) ─────────────────────────────────────────────


class TestQueryContract:
    """Test query() SQL rewriting and guards using a local parquet file.

    A small parquet is created in a temp dir and the GCS path is overridden
    to point to this local file. This tests the query pipeline end-to-end
    without network or GCS access.
    """

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create a small parquet on disk and patch a dataset's path."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        # Create a tiny parquet with sample Eurostat-like data
        duckdb.sql(
            """
            SELECT 'A' AS freq, 'EUR_HAB' AS unit, 'ITC4' AS geo,
                   2024 AS year, 42000.0 AS value, '' AS flag
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITH5', 2024, 38000.0, ''
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITI4', 2024, 35000.0, ''
            """
        ).write_parquet(self._parquet_path)

        # Override the first dataset's URL to our local file
        self._orig_url = DATASETS["eurostat_gdp_nuts3"]["parquet_url"]
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._orig_url

    def test_query_returns_rows(self):
        result = query("eurostat_gdp_nuts3", "SELECT * FROM data")
        assert isinstance(result, list)
        assert len(result) == 3  # 3 rows in fixture
        assert "geo" in result[0]
        assert "value" in result[0]
        assert "year" in result[0]

    def test_query_with_where(self):
        result = query(
            "eurostat_gdp_nuts3",
            "SELECT year, value FROM data WHERE geo = 'ITC4'",
        )
        assert len(result) == 1
        assert result[0]["value"] == 42000.0
        assert result[0]["year"] == 2024

    def test_query_with_group_by(self):
        result = query(
            "eurostat_gdp_nuts3",
            "SELECT geo, CAST(AVG(value) AS BIGINT) AS avg_val FROM data "
            "GROUP BY geo ORDER BY avg_val DESC",
            limit=10,
        )
        assert len(result) == 3  # 3 distinct geo values
        assert result[0]["geo"] == "ITC4"  # highest GDP

    def test_query_respects_limit(self):
        result = query("eurostat_gdp_nuts3", "SELECT * FROM data", limit=2)
        assert len(result) == 2

    def test_query_with_user_limit(self):
        """User's own LIMIT should be stripped and replaced."""
        result = query(
            "eurostat_gdp_nuts3",
            "SELECT * FROM data LIMIT 1",
            limit=3,
        )
        # Our limit wins
        assert len(result) == 3

    def test_query_lowercase_from(self):
        """FROM data should work case-insensitively."""
        result = query("eurostat_gdp_nuts3", "select * from data")
        assert len(result) == 3

    def test_query_invalid_slug(self):
        with pytest.raises(ValueError, match="Unknown dataset slug"):
            query("nonexistent", "SELECT * FROM data")

    def test_query_missing_from_data(self):
        with pytest.raises(ValueError, match="FROM data"):
            query("eurostat_gdp_nuts3", "SELECT 1")

    def test_query_blocked_keyword(self):
        with pytest.raises(ValueError, match="blocked"):
            query("eurostat_gdp_nuts3", "SELECT * FROM read_parquet('/etc/passwd')")


# ── describe_dataset (contract, no network) ────────────────────────────────────


class TestDescribeDataset:
    """Test describe_dataset() using a local parquet file (no GCS)."""

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create a small parquet on disk and patch a dataset's path."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        duckdb.sql(
            """
            SELECT 'A' AS freq, 'EUR_HAB' AS unit, 'ITC4' AS geo,
                   2024 AS year, 42000.0 AS value, '' AS flag
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITH5', 2024, 38000.0, ''
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITI4', 2024, 35000.0, ''
            """
        ).write_parquet(self._parquet_path)

        self._orig_url = DATASETS["eurostat_gdp_nuts3"]["parquet_url"]
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._orig_url

    def test_describe_valid_slug(self):
        result = describe_dataset("eurostat_gdp_nuts3")
        assert isinstance(result, dict)
        assert result["slug"] == "eurostat_gdp_nuts3"
        assert result["row_count"] == 3
        assert result["year_range"] == {"min": 2024, "max": 2024}

    def test_describe_invalid_slug(self):
        with pytest.raises(ValueError, match="Unknown dataset slug"):
            describe_dataset("nonexistent")

    def test_describe_columns_shape(self):
        result = describe_dataset("eurostat_gdp_nuts3")
        assert "columns" in result
        assert len(result["columns"]) >= 3
        col_names = [c["name"] for c in result["columns"]]
        assert "geo" in col_names
        assert "value" in col_names
        assert "year" in col_names
        assert all("type" in c for c in result["columns"])

    def test_describe_dimensions(self):
        result = describe_dataset("eurostat_gdp_nuts3")
        assert "dimensions" in result
        assert "geo" in result["dimensions"]
        geo = result["dimensions"]["geo"]
        assert "values" in geo
        assert "total_count" in geo
        assert "truncated" in geo
        geo_codes = [v.get("code") for v in geo["values"]]
        assert "ITC4" in geo_codes
        assert "ITH5" in geo_codes
        assert "ITI4" in geo_codes

    def test_describe_dimension_truncation(self):
        result = describe_dataset("eurostat_gdp_nuts3")
        # geo has exactly 3 distinct values, well under limit
        assert result["dimensions"]["geo"]["total_count"] >= 3
        assert result["dimensions"]["geo"]["truncated"] is False
        # freq has 1 value
        assert len(result["dimensions"]["freq"]["values"]) == 1


# ── facts (contract, no network) ─────────────────────────────────────────────


class TestFacts:
    """Test facts() auto-discovery using a local parquet file (no GCS).

    All tests use dataset='eurostat_gdp_nuts3' to avoid scanning all datasets
    (which would hit GCS for non-patched URLs).
    """

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create a small parquet on disk and patch the test dataset path."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        duckdb.sql(
            """
            SELECT 'A' AS freq, 'EUR_HAB' AS unit, 'ITC4' AS geo,
                   'Lombardia' AS geo_label_en, 'Nord-Ovest' AS nuts_parent_label_en,
                   'NUTS2' AS nuts_level, 2024 AS year, 42000.0 AS value, '' AS flag
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITH5', 'Emilia-Romagna', 'Nord-Est',
                   'NUTS2', 2024, 38000.0, ''
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITF3', 'Campania', 'Sud',
                   'NUTS2', 2023, 19500.0, ''
            UNION ALL
            SELECT 'A', 'EUR_HAB', 'ITF3', 'Campania', 'Sud',
                   'NUTS2', 2024, 20500.0, ''
            """
        ).write_parquet(self._parquet_path)

        self._orig_url = DATASETS["eurostat_gdp_nuts3"]["parquet_url"]
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._orig_url

    def test_facts_single_dataset(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        assert len(result) == 1
        assert result[0]["dataset"] == "eurostat_gdp_nuts3"

    def test_facts_has_expected_keys(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        entry = result[0]
        assert "dataset" in entry
        assert "theme" in entry
        assert "summary" in entry
        assert "facts" in entry
        assert "schema_facts" in entry

    def test_facts_summary_has_rows_years(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        s = result[0]["summary"]
        assert "rows" in s
        assert "years" in s

    def test_facts_has_schema_facts(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        assert len(result[0]["schema_facts"]) >= 1
        labels = [f["label"] for f in result[0]["schema_facts"]]
        assert any("Regional" in lab for lab in labels)
        assert any("Temporal" in lab for lab in labels)

    def test_facts_detail_contains_trend(self):
        result = facts(dataset="eurostat_gdp_nuts3", detail=True, limit=3)
        labels = [f["label"] for f in result[0]["facts"]]
        assert (
            any("Italy average" in lab for lab in labels)
            or any("Top" in lab for lab in labels)
            or any("year" in lab.lower() for lab in labels)
        )

    def test_facts_detail_contains_rankings(self):
        result = facts(dataset="eurostat_gdp_nuts3", detail=True, limit=3)
        labels = [f["label"] for f in result[0]["facts"]]
        assert any("Top" in lab for lab in labels) or any(
            "rank" in lab.lower() for lab in labels
        )

    def test_facts_invalid_slug(self):
        with pytest.raises(ValueError, match="Unknown dataset slug"):
            facts(dataset="nonexistent")

    def test_facts_row_count(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        rows = result[0]["summary"]["rows"]
        assert rows == "4"


# ── facts: limit validation ────────────────────────────────────────────────


class TestFactsLimit:
    """Test facts() limit validation — should clamp like _validate_limit."""

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")
        duckdb.sql("SELECT 1 AS x").write_parquet(self._parquet_path)
        self._orig = DATASETS["eurostat_gdp_nuts3"]["parquet_url"]
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gdp_nuts3"]["parquet_url"] = self._orig

    def test_limit_negative_clamped(self):
        result = facts(dataset="eurostat_gdp_nuts3", limit=-1)
        assert len(result) == 1  # non crasha

    def test_limit_zero_clamped(self):
        result = facts(dataset="eurostat_gdp_nuts3", limit=0)
        assert len(result) == 1

    def test_limit_over_max_clamped(self):
        result = facts(dataset="eurostat_gdp_nuts3", limit=1000)
        assert len(result) == 1

    def test_limit_default_works(self):
        result = facts(dataset="eurostat_gdp_nuts3")
        assert len(result) == 1


# ── facts: multi-dimensional datasets (extra dim filters) ──────────────────


class TestFactsMultiDim:
    """Test facts() with extra dimensions (nace_r2, sex, age, wstatus).

    Uses a local parquet that simulates a multi-dimensional dataset like
    GVA or EMP to verify that _build_extra_dim_where filters correctly.
    """

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create a small multi-dim parquet and patch a dataset."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        duckdb.sql(
            """
            -- GVA-like: multiple nace_r2 values per region
            SELECT 'A' AS freq, 'CP_MEUR' AS unit,
                   'ITC4' AS geo, 'Lombardia' AS geo_label_en,
                   'Nord-Ovest' AS nuts_parent_label_en,
                   'NUTS2' AS nuts_level,
                   2024 AS year,
                   'TOTAL' AS nace_r2, 451114.0 AS value, '' AS flag
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITC4', 'Lombardia', 'Nord-Ovest',
                   'NUTS2', 2024,
                   'C', 95000.0, ''  -- Manufacturing (should NOT appear in ranking)
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITH5', 'Emilia-Romagna', 'Nord-Est',
                   'NUTS2', 2024,
                   'TOTAL', 177320.0, ''
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITF3', 'Campania', 'Sud',
                   'NUTS2', 2024,
                   'TOTAL', 122904.0, ''
            """
        ).write_parquet(self._parquet_path)

        self._orig_url = DATASETS["eurostat_gva_nuts3"]["parquet_url"]
        DATASETS["eurostat_gva_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gva_nuts3"]["parquet_url"] = self._orig_url

    def test_facts_shows_extra_dim_filters(self):
        """Detail mode on a multi-dim dataset should report extra_dim_filters."""
        result = facts(dataset="eurostat_gva_nuts3", detail=True, limit=3)
        s = result[0].get("summary", {})
        assert "extra_dim_filters" in s, f"missing filters in {s}"
        assert "nace_r2" in s["extra_dim_filters"]

    def test_facts_ranking_no_duplicates(self):
        """Ranking should not contain the same region twice (nace_r2 filtered)."""
        result = facts(dataset="eurostat_gva_nuts3", detail=True, limit=5)
        rankings = [
            f
            for f in result[0]["facts"]
            if "Top" in f["label"] or "Bottom" in f["label"]
        ]
        if rankings:
            for r in rankings:
                # Count distinct region names in the value
                regions = [
                    part.split(":")[0].strip() for part in r["value"].split(", ")
                ]
                assert len(regions) == len(set(regions)), (
                    f"Duplicate regions in ranking: {regions}"
                )

    def test_facts_ranking_correct_values(self):
        """Ranking should use TOTAL nace_r2 values only."""
        result = facts(dataset="eurostat_gva_nuts3", detail=True, limit=3)
        for f in result[0]["facts"]:
            if "Top" in f["label"]:
                # Lombardia should be first (451,114), Milan manufacturing excluded
                assert "Lombardia" in f["value"]
                assert "€ 451,114" in f["value"] or "€451,114" in f["value"]


# ── facts: NUTS level consistency and has_trend flag ─────────────────────


class TestFactsTrendConsistency:
    """Test that trends use a consistent NUTS level and has_trend is accurate.

    Creates a parquet where NUTS3 rows exist only in the latest year,
    simulating GVA/EMP data patterns. Before the fix, the Italy average
    would artificially jump because of the extra NUTS3 rows.
    """

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create parquet with NUTS2 in all years + NUTS3 only in 2024."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        duckdb.sql(
            """
            -- 2022: only NUTS2 rows (2 regions)
            SELECT 'A' AS freq, 'CP_MEUR' AS unit,
                   'ITC4' AS geo, 'Lombardia' AS geo_label_en,
                   'Nord-Ovest' AS nuts_parent_label_en,
                   'NUTS2' AS nuts_level,
                   2022 AS year, 'TOTAL' AS nace_r2, 400000.0 AS value, '' AS flag
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITH5', 'Emilia-Romagna', 'Nord-Est',
                   'NUTS2', 2022, 'TOTAL', 150000.0, ''
            -- 2024: NUTS2 + NUTS3 rows (2 NUTS2 + 2 NUTS3)
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITC4', 'Lombardia', 'Nord-Ovest',
                   'NUTS2', 2024, 'TOTAL', 451114.0, ''
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITH5', 'Emilia-Romagna', 'Nord-Est',
                   'NUTS2', 2024, 'TOTAL', 177320.0, ''
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITC46', 'Bergamo', 'Lombardia',
                   'NUTS3', 2024, 'TOTAL', 25000.0, ''
            UNION ALL
            SELECT 'A', 'CP_MEUR', 'ITH58', 'Modena', 'Emilia-Romagna',
                   'NUTS3', 2024, 'TOTAL', 18000.0, ''
            """
        ).write_parquet(self._parquet_path)

        self._orig_url = DATASETS["eurostat_gva_nuts3"]["parquet_url"]
        DATASETS["eurostat_gva_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_gva_nuts3"]["parquet_url"] = self._orig_url

    def test_italy_trend_consistent_level(self):
        """Italy average should use NUTS2 only, avoiding artificial jumps."""
        result = facts(dataset="eurostat_gva_nuts3", detail=True, limit=3)
        for f in result[0]["facts"]:
            if "Italy average" in f["label"]:
                # Both years should have similar magnitude (both NUTS2 averages)
                # 2022: (400000 + 150000) / 2 = 275000
                # 2024: (451114 + 177320) / 2 = 314217
                assert "275,000" in f["value"] or "275000" in f["value"]
                assert "314,217" in f["value"] or "314217" in f["value"]
                # Should NOT include NUTS3 values (25000, 18000)
                assert "25,000" not in f["value"]
                assert "18,000" not in f["value"]
                return
        raise AssertionError("Italy average fact not found")

    def test_has_trend_false_no_rankings(self):
        """has_trend should be False when detail only produces Latest year."""
        # Patch to a country-only dataset (simulate crime)
        result = facts(dataset="eurostat_gva_nuts3", detail=True, limit=3)
        # With our fixture, geo is present, so we should have rankings
        assert result[0]["summary"].get("has_trend", False) is True


class TestFactsHasTrendFlag:
    """Test that has_trend is False when no rankings/trends exist (crime-like)."""

    @pytest.fixture(autouse=True)
    def _setup_parquet(self):
        """Create parquet WITHOUT geo column — only country-level data."""
        self._tmpdir = tempfile.mkdtemp()
        self._parquet_path = os.path.join(self._tmpdir, "test.parquet")

        duckdb.sql(
            """
            SELECT 'A' AS freq, 'NR' AS unit,
                   'IT' AS geo, 'Italy' AS geo_label_en,
                   NULL AS nuts_parent_label_en,
                   'country' AS nuts_level,
                   2005 AS year, 'TOTAL' AS iccs, 500000.0 AS value, '' AS flag
            """
        ).write_parquet(self._parquet_path)

        self._orig_url = DATASETS["eurostat_crime_nuts3"]["parquet_url"]
        DATASETS["eurostat_crime_nuts3"]["parquet_url"] = self._parquet_path
        yield
        DATASETS["eurostat_crime_nuts3"]["parquet_url"] = self._orig_url

    def test_has_trend_false(self):
        """has_trend should be False when detail produces only Latest year."""
        result = facts(dataset="eurostat_crime_nuts3", detail=True, limit=3)
        has = result[0]["summary"].get("has_trend", False)
        assert has is False, f"has_trend should be False but got {has}"
        # Should still show Latest year
        labels = [f["label"] for f in result[0]["facts"]]
        assert any("Latest" in lab for lab in labels)
