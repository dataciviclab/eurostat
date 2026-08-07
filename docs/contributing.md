# Contributing

## Adding a dataset (intake)

### 1. Scaffold

Copy an existing migrated dataset as template — `eurostat-poverty-risk-nuts2`
(single-unit) or `eurostat-early-school-leavers-nuts2` (extra dims) are the
reference patterns:

```bash
cp -r datasets/eurostat-poverty-risk-nuts2 datasets/eurostat-{slug}
```

Edit `dataset.yml`:
- `dataset.name` — underscore (GCS compat), `registry.dataflow` — the
  Eurostat flow ID (e.g. `TGS00109`)
- `raw.sources[0]` — `type: sdmx`, `args: {agency: ESTAT, flow: <FLOW_ID>}`
  (declarative fetch via the toolkit ESTAT profile; no ad-hoc scripts)
- `tags`/`category` — from the closed vocabulary (see dataset-incubator
  `docs/candidate-standard.md` Appendice A)
- `support:` — codelists used by clean.sql (freq/unit/flag; iccs for crime)
- `mart.tables` — the 3 analytical marts (benchmark/sintesi/trend) with
  `table_rules` (`primary_key` from the mart GROUP BY / grain)

### 2. Codelists

- `clean.sql` joins codelists via `read_parquet('{support.xxx.path}')` —
  the toolkit materializes them from the SDMX codelist (freq, unit, flag,
  iccs...)
- **geo** stays a repo CSV (`codelists/geo.csv`) — the SDMX annotation set
  (LEVEL only) does not carry `nuts_level` text / `parent_code`; it is
  refreshed by `scripts/update_codelists.py`
- If `clean.sql` needs a new codelist: add `update_XXX()` to
  `scripts/update_codelists.py` (for geo-style CSVs) or a `support:` entry
  with `id` (for SDMX codelists)
- Never write codelists by hand

### 3. Analytical marts

Each migrated dataset produces 3 mart tables (pattern from the benchmark
pilot):

| Mart | Grain | Content |
|---|---|---|
| `mart_geo_benchmark` | geo × year × unit | EU27 average, country average, percentile, national rank, % distance from EU27 average |
| `mart_sintesi` | country × year | national aggregates + EU27 cross-country ranking |
| `mart_trend` | geo | multi-year CAGR and delta |

Rules:
- Benchmark columns computed **only** for the reference slice (e.g.
  `unit='PC' AND sex='T'`) — other breakdown rows carry NULL benchmark
- Benchmark scoped to **EU27** (post-2020, Greece = `EL`) via the
  `eu_countries` CTE — non-EU rows keep media as reference but NULL
  percentile/rank
- Window partitions must include **all** extra dims (sex, age, iccs...) —
  a missing dim skews ranks on tied values (regression found on
  early-school-leavers)
- `RANK()` not `ROW_NUMBER()` — ties share the rank, deterministic

### 4. Run & verify

```bash
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/{slug}/dataset.yml --years 2026
```

Then verify **before committing**:

```bash
# Schema: check columns and types
toolkit inspect config --config datasets/{slug}/dataset.yml --mode schema

# Preview: spot-check rows
toolkit inspect config --config datasets/{slug}/dataset.yml --mode preview --limit 5

# Mart: check row count and NUTS level distribution
toolkit inspect config --config datasets/{slug}/dataset.yml --layer mart --mode sql --sql "SELECT nuts_level, COUNT(*) AS n FROM data GROUP BY nuts_level"
```

Readiness must be **8/8 ready** before PR.

### 5. Tests

Add the dataset to `tests/test_analytical_marts.py`:
- one row in the `ANALYTICAL_DATASETS` list (slug, benchmark unit, extra
  dims via `dim`/`dim2`, single-unit flag if applicable)
- a `Test<Name>Facts` class with verified data facts (rank positions,
  benchmark values, coverage gaps) — the shared contract suite runs
  automatically on the new row

### 6. PR

Update `docs/dataset-registry.md` (if a new dataflow), branch, commit, push,
open a PR using the repo's template. Merged PRs trigger the pipeline
workflow: run + GCS sync + registry + draft registry PR.

## Conventions

| Thing | Rule |
|---|---|
| **Directory slug** | `eurostat-XXX-nuts3` (hyphen) |
| **Dataset name** | `eurostat_XXX_nuts3` (underscore, for GCS compat) |
| **dataset.yml year** | `[2026]` (fictional — TSV contains all years) |
| **Raw source** | `type: sdmx` (ESTAT profile) — no ad-hoc download scripts |
| **Codelists** | `support:` (SDMX) or `update_codelists.py` (geo); never hand-written |
| **Marts** | 3 analytical tables (benchmark/sintesi/trend), EU27-scoped |
| **Labels in mart** | Already in clean, do not repeat JOINs |

## NUTS hierarchy

`codelists/geo.csv` includes full NUTS0/1/2/3 tree with `parent_code`. For
province marts: `nuts_level = 'NUTS3'`. The geo hierarchy is a documented
debt: the SDMX codelist annotation set carries LEVEL (0-3) but not the
`nuts_level` text / `parent_code` — so geo stays a repo CSV.

## Tests

```bash
pytest tests/ -v
ruff check connectors/ tests/ eurostat-mcp/
```
