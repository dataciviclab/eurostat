-- mart_benchmark_it.sql: Italia nel contesto UE27 — emigrazioni totali per anno.
--
-- Slice: unit = NR, sex = T, age = TOTAL, agedef = REACH, citizen = TOTAL.
-- L'aggregato geo = 'EU27_2020' con citizen = TOTAL non e' pubblicato per gli
-- anni recenti (solo fino al 2006): l'UE27 e' quindi la somma dei 27 stati
-- membri. posizione_it = rango dell'Italia tra i paesi con dato.

WITH nat AS (
    SELECT year, country, value
    FROM clean_input
    WHERE unit = 'NR'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND agedef = 'REACH'
      AND citizen = 'TOTAL'
      AND country IS NOT NULL
      AND value IS NOT NULL
),
eu27(geo) AS (
    VALUES ('AT'), ('BE'), ('BG'), ('HR'), ('CY'), ('CZ'), ('DK'), ('EE'),
           ('FI'), ('FR'), ('DE'), ('EL'), ('HU'), ('IE'), ('IT'), ('LV'),
           ('LT'), ('LU'), ('MT'), ('NL'), ('PL'), ('PT'), ('RO'), ('SK'),
           ('SI'), ('ES'), ('SE')
),
ue AS (
    SELECT n.year, SUM(n.value) AS value
    FROM nat n
    JOIN eu27 e ON e.geo = n.country
    GROUP BY n.year
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
