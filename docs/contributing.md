# Contributing

## Adding a dataset (intake)

### 1. Scaffold

```bash
# Find your dataflow in the catalog
python scripts/assess_candidate.py --list | grep "keyword"

# Generate dataset.yml + clean.sql + mart.sql
python scripts/assess_candidate.py --flow DATAFLOW_ID --slug eurostat-XXX-nuts3
```

### 2. Codelist

If `clean.sql` has a `-- DIMENSION ... add codelist` comment:
- Add `update_XXX()` to `scripts/update_codelists.py`
- Run `python scripts/update_codelists.py` to fetch it from the SDMX API
- If the codelist already exists, skip.

### 3. Run & verify

```bash
TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run -c datasets/{slug}/dataset.yml --years 2026
```

Then **verify the output before committing**:

```bash
# Schema: check columns and types
toolkit inspect config --config datasets/{slug}/dataset.yml --mode schema

# Preview: spot-check rows
toolkit inspect config --config datasets/{slug}/dataset.yml --mode preview --limit 5

# Mart: check row count and NUTS level distribution
toolkit inspect config --config datasets/{slug}/dataset.yml --layer mart --mode sql --sql "SELECT nuts_level, COUNT(*) AS n FROM data GROUP BY nuts_level"
```

Also review the generated `mart.sql`. The scaffold produces a minimal version — you may want to:
- Keep **all dimensions** (c_resid, nace_r2, unit, label_en, flag_desc_en...)
- Filter by the primary unit (e.g. `unit = 'NR'`)
- For province-level mart: `AND nuts_level = 'NUTS3'`

See `datasets/eurostat-gva-nuts3/sql/mart.sql` for a complete example.

### 4. PR

Update `docs/dataset-registry.md`, branch, commit, push, and open a PR using the repo's template.

## Conventions

| Thing | Rule |
|---|---|
| **Directory slug** | `eurostat-XXX-nuts3` (hyphen) |
| **Dataset name** | `eurostat_XXX_nuts3` (underscore, for GCS compat) |
| **dataset.yml year** | `[2026]` (fictional — TSV contains all years) |
| **clean.sql** | LEFT JOIN on codelists/, never CASE WHEN |
| **New codelist** | Add to `update_codelists.py`, never write CSVs by hand |
| **mart.sql** | Keep all clean columns, filter geo + unit + nuts_level |
| **Labels in mart** | Already in clean, do not repeat JOINs |
| **sample_size: -1** | Only if DuckDB mis-detects column type (e.g. sex T/M/F) |

## NUTS hierarchy

`codelists/geo.csv` includes full NUTS0/1/2/3 tree with `parent_code`. For province marts: `nuts_level = 'NUTS3'`.

## Tests

```bash
pytest tests/ -v
ruff check connectors/ tests/
```
