"""Tests for tsv_normalize.py connector."""

import csv
import io
from pathlib import Path

import pytest

from connectors.tsv_normalize import (
    parse_tsv_header,
    parse_value,
    tsv_to_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseTsvHeader:
    def test_standard_header(self):
        header = 'freq,unit,geo\\TIME_PERIOD\t2000\t2001\t2002'
        dims, years = parse_tsv_header(header)
        assert dims == ["freq", "unit", "geo"]
        assert years == ["2000", "2001", "2002"]

    def test_multi_dim_header(self):
        header = 'freq,age,sex,unit,geo\\TIME_PERIOD\t2020\t2021'
        dims, years = parse_tsv_header(header)
        assert dims == ["freq", "age", "sex", "unit", "geo"]
        assert years == ["2020", "2021"]


class TestParseValue:
    def test_normal_number(self):
        v, f = parse_value("50400")
        assert v == 50400.0
        assert f is None

    def test_decimal_number(self):
        v, f = parse_value("312.3")
        assert v == 312.3
        assert f is None

    def test_missing_colon(self):
        v, f = parse_value(":")
        assert v is None
        assert f is None

    def test_missing_colon_space(self):
        v, f = parse_value(": ")
        assert v is None
        assert f is None

    def test_flag_b(self):
        v, f = parse_value("312.3  b")
        assert v == 312.3
        assert f == "b"

    def test_flag_d(self):
        v, f = parse_value("237  d")
        assert v == 237.0
        assert f == "d"

    def test_flag_e(self):
        v, f = parse_value("50400  e")
        assert v == 50400.0
        assert f == "e"

    def test_flag_p(self):
        v, f = parse_value("1000  p")
        assert v == 1000.0
        assert f == "p"


class TestTsvToCsv:
    def test_sample_file(self):
        tsv_path = FIXTURES / "nama_10r_3gdp_sample.tsv"
        if not tsv_path.exists():
            pytest.skip("Fixture not available")
        csv_content = tsv_to_csv(str(tsv_path))
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) > 0
        # Expected fields
        assert "freq" in rows[0]
        assert "unit" in rows[0]
        assert "geo" in rows[0]
        assert "anno" in rows[0]
        assert "valore" in rows[0]
        assert "flag" in rows[0]
        # Every row should have a numeric year
        for row in rows:
            assert row["anno"].isdigit(), f"Non-numeric year: {row['anno']}"

    def test_inline_data(self):
        """Test with inline TSV data (no fixture dependency)."""
        tsv_data = (
            'freq,unit,geo\\TIME_PERIOD\t2020\t2021\n'
            'A,EUR_HAB,IT\t35000\t36000\n'
            'A,EUR_HAB,ITC4\t50400\t51200\n'
        )
        with open("/tmp/_test_eurostat.tsv", "w") as f:
            f.write(tsv_data)
        csv_content = tsv_to_csv("/tmp/_test_eurostat.tsv")
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 4  # 2 rows x 2 years
        # Check Italy total 2020
        it_2020 = [r for r in rows if r["geo"] == "IT" and r["anno"] == "2020"]
        assert len(it_2020) == 1
        assert it_2020[0]["valore"] == "35000.0"
        # Check Lombardia 2021
        lomb_2021 = [r for r in rows if r["geo"] == "ITC4" and r["anno"] == "2021"]
        assert len(lomb_2021) == 1
        assert lomb_2021[0]["valore"] == "51200.0"
