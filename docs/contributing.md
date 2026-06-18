# Contributing

## Adding a new dataset

1. Identify the Eurostat dataflow ID (e.g. `NAMA_10R_3GDP`)
2. Create a directory under `datasets/`: `datasets/{slug}/`
3. Create `dataset.yml` with source configuration (see existing examples)
4. Create `sql/mart.sql` with your analysis logic
5. Run the pipeline:
   ```bash
   toolkit run full --config datasets/{slug}/dataset.yml --years 2024
   ```
6. Update `docs/dataset-registry.md`

## Dataset YAML template

```yaml
root: "../../out"
schema_version: 1

dataset:
  name: "{slug}"
  source_id: "eurostat"
  years: [2024]

raw:
  output_policy: overwrite
  sources:
    - name: "eurostat_{dataflow}"
      type: "http_file"
      args:
        url: "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{DATAFLOW_ID}?format=TSV"
        filename: "{dataflow_id}.tsv"
      primary: true

clean:
  sql: "sql/clean.sql"
  read:
    source: auto
    mode: latest
    delim: "\t"
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

## Clean SQL template

```sql
-- Standard clean.sql for Eurostat TSV bulk
-- Unpivots years from columns to rows, parses flags and missing values
SELECT *
FROM (
    UNPIVOT raw_input
        ON COLUMNS(* EXCLUDE "freq,unit,geo\\TIME_PERIOD")
        INTO
            NAME anno
            VALUE valore_raw
)
```

## Guidelines

- Keep `clean.sql` minimal — just UNPIVOT
- Put all business logic in `mart.sql`
- Always add `min_rows` validation
- Document NUTS codes mapping in comments
