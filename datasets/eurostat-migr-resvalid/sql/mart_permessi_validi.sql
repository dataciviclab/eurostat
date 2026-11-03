-- mart_permessi_validi.sql: permessi di soggiorno validi al 31/12 per motivo,
-- paese x anno.
--
-- Slice: citizen = TOTAL, duration = TOTAL. `reason` e' il solo dettaglio
-- (FAM/EDUC/EMP/RFG/SPROT/OTH): la riga aggregata TOTAL e' ESCLUSA, come nei
-- mart per cittadinanza, per non far sommare il doppio. Attenzione: per l'UE27
-- RFG/SPROT non sono pubblicati, quindi la somma dei motivi < totale ufficiale.
-- `country` NULL sugli aggregati (EU27_2020, ...).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    reason,
    reason_label_en,
    CAST(value AS BIGINT) AS permessi_validi
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND duration = 'TOTAL'
  AND reason != 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, reason
