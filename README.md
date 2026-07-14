# Eurostat 🇪🇺 — European regional data, open and queryable

> **19+ datasets on economy, demography, health, education, crime, climate and environment — at NUTS2 (regional) and NUTS3 (provincial) level for all EU countries.**

Eurostat for DataCivicLab downloads, normalises and publishes Eurostat SDMX data as columnar parquet files on Google Cloud Storage. All data is open, free, and SQL-queryable.

---

## 🟢 Query the data via MCP

All datasets are accessible via an MCP server. Connect it to your AI client (Claude, Copilot, OpenCode) with the standard Lab configuration. Use `eurostat_query` to run SQL on any dataset:

```sql
-- GDP per capita of Italian provinces (2024)
SELECT geo_label_en, ROUND(value) AS gdp_pc
FROM data WHERE geo LIKE 'IT%' AND unit='EUR_HAB' AND year=2024
ORDER BY value DESC;

-- At-risk-of-poverty rate by region (2024)
SELECT geo_label_en, ROUND(value, 1) AS pct
FROM data WHERE unit='PC' AND year=2024 AND geo LIKE 'IT%' AND nuts_level='NUTS2'
ORDER BY value DESC;

-- Early school leaving across Europe (2024)
SELECT geo_label_en, ROUND(value, 1) AS pct
FROM data WHERE unit='PC' AND sex='T' AND year=2024 AND nuts_level='NUTS2'
ORDER BY value DESC;
```

**Available tools:**
- `eurostat_list_datasets` — list with metadata
- `eurostat_describe_dataset` — schema, years, dimensions
- `eurostat_query` — SQL on `FROM data`
- `eurostat_get_codelist` — code lookups

---

## 💬 Join the discussions

**Discussions** are the heart of the project. Each dataset has open questions to explore with data:

| Theme | Discussion |
|---|---|
| 💼 [Economy](https://github.com/dataciviclab/eurostat/discussions/93) | Labour productivity — who produces most per worker in the EU? |
| 📚 [Education](https://github.com/dataciviclab/eurostat/discussions/94) | Early school leaving — who drops out and where? |
| 🏥 [Health](https://github.com/dataciviclab/eurostat/discussions/95) | Hospital beds — healthcare capacity by region |
| 🏢 [Business](https://github.com/dataciviclab/eurostat/discussions/96) | Enterprise births — where are startups created? |
| 🔬 [R&D](https://github.com/dataciviclab/eurostat/discussions/97) | R&D spending — who invests in innovation? |

Found something interesting? Start a discussion. Have a question? Use **Q&A**.

---

## 📦 Data overview

| | |
|---|---|
| **Published datasets** | **19 NUTS3 + 8 NUTS2** (27 total) |
| **Period** | 1980 — 2025 (varies by dataset) |
| **Granularity** | NUTS3 (province) and NUTS2 (region) |
| **Coverage** | All EU + EFTA + candidate countries |
| **Format** | Parquet on public GCS |

### Coverage by theme

| Theme | Datasets |
|---|---|
| 💼 Economy | GDP, GVA, Employment, **Productivity** |
| 👥 Demography | Population, Deaths, Births, Ageing, **Structure** |
| 🚓 Crime | Recorded offences by ICCS |
| 🏨 Tourism | Nights spent at accommodation |
| 🚗 Transport | Road accidents |
| 🌡️ Climate | Heating/cooling degree days |
| 🌱 Environment | Soil erosion |
| 🏢 Business | Enterprise births/deaths, high-growth |
| 🏥 Health | Physicians, Hospital beds |
| 📊 Social | Poverty risk, **Income inequality** |
| 📚 Education | **Early school leaving**, **Tertiary attainment** |
| 🔬 Innovation | **R&D expenditure** |

Full list: [docs/dataset-registry.md](docs/dataset-registry.md)

---

## 🧭 How to use

- **Explore discussions** — each theme starts with an open question
- **Query with SQL** — via MCP or DuckDB directly on GCS
- **Download the parquet** — from public GCS buckets
- **Add a dataset** — see [docs/contributing.md](docs/contributing.md)

### Direct access (DuckDB)

```python
import duckdb

# GDP per capita of Italian provinces
duckdb.sql("""
    SELECT geo_label_en, ROUND(value) AS gdp_pc
    FROM read_parquet('gs://dataciviclab-clean/eurostat/eurostat_gdp_nuts3/*_clean.parquet')
    WHERE geo LIKE 'IT%' AND unit='EUR_HAB' AND year=2024
    ORDER BY value DESC
""").show()
```

**Public GCS buckets:**
- Clean: `gs://dataciviclab-clean/eurostat/{slug}/`
- Mart: `gs://dataciviclab-mart/eurostat/{slug}/`

---

## 📚 Technical docs

- [Dataset registry](docs/dataset-registry.md) — published + planned
- [Contributing](docs/contributing.md) — how to add a dataset
- [Pipeline](.github/workflows/publish.yml) — CI + automatic publish

## Connect

- [GitHub Discussions](https://github.com/dataciviclab/eurostat/discussions) — questions, findings, ideas
- [Good first issues](https://github.com/dataciviclab/eurostat/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — contribute
- [DataCivicLab](https://github.com/dataciviclab) — the lab
- [License: MIT](LICENSE)
