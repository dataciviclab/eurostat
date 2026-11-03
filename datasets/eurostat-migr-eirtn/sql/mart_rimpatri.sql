-- mart_rimpatri.sql: rimpatri dopo ordine di allontanamento, paese x anno x
-- destinazione (c_dest).
--
-- Slice: citizen = TOTAL (tutte le cittadinanze), sex = T, age = TOTAL.
-- c_dest = 'THRD' (paese terzo). La riga aggregata TOTAL e' ESCLUSA, come nei
-- mart per cittadinanza, per non far sommare il doppio (per l'IT THRD = TOTAL,
-- per la DE no).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    c_dest,
    c_dest_label_en,
    CAST(value AS BIGINT) AS rimpatri
FROM clean_input
WHERE unit = 'PER'
  AND citizen = 'TOTAL'
  AND sex = 'T'
  AND age = 'TOTAL'
  AND c_dest != 'TOTAL'
  AND value IS NOT NULL
ORDER BY year, geo, c_dest
