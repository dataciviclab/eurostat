-- clean.sql: LFST_R_LFE2EMPRT — employment rate by sex, age and NUTS2
-- region, enriched.
--
-- Dimensions: freq, unit (PC), sex (M/F/T), age (age group), geo.
-- Sex labels are simple code mappings (inline CASE); age label is the
-- raw code (Y15-24, Y25-34, Y_GE65, TOTAL, ...).
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: slice benchmark = sex T + age Y15-64 (total working-age employment
-- rate, unit PC). Higher value = better (more people employed).

SELECT
    r.freq,
    r.unit,
    r.geo,
    r.sex AS sex,
    r.age AS age,
    CAST(r.year AS INTEGER) AS year,
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
    CASE r.sex
        WHEN 'M' THEN 'Male'
        WHEN 'F' THEN 'Female'
        WHEN 'T' THEN 'Total'
        ELSE r.sex
    END AS sex_label_en,
    r.age AS age_label_en,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.label_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_parquet('{support.freq.path}') f ON r.freq = f.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
