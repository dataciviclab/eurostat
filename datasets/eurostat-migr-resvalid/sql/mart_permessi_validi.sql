-- mart_permessi_validi.sql: permessi di soggiorno validi al 31/12 per motivo,
-- paese x anno.
--
-- Slice: citizen = TOTAL, duration = TOTAL.
-- Il mart contiene il dettaglio per motivo (FAM/EDUC/EMP/RFG/SPROT/OTH) E la
-- riga aggregata ufficiale (reason='TOTAL', `is_total = true`): per sommare i
-- motivi filtrare `WHERE NOT is_total`, altrimenti si conta il doppio. La riga
-- TOTAL e' l'unico totale affidabile per l'UE27 (dove RFG/SPROT non sono
-- pubblicati, quindi la somma dei motivi e' minore del totale).
-- `country` NULL sugli aggregati (EU27_2020, ...).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    reason,
    reason_label_en,
    (reason = 'TOTAL') AS is_total,
    CAST(value AS BIGINT) AS permessi_validi
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND duration = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, reason
