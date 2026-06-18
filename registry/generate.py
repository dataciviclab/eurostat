"""Generate registry/datasets.json from dataset.yml files.

Scans datasets/*/dataset.yml, extracts the `registry:` block and
builds the canonical registry artifact consumed by MCP, CLI, and
downstream consumers.

CI on main runs this script and opens a PR if the JSON changed.
CI on PR validates that datasets.json is up to date (via git diff).

No manual metadata — the dataset.yml is the single source of truth.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = REPO_ROOT / "registry" / "datasets.json"
DATASETS_DIR = REPO_ROOT / "datasets"

GCS_CLEAN_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_CURRENT_YEAR = "2024"


def _parse_dataset_yml(path: Path) -> dict | None:
    """Extract slug + registry metadata from a dataset.yml."""
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:
        print(f"  [warn] YAML parse error: {path}: {exc}", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        return None

    ds = data.get("dataset", {})
    reg = data.get("registry", {})
    if not ds or not reg:
        return None

    return {
        "slug": ds.get("name", ""),
        "dimensions": reg.get("dimensions", []),
        "dataflow": reg.get("dataflow", ""),
        "theme": reg.get("theme", ""),
        "nuts_level": reg.get("nuts_level", 3),
        "description": reg.get("description", ""),
    }


def _build_parquet_url(slug: str) -> str:
    return (
        f"{GCS_CLEAN_BASE}/{slug}/{_CURRENT_YEAR}"
        f"/{slug}_{_CURRENT_YEAR}_clean.parquet"
    )


def generate() -> dict[str, object]:
    """Scan all datasets, build registry, write datasets.json."""
    errors: list[str] = []
    datasets: dict[str, dict] = {}

    for dir_entry in sorted(DATASETS_DIR.iterdir()):
        if not dir_entry.is_dir():
            continue

        yml_path = dir_entry / "dataset.yml"
        if not yml_path.exists():
            errors.append(f"Missing dataset.yml: {yml_path}")
            continue

        meta = _parse_dataset_yml(yml_path)
        if meta is None or not meta["slug"]:
            errors.append(f"Cannot parse registry metadata: {yml_path}")
            continue

        slug = meta["slug"]
        datasets[slug] = {
            "dataflow": meta["dataflow"],
            "theme": meta["theme"],
            "nuts_level": meta["nuts_level"],
            "dimensions": list(meta["dimensions"]),
            "description": meta["description"],
            "parquet_url": _build_parquet_url(slug),
        }

    if not datasets:
        print("⚠️  No datasets found!", file=sys.stderr)
        sys.exit(1)

    registry = {
        "version": 1,
        "updated": date.today().isoformat(),
        "datasets": datasets,
    }

    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2) + "\n")
    print(f"✓ registry/datasets.json — {len(datasets)} datasets")

    if errors:
        print("⚠️  Warnings:", file=sys.stderr)
        for err in errors:
            print(f"  • {err}", file=sys.stderr)

    return {"datasets": datasets, "errors": errors} if errors else {"datasets": datasets}


if __name__ == "__main__":
    generate()
