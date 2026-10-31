-- mart_parco.sql: parco veicolare in valore assoluto, geo x anno x tipo veicolo.
-- Esclude l'aggregato TOT_X_TM (somma di categorie non omogenee) e la unit
-- per-1000, che vive nel mart dedicato.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    vehicle,
    vehicle_label_en,
    CAST(value AS BIGINT) AS veicoli
FROM clean_input
WHERE unit = 'NR'
  AND vehicle IS NOT NULL
  AND vehicle != 'TOT_X_TM'
  AND value IS NOT NULL
ORDER BY year, geo, vehicle
