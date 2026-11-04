-- mart_benchmark_it.sql: Italia nel contesto UE27 — domande di asilo totali per
-- anno.
--
-- Slice: unit = PER, sex = T, age = TOTAL, applicant = TOTAL, citizen = TOTAL.
-- L'aggregato geo = 'EU27_2020' e' pubblicato dal 2013; per gli anni in cui
-- manca (2008-2012) l'UE27 e' la somma dei 27 stati membri.
-- posizione_it = rango dell'Italia per numero di domande tra i paesi con dato
-- (1 = piu' domande). quota_it_su_ue27_pct = quota dell'Italia sul totale UE27.
-- Non imputiamo: se UE27 manca, la quota resta NULL.

WITH nat AS (
    SELECT year, country, value
    FROM clean_input
    WHERE unit = 'PER'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND applicant = 'TOTAL'
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
ue_pub AS (
    SELECT year, value
    FROM clean_input
    WHERE unit = 'PER'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND applicant = 'TOTAL'
      AND citizen = 'TOTAL'
      AND geo = 'EU27_2020'
      AND value IS NOT NULL
),
ue_calc AS (
    SELECT n.year, SUM(n.value) AS value
    FROM nat n
    JOIN eu27 e ON e.geo = n.country
    GROUP BY n.year
),
ue AS (
    SELECT COALESCE(p.year, c.year) AS year,
           COALESCE(p.value, c.value) AS value
    FROM ue_pub p
    FULL OUTER JOIN ue_calc c ON c.year = p.year
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
    CAST(r.value AS BIGINT) AS domande_it,
    r.posizione AS posizione_it,
    r.n_paesi,
    CAST(u.value AS BIGINT) AS domande_ue27,
    ROUND(r.value / NULLIF(u.value, 0) * 100, 2) AS quota_it_su_ue27_pct
FROM ranked r
LEFT JOIN ue u ON u.year = r.year
WHERE r.country = 'IT'
ORDER BY r.year
