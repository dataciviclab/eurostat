-- mart.sql: Indicatori struttura popolazione NUTS3 — Italia
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    freq,
    freq_label_en,
    indic_de,
    indic_de_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND nuts_level = 'NUTS3'
  AND value IS NOT NULL
ORDER BY year DESC, geo, indic_de
