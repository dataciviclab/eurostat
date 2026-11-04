-- mart_decisioni_asilo.sql: decisioni di primo grado per tipo di decisione,
-- paese x anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, citizen = TOTAL.
-- `decision`: TOTAL (totale ufficiale), POS (accolte, totale), POS_RFG (status di
-- rifugiato), POS_HUM (protezione umanitaria), POS_SPROT (protezione
-- sussidiaria), NEG (dinieghi).
-- La riga decision = 'TOTAL' ha `is_total = true`: per sommare le categorie
-- filtrare `WHERE NOT is_total`, altrimenti si conta il doppio.
-- `country` NULL sugli aggregati (EU27_2020, ...).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    decision,
    decision_label_en,
    (decision = 'TOTAL') AS is_total,
    CAST(value AS BIGINT) AS decisioni
FROM clean_input
WHERE unit = 'PER'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND citizen = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, decision
