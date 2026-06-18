#!/usr/bin/env python3
"""
Eurostat TSV normalizer — universal, streaming, DSD-agnostic.

Usage:
    python tsv_normalize.py --flow NAMA_10R_3GDP [--output file.csv]

Reads TSV from Eurostat SDMX API, detects dimensions automatically
from the header, unpivots years into rows, parses flags and missing values.

Output: CSV with columns [dim1, dim2, ..., dimN, anno, valore, flag]
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


def normalize(flow: str, output: Path | None = None) -> str:
    """Download TSV, normalize, return CSV content."""
    url = eurostat_url(flow)
    sys.stderr.write(f"Fetching {url}...\n")
    
    response = urllib.request.urlopen(url)
    # Read header
    raw_header = response.readline().decode("utf-8")
    dims = detect_dims(raw_header)
    sys.stderr.write(f"Detected dimensions: {dims}\n")
    
    # Parse year columns from header
    parts = raw_header.strip().split("\t")
    year_cols = [y.strip() for y in parts[1:] if y.strip()]
    sys.stderr.write(f"Year columns: {year_cols[0]}..{year_cols[-1]} ({len(year_cols)} years)\n")
    
    # Output CSV
    buf = io.StringIO()
    fieldnames = list(dims) + ["anno", "valore", "flag"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    
    row_count = 0
    for line_bytes in response:
        line = line_bytes.decode("utf-8").strip()
        if not line:
            continue
        
        cols = line.split("\t")
        if not cols:
            continue
        
        # Parse dimension values from first column
        dim_values = [v.strip() for v in cols[0].split(",")]
        base_row = {}
        for i, d in enumerate(dims):
            base_row[d] = dim_values[i] if i < len(dim_values) else ""
        
        # Each subsequent column is a year
        for i, year in enumerate(year_cols):
            if i + 1 >= len(cols):
                continue
            valore, flag = parse_value(cols[i + 1])
            row = dict(base_row)
            row["anno"] = year
            row["valore"] = str(valore) if valore is not None else ""
            row["flag"] = flag or ""
            writer.writerow(row)
            row_count += 1
    
    csv_content = buf.getvalue()
    
    if output:
        output.write_text(csv_content, encoding="utf-8")
        sys.stderr.write(f"Written {row_count} rows to {output}\n")
    else:
        sys.stdout.write(csv_content)
        sys.stderr.write(f"Written {row_count} rows to stdout\n")
    
    return csv_content


def main():
    parser = argparse.ArgumentParser(description="Eurostat TSV normalizer")
    parser.add_argument("--flow", required=True, help="Eurostat dataflow ID (e.g. NAMA_10R_3GDP)")
    parser.add_argument("--output", type=Path, default=None, help="Output CSV path (default: stdout)")
    args = parser.parse_args()
    
    normalize(args.flow, args.output)


if __name__ == "__main__":
    main()
