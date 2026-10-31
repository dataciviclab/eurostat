-- clean.sql: TRAN_R_NET — estensione delle reti di trasporto.

SELECT
    r.freq,
    r.unit,
    r.tra_infr,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    ti.label_en AS tra_infr_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    CASE
        WHEN g.nuts_level IS NOT NULL AND g.nuts_level != '' THEN LEFT(r.geo, 2)
        ELSE NULL
    END AS country,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.label_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_parquet('{support.freq.path}') f ON r.freq = f.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_parquet('{support.tra_infr.path}') ti ON r.tra_infr = ti.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
