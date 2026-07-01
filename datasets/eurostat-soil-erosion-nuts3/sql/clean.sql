-- clean.sql: AEI_PR_SOILER — erosione suolo + label per levels e clc18
SELECT
    r.freq,
    r.levels,
    r.clc18,
    r.unit,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    CASE r.levels
        WHEN 'TOTAL' THEN 'Total'
        WHEN 'MOD' THEN 'Moderate erosion'
        WHEN 'SEV' THEN 'Severe erosion'
        WHEN 'MOD_SEV' THEN 'Moderate to severe erosion'
    END AS levels_label_en,
    CASE r.clc18
        WHEN 'CLC23_321' THEN 'Pastures and natural grassland'
        WHEN 'CLC2X23' THEN 'Agricultural areas (excluding pastures)'
        WHEN 'CLC2_321' THEN 'Agricultural areas and natural grassland'
        WHEN 'CLC2_3X331_332_335' THEN 'Agricultural areas, forest and semi natural areas'
    END AS clc18_label_en,
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
