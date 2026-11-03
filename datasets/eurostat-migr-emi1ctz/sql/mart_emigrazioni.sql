-- mart_emigrazioni.sql: emigrazioni per cittadinanza, paese x anno.
--
-- Slice: unit = NR, sex = T, age = TOTAL, agedef = REACH.
--   Nota: a age = TOTAL i due agedef (REACH/COMPLET) coincidono (verificato sui
--   dati 2023), quindi filtrare REACH non perde informazione.
-- `citizen` e' la cittadinanza del migrante: si tengono le sole cittadinanze
-- reali (codici ISO-3166 alpha-2), esclusi gli aggregati (TOTAL, EU27_2020,
-- EUR, ...). Il totale nazionale vive in mart_benchmark_it.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    citizen,
    citizen_label_en,
    CAST(value AS BIGINT) AS emigrazioni
FROM clean_input
WHERE unit = 'NR'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND agedef = 'REACH'
  AND LENGTH(citizen) = 2
  AND citizen NOT IN ('EU', 'EA')
  AND value IS NOT NULL
ORDER BY year, geo, emigrazioni DESC
