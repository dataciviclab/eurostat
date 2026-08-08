-- clean.sql: BD_SIZE_R3 — business demography by NUTS3 region, enriched.
--
-- Extra dimensions vs the base pattern: indic_sb (business indicator),
-- sizeclas (size class) and nace_r2 (NACE sector), enriched with labels
-- from the support codelists. No `unit` dimension in this dataflow.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: V11920 = enterprise births. Slice benchmark = indic_sb V11920 +
-- sizeclas TOTAL + nace_r2 B-S_X_K642 (all sectors).

SELECT
    r.freq,
    r.indic_sb,
    r.sizeclas,
    r.nace_r2,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    i.label_en AS indic_sb_label_en,
    sc.label_en AS sizeclas_label_en,
    n.label_en AS nace_r2_label_en,
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
LEFT JOIN read_parquet('{support.indic_sb.path}') i ON r.indic_sb = i.code
LEFT JOIN read_parquet('{support.sizeclas.path}') sc ON r.sizeclas = sc.code
LEFT JOIN read_parquet('{support.nace_r2.path}') n ON r.nace_r2 = n.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
