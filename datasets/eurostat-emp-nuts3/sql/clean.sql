-- clean.sql: NAMA_10R_3EMPERS — employment by NUTS3 region, enriched.
--
-- Extra dimensions vs the base pattern: wstatus (working status) and
-- nace_r2 (NACE sector), enriched with labels from the support codelists.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: THS = employed persons in thousands. Slice benchmark = wstatus
-- EMP + nace_r2 TOTAL (total employment).

SELECT
    r.freq,
    r.unit,
    r.wstatus,
    r.nace_r2,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    w.label_en AS wstatus_label_en,
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
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_parquet('{support.nace_r2.path}') n ON r.nace_r2 = n.code
LEFT JOIN read_parquet('{support.wstatus.path}') w ON r.wstatus = w.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
