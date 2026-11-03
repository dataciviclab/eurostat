-- clean.sql: TRAN_R_VEHST — parco veicolare per tipo, paese e regioni NUTS.

SELECT
    r.freq,
    r.unit,
    r.vehicle,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    v.label_en AS vehicle_label_en,
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
LEFT JOIN read_parquet('{support.vehicle.path}') v ON r.vehicle = v.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
