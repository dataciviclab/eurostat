-- mart_popolazione_cittadinanza.sql: residenti per cittadinanza, paese x anno.
--
-- Slice: unit = NR, sex = T, age = TOTAL.
-- Sono tenute le sole cittadinanze reali (codici ISO-3166 alpha-2), escluse le
-- aggregazioni (TOTAL, NAT, EU27_2020, EXT_EU27_2020, ...). La regola euristica
-- `LENGTH(citizen) = 2` scarta gli aggregati (che hanno codici piu' lunghi) e
-- tiene i paesi; restano fuori solo EU/EA, esclusi esplicitamente.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    citizen,
    citizen_label_en,
    CAST(value AS BIGINT) AS persone
FROM clean_input
WHERE unit = 'NR'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND LENGTH(citizen) = 2
  AND citizen NOT IN ('EU', 'EA')
  AND value IS NOT NULL
ORDER BY year, geo, persone DESC
