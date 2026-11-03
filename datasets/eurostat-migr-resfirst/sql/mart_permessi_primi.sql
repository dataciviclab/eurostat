-- mart_permessi_primi.sql: primi permessi di soggiorno per motivo, paese x anno.
--
-- Slice: citizen = TOTAL (tutte le cittadinanze), duration = TOTAL (tutte le
-- durate).
-- Il mart contiene il dettaglio per motivo (FAM/EDUC/EMP/OTH) E la riga
-- aggregata ufficiale (reason='TOTAL', `is_total = true`): per sommare i motivi
-- filtrare `WHERE NOT is_total`, altrimenti si conta il doppio.
-- `country` resta NULL sugli aggregati (EU27_2020, ...): usare geo per quelli.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    reason,
    reason_label_en,
    (reason = 'TOTAL') AS is_total,
    CAST(value AS BIGINT) AS permessi
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND duration = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, reason
