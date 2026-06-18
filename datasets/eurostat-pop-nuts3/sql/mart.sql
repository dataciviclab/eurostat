-- mart.sql: Popolazione NUTS3 — Italia, totale per sesso ed età
-- Il clean ha già arricchito le codelist (geo, freq, unit, flag)
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    sex,
    sex_label_en,
    age,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit = 'NR'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year DESC, geo
