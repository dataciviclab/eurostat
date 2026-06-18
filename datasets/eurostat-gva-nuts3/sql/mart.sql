-- mart.sql: Valore Aggiunto Lordo NUTS3 — Italia
SELECT
    anno,
    geo,
    geo_label_en,
    nuts_level,
    nace_r2,
    nace_label_en,
    unit,
    valore,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit IN ('CP_MEUR')
  AND valore IS NOT NULL
ORDER BY anno DESC, geo, nace_r2
