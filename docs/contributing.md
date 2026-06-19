# Contributing

## Before you start

- **Not sure where to begin?** Browse [good first issues](https://github.com/dataciviclab/eurostat/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) — beginner-friendly datasets with step-by-step instructions.
- **Have a question or idea?** Open a [GitHub Discussion](https://github.com/dataciviclab/eurostat/discussions) — the community and maintainers will help.
- **Want to discuss with the broader Lab community?** Join the [DataCivicLab Forum](https://github.com/orgs/dataciviclab/discussions).

## Adding a new dataset

Each Eurostat dataflow maps to one dataset directory. The connector handles TSV parsing and
unpivot automatically — you only need to configure the pipeline and write a mart view.

### Steps

1. **Identify the dataflow ID** — e.g. `NAMA_10R_3GDP`. Search the Eurostat catalog
   or use the [online data browser](https://ec.europa.eu/eurostat/web/main/data/database).

2. **Create a dataset directory**:
   ```bash
   mkdir -p datasets/{slug}/sql
   ```

3. **Create `dataset.yml`** — see template below.

4. **Create `sql/clean.sql`** — codelist enrichment (see template below).
   If your dataflow has extra dimensions beyond `freq, unit, geo`, add their labels here.

5. **Create `sql/mart.sql`** — your business logic (filter, derive indicators).

6. **Run the pipeline**:
   ```bash
   TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run full --config datasets/{slug}/dataset.yml --years $(date +%Y)
   ```

7. **Update** `docs/dataset-registry.md`.

### dataset.yml template

```yaml
root: "../../out"
schema_version: 1

dataset:
  name: "{slug}"
  source_id: "eurostat"
  years: [2026]        # usa l'anno corrente
  time_coverage:
    start_year: 2000    # primo anno disponibile nel dataflow
    end_year: 2026      # ultimo anno disponibile

raw:
  output_policy: overwrite
  sources:
    - name: "eurostat_{dataflow}"
      type: "script"
      args:
        command: "../../connectors/tsv_normalize.py --flow {DATAFLOW_ID}"
        output: "{dataflow_id}_normalized.parquet"
        filename: "{dataflow_id}_normalized.parquet"
      primary: true

clean:
  sql: "sql/clean.sql"
  read:
    source: auto
    mode: latest
    delim: ","
    encoding: utf-8
    header: true
  validate:
    min_rows: 100

mart:
  tables:
    - name: "mart_{slug}"
      sql: "sql/mart.sql"
  required_tables:
    - "mart_{slug}"

validation:
  fail_on_error: true
```

### clean.sql template

Standard codelist enrichment. Customize if the dataflow has extra dimensions:

```sql
SELECT
    r.* EXCLUDE (value, flag),
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    -- Dimension labels: JOIN on existing codelist or create a new one
    -- Examples:
    -- LEFT JOIN read_csv('codelists/nace_r2.csv', …) n ON r.nace_r2 = n.code
    -- LEFT JOIN read_csv('codelists/sex.csv', …) s ON r.sex = s.code
    r.value,
    r.flag,
    fl.description_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON r.freq = f.freq
LEFT JOIN read_csv('codelists/units.csv', auto_detect=true, delim=',', header=true) u ON r.unit = u.unit
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
```

See existing datasets for examples with sex/age labels (`eurostat-pop-nuts3`)
or NACE sector labels (`eurostat-gva-nuts3` and `eurostat-emp-nuts3`).

> **Adding a new dimension codelist**: if your dataflow has a DSD dimension not yet
> in `codelists/` (e.g. `sex`, `age`, `iccs`), create a new CSV with columns `code,label_en`
> (columns: `code,label_en`). Use `LEFT JOIN` in `clean.sql` as shown above. Avoid
> `CASE WHEN` chains — they duplicate logic across datasets.

### mart.sql template

Standard Italy-filtered view:

```sql
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    -- your indicators
    value,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND value IS NOT NULL
ORDER BY year DESC, geo
```

## Guidelines

- **clean.sql** — always the same pattern: codelist enrichment. Add dimension-specific labels
  as `LEFT JOIN` on `codelists/{dim}.csv`. If no CSV exists for the dimension, create one
  (columns: `code,label_en`). Prefer JOINs over `CASE WHEN` chains — they
  avoid logic duplication when the same dimension appears in multiple datasets.
- **mart.sql** — business logic only: filter, derive, rename. No codelist JOINs (already in clean).
- **`sample_size: -1`** — add to `dataset.yml` `clean.read` if DuckDB mis-detects a column type
  (common with `sex` values `T`/`M`/`F`).
- **Validation** — always set `min_rows` in `clean.validate` and `mart.validate.table_rules`.
- **Run requires** `TOOLKIT_ALLOW_SCRIPT_SOURCE=1` — security guard on `type: script`.

## NUTS codes

Eurostat uses the NUTS2021 classification. The `codelists/geo.csv` includes:
- All EU country codes (NUTS0)
- Full Italian hierarchy: NUTS1 (groups), NUTS2 (regions), NUTS3 (provinces)
- `parent_code` for parent-child navigation

## Tests

Always run tests before committing:

```bash
pytest tests/ -v
ruff check connectors/ tests/
```
