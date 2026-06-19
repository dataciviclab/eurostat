-- mart.sql: Pernottamenti turistici NUTS3 — Italia, per residenza e tipo struttura
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    c_resid,
    c_resid_label_en,
    nace_r2,
    nace_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit IN ('NR')
  AND nuts_level = 'NUTS3'
  AND value IS NOT NULL
ORDER BY year DESC, geo, c_resid, nace_r2
