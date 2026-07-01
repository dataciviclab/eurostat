-- mart.sql: Medici per regione NUTS2 — Italia
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    freq,
    freq_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND nuts_level = 'NUTS2'
  AND value IS NOT NULL
ORDER BY year DESC, geo
