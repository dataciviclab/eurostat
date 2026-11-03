-- mart_popolazione_straniera.sql: popolazione totale, nazionali e stranieri
-- residenti per paese x anno, con quota di stranieri.
--
-- Slice: unit = NR, sex = T, age = TOTAL.
--   popolazione_totale = citizen TOTAL (tutti i cittadini)
--   nazionali          = citizen NAT  (cittadini del paese di riferimento)
--   stranieri          = totale - nazionali
-- Include la riga geo = EU27_2020 come termine di confronto, ma ATTENZIONE:
-- per l'aggregato UE27 Eurostat pubblica TOTAL/NAT solo per pochi anni
-- (2016, 2018-2020), quindi la riga UE27 esiste solo li' e poi "sparisce".
-- L'Italia (e i singoli paesi) hanno la serie completa 1998-2025.

WITH base AS (
    SELECT year, geo, geo_label_en, nuts_level, country, citizen, value
    FROM clean_input
    WHERE unit = 'NR'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND citizen IN ('TOTAL', 'NAT')
),
piv AS (
    SELECT
        year,
        geo,
        geo_label_en,
        nuts_level,
        country,
        MAX(CASE WHEN citizen = 'TOTAL' THEN value END) AS popolazione_totale,
        MAX(CASE WHEN citizen = 'NAT' THEN value END) AS nazionali
    FROM base
    GROUP BY year, geo, geo_label_en, nuts_level, country
)
SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    CAST(popolazione_totale AS BIGINT) AS popolazione_totale,
    CAST(nazionali AS BIGINT) AS nazionali,
    CAST(popolazione_totale - nazionali AS BIGINT) AS stranieri,
    ROUND((popolazione_totale - nazionali) / NULLIF(popolazione_totale, 0) * 100, 2) AS quota_stranieri_pct
FROM piv
WHERE popolazione_totale IS NOT NULL
ORDER BY year, geo
