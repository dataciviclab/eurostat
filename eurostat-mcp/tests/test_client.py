"""Tests for eurostat-mcp client — validation, SQL guards, query contract."""

import os
import tempfile

import duckdb
import pytest
from client import (
    DATASETS,
    _validate_limit,
    _validate_slug,
    _validate_sql_safe,
    describe_dataset,
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


# ── mart derivation ──────────────────────────────────────────────────────────


class TestMartDerivation:
    """Analytical marts are auto-discovered from dataset.yml mart.tables."""

    @pytest.mark.contract
    def test_marts_exist(self):
        """At least the 5 migrated datasets expose analytical marts."""
        marts = list_datasets("mart")
        assert len(marts) > 0
        # The migrated datasets expose the 3 analytical marts each.
        for slug in ("eurostat_gdp_nuts3", "eurostat_crime_nuts3"):
            mart_slugs = [m["slug"] for m in marts if m["slug"].startswith(f"{slug}__")]
            assert len(mart_slugs) >= 3, f"{slug} should expose >= 3 marts"

    @pytest.mark.policy
    def test_mart_type_filter(self):
        """type filter isolates clean from mart entries."""
        cleans = list_datasets("clean")
        marts = list_datasets("mart")
        assert all(m["type"] == "mart" for m in marts)
        assert all(c["type"] == "clean" for c in cleans)
        # No overlap between clean and mart slugs.
        clean_slugs = {c["slug"] for c in cleans}
        mart_slugs = {m["slug"] for m in marts}
        assert not (clean_slugs & mart_slugs)

    @pytest.mark.policy
    def test_invalid_type_rejected(self):
        with pytest.raises(ValueError):
            list_datasets("bogus")

    @pytest.mark.contract
    def test_mart_slug_convention(self):
        """Mart slug is {dataset}__{mart_table}."""
        marts = list_datasets("mart")
        for m in marts:
            dataset, _, table = m["slug"].partition("__")
            assert dataset in DATASETS
            assert table.startswith("mart_")
            # The mart table is declared in the source dataset.yml.
            assert DATASETS[m["slug"]]["mart_table"] == table

    @pytest.mark.contract
    def test_mart_parquet_url(self):
        """Mart URL points to the mart bucket, no-year layout."""
        for m in list_datasets("mart"):
            url = DATASETS[m["slug"]]["parquet_url"]
            assert "dataciviclab-mart" in url
            assert url.endswith(".parquet")
            # no-year layout: {slug}/{table}.parquet (matches publish rsync)
            dataset, _, table = m["slug"].partition("__")
            assert f"/{dataset}/{table}.parquet" in url


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
