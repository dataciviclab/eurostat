-- clean.sql: Deaths by age group, sex and NUTS3 region (DEMO_R_MAGEC3)
-- Dimensioni: freq, sex, unit, age, geo

SELECT
    r.freq,
    r.unit,
    r.geo,
    CAST(r.sex AS VARCHAR) AS sex,
    CAST(r.age AS VARCHAR) AS age,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    CASE CAST(r.sex AS VARCHAR)
        WHEN 'M' THEN 'Male'
        WHEN 'F' THEN 'Female'
        WHEN 'T' THEN 'Total'
        ELSE CAST(r.sex AS VARCHAR)
    END AS sex_label_en,
    r.age AS age_label_en,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.description_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON r.freq = f.freq
LEFT JOIN read_csv('codelists/units.csv', auto_detect=true, delim=',', header=true) u ON r.unit = u.unit
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
