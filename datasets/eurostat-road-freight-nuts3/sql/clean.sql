-- clean.sql: ROAD_GO_NA_RU3G — national road freight transport by region of
-- unloading (NUTS3) and type of goods, enriched.
--
-- Real DSD dimensions (verified on the ESTAT DSD): freq, nst07, unit, geo.
-- nst07 = NST 2007 goods classification (TOTAL, GT01-GT20, UNK), enriched
-- with labels from the NST07 support codelist. unit = THS_T only
-- (thousand tonnes).
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: geo = region of UNLOADING (destination of goods), national
-- transport only (hauliers registered in the reporting country).

SELECT
    r.freq,
    r.nst07,
    r.unit,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    n.label_en AS nst07_label_en,
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
LEFT JOIN read_parquet('{support.nst07.path}') n ON r.nst07 = n.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
