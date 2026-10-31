-- mart_benchmark_it.sql: Italia vs UE27 nel trasporto merci, per anno e modo.
-- delta_pp = quota IT - quota UE27 (punti percentuali). Nessuna imputazione.

WITH it AS (
    SELECT year, tra_mode, value
    FROM clean_input
    WHERE geo = 'IT' AND unit = 'PC' AND tra_mode IN ('ROAD', 'RAIL')
),
ue AS (
    SELECT year, tra_mode, value
    FROM clean_input
    WHERE geo = 'EU27_2020' AND unit = 'PC' AND tra_mode IN ('ROAD', 'RAIL')
),
modi AS (
    SELECT 'strada' AS modo, 'ROAD' AS tra_mode
    UNION ALL SELECT 'ferrovia', 'RAIL'
)
SELECT
    i.year,
    m.modo,
    i.value AS quota_it_pct,
    u.value AS quota_ue27_pct,
    ROUND(i.value - u.value, 2) AS delta_pp
FROM modi m
JOIN it i ON i.tra_mode = m.tra_mode
LEFT JOIN ue u ON u.tra_mode = m.tra_mode AND u.year = i.year
ORDER BY i.year, m.modo
