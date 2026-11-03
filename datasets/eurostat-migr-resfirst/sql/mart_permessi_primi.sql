-- mart_permessi_primi.sql: primi permessi di soggiorno per motivo, paese x anno.
--
-- Slice: citizen = TOTAL (tutte le cittadinanze), duration = TOTAL (tutte le
-- durate). `reason` e' il solo dettaglio (FAM/EDUC/EMP/OTH): la riga aggregata
-- TOTAL e' ESCLUSA, come nei mart per cittadinanza, per non far sommare il
-- doppio. Il totale nazionale e' la somma dei motivi (o la riga TOTAL del clean).
-- `country` resta NULL sugli aggregati (EU27_2020, ...): usare geo per quelli.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    reason,
    reason_label_en,
    CAST(value AS BIGINT) AS permessi
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND duration = 'TOTAL'
  AND reason != 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, reason
