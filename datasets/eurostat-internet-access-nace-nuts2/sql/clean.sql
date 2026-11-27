-- clean.sql: enrich enterprise internet access raw data with codelist labels and derived columns.

SELECT
    r.freq, r.size_emp, r.indic_is, r.unit, r.nace_r2, r.geo, r.year,
    f.label_en AS freq_label_en,
    se.label_en AS size_emp_label_en,
    ii.label_en AS indic_is_label_en,
    u.label_en AS unit_label_en,
    n.label_en AS nace_r2_label_en,
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
LEFT JOIN read_parquet('{support.size_emp.path}') se ON r.size_emp = se.code
LEFT JOIN read_parquet('{support.indic_is.path}') ii ON r.indic_is = ii.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_csv('{support.nace_r2.path}', auto_detect=true, delim=',', header=true) n ON r.nace_r2 = n.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
