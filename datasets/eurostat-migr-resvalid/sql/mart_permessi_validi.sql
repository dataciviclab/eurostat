-- mart_permessi_validi.sql: permessi di soggiorno validi al 31/12 per motivo,
-- paese x anno.
--
-- Slice: citizen = TOTAL, duration = TOTAL. `reason` include la riga TOTAL oltre
-- a FAM/EDUC/EMP/RFG/SPROT/OTH. `country` NULL sugli aggregati (EU27_2020, ...).

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
  AND value IS NOT NULL
ORDER BY year, geo, reason
