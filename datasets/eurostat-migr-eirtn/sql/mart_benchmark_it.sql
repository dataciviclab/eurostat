-- mart_benchmark_it.sql: Italia nel contesto UE27 — rimpatri totali per anno.
--
-- Slice: unit = PER, citizen = TOTAL, sex = T, age = TOTAL, c_dest = TOTAL.
-- posizione_it = rango dell'Italia per numero di rimpatri tra i paesi con dato.
-- quota_it_su_ue27_pct = quota dell'Italia sul totale UE27.

WITH nat AS (
    SELECT year, country, value
    FROM clean_input
    WHERE unit = 'PER'
      AND citizen = 'TOTAL'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND c_dest = 'TOTAL'
      AND country IS NOT NULL
      AND value IS NOT NULL
),
ue AS (
    SELECT year, value
    FROM clean_input
    WHERE unit = 'PER'
      AND citizen = 'TOTAL'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND c_dest = 'TOTAL'
      AND geo = 'EU27_2020'
),
ranked AS (
    SELECT
        year,
        country,
        value,
        RANK() OVER (PARTITION BY year ORDER BY value DESC) AS posizione,
        COUNT(*) OVER (PARTITION BY year) AS n_paesi
    FROM nat
)
SELECT
    r.year,
    CAST(r.value AS BIGINT) AS valore_it,
    r.posizione AS posizione_it,
    r.n_paesi,
    CAST(u.value AS BIGINT) AS valore_ue27,
    ROUND(r.value / NULLIF(u.value, 0) * 100, 2) AS quota_it_su_ue27_pct
FROM ranked r
LEFT JOIN ue u ON u.year = r.year
WHERE r.country = 'IT'
ORDER BY r.year
