-- mart.sql: Italy-filtered view on clean data
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    value,
    flag
FROM clean_input
WHERE geo LIKE 'IT%'
  AND value IS NOT NULL
ORDER BY year DESC, geo
