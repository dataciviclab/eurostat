"""Dataset registry — reads directly from datasets/*/dataset.yml.

No intermediate artifact. The dataset.yml files ARE the registry.
MCP client and CLI both call `list_datasets()` and `get_parquet_url()`.
Results are cached once per process.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = REPO_ROOT / "datasets"
GCS_CLEAN_BASE = "https://storage.googleapis.com/dataciviclab-clean/eurostat"
_CURRENT_YEAR = "2024"


@functools.lru_cache(maxsize=1)
def _scan() -> dict[str, dict]:
    """Scan datasets/*/dataset.yml, return {slug → metadata}."""
    datasets: dict[str, dict] = {}
    for dir_entry in sorted(DATASETS_DIR.iterdir()):
        if not dir_entry.is_dir():
            continue
        yml = dir_entry / "dataset.yml"
        if not yml.exists():
            continue
        data = yaml.safe_load(yml.read_text())
        if not isinstance(data, dict):
            continue

        ds = data.get("dataset", {}) or {}
        reg = data.get("registry", {}) or {}
        slug = ds.get("name", "")
        if not slug:
            continue

        datasets[slug] = {
            "dataflow": reg.get("dataflow", ""),
            "theme": reg.get("theme", ""),
            "nuts_level": reg.get("nuts_level", 3),
            "dimensions": list(reg.get("dimensions", [])),
            "description": reg.get("description", slug),
            "parquet_url": (
                f"{GCS_CLEAN_BASE}/{slug}/{_CURRENT_YEAR}"
                f"/{slug}_{_CURRENT_YEAR}_clean.parquet"
            ),
        }
    return datasets


def list_datasets() -> dict[str, dict]:
    """Return {slug → metadata} for all datasets."""
    return dict(_scan())


def get_parquet_url(slug: str) -> str:
    """Resolve a dataset slug to its clean parquet URL on GCS."""
    datasets = _scan()
    meta = datasets.get(slug)
    if meta is None:
        raise KeyError(f"Unknown dataset slug: '{slug}'. Available: {sorted(datasets)}")
    return meta["parquet_url"]


def get_metadata(slug: str) -> dict:
    """Return all metadata for a dataset."""
    datasets = _scan()
    meta = datasets.get(slug)
    if meta is None:
        raise KeyError(f"Unknown dataset slug: '{slug}'. Available: {sorted(datasets)}")
    return dict(meta)
