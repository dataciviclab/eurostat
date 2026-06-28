-- mart.sql: Italy NUTS3 view — all dimensions preserved
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    freq,
    freq_label_en,
    indic_sb,
    indic_sb_label_en,
    nace_r2,
    nace_r2_label_en,
    value,
    flag,
    flag_desc_en
FROM clean_input
WHERE geo LIKE 'IT%'
  AND nuts_level = 'NUTS3'
  AND value IS NOT NULL
ORDER BY year DESC, geo
