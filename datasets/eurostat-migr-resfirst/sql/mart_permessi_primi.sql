-- mart_permessi_primi.sql: primi permessi di soggiorno per motivo, paese x anno.
--
-- Slice: citizen = TOTAL (tutte le cittadinanze), duration = TOTAL (tutte le
-- durate). `reason` include la riga TOTAL oltre a FAM/EDUC/EMP/OTH.
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
  AND value IS NOT NULL
ORDER BY year, geo, reason
