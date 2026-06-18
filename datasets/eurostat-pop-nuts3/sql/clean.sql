-- clean.sql: DEMO_R_D2JAN — 5 dimensioni (freq,unit,sex,age,geo)
WITH unpivoted AS (
    SELECT *
    FROM (
        UNPIVOT raw_input
            ON COLUMNS(* EXCLUDE "freq,unit,sex,age,geo\TIME_PERIOD")
            INTO
                NAME anno
                VALUE valore_raw
    )
),
parsed AS (
    SELECT
        trim(split_part("freq,unit,sex,age,geo\TIME_PERIOD", ',', 1)) AS freq,
        trim(split_part("freq,unit,sex,age,geo\TIME_PERIOD", ',', 2)) AS unit,
        trim(split_part("freq,unit,sex,age,geo\TIME_PERIOD", ',', 3)) AS sex,
        trim(split_part("freq,unit,sex,age,geo\TIME_PERIOD", ',', 4)) AS age,
        trim(split_part("freq,unit,sex,age,geo\TIME_PERIOD", ',', 5)) AS geo,
        try_cast(trim(anno) AS INTEGER) AS anno,
        CASE
            WHEN regexp_matches(trim(valore_raw), '^\d+(\.\d+)?')
            THEN try_cast(regexp_extract(trim(valore_raw), '^\d+(\.\d+)?', 0) AS DOUBLE)
        END AS valore,
        regexp_extract(trim(valore_raw), '\s+([a-z])$', 1) AS flag
    FROM unpivoted
    WHERE anno IS NOT NULL
)
SELECT
    p.freq,
    f.label_en AS freq_label_en,
    p.unit,
    u.label_en AS unit_label_en,
    p.sex,
    CASE p.sex
        WHEN 'F' THEN 'Female'
        WHEN 'M' THEN 'Male'
        WHEN 'T' THEN 'Total'
        ELSE p.sex
    END AS sex_label_en,
    p.age,
    CASE
        WHEN p.age = 'TOTAL' THEN 'Total'
        WHEN p.age = 'Y_LT1' THEN 'Under 1 year'
        WHEN p.age = 'Y1' THEN '1 year'
        WHEN p.age = 'Y_LT5' THEN 'Under 5 years'
        WHEN p.age = 'Y5' THEN '5 years'
        WHEN p.age = 'Y10' THEN '10 years'
        WHEN p.age LIKE 'Y_GE%' THEN replace(p.age, 'Y_GE', '≥ ') || ' years'
        WHEN p.age LIKE 'Y%' THEN replace(p.age, 'Y', '') || ' years'
        WHEN p.age LIKE 'Y_%' THEN replace(p.age, 'Y_', '') || ' years'
        ELSE p.age
    END AS age_label_en,
    p.geo,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    p.anno,
    p.valore,
    p.flag,
    fl.description_en AS flag_desc_en
FROM parsed p
LEFT JOIN read_csv('codelists/freq.csv', auto_detect=true, delim=',', header=true) f ON p.freq = f.freq
LEFT JOIN read_csv('codelists/units.csv', auto_detect=true, delim=',', header=true) u ON p.unit = u.unit
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON p.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_csv('codelists/flags.csv', auto_detect=true, delim=',', header=true) fl ON p.flag = fl.flag
