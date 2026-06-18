#!/usr/bin/env python3
"""
Eurostat TSV normalizer — universal, streaming, DSD-agnostic.

Usage:
    python tsv_normalize.py --flow NAMA_10R_3GDP [--output file.parquet]

Reads TSV from Eurostat SDMX API, detects dimensions automatically
from the header, unpivots years into rows, parses flags and missing values.

Output: parquet with columns [dim1, dim2, ..., dimN, year, value, flag]
         EU-wide, no filtering.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

SDMX_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
MISSING = ":"
FLAG_RE = re.compile(r"\s+([a-z])$")


def eurostat_url(flow: str) -> str:
    return f"{SDMX_BASE}/{flow}?format=TSV"


def detect_dims(raw_header: str) -> list[str]:
    """Detect dimension names from the first column of the TSV header.

    Header format: "dim1,dim2,...,dimN\\TIME_PERIOD\\t2020\\t2021..."
    """
    parts = raw_header.strip().split("\t")
    first_col = parts[0]
    backslash_pos = first_col.find("\\")
    dims_raw = first_col[:backslash_pos] if backslash_pos > 0 else first_col
    return [d.strip() for d in dims_raw.split(",") if d.strip()]


def parse_value(raw: str) -> tuple[float | None, str | None]:
    """Parse value cell: extract number and optional quality flag."""
    s = raw.strip()
    if not s or s == MISSING:
        return None, None
    m = FLAG_RE.search(s)
    flag = m.group(1) if m else None
    num = s[: m.start()].strip() if m else s
    try:
        return float(num), flag
    except ValueError:
        return None, flag


def normalize_stream(
    input_stream: io.TextIOBase,
    output: Path | None = None,
    filter_geo: str | None = None,
    fmt: str = "parquet",
) -> str:
    """Normalize TSV from a text stream to unpivoted CSV/parquet.

    Parses the SDMX-TSV header to detect dimensions, then unpivots
    year columns into rows with columns [dim1..dimN, year, value, flag].

    When fmt='parquet' (default), writes parquet via DuckDB (all_varchar
    to avoid type sniffing issues). When fmt='csv', writes CSV directly.

    Args:
        input_stream: Text stream containing the TSV data.
        output: Optional path to write output file. If None, returns CSV as string.
        filter_geo: Optional geo prefix filter (e.g. 'IT' for Italy only).
        fmt: Output format ('parquet' or 'csv').

    Returns:
        CSV content as string (even for parquet, for backward compat).
    """
    raw_header = input_stream.readline()
    dims = detect_dims(raw_header)
    sys.stderr.write(f"Detected dimensions: {dims}\n")

    # Geo is always the last dimension before TIME_PERIOD
    geo_dim_index = len(dims) - 1
    if filter_geo:
        sys.stderr.write(f"Filtering geo: {filter_geo}*\n")

    # Parse year columns from header
    parts = raw_header.strip().split("\t")
    year_cols = [y.strip() for y in parts[1:] if y.strip()]
    sys.stderr.write(
        f"Year columns: {year_cols[0]}..{year_cols[-1]} ({len(year_cols)} years)\n"
    )

    # Output CSV — lineterminator='\n' per evitare \r\n in stdout/pipe
    buf = io.StringIO()
    fieldnames = list(dims) + ["year", "value", "flag"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    row_count = 0
    for line in input_stream:
        line = line.strip()
        if not line:
            continue

        cols = line.split("\t")
        if not cols:
            continue

        # Parse dimension values from first column
        dim_values = [v.strip() for v in cols[0].split(",")]

        # Apply geo filter early (skip entire row if geo doesn't match)
        if filter_geo:
            geo_val = (
                dim_values[geo_dim_index] if geo_dim_index < len(dim_values) else ""
            )
            if not geo_val.startswith(filter_geo):
                continue

        base_row = {}
        for i, d in enumerate(dims):
            base_row[d] = dim_values[i] if i < len(dim_values) else ""

        # Each subsequent column is a year
        for i, year in enumerate(year_cols):
            if i + 1 >= len(cols):
                continue
            value_parsed, flag = parse_value(cols[i + 1])
            row = dict(base_row)
            row["year"] = year
            row["value"] = str(value_parsed) if value_parsed is not None else ""
            row["flag"] = flag or ""
            writer.writerow(row)
            row_count += 1

    csv_content = buf.getvalue()

    if output:
        if fmt == "parquet":
            # Write parquet via DuckDB: CSV in memory → COPY to parquet.
            # all_varchar avoids type sniffing (e.g. sex F/M/T → BOOLEAN).
            # year and value are explicitly cast so consumers get correct types.
            import duckdb

            parquet_path = output  # output path already has .parquet extension
            tmp_csv = output.with_suffix(".csv.tmp")
            tmp_csv.write_text(csv_content, encoding="utf-8")
            duckdb.sql(
                f"COPY ("
                f"SELECT * EXCLUDE (year, value), "
                f"CAST(year AS INTEGER) AS year, "
                f"CAST(NULLIF(value, '') AS DOUBLE) AS value "
                f"FROM read_csv('{tmp_csv}', "
                "auto_detect=true, all_varchar=true)"
                f") TO '{parquet_path}' (FORMAT PARQUET)"
            )
            tmp_csv.unlink()
            sys.stderr.write(f"Written {row_count} rows to {parquet_path}\n")
        else:
            output.write_text(csv_content, encoding="utf-8")
            sys.stderr.write(f"Written {row_count} rows to {output}\n")
    else:
        sys.stdout.write(csv_content)
        sys.stderr.write(f"Written {row_count} rows to stdout\n")

    return csv_content


def normalize(
    flow: str,
    output: Path | None = None,
    filter_geo: str | None = None,
    fmt: str = "parquet",
) -> str:
    """Download TSV from Eurostat SDMX API, normalize to parquet.

    Wraps normalize_stream with an HTTP fetch.
    """
    url = eurostat_url(flow)
    sys.stderr.write(f"Fetching {url}...\n")
    response = urllib.request.urlopen(url)
    text_stream = io.TextIOWrapper(response, encoding="utf-8")
    return normalize_stream(text_stream, output, filter_geo, fmt)


def main():
    parser = argparse.ArgumentParser(description="Eurostat TSV normalizer")
    parser.add_argument(
        "--flow", required=True, help="Eurostat dataflow ID (e.g. NAMA_10R_3GDP)"
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Output path (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default="parquet",
        help="Output format (default: parquet)",
    )
    parser.add_argument(
        "--filter-geo", default=None, help="Filter by geo prefix (e.g. IT, DE, FR)"
    )
    args = parser.parse_args()

    normalize(args.flow, args.output, filter_geo=args.filter_geo, fmt=args.format)


if __name__ == "__main__":
    main()
