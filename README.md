# Eurostat 🇪🇺 — European regional data, open and queryable

**GDP, population, crime, health, education, climate — at NUTS2 (regional) and NUTS3 (provincial) level for every EU country.**

Eurostat for DataCivicLab downloads, normalises and publishes Eurostat SDMX data
as columnar parquet files on Google Cloud Storage. All data is open, free, and
SQL-queryable.

## What's inside

| | |
|---|---|
| **Published datasets** | **21 NUTS3 + 9 NUTS2 + 11 country/NUTS** (41 total) |
| **Period** | 1980 — 2025 (varies by dataset) |
| **Coverage** | All EU + EFTA + candidate countries |
| **Format** | Parquet on public GCS |

### By theme

| Theme | Examples |
|---|---|
| 💼 Economy | GDP, GVA, Employment, Productivity |
| 👥 Demography | Population, Deaths, Births, Ageing |
| 🌍 Migration | Foreign population, residence permits, asylum, citizenship, returns |
| 🚓 Crime | Recorded offences by ICCS |
| 🏨 Tourism | Nights spent at accommodation |
| 🚗 Transport | Road accidents, modal split (passengers/freight), vehicle stock, networks |
| 🌡️ Climate | Heating/cooling degree days |
| 🌱 Environment | Soil erosion |
| 🏢 Business | Enterprise births/deaths |
| 🏥 Health | Physicians, Hospital beds |
| 📊 Social | Poverty risk, Income inequality |
| 📚 Education | Early school leaving, Tertiary attainment |
| 🔬 Innovation | R&D expenditure |

Full list: [docs/dataset-registry.md](docs/dataset-registry.md)

> **Note**: all 41 datasets use the declarative SDMX pipeline (`type: sdmx`,
> agency ESTAT). The two historical script-based connectors
> (`eurostat-bd-hgnace2-r3-nuts3`, `eurostat-pop-nuts3`) were migrated to SDMX
> and now produce the same analytical marts as the rest of the catalog.

## Questions you can answer

- **Which Italian province has the highest GDP per capita?** And the lowest?
- **How does the crime rate compare between European regions?**
- **Which regions have the oldest population?** And the youngest?
- **Where is R&D spending growing fastest in Europe?**
- **How does the poverty risk differ between northern and southern Europe?**
- **How does Italy's migration profile compare with the rest of the EU?** (foreign population, permits, asylum, returns)

## Three ways to access

### 1. Via MCP (toolkit)

All datasets are accessible via the DataCivicLab **toolkit MCP server** — the
single MCP entry point for every Lab dataset. Connect it to your AI client:

```sql
-- GDP per capita of Italian provinces (2024)
SELECT geo_label_en, ROUND(value) AS gdp_pc
FROM eurostat_gdp_nuts3
WHERE geo LIKE 'IT%' AND unit='EUR_HAB' AND year=2024
ORDER BY value DESC;
```

**Available tools**: `toolkit_find`, `toolkit_dataset_overview`,
`toolkit_layer` (SQL query; mart tables via `table=mart_sintesi|mart_trend|
mart_geo_benchmark`), `toolkit_registry_show` (codelists).

### 2. Via DuckDB directly

```python
import duckdb
duckdb.sql("""
    SELECT geo_label_en, ROUND(value) AS gdp_pc
    FROM read_parquet('gs://dataciviclab-clean/eurostat/eurostat_gdp_nuts3/*_clean.parquet')
    WHERE geo LIKE 'IT%' AND unit='EUR_HAB' AND year=2024
    ORDER BY value DESC
""").show()
```

### 3. Via download parquet

Public GCS buckets:
- Clean: `gs://dataciviclab-clean/eurostat/{slug}/`
- Mart: `gs://dataciviclab-mart/eurostat/{slug}/`

## Discussions by theme

| Theme | Discussion |
|---|---|
| 💼 [Economy](https://github.com/dataciviclab/eurostat/discussions/93) | Labour productivity across the EU |
| 📚 [Education](https://github.com/dataciviclab/eurostat/discussions/94) | Early school leaving |
| 🏥 [Health](https://github.com/dataciviclab/eurostat/discussions/95) | Hospital bed capacity |
| 🏢 [Business](https://github.com/dataciviclab/eurostat/discussions/96) | Enterprise births |
| 🔬 [R&D](https://github.com/dataciviclab/eurostat/discussions/97) | R&D spending |

## Contribute

- [Discussions](https://github.com/dataciviclab/eurostat/discussions) — questions, findings, ideas
- [Good first issues](https://github.com/dataciviclab/eurostat/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- [Contributing guide](docs/contributing.md) — how to add a dataset

## Technical docs

- [Dataset registry](docs/dataset-registry.md) — published + planned
- [License: MIT](LICENSE)

## Data licence

Code is MIT. The underlying data is Eurostat's: reuse is allowed, including
commercially, with source attribution (Commission Decision 2011/833/EU on the
reuse of Commission documents — "© European Union, 1995–2026, source: Eurostat").
Each published dataset keeps the original Eurostat dataflow code in
`registry.dataflow` so every number can be traced back to its source.

Part of [DataCivicLab](https://github.com/dataciviclab).
