"""Genera gli artifact registry del repo: clean_catalog, mart_catalog, pipeline_signals.

Wrapper sottile sul builder condiviso ``toolkit.registry`` (il toolkit ospita la
logica di generazione, riusando config model/path resolver/run_state/parquet_schema):
qui solo layout, path contract e scrittura.

Layout eurostat:
- dataset.yml in ``datasets/*/`` (chiave canonica: ``dataset.name``, underscore);
- parquet e run records in ``out/data/`` (root dichiarato nei dataset.yml);
- GCS: ``gs://dataciviclab-{clean,mart}/eurostat/{slug}/`` (layout flat, no-year).

Usage:
    python scripts/build_registry.py            # dry-run (stampa riepilogo)
    python scripts/build_registry.py --write    # scrive in registry/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "registry"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write",
        action="store_true",
        help="Scrive gli artifact in registry/ (default: dry-run)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Dir di output (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()

    try:
        from toolkit.registry import PathContract, RepoLayout
        from toolkit.registry.builders import build_registry
    except ImportError as exc:  # pragma: no cover
        print(
            f"ERRORE: toolkit.registry non disponibile ({exc}).\n"
            "Serve toolkit >= v1.48.1 (modulo registry su main).",
            file=sys.stderr,
        )
        return 1

    layout = RepoLayout(
        repo_root=ROOT,
        dataset_dirs=("datasets",),
        source_repo="dataciviclab/eurostat",
    )
    contract = PathContract(prefix="eurostat", clean_layout="flat", mart_layout="flat")

    existing_catalog = None
    existing_signals = None
    existing_path = args.out / "registry.json"
    if existing_path.is_file():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
            existing_catalog = {"datasets": existing.get("datasets", [])}
            existing_signals = {"signals": existing.get("signals", [])}
        except json.JSONDecodeError:
            print(
                "WARN: registry.json esistente illeggibile — riparto da zero",
                file=sys.stderr,
            )
    # Fallback legacy: il vecchio clean_catalog.json (repo non ancora migrati)
    if existing_catalog is None:
        legacy_path = args.out / "clean_catalog.json"
        if legacy_path.is_file():
            try:
                existing_catalog = json.loads(legacy_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                print(
                    "WARN: clean_catalog.json esistente illeggibile — riparto da zero",
                    file=sys.stderr,
                )

    result = build_registry(
        layout,
        path_contract=contract,
        existing_catalog=existing_catalog,
        existing_signals=existing_signals,
    )

    # Errori già categorizzati dal builder: derive = warning (checkout
    # parziali), validation = bloccanti (artifact non conforme allo schema).
    all_warnings: list[str] = []
    all_real: list[str] = []
    for artifact, errors in result["errors"].items():
        all_warnings.extend(f"{artifact}: {e}" for e in errors["derive"])
        all_real.extend(f"{artifact}: {e}" for e in errors["validation"])

    for w in all_warnings:
        print(f"WARN: {w}", file=sys.stderr)

    if all_real:
        for e in all_real:
            print(f"ERROR: {e}", file=sys.stderr)
        print("Artifact NON scritti: errori di validazione.", file=sys.stderr)
        return 1

    registry = result["registry"]
    if not args.write:
        s = registry["summary"]
        print(
            f"[dry-run] registry.json — datasets {s['datasets']}, "
            f"marts {s['marts']}, signals {s['signals']}"
        )
        print("Usa --write per scrivere il file.")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / "registry.json"
    out_path.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"scritto {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
