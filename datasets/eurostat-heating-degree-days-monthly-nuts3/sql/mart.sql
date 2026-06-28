-- mart.sql: Gradi giorno mensili NUTS3 — Italia
SELECT
    year,
    month,
    month_label_en,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    freq,
    freq_label_en,
    unit,
    unit_label_en,
    indic_nrg,
    indic_nrg_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit = 'NR'
  AND nuts_level = 'NUTS3'
  AND value IS NOT NULL
ORDER BY year DESC, month DESC, geo, indic_nrg
