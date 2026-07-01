-- mart.sql: Italy NUTS3 — area in km² by land use category
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    freq,
    freq_label_en,
    landuse,
    landuse_label_en,
    unit,
    unit_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND nuts_level = 'NUTS3'
  AND unit = 'KM2'
  AND value IS NOT NULL
ORDER BY year DESC, geo, landuse
