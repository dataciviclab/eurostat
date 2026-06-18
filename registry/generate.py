"""Generate registry/datasets.json — single source of truth for all consumers.

Run from repo root:
    python registry/generate.py

Validates that each dataset has a matching directory in datasets/.
CI runs this and checks `git diff --exit-code registry/datasets.json`.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = REPO_ROOT / "registry" / "datasets.json"
DATASETS_DIR = REPO_ROOT / "datasets"

GCS_CLEAN_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_CURRENT_YEAR = "2024"


# ── Dataset metadata (single source) ──────────────────────────────────────────
# Aggiungere un dataset = aggiungere una entry qui + directory datasets/{slug}/

DATASET_METADATA: dict[str, dict[str, object]] = {
    "eurostat_gdp_nuts3": {
        "dataflow": "NAMA_10R_3GDP",
        "theme": "Economy / GDP per capita",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "geo"],
        "description": "GDP at current market prices by NUTS 3 region",
    },
    "eurostat_gva_nuts3": {
        "dataflow": "NAMA_10R_3GVA",
        "theme": "Economy / Gross Value Added",
        "nuts_level": 3,
        "dimensions": ["freq", "nace_r2", "unit", "geo"],
        "description": "Gross Value Added by NUTS 3 region and NACE sector",
    },
    "eurostat_crime_nuts3": {
        "dataflow": "CRIM_GEN",
        "theme": "Crime / Recorded offences",
        "nuts_level": 3,
        "dimensions": ["freq", "iccs", "unit", "geo"],
        "description": "Recorded crimes by NUTS 3 region and ICCS category",
    },
    "eurostat_pop_nuts3": {
        "dataflow": "DEMO_R_D2JAN",
        "theme": "Demography / Population",
        "nuts_level": 3,
        "dimensions": ["freq", "unit", "sex", "age", "geo"],
        "description": "Population on 1 January by NUTS 3 region, sex and age",
    },
}


def _slug_to_dir(slug: str) -> str:
    """Convert slug (eurostat_gdp_nuts3) to directory name (eurostat-gdp-nuts3)."""
    return slug.replace("_", "-")


def _build_parquet_url(slug: str) -> str:
    return (
        f"{GCS_CLEAN_BASE}/{slug}/{_CURRENT_YEAR}"
        f"/{slug}_{_CURRENT_YEAR}_clean.parquet"
    )


def generate() -> dict[str, object]:
    """Build the full registry dict and write datasets.json."""
    errors: list[str] = []
    datasets = {}

    for slug, meta in sorted(DATASET_METADATA.items()):
        dir_name = _slug_to_dir(slug)
        dataset_dir = DATASETS_DIR / dir_name

        if not dataset_dir.is_dir():
            errors.append(
                f"Dataset '{slug}' has metadata but no directory: "
                f"datasets/{dir_name}/"
            )
            continue
        if not (dataset_dir / "dataset.yml").exists():
            errors.append(
                f"Dataset '{slug}' directory exists but missing dataset.yml: "
                f"datasets/{dir_name}/dataset.yml"
            )
            continue

        datasets[slug] = {
            "dataflow": meta["dataflow"],
            "theme": meta["theme"],
            "nuts_level": meta["nuts_level"],
            "dimensions": list(meta["dimensions"]),
            "description": meta["description"],
            "parquet_url": _build_parquet_url(slug),
        }

    # Check for orphan directories (not in metadata)
    for dir_entry in sorted(DATASETS_DIR.iterdir()):
        if not dir_entry.is_dir():
            continue
        slug = dir_entry.name.replace("-", "_")
        if slug not in DATASET_METADATA:
            errors.append(
                f"Orphan dataset directory (no metadata): "
                f"datasets/{dir_entry.name}/"
            )

    registry = {
        "version": 1,
        "updated": date.today().isoformat(),
        "datasets": datasets,
        "errors": errors,
    }

    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2) + "\n")

    if errors:
        print("⚠️  Registry generated with warnings:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)

    print(f"✓ registry/datasets.json — {len(datasets)} datasets")
    return registry


if __name__ == "__main__":
    generate()
