#!/usr/bin/env python3
"""
Fetch Eurostat SDMX codelists and regenerate codelists/*.csv.

Fetches ALL codelists from the Eurostat JSON API (GEO, NACE_R2, FREQ,
UNIT, OBS_FLAG). GEO includes NUTS hierarchy (nuts_level, parent_code)
deduced from code length. All CSVs are written with canonical columns.

Uso:  python scripts/update_codelists.py

Run this when Eurostat updates its classifications (NUTS ~every 3 years,
NACE rarely). Called automatically by publish.yml before processing
datasets, so codelists are always fresh on GCS pushes.
"""

from __future__ import annotations

import csv
import urllib.request
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CODELISTS_DIR = REPO_ROOT / "codelists"
API_BASE = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT"
TIMEOUT = 30


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fetch_codelist(codelist_id: str) -> dict[str, str]:
    """Fetch a codelist from Eurostat JSON API, return {code: label_en}."""
    url = f"{API_BASE}/{codelist_id}?format=json"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    data: dict[str, Any] = json.loads(resp.read())
    return data.get("category", {}).get("label", {}) or {}


def _write_csv(filename: str, header: list[str], rows: list[tuple]) -> Path:
    """Write rows to codelists/{filename}, return path."""
    path = CODELISTS_DIR / filename
    CODELISTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


# ── NUTS helpers (for GEO) ────────────────────────────────────────────────────


def _nuts_level(code: str) -> str:
    n = len(code.strip())
    if n <= 2:
        return "country"
    elif n == 3:
        return "NUTS1"
    elif n == 4:
        return "NUTS2"
    else:
        return "NUTS3"


def _parent_code(code: str) -> str:
    c = code.strip()
    return c[:-1] if len(c) > 2 else ""


# ── Codelist generators ───────────────────────────────────────────────────────


def update_geo() -> int:
    """Fetch GEO codelist and write geo.csv with NUTS hierarchy.

    Filters out historic NUTS codes (suffixed with '(NUTS 2006)' etc.)
    and special Italian extra-regio codes.
    """
    labels = _fetch_codelist("GEO/latest")
    rows: list[tuple[str, str, str, str]] = []
    skipped = 0

    for code in sorted(labels):
        label = labels[code]

        # Skip historic codes
        if "(NUTS" in label:
            skipped += 1
            continue
        # Skip Italian extra-regio
        if (
            code.startswith("ITX")
            or code.startswith("IT_CAP")
            or code.startswith("IT_DEL")
            or code.startswith("IT_NAL")
        ):
            skipped += 1
            continue

        rows.append((code, label, _nuts_level(code), _parent_code(code)))

    _write_csv("geo.csv", ["code", "label_en", "nuts_level", "parent_code"], rows)
    print(f"  ✅ geo.csv: {len(rows)} entries ({skipped} skipped)")
    return len(rows)


def update_nace() -> int:
    """Fetch NACE_R2 codelist and write nace_r2.csv (all codes)."""
    labels = _fetch_codelist("NACE_R2")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("nace_r2.csv", ["code", "label_en"], rows)
    print(f"  ✅ nace_r2.csv: {len(rows)} entries")
    return len(rows)


def update_freq() -> int:
    """Fetch FREQ codelist and write freq.csv."""
    labels = _fetch_codelist("FREQ")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("freq.csv", ["freq", "label_en"], rows)
    print(f"  ✅ freq.csv: {len(rows)} entries")
    return len(rows)


def update_units() -> int:
    """Fetch UNIT codelist and write units.csv."""
    labels = _fetch_codelist("UNIT")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("units.csv", ["unit", "label_en"], rows)
    print(f"  ✅ units.csv: {len(rows)} entries")
    return len(rows)


def update_flags() -> int:
    """Fetch OBS_FLAG codelist and write flags.csv."""
    labels = _fetch_codelist("OBS_FLAG")
    rows = [(code, labels[code]) for code in sorted(labels)]
    _write_csv("flags.csv", ["flag", "description_en"], rows)
    print(f"  ✅ flags.csv: {len(rows)} entries")
    return len(rows)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("Updating Eurostat codelists from SDMX API...")
    total = 0
    total += update_geo()
    total += update_nace()
    total += update_freq()
    total += update_units()
    total += update_flags()
    print(f"✔ Done: {total} total entries across 5 codelists")


if __name__ == "__main__":
    main()
