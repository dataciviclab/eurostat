-- clean.sql: EDAT_LFSE_16 — abbandono scolastico per regione NUTS2
SELECT
    r.freq,
    r.unit,
    r.sex,
    r.age,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    CASE r.sex
        WHEN 'M' THEN 'Male'
        WHEN 'F' THEN 'Female'
        WHEN 'T' THEN 'Total'
    END AS sex_label_en,
    CASE r.age
        WHEN 'Y18-24' THEN 'From 18 to 24 years'
    END AS age_label_en,
    u.label_en AS unit_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    r.value,
    r.flag,
    fl.description_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON r.freq = f.freq
LEFT JOIN read_csv('codelists/units.csv', auto_detect=true, delim=',', header=true) u ON r.unit = u.unit
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
