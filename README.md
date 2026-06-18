# Eurostat 🇪🇺 for DataCivicLab

Eurostat datasets, connectors and pipelines — designed for regional (NUTS2/NUTS3) analysis across Europe.

## Structure

```
eurostat/
├── connectors/     # SDMX-TSV connectors, unpivot, discovery
├── datasets/       # dataset.yml + mart.sql per dataflow
├── tests/          # fixtures + test suite
└── docs/           # registry, dimension guide, contributing
```

## Quick start

```bash
pip install -e .   # installs into workspace .venv

# Run a dataset pipeline
toolkit run full --config datasets/eurostat-gdp-nuts3/dataset.yml --years 2024
```

## Dataset registry

See [docs/dataset-registry.md](docs/dataset-registry.md).

## Contributing

See [docs/contributing.md](docs/contributing.md).
