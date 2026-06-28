-- clean.sql: auto-generated for freq, indic_sb, nace_r2, geo
SELECT
    r.freq,
    r.indic_sb,
    r.nace_r2,
    r.geo,
    CAST(r.year AS INTEGER) AS year,
    f.label_en AS freq_label_en,
    sb.label_en AS indic_sb_label_en,
    n.label_en AS nace_r2_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.description_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON r.freq = f.freq
LEFT JOIN read_csv('codelists/indic_sb.csv', auto_detect=true, delim=',', header=true) sb ON r.indic_sb = sb.code
LEFT JOIN read_csv('codelists/nace_r2.csv', auto_detect=true, delim=',', header=true) n ON r.nace_r2 = n.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
