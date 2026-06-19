-- clean.sql: demographic balance — dimensione extra indic_de
SELECT
    r.freq,
    r.indic_de,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    d.label_en AS indic_de_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.description_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON r.freq = f.freq
LEFT JOIN read_csv('codelists/indic_de.csv', auto_detect=true, delim=',', header=true) d ON r.indic_de = d.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
