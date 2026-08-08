-- clean.sql: DEMO_R_GIND3 — demographic balance by NUTS3 region, enriched.
--
-- Extra dimension vs the base pattern: indic_de (demographic indicator),
-- enriched with label from the support codelist.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: GROWRT = population growth rate per 1000 inhabitants — the
-- comparable demographic balance metric.

SELECT
    r.freq,
    r.indic_de,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    d.label_en AS indic_de_label_en,
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
LEFT JOIN read_parquet('{support.indic_de.path}') d ON r.indic_de = d.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
