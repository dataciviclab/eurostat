-- mart_decisioni_asilo_cittadinanza.sql: decisioni di primo grado per
-- cittadinanza del richiedente, paese x anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, decision = TOTAL.
-- `citizen` e' la cittadinanza del richiedente: si tengono le sole cittadinanze
-- reali (codici ISO-3166 alpha-2), esclusi gli aggregati (TOTAL, EU27_2020, ...).
-- Il totale nazionale vive in mart_benchmark_it.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    citizen,
    citizen_label_en,
    CAST(value AS BIGINT) AS decisioni
FROM clean_input
WHERE unit = 'PER'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND decision = 'TOTAL'
  AND LENGTH(citizen) = 2
  AND citizen NOT IN ('EU', 'EA')
  AND value IS NOT NULL
ORDER BY year, geo, decisioni DESC
