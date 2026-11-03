-- mart_benchmark_it.sql: Italia vs UE27, per anno e modo.
--
-- delta_pp = quota IT - quota UE27 (punti percentuali). Positivo = l'Italia usa
-- quel modo più della media UE. Righe con uno dei due lati mancante restano con
-- NULL nel delta: non imputiamo.

WITH it AS (
    SELECT year, vehicle, value
    FROM clean_input
    WHERE geo = 'IT'
      AND unit = 'PC'
      AND vehicle IN ('CAR', 'BUS_TOT', 'TRN')
),
ue AS (
    SELECT year, vehicle, value
    FROM clean_input
    WHERE geo = 'EU27_2020'
      AND unit = 'PC'
      AND vehicle IN ('CAR', 'BUS_TOT', 'TRN')
),
modi AS (
    SELECT 'auto' AS modo, 'CAR' AS vehicle
    UNION ALL SELECT 'bus', 'BUS_TOT'
    UNION ALL SELECT 'treno', 'TRN'
)
SELECT
    COALESCE(i.year, u.year) AS year,
    m.modo,
    i.value AS quota_it_pct,
    u.value AS quota_ue27_pct,
    ROUND(i.value - u.value, 2) AS delta_pp
FROM modi m
LEFT JOIN it i ON i.vehicle = m.vehicle
LEFT JOIN ue u ON u.vehicle = m.vehicle AND u.year = i.year
WHERE COALESCE(i.year, u.year) IS NOT NULL
ORDER BY year, modo
