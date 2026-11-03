-- mart_rimpatri.sql: rimpatri dopo ordine di allontanamento, paese x anno x
-- destinazione (c_dest).
--
-- Slice: citizen = TOTAL (tutte le cittadinanze), sex = T, age = TOTAL.
-- Il mart contiene THRD (paese terzo) E la riga aggregata ufficiale
-- (c_dest='TOTAL', `is_total = true`): per sommare filtrare `WHERE NOT is_total`,
-- altrimenti si conta il doppio. THRD non equivale al totale per tutti i paesi
-- (DE 2024: 18.695 vs 22.005, FR 14.670 vs 16.665), quindi la riga TOTAL serve.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    c_dest,
    c_dest_label_en,
    (c_dest = 'TOTAL') AS is_total,
    CAST(value AS BIGINT) AS rimpatri
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, c_dest
