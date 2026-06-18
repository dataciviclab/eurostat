-- mart.sql: Reati denunciati NUTS3 — Italia
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    iccs,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit = 'NR'
  AND value IS NOT NULL
ORDER BY year DESC, geo, iccs
