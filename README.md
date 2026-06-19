# Eurostat 🇪🇺 for DataCivicLab

[![CI](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml/badge.svg)](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Data on GCS](https://img.shields.io/badge/data-GCS-blue)](https://console.cloud.google.com/storage/browser/dataciviclab-clean/eurostat)
[![MCP](https://img.shields.io/badge/MCP-ready-purple)](eurostat-mcp/server.py)
[![Contributors welcome](https://img.shields.io/badge/contributors-welcome-brightgreen)](docs/contributing.md)
[![Discussions](https://img.shields.io/badge/discussions-join-8B5CF6)](https://github.com/dataciviclab/eurostat/discussions)

**Eurostat datasets, connectors and pipelines** — designed for regional (NUTS2/NUTS3) analysis across Europe.
Part of [DataCivicLab](https://github.com/dataciviclab), a civic data laboratory.

## What this is

A reproducible pipeline that fetches, normalizes and publishes Eurostat SDMX-TSV data as columnar parquet files on Google Cloud Storage.

- **Raw**: SDMX-TSV bulk download — all EU countries, all available years
- **Clean**: unpivoted rows + codelist enrichment (geo hierarchy, unit labels, quality flags) — **public on GCS**
- **Mart**: Italy-focused views with business logic — **public on GCS**

## Published datasets

See [docs/dataset-registry.md](docs/dataset-registry.md) for the full list of published and planned datasets (slug, dataflow, theme, row count, status).

## Access the data

### Via MCP (recommended for AI agents)

The repo includes an MCP server exposing 4 tools:

| Tool | Description |
|---|---|
| `eurostat_list_datasets` | List available datasets with metadata |
| `eurostat_describe_dataset` | Inspect schema, years, and dimension values |
| `eurostat_query` | Run SQL against a dataset (`FROM data`) |
| `eurostat_get_codelist` | Resolve freq/unit/flag/nuts_italy codes |

Source: [eurostat-mcp/server.py](eurostat-mcp/server.py)

Register in your MCP client:

```json
{
  "eurostat": {
    "command": ["python", "path/to/eurostat-mcp/server.py"],
    "env": { "PYTHONPATH": "path/to/eurostat-mcp" },
    "enabled": true
  }
}
```

### Direct DuckDB access

All datasets are public on GCS. Query directly with DuckDB:

```python
import duckdb

# GDP per capita of Italian provinces (latest year)
duckdb.sql("""
    SELECT geo, value
    FROM read_parquet('gs://dataciviclab-clean/eurostat/eurostat_gdp_nuts3/*_clean.parquet')
    WHERE geo LIKE 'IT%' AND unit = 'EUR_HAB'
    ORDER BY value DESC
""").show()

# Population by region (from mart, Italy-filtered)
duckdb.sql("""
    SELECT geo, SUM(value) AS pop
    FROM read_parquet('gs://dataciviclab-mart/eurostat/eurostat_pop_nuts3/mart_pop_nuts3.parquet')
    WHERE sex = 'T' AND age = 'TOTAL'
    GROUP BY geo
    ORDER BY pop DESC
""").show()
```

GCS buckets (public):
- **Clean**: `gs://dataciviclab-clean/eurostat/{slug}/` — parquet per year (`*_clean.parquet`)
- **Mart**: `gs://dataciviclab-mart/eurostat/{slug}/` — Italy-filtered views

## Structure

```
eurostat/
├── connectors/          # SDMX-TSV normalizer (universal, DSD-agnostic)
├── datasets/            # dataset.yml + clean.sql + mart.sql per dataflow
├── eurostat-mcp/        # MCP server (4 tools)
├── codelists/           # geo, nace_r2, unit, freq, flag lookups
├── scripts/
│   ├── update_codelists.py   # fetches all codelists from Eurostat API
│   └── assess_candidate.py   # probes a new dataflow and generates skeleton
├── tests/               # pytest suite (connector + fixtures)
├── docs/                # dataset registry, contributing guide
└── .github/workflows/   # CI + monthly publish to GCS
```

## Quick start

```bash
# Requires Python 3.12+
pip install -e ".[dev]"
pip install -e ".[mcp]"

# Run all tests
pytest tests/ eurostat-mcp/tests/ -v

# Run a dataset pipeline (script source requires env var)
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 \
  toolkit run full --config datasets/eurostat-gdp-nuts3/dataset.yml --years 2026

# Add a new dataset (probe, generate skeleton, then run pipeline)
python scripts/assess_candidate.py --flow LFST_R_LFE2EMPRT
```

## How it works

The connector (`tsv_normalize.py`) downloads SDMX-TSV from the Eurostat API, detects dimensions from the header, and writes unpivoted **parquet** files with columns `[dim1..dimN, year, value, flag]`.

The toolkit pipeline then:
1. Runs the connector (`type: script`) → raw parquet
2. Applies `clean.sql` → enriches with codelist labels (geo, unit, freq, flags)
3. Applies `mart.sql` → filters Italy, adds business logic
4. **CI publish workflow** → syncs clean + mart parquet to GCS

## Get involved

- **Discuss** — join [GitHub Discussions](https://github.com/dataciviclab/eurostat/discussions) to ask questions, share findings, propose new datasets or methods.
- **Good first issues** — [browse beginner-friendly tasks](https://github.com/dataciviclab/eurostat/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) to add a new Eurostat dataflow.
- **DataCivicLab Forum** — larger conversations about civic data in Italy happen on the [main Lab hub](https://github.com/orgs/dataciviclab/discussions).

## Contributing

See [docs/contributing.md](docs/contributing.md).

## License

MIT — see [LICENSE](LICENSE).
