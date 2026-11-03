-- mart_benchmark_it.sql: Italia vs UE27 — composizione dei primi permessi per
-- motivo, in quota % (confronto di composizione, non di volume).
--
-- quota_*_pct = permessi del motivo / TOTALE ufficiale del paese (riga
-- reason='TOTAL'), per anno. Per resfirst i 4 motivi (FAM/EDUC/EMP/OTH) sommano
-- gia' al totale, ma si usa comunque la riga TOTAL per coerenza col resto.
-- delta_pp = quota IT - quota UE27 (punti percentuali). Non imputiamo: se un
-- lato manca, il delta resta NULL.

WITH tot AS (
    SELECT year, geo, value AS tot
    FROM clean_input
    WHERE unit = 'PER'
      AND citizen = 'TOTAL'
      AND duration = 'TOTAL'
      AND geo IN ('IT', 'EU27_2020')
      AND reason = 'TOTAL'
      AND value IS NOT NULL
),
base AS (
    SELECT year, geo, reason, value
    FROM clean_input
    WHERE unit = 'PER'
      AND citizen = 'TOTAL'
      AND duration = 'TOTAL'
      AND geo IN ('IT', 'EU27_2020')
      AND reason IN ('FAM', 'EDUC', 'EMP', 'OTH')
      AND value IS NOT NULL
),
quota AS (
    SELECT b.year, b.geo, b.reason, b.value / NULLIF(t.tot, 0) * 100 AS quota_pct
    FROM base b
    JOIN tot t ON t.year = b.year AND t.geo = b.geo
)
SELECT
    COALESCE(i.year, u.year) AS year,
    COALESCE(i.reason, u.reason) AS reason,
    ROUND(i.quota_pct, 2) AS quota_it_pct,
    ROUND(u.quota_pct, 2) AS quota_ue27_pct,
    ROUND(i.quota_pct - u.quota_pct, 2) AS delta_pp
FROM (SELECT * FROM quota WHERE geo = 'IT') i
FULL OUTER JOIN (SELECT * FROM quota WHERE geo = 'EU27_2020') u
    ON u.year = i.year AND u.reason = i.reason
WHERE COALESCE(i.year, u.year) IS NOT NULL
ORDER BY year, reason
