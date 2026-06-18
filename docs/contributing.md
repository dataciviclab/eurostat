# Contributing

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
   TOOLKIT_ALLOW_SCRIPT_SOURCE=1 toolkit run full --config datasets/{slug}/dataset.yml --years 2024
   ```

7. **Update** `docs/dataset-registry.md`.

### dataset.yml template

```yaml
root: "../../out"
schema_version: 1

dataset:
  name: "{slug}"
  source_id: "eurostat"
  years: [2024]
  time_coverage:
    start_year: 2000
    end_year: 2024

raw:
  output_policy: overwrite
  sources:
    - name: "eurostat_{dataflow}"
      type: "script"
      args:
        command: "../../connectors/tsv_normalize.py --flow {DATAFLOW_ID}"
        output: "{dataflow_id}_normalized.csv"
        filename: "{dataflow_id}_normalized.csv"
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
    r.* EXCLUDE (valore, flag),
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    u.label_it AS unit_label_it,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    -- Add dimension labels here if your DSD has extra columns
    -- e.g. r.sex, r.age, r.nace_r2, r.iccs, r.wstatus
    r.valore,
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
or NACE sector labels (`eurostat-gva-nuts3`).

### mart.sql template

Standard Italy-filtered view:

```sql
SELECT
    anno,
    geo,
    geo_label_en,
    nuts_level,
    -- your indicators
    valore,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND valore IS NOT NULL
ORDER BY anno DESC, geo
```

## Guidelines

- **clean.sql** — always the same pattern: codelist enrichment. Add dimension-specific labels
  (sex, age, nace) as `CASE` expressions or additional JOINs.
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
