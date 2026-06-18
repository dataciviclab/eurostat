-- mart.sql: Popolazione NUTS3 — Italia
SELECT
    anno,
    geo,
    geo_label_en,
    nuts_level,
    sex,
    sex_label_en,
    age,
    age_label_en,
    unit,
    valore,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit = 'NR'  -- number of residents
  AND sex = 'T'    -- total (M+F)
  AND age = 'TOTAL'
  AND valore IS NOT NULL
ORDER BY anno DESC, geo
