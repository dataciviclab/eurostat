-- mart.sql: Reati denunciati NUTS3 — Italia
SELECT
    anno,
    geo,
    geo_label_en,
    nuts_level,
    iccs,
    unit,
    valore,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit = 'NR'
  AND valore IS NOT NULL
ORDER BY anno DESC, geo, iccs
