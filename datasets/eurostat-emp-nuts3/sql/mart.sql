-- mart.sql: vista Italia su clean arricchito
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    wstatus,
    wstatus_label_en,
    nace_r2,
    nace_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND value IS NOT NULL
ORDER BY year DESC, geo, wstatus, nace_r2
