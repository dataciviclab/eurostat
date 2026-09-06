-- clean.sql: NAMQ_10_GDP — Quarterly GDP by NUTS 2 region.
-- Raw has year as "1978-Q1" — extract year and quarter.

SELECT
    r.freq, r.unit, r.s_adj, r.na_item, r.geo,
    CAST(SPLIT_PART(r.year, '-', 1) AS INTEGER) AS year,
    SPLIT_PART(r.year, '-', 2) AS quarter,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    ni.label_en AS na_item_label_en,
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
LEFT JOIN read_parquet('{support.na_item.path}') ni ON r.na_item = ni.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
