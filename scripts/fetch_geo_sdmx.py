#!/usr/bin/env python3
"""
Scarica la codelist GEO da Eurostat SDMX e genera codelists/geo.csv.

La fonte ufficiale è l'API SDMX di Eurostat:
  https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/GEO/latest

Lo script filtra i codici NUTS2021 correnti (senza suffissi storici
" (NUTS 2006)" etc.) e deduce nuts_level e parent_code dalla
lunghezza del codice.

Uso:  python scripts/fetch_geo_sdmx.py

Serve solo quando cambia la classificazione NUTS (ogni ~3 anni).
"""

from __future__ import annotations

import csv
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SDMX_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/"
    "codelist/ESTAT/GEO/latest"
)
# Filtra codici con annotazioni storiche come " (NUTS 2006)"
HISTORIC_SUFFIX = re.compile(r"\(NUTS\s+\d{4}\)")

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "codelists" / "geo.csv"


def nuts_level(code: str) -> str:
    """Deduce NUTS level from code length."""
    n = len(code.strip())
    if n <= 2:
        return "country"
    elif n == 3:
        return "NUTS1"
    elif n == 4:
        return "NUTS2"
    elif n >= 5:
        return "NUTS3"
    return ""


def parent_code(code: str) -> str:
    """Parent code: truncate last char (NUTS hierarchy)."""
    c = code.strip()
    n = len(c)
    if n <= 2:
        return ""
    return c[:-1] if n > 2 else ""


def main():
    ns = {
        "mes": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
        "str": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
        "com": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    }

    print(f"Fetching {SDMX_URL}...")
    req = urllib.request.Request(SDMX_URL)
    resp = urllib.request.urlopen(req, timeout=15)
    root = ET.fromstring(resp.read())

    codes = root.findall(".//str:Code", ns)
    rows: list[tuple[str, str, str, str]] = []
    skipped = 0

    for code_elem in codes:
        cid = code_elem.get("id", "")
        names = code_elem.findall("com:Name", ns)
        label = names[0].text.strip() if names else ""

        # Skip historic codes (NUTS 2006/2010/2016)
        if HISTORIC_SUFFIX.search(label):
            skipped += 1
            continue
        # Skip extra-regio / not allocated
        if cid.startswith("ITX") or cid.startswith("IT_CAP") or cid.startswith("IT_DEL") or cid.startswith("IT_NAL"):
            skipped += 1
            continue

        rows.append((cid, label, nuts_level(cid), parent_code(cid)))

    # Sort by code
    rows.sort(key=lambda r: r[0])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "label_en", "nuts_level", "parent_code"])
        w.writerows(rows)

    print(f"✅ geo.csv written: {len(rows)} entries ({skipped} historic skipped)")
    print(f"   {OUTPUT}")


if __name__ == "__main__":
    main()
