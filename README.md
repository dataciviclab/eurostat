# Eurostat 🇪🇺 for DataCivicLab

[![CI](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml/badge.svg)](https://github.com/dataciviclab/eurostat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![Data on GCS](https://img.shields.io/badge/data-GCS-blue)](https://console.cloud.google.com/storage/browser/dataciviclab-clean/eurostat)
[![MCP](https://img.shields.io/badge/MCP-ready-purple)](eurostat-mcp/server.py)

**Eurostat datasets, connectors and pipelines** — designed for regional (NUTS2/NUTS3) analysis across Europe.  
Part of [DataCivicLab](https://github.com/dataciviclab), a civic data laboratory.

## What this is

A reproducible pipeline that fetches, normalizes and publishes Eurostat SDMX-TSV data as columnar parquet files on Google Cloud Storage.

- **Raw**: SDMX-TSV bulk download — all EU countries, all available years
- **Clean**: unpivoted rows + codelist enrichment (geo hierarchy, unit labels, quality flags) — **public on GCS**
- **Mart**: Italy-focused views with business logic — **public on GCS**

## Published datasets

| Dataset | Dataflow | Theme | Clean rows | Clean size | GCS |
|---|---|---|---|---|---|
| `eurostat-gdp-nuts3` | `NAMA_10R_3GDP` | Regional GDP by NUTS 3 | 308K | 1.1 MB | ✅ |
| `eurostat-gva-nuts3` | `NAMA_10R_3GVA` | Regional GVA by NUTS 3 (by NACE sector) | 1.3M | 6.5 MB | ✅ |
| `eurostat-crime-nuts3` | `CRIM_GEN` | Recorded crimes by NUTS 3 | 4K | 20 KB | ✅ |
| `eurostat-pop-nuts3` | `DEMO_R_D2JAN` | Population on 1 Jan by NUTS 3 (sex × age) | 300K | 1.3 MB | ✅ |

Full details: [docs/dataset-registry.md](docs/dataset-registry.md)

## Access the data

### Via MCP (recommended for AI agents)

The repo includes an MCP server that exposes 3 tools:

```
eurostat_list_datasets   — list available datasets with metadata
eurostat_query           — run SQL against a dataset (FROM data)
eurostat_get_codelist    — resolve freq/unit/flag/nuts_italy codes
```

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

Example queries:

| Natural language | MCP call |
|---|---|
| "GDP per capita of Italian provinces in 2024" | `eurostat_query(slug="eurostat_gdp_nuts3", sql="SELECT geo, geo_label_en, value FROM data WHERE geo LIKE 'IT%' AND unit='EUR_HAB' ORDER BY value DESC")` |
| "Population of Italy in 2024" | `eurostat_query(slug="eurostat_pop_nuts3", sql="SELECT SUM(value) AS population FROM data WHERE geo LIKE 'IT%' AND unit='NR' AND sex='T' AND age='TOTAL'")` |
| "Crimes in Milan by category" | `eurostat_query(slug="eurostat_crime_nuts3", sql="SELECT iccs, value FROM data WHERE geo='ITC4C' AND unit='NR'")` |
| "What datasets are available?" | `eurostat_list_datasets()` |
| "What does code ITC4 mean?" | `eurostat_get_codelist(codelist_id="nuts_italy")` |

### Direct DuckDB access

All datasets are public on GCS. Query directly with DuckDB:

```python
import duckdb

# GDP per capita of Italian provinces
duckdb.sql("""
    SELECT geo, value
    FROM read_parquet('gs://dataciviclab-clean/eurostat/eurostat_gdp_nuts3/*/*.parquet')
    WHERE geo LIKE 'IT%' AND unit = 'EUR_HAB'
    ORDER BY value DESC
""").show()

# Population by region (from mart, Italy-filtered)
duckdb.sql("""
    SELECT geo, SUM(value) AS pop
    FROM read_parquet('gs://dataciviclab-mart/eurostat/eurostat_pop_nuts3/*/mart_pop_nuts3.parquet')
    WHERE sex = 'T' AND age = 'TOTAL'
    GROUP BY geo
    ORDER BY pop DESC
""").show()
```

GCS paths:
- **Clean** (all EU, all years): `gs://dataciviclab-clean/eurostat/{slug}/*/*.parquet`
- **Mart** (Italy-filtered): `gs://dataciviclab-mart/eurostat/{slug}/*/mart_{slug}.parquet`

### Via CLI (schema-driven facts)

```bash
# Install with CLI dependencies
pip install -e ".[cli]"
pip install git+https://github.com/dataciviclab/lab-connectors.git

# Show facts for all datasets
eurostat

# Show facts for a specific dataset
eurostat gdp
eurostat pop
eurostat crime
eurostat gva

# Each output shows:
# - Top N regions for the main metric (latest year)
# - Category breakdown (by sector, crime type, sex, etc.)
# - Time trend for the representative entity
```

The CLI auto-discovers the dataset schema from the GCS parquet:
columns, available units, years, and category dimensions — no hardcoded
queries. Adding a new dataset to the registry automatically produces
facts for it.

## Structure

```
eurostat/
├── connectors/          # SDMX-TSV normalizer (universal, DSD-agnostic)
├── datasets/            # dataset.yml + mart.sql per dataflow
│   ├── eurostat-gdp-nuts3/
│   ├── eurostat-gva-nuts3/
│   ├── eurostat-crime-nuts3/
│   └── eurostat-pop-nuts3/
├── eurostat/            # CLI package (schema-driven facts)
│   ├── cli.py           # `eurostat facts` command
│   └── _registry.py     # GCS path registry for datasets
├── eurostat-mcp/        # MCP server (3 tools, 34 tests)
├── codelists/           # geo, unit, freq, flag lookups
├── tests/               # pytest suite (connector contract tests)
├── docs/                # registry, contributing
└── .github/workflows/   # CI (test + validate + publish to GCS)
```

## Quick start

```bash
# Requires Python 3.12+
pip install -e ".[dev,cli]"
pip install git+https://github.com/dataciviclab/lab-connectors.git

# Run all tests
pytest tests/ eurostat-mcp/tests/ -v

# Run the CLI
eurostat

# Run a dataset pipeline (script source requires env var)
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 \
  toolkit run full --config datasets/eurostat-gdp-nuts3/dataset.yml --years 2024
```

## How it works

The connector (`tsv_normalize.py`) downloads SDMX-TSV from the Eurostat API, auto-detects dimensions from the header, and unpivots year columns into analytical rows. Output is a CSV with columns `[dim1..dimN, year, value, flag]`.

The toolkit pipeline then:
1. Runs the connector (`type: script`) → raw CSV
2. Applies `clean.sql` → enriches with codelist labels (geo, unit, freq, flags)
3. Applies `mart.sql` → filters Italy, adds business logic
4. **CI publish workflow** → syncs clean + mart parquet to GCS

## Dataset registry

See [docs/dataset-registry.md](docs/dataset-registry.md) for the full list of published and planned datasets.

## Contributing

See [docs/contributing.md](docs/contributing.md).

## License

MIT — see [LICENSE](LICENSE).
