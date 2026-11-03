-- clean.sql: MIGR_RESFIRST — primi permessi di soggiorno per motivo e durata.
--
-- Dimensions: freq, reason (TOTAL/FAM/EDUC/EMP/OTH), citizen, duration
-- (TOTAL/M3-5/M6-11/M_GE12), unit (PER), geo.
--
-- Contract note: `country` derivato dal prefisso ISO2 del codice geo, ma SOLO
-- per geografie reali (nuts_level valorizzato). Gli aggregati (EU27_2020, EU28)
-- restano a NULL così non inquinano i confronti paese.

SELECT
    r.freq,
    r.reason,
    r.citizen,
    r.duration,
    r.unit,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    re.label_en AS reason_label_en,
    d.label_en AS duration_label_en,
    ci.label_en AS citizen_label_en,
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
LEFT JOIN read_parquet('{support.reason.path}') re ON r.reason = re.code
LEFT JOIN read_parquet('{support.duration.path}') d ON r.duration = d.code
LEFT JOIN read_parquet('{support.citizen.path}') ci ON r.citizen = ci.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
