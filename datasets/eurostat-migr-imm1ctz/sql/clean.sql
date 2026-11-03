-- clean.sql: MIGR_IMM1CTZ — immigrazioni per cittadinanza, sesso, età.
--
-- Dimensions: freq, citizen (cittadinanza; TOTAL/NAT/paesi/aggregati), agedef
-- (REACH/COMPLET), age, unit (NR), sex, geo.
--
-- Contract note: `country` derivato dal prefisso ISO2 del codice geo, ma SOLO
-- per geografie reali (nuts_level valorizzato). Gli aggregati restano a NULL.

SELECT
    r.freq,
    r.citizen,
    r.agedef,
    r.age,
    r.unit,
    r.sex,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    ci.label_en AS citizen_label_en,
    ad.label_en AS agedef_label_en,
    a.label_en AS age_label_en,
    s.label_en AS sex_label_en,
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
LEFT JOIN read_parquet('{support.citizen.path}') ci ON r.citizen = ci.code
LEFT JOIN read_parquet('{support.agedef.path}') ad ON r.agedef = ad.code
LEFT JOIN read_parquet('{support.age.path}') a ON r.age = a.code
LEFT JOIN read_parquet('{support.sex.path}') s ON r.sex = s.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
