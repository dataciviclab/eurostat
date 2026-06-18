-- mart.sql: Popolazione NUTS3 — Italia, totale
SELECT
    anno,
    geo,
    g.label_en AS geo_label_en,
    g.nuts_level,
    sex,
    CASE sex
        WHEN 'F' THEN 'Female' WHEN 'M' THEN 'Male' WHEN 'T' THEN 'Total'
    END AS sex_label_en,
    age,
    valore,
    flag
FROM clean_input
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g
    ON geo = g.code
WHERE geo LIKE 'IT%'
  AND unit = 'NR'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND valore IS NOT NULL
ORDER BY anno DESC, geo
