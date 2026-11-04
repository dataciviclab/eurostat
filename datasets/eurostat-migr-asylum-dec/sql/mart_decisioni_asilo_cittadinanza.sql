-- mart_decisioni_asilo_cittadinanza.sql: decisioni di primo grado per
-- cittadinanza del richiedente, paese x anno, con tasso di riconoscimento.
--
-- Slice: unit = PER, sex = T, age = TOTAL.
-- `decisioni` = totale decisioni (decision = TOTAL); `accolte`/`dinieghi` =
-- decisioni di merito (POS / NEG); `tasso_riconoscimento_pct` =
-- accolte / (accolte + dinieghi) * 100.
-- `citizen` e' la cittadinanza del richiedente: si tengono le sole cittadinanze
-- reali (codici ISO-3166 alpha-2), esclusi gli aggregati (TOTAL, EU27_2020, ...).
-- Il totale nazionale vive in mart_benchmark_it.

WITH base AS (
    SELECT
        year,
        geo,
        geo_label_en,
        nuts_level,
        country,
        citizen,
        citizen_label_en,
        decision,
        value
    FROM clean_input
    WHERE unit = 'PER'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND LENGTH(citizen) = 2
      AND citizen NOT IN ('EU', 'EA')
      AND decision IN ('TOTAL', 'POS', 'NEG')
      AND value IS NOT NULL
)
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    citizen,
    citizen_label_en,
    CAST(MAX(value) FILTER (WHERE decision = 'TOTAL') AS BIGINT) AS decisioni,
    CAST(MAX(value) FILTER (WHERE decision = 'POS') AS BIGINT) AS accolte,
    CAST(MAX(value) FILTER (WHERE decision = 'NEG') AS BIGINT) AS dinieghi,
    ROUND(
        100.0 * MAX(value) FILTER (WHERE decision = 'POS')
        / NULLIF(
            MAX(value) FILTER (WHERE decision = 'POS')
            + MAX(value) FILTER (WHERE decision = 'NEG'),
            0
        ),
        2
    ) AS tasso_riconoscimento_pct
FROM base
GROUP BY ALL
ORDER BY year, geo, decisioni DESC
