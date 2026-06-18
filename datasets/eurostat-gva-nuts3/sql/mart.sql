-- mart.sql: Valore Aggiunto Lordo NUTS3 — Italia, per settore NACE
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    nace_r2,
    nace_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit IN ('CP_MEUR')
  AND value IS NOT NULL
ORDER BY year DESC, geo, nace_r2
