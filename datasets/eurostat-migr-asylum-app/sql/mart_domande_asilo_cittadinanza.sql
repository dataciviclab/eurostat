-- mart_domande_asilo_cittadinanza.sql: domande di protezione internazionale per
-- cittadinanza del richiedente, paese x anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, applicant = TOTAL.
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
    CAST(value AS BIGINT) AS domande
FROM clean_input
WHERE unit = 'PER'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND applicant = 'TOTAL'
  AND LENGTH(citizen) = 2
  AND citizen NOT IN ('EU', 'EA')
  AND value IS NOT NULL
ORDER BY year, geo, domande DESC
