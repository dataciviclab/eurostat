"""
Eurostat TSV bulk normalizer.

Eurostat bulk TSV format has years as columns (pivot format).
This module converts it into analytical (unpivoted) format.

Input format (TSV, tab-separated):
    freq,unit,geo\\TIME_PERIOD    2000    2001    2002 ...
    A,EUR_HAB,ITC4    50400    51200    52100 ...

Output:
    freq | unit | geo | anno | valore | flag
    A    | EUR_HAB | ITC4 | 2000 | 50400 | NULL
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Iterator

MISSING = ":"
FLAG_PATTERN = re.compile(r"\s+([a-z])$")


def parse_tsv_header(raw_header: str) -> tuple[list[str], list[str]]:
    """Parse Eurostat TSV header: extract dimension names and year columns."""
    parts = raw_header.strip().split("\t")
    first_col = parts[0]
    # Column 1 name has format: "dim1,dim2,...,dimN\\TIME_PERIOD"
    backslash_pos = first_col.find("\\")
    dims_raw = first_col[:backslash_pos] if backslash_pos > 0 else first_col
    dim_names = [d.strip() for d in dims_raw.split(",") if d.strip()]
    year_cols = [y.strip() for y in parts[1:] if y.strip()]
    return dim_names, year_cols


def parse_value(value_raw: str) -> tuple[float | None, str | None]:
    """Parse a Eurostat TSV value cell. Returns (valore, flag)."""
    stripped = value_raw.strip()
    if not stripped or stripped == MISSING:
        return None, None
    m = FLAG_PATTERN.search(stripped)
    flag = m.group(1) if m else None
    num_str = stripped[: m.start()].strip() if m else stripped
    try:
        valore = float(num_str)
    except ValueError:
        return None, flag
    return valore, flag


def tsv_to_csv(tsv_path: str | Path, encoding: str = "utf-8") -> str:
    """Convert Eurostat bulk TSV into unpivoted CSV string.

    Returns CSV with columns: dim1, dim2, ..., dimN, anno, valore, flag
    """
    with open(tsv_path, "r", encoding=encoding) as f:
        raw_header = f.readline()
        dim_names, year_cols = parse_tsv_header(raw_header)

        output = io.StringIO()
        fieldnames = list(dim_names) + ["anno", "valore", "flag"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if not parts:
                continue

            # Parse dimension codes from first column
            dim_values = [d.strip() for d in parts[0].split(",")]
            base_row = {}
            for i, name in enumerate(dim_names):
                base_row[name] = dim_values[i] if i < len(dim_values) else ""

            # Each subsequent column is a year
            for i, year_col in enumerate(year_cols):
                if i + 1 >= len(parts):
                    continue
                valore, flag = parse_value(parts[i + 1])
                row = dict(base_row)
                row["anno"] = year_col
                row["valore"] = valore if valore is not None else ""
                row["flag"] = flag or ""
                writer.writerow(row)

        return output.getvalue()


def normalize_file(
    tsv_path: str | Path,
    output_path: str | Path | None = None,
    encoding: str = "utf-8",
) -> str:
    """Normalize a Eurostat TSV file and optionally save to output_path.

    Returns the CSV content.
    """
    csv_content = tsv_to_csv(tsv_path, encoding=encoding)
    if output_path:
        Path(output_path).write_text(csv_content, encoding="utf-8")
    return csv_content


def preview_normalized(tsv_path: str | Path, n: int = 10) -> None:
    """Print first n rows of normalized output."""
    csv_content = tsv_to_csv(tsv_path)
    reader = csv.DictReader(io.StringIO(csv_content))
    for i, row in enumerate(reader):
        if i >= n:
            break
        print(row)
    if sum(1 for _ in csv.DictReader(io.StringIO(csv_content))) > n:
        print(f"... ({sum(1 for _ in csv.DictReader(io.StringIO(csv_content)))} total rows)")
