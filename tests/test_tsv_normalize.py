"""Tests for tsv_normalize.py connector — contract + pure_unit."""

import io
from pathlib import Path

import pytest

from connectors.tsv_normalize import (
    detect_dims,
    normalize_stream,
    parse_value,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ── detect_dims ──────────────────────────────────────────────────────────────
# contract: header parsing è il contratto centrale tra connector e formato SDMX-TSV


class TestDetectDims:
    """detect_dims(raw_header: str) -> list[str]"""

    def test_standard(self):
        """3 dimensioni: freq, unit, geo"""
        header = "freq,unit,geo\\TIME_PERIOD\t2000\t2001\t2002"
        assert detect_dims(header) == ["freq", "unit", "geo"]

    def test_multi_dim(self):
        """5 dimensioni: freq, age, sex, unit, geo (popolazione)"""
        header = "freq,age,sex,unit,geo\\TIME_PERIOD\t2020\t2021"
        assert detect_dims(header) == ["freq", "age", "sex", "unit", "geo"]

    def test_nace_dim(self):
        """con nace_r2 (GVA)"""
        header = "freq,nace_r2,unit,geo\\TIME_PERIOD\t2010\t2011"
        assert detect_dims(header) == ["freq", "nace_r2", "unit", "geo"]


# ── parse_value ──────────────────────────────────────────────────────────────
# policy: i flag qualità Eurostat vanno preservati, i missing vanno resi come None


class TestParseValue:
    """parse_value(raw: str) -> tuple[float | None, str | None]"""

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
        """b = break in time series"""
        v, f = parse_value("312.3  b")
        assert v == 312.3
        assert f == "b"

    def test_flag_d(self):
        """d = definition differs"""
        v, f = parse_value("237  d")
        assert v == 237.0
        assert f == "d"

    def test_flag_e(self):
        """e = estimated"""
        v, f = parse_value("50400  e")
        assert v == 50400.0
        assert f == "e"

    def test_flag_p(self):
        """p = provisional"""
        v, f = parse_value("1000  p")
        assert v == 1000.0
        assert f == "p"


# ── normalize_stream ─────────────────────────────────────────────────────────
# contract: TSV → CSV unpivoted con colonne [dim1..dimN, year, value, flag]


class TestNormalizeStream:
    """normalize_stream(input_stream, output=None, filter_geo=None) -> str"""

    def _tsv_stream(self, content: str) -> io.StringIO:
        return io.StringIO(content)

    def test_inline_data(self):
        """2 righe × 2 anni → 4 righe CSV"""
        tsv = (
            "freq,unit,geo\\TIME_PERIOD\t2020\t2021\n"
            "A,EUR_HAB,IT\t35000\t36000\n"
            "A,EUR_HAB,ITC4\t50400\t51200\n"
        )
        csv_content = normalize_stream(self._tsv_stream(tsv))
        rows = [r.split(",") for r in csv_content.strip().split("\n")]
        header = rows[0]
        assert header == ["freq", "unit", "geo", "year", "value", "flag"]
        assert len(rows) == 5  # header + 4 data rows
        # IT 2020
        it_2020 = [r for r in rows[1:] if r[2] == "IT" and r[3] == "2020"]
        assert len(it_2020) == 1
        assert it_2020[0][4] == "35000.0"
        # ITC4 2021
        lomb_2021 = [r for r in rows[1:] if r[2] == "ITC4" and r[3] == "2021"]
        assert len(lomb_2021) == 1
        assert lomb_2021[0][4] == "51200.0"

    def test_missing_values(self):
        """Valori mancanti (':') → cella vuota"""
        tsv = "freq,unit,geo\\TIME_PERIOD\t2020\t2021\nA,EUR_HAB,IT\t:\t36000\n"
        csv_content = normalize_stream(self._tsv_stream(tsv))
        assert ":," not in csv_content  # no colon in output
        rows = csv_content.strip().split("\n")
        it_2020 = [r for r in rows[1:] if "IT,2020" in r]
        assert len(it_2020) == 1
        # value should be empty
        assert it_2020[0].endswith(",,") or ",," in it_2020[0]

    def test_flags_preserved(self):
        """Flag qualità preservati come colonna 'flag'"""
        tsv = "freq,unit,geo\\TIME_PERIOD\t2020\nA,EUR_HAB,IT\t50400  e\n"
        csv_content = normalize_stream(self._tsv_stream(tsv))
        rows = csv_content.strip().split("\n")
        data_row = rows[1]
        assert data_row.endswith(",e")

    def test_geo_filter(self):
        """filter_geo='IT' esclude righe non italiane"""
        tsv = (
            "freq,unit,geo\\TIME_PERIOD\t2020\n"
            "A,EUR_HAB,IT\t35000\n"
            "A,EUR_HAB,FR\t30000\n"
            "A,EUR_HAB,DE\t38000\n"
        )
        csv_content = normalize_stream(self._tsv_stream(tsv), filter_geo="IT")
        rows = [r for r in csv_content.strip().split("\n") if r]
        assert len(rows) == 2  # header + solo IT
        assert "FR" not in csv_content
        assert "DE" not in csv_content

    def test_geo_filter_nuts3(self):
        """filter_geo='IT' su 4-dim (con nace_r2)"""
        tsv = (
            "freq,nace_r2,unit,geo\\TIME_PERIOD\t2020\n"
            "A,TOTAL,CP_MEUR,ITC4\t50400\n"
            "A,TOTAL,CP_MEUR,FR10\t30000\n"
        )
        csv_content = normalize_stream(self._tsv_stream(tsv), filter_geo="IT")
        rows = [r for r in csv_content.strip().split("\n") if r]
        assert len(rows) == 2  # header + solo ITC4
        assert "FR10" not in csv_content

    def test_nace_codelist_complete(self):
        """nace_r2.csv copre TUTTI i codici NACE presenti nei dati Eurostat.

        Contratto: il codelist deve contenere tutti i codici nace_r2 che
        compaiono nei dataset reali. Se Eurostat aggiunge nuovi codici,
        questo test fallisce e qualcuno deve aggiungerli al codelist.
        """
        import duckdb

        # Verifica parseabilità del CSV (label con virgole quotate)
        cl_rows = duckdb.sql(
            "SELECT code, label_en FROM read_csv('codelists/nace_r2.csv', "
            "auto_detect=true, delim=',', header=true) ORDER BY code"
        ).fetchall()
        assert len(cl_rows) >= 15, f"Solo {len(cl_rows)} codici, servono almeno 15"
        labels = dict(cl_rows)

        # Tutti i codici devono avere label non NULL
        for code, label in cl_rows:
            assert label is not None, f"Label mancante per codice NACE: {code}"

        # Label specifiche devono essere corrette
        assert labels["A"] == "Agriculture, forestry and fishing"
        assert (
            labels["TOTAL"] == "Total - all NACE activities"
        )  # official Eurostat label

        # Verifica copertura contro dati reali (se disponibili)
        raw_files = [
            "out/data/raw/eurostat_emp_nuts3/2026/nama_10r_3empers_normalized.csv",
            "out/data/raw/eurostat_gva_nuts3/2024/nama_10r_3gva_normalized.csv",
        ]
        all_data_codes: set[str] = set()
        for f in raw_files:
            try:
                codes = duckdb.sql(
                    f"SELECT DISTINCT nace_r2 FROM read_csv('{f}', "
                    "auto_detect=true) WHERE nace_r2 IS NOT NULL ORDER BY 1"
                ).fetchall()
                all_data_codes.update(r[0] for r in codes)
            except Exception:
                pass  # raw file potrebbe non esistere in CI

        if all_data_codes:
            missing = all_data_codes - set(labels.keys())
            assert not missing, (
                f"Codici NACE nei dati senza label nel codelist: "
                f"{sorted(missing)}. Aggiungili a codelists/nace_r2.csv"
            )

    def test_sample_fixture(self):
        """Test con fixture reale NAMA_10R_3GDP (Albania NUTS3)"""
        tsv_path = FIXTURES / "nama_10r_3gdp_sample.tsv"
        if not tsv_path.exists():
            pytest.skip("Fixture not available — run from repo root")
        tsv = tsv_path.read_text(encoding="utf-8")
        csv_content = normalize_stream(self._tsv_stream(tsv))
        rows = [r for r in csv_content.strip().split("\n") if r]
        assert len(rows) > 1  # header + almeno 1 data row
        header = rows[0].split(",")
        assert "freq" in header
        assert "unit" in header
        assert "geo" in header
        assert "year" in header
        assert "value" in header
        assert "flag" in header
        # Ogni riga dato deve avere year numerico
        for row in rows[1:]:
            cols = row.split(",")
            year = cols[header.index("year")]
            assert year.isdigit(), f"Non-numeric year: {year}"
