-- clean.sql: TGS00109 — tertiary educational attainment by NUTS2 region,
-- enriched.
--
-- Extra dimensions vs the base pattern: isced11 (level), age, sex. Their
-- labels are simple code mappings — kept inline via CASE. freq/unit/flag
-- come from `support:` codelists.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: higher value = better (higher tertiary attainment, unit PC).

SELECT
    r.freq,
    r.unit,
    r.isced11,
    r.age,
    r.sex,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    CASE r.isced11
        WHEN 'ED5-8' THEN 'Tertiary education (levels 5-8)'
    END AS isced11_label_en,
    CASE r.age
        WHEN 'Y25-64' THEN 'From 25 to 64 years'
    END AS age_label_en,
    CASE r.sex
        WHEN 'M' THEN 'Male'
        WHEN 'F' THEN 'Female'
        WHEN 'T' THEN 'Total'
    END AS sex_label_en,
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
