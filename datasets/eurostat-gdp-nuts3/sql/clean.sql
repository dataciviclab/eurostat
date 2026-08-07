-- clean.sql: enrich raw data with codelist labels and derived columns.
--
-- The raw input already has: freq, unit, geo, year, value, flag
-- (or more dimensions: freq, ..., geo, year, value, flag).
-- Here we enrich with codelist labels.
--
-- Codelists come from `support:` (type codelist, materialized by the toolkit
-- via SdmxSource.fetch_codelist — see dataset.yml). Only the geo hierarchy
-- still reads the repo CSV (nuts_level/parent_code are not in the SDMX
-- codelist annotation set; tracked as debt).
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the geo
-- code, but ONLY for real NUTS geographies (nuts_level in country/NUTS1/NUTS2/NUTS3).
-- Aggregated geographies (EU, EA, G20, ACP, ...) get NULL so they never pollute
-- country-level benchmarks.

SELECT
    r.freq, r.unit, r.geo, r.year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    -- Derived country: ISO2 prefix for real geographies only
    CASE
        WHEN g.nuts_level IS NOT NULL AND g.nuts_level != '' THEN LEFT(r.geo, 2)
        ELSE NULL
    END AS country,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    r.value,
    r.flag,
    fl.label_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_parquet('{support.freq.path}') f ON r.freq = f.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
