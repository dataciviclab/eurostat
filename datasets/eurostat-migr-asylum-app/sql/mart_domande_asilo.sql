-- mart_domande_asilo.sql: domande di protezione internazionale per tipo di
-- richiedente, paese x anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, citizen = TOTAL.
-- `applicant`: FRST (prima istanza), SSEQ (reiterate), TOTAL (totale ufficiale).
-- `is_aggregato` marca la riga aggregata (applicant = 'TOTAL'): per sommare
-- FRST + SSEQ filtrare `WHERE NOT is_aggregato`, altrimenti si conta il doppio.
--
-- CAVEAT disponibilita': `SSEQ` e' pubblicato solo dal 2021; `FRST` dal 2008
-- (copertura crescente per paese: 18 nel 2008 → 33 nel 2018). Prima del 2021
-- `FRST + SSEQ <> TOTAL`: non usare `NOT is_aggregato` per ricostruire il
-- totale in quegli anni.
--
-- `country` NULL sugli aggregati (EU27_2020, ...).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    applicant,
    applicant_label_en,
    (applicant = 'TOTAL') AS is_aggregato,
    CAST(value AS BIGINT) AS domande
FROM clean_input
WHERE unit = 'PER'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND citizen = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, applicant
