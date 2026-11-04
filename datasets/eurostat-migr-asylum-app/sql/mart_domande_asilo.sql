-- mart_domande_asilo.sql: domande di protezione internazionale per tipo di
-- richiedente, paese x anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, citizen = TOTAL.
-- `applicant`: FRST (prima istanza), SSEQ (reiterate), TOTAL (totale ufficiale).
-- La riga applicant = 'TOTAL' ha `is_total = true`: per sommare FRST + SSEQ
-- filtrare `WHERE NOT is_total`, altrimenti si conta il doppio.
-- `country` NULL sugli aggregati (EU27_2020, ...).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    applicant,
    applicant_label_en,
    (applicant = 'TOTAL') AS is_total,
    CAST(value AS BIGINT) AS domande
FROM clean_input
WHERE unit = 'PER'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND citizen = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, applicant
