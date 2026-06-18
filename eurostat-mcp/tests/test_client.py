"""Tests for eurostat-mcp client — validation + contract."""

import pytest

from client import (
    _validate_slug,
    _validate_limit,
    get_codelist,
    list_datasets,
)


class TestValidateSlug:
    def test_valid_slug(self):
        assert _validate_slug("eurostat_gdp_nuts3") == "eurostat_gdp_nuts3"

    def test_all_valid_slugs(self):
        for slug in ["eurostat_gdp_nuts3", "eurostat_gva_nuts3",
                       "eurostat_crime_nuts3", "eurostat_pop_nuts3"]:
            assert _validate_slug(slug) == slug

    def test_invalid_slug(self):
        with pytest.raises(ValueError, match="Unknown dataset slug"):
            _validate_slug("nonexistent")


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
        assert "e" in result["entries"]

    def test_nuts_italy(self):
        result = get_codelist("nuts_italy")
        assert result["codelist"] == "nuts_italy"
        assert "ITC4" in result["entries"]
        assert result["entries"]["ITC4"] == "Lombardia"

    def test_case_insensitive(self):
        result = get_codelist("FREQ")
        assert result["codelist"] == "freq"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Unknown codelist"):
            get_codelist("invalid")
