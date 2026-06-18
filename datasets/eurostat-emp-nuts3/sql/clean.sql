-- clean.sql: arricchimento employment — dimensione extra wstatus e nace_r2
SELECT
    r.* EXCLUDE (value, flag),
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    u.label_it AS unit_label_it,
    CASE r.wstatus
        WHEN 'TOTAL' THEN 'Total employment'
        WHEN 'EMP' THEN 'Employed'
        WHEN 'UNE' THEN 'Unemployed'
        WHEN 'INACT' THEN 'Inactive'
        WHEN 'SAL' THEN 'Salaried'
        WHEN 'SELF' THEN 'Self-employed'
        WHEN 'EMPL' THEN 'Employees'
        ELSE r.wstatus
    END AS wstatus_label_en,
    CASE r.nace_r2
        WHEN 'A' THEN 'Agriculture, forestry and fishing'
        WHEN 'B-E' THEN 'Industry (except construction)'
        WHEN 'C' THEN 'Manufacturing'
        WHEN 'F' THEN 'Construction'
        WHEN 'G-I' THEN 'Wholesale, retail, transport'
        WHEN 'G-J' THEN 'Wholesale, retail, transport, ICT'
        WHEN 'J' THEN 'ICT'
        WHEN 'K-N' THEN 'Financial and business services'
        WHEN 'O-U' THEN 'Public admin, education, health'
        WHEN 'TOTAL' THEN 'All NACE activities'
        ELSE r.nace_r2
    END AS nace_label_en,
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
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON r.flag = fl.flag
