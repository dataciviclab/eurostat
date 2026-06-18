# Eurostat 🇪🇺 for DataCivicLab

[![CI](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml/badge.svg)](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)

**Eurostat datasets, connectors and pipelines** — designed for regional (NUTS2/NUTS3) analysis across Europe.

Part of [DataCivicLab](https://github.com/dataciviclab), a civic data laboratory.

## What this is

A reproducible pipeline that fetches, normalizes and publishes Eurostat SDMX-TSV data as columnar parquet files.

- **Raw**: SDMX-TSV bulk download — all EU countries, all years
- **Clean**: unpivoted rows + codelist enrichment (geo hierarchy, unit labels, quality flags)
- **Mart**: Italy-focused views with business logic

## Published datasets

| Dataset | Dataflow | Theme | Clean rows | Clean size |
|---|---|---|---|---|
| `eurostat-gdp-nuts3` | `NAMA_10R_3GDP` | Regional GDP by NUTS 3 | 308K | 1.1 MB |
| `eurostat-gva-nuts3` | `NAMA_10R_3GVA` | Regional GVA by NUTS 3 (by NACE sector) | 1.3M | 6.5 MB |
| `eurostat-crime-nuts3` | `CRIM_GEN` | Recorded crimes by NUTS 3 | 4K | 20 KB |
| `eurostat-pop-nuts3` | `DEMO_R_D2JAN` | Population on 1 Jan by NUTS 3 (sex × age) | 300K | 1.3 MB |

Full details: [docs/dataset-registry.md](docs/dataset-registry.md)

## Structure

```
eurostat/
├── connectors/         # SDMX-TSV normalizer (universal, DSD-agnostic)
├── datasets/           # dataset.yml + mart.sql per dataflow
│   ├── eurostat-gdp-nuts3/
│   ├── eurostat-gva-nuts3/
│   ├── eurostat-crime-nuts3/
│   └── eurostat-pop-nuts3/
├── codelists/          # geo, unit, freq, flag lookups
├── tests/              # pytest suite (contract tests)
├── docs/               # registry, contributing
├── .github/workflows/  # CI pipeline
└── out/                # pipeline artifacts (gitignored)
```

## Quick start

```bash
# Requires Python 3.12+
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a dataset pipeline (script source requires env var)
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 \
  toolkit run full --config datasets/eurostat-gdp-nuts3/dataset.yml --years 2024
```

## How it works

The connector (`tsv_normalize.py`) downloads SDMX-TSV from the Eurostat API, auto-detects dimensions from the header, and unpivots year columns into analytical rows. Output is a CSV with columns `[dim1..dimN, anno, valore, flag]`.

The toolkit pipeline then:
1. Runs the connector (`type: script`) → raw CSV
2. Applies `clean.sql` → enriches with codelist labels (geo, unit, freq, flags)
3. Applies `mart.sql` → filters Italy, adds business logic

## Dataset registry

See [docs/dataset-registry.md](docs/dataset-registry.md) for the full list of published and planned datasets.

## Contributing

See [docs/contributing.md](docs/contributing.md).

## License

MIT — see [LICENSE](LICENSE).
