#!/usr/bin/env python3
"""
Fetch the Eurostat GEO codelist and regenerate codelists/geo.csv.

GEO is the only codelist kept as a repo CSV: the clean.sql files join
it directly for the NUTS hierarchy (nuts_level, parent_code), which the
SDMX codelist annotation set does not carry. All other codelists are
materialized at run-time by the toolkit support (provider: sdmx).

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


def _fetch_raw(url: str) -> dict[str, Any]:
    """Fetch a URL and return parsed JSON."""
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    return json.loads(resp.read())  # type: ignore[no-any-return]


def _write_csv(filename: str, header: list[str], rows: list[tuple]) -> Path:
    """Write rows to codelists/{filename}, return path."""
    path = CODELISTS_DIR / filename
    CODELISTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


# ── GEO helpers (NUTS level from API annotations) ────────────────────────────

# Mapping from API LEVEL annotation values to geo.csv nuts_level strings.
_LEVEL_MAP: dict[str, str] = {
    "0": "country",
    "1": "NUTS1",
    "2": "NUTS2",
    "3": "NUTS3",
}


def _parent_code(code: str) -> str:
    """Derive NUTS parent code by truncating the last character."""
    c = code.strip()
    return c[:-1] if len(c) > 2 else ""


# ── Codelist generators ───────────────────────────────────────────────────────


def update_geo() -> int:
    """Fetch GEO codelist and write geo.csv with NUTS hierarchy.

    Uses the API's code annotations (LEVEL, IS_STANDARD_CODE) instead
    of heuristic code-length sniffing, avoiding false NUTS levels on
    EU aggregates like EU27_2020, ACP_*, etc.
    """
    data = _fetch_raw(f"{API_BASE}/GEO/latest?format=json")
    labels: dict[str, str] = data.get("category", {}).get("label", {}) or {}
    annotations: dict[str, list[dict[str, Any]]] = (
        data.get("extension", {}).get("code-annotation", {}) or {}
    )

    def _get_attrib(code: str, attr: str) -> str | None:
        """Extract a single annotation attribute by type."""
        ann_list = annotations.get(code, [])
        for ann in ann_list:
            if ann.get("type") == attr:
                val = ann.get("title")
                if val is not None:
                    return str(val)
        return None

    rows: list[tuple[str, str, str, str]] = []
    obsolete = 0

    for code in sorted(labels):
        label = labels[code]

        # Obsolete codes: keep (data may reference them) but no nuts_level
        is_std = _get_attrib(code, "IS_STANDARD_CODE")
        if is_std == "O":
            rows.append((code, label, "", ""))
            obsolete += 1
            continue

        # Resolve NUTS level from API annotation
        level_raw = _get_attrib(code, "LEVEL")
        if level_raw and level_raw in _LEVEL_MAP:
            nuts = _LEVEL_MAP[level_raw]
            parent = _parent_code(code) if nuts.startswith("NUTS") else ""
        else:
            nuts = ""
            parent = ""

        rows.append((code, label, nuts, parent))

    _write_csv("geo.csv", ["code", "label_en", "nuts_level", "parent_code"], rows)
    print(f"  ✅ geo.csv: {len(rows)} entries ({obsolete} obsolete kept)")
    return len(rows)


def main():
    print("Updating Eurostat codelists from SDMX API...")
    total = update_geo()
    print(f"✔ Done: {total} entries in geo.csv")


if __name__ == "__main__":
    main()
