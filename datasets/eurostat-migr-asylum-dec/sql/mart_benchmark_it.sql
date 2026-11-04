-- mart_benchmark_it.sql: Italia nel contesto UE27 — decisioni di primo grado
-- totali per anno, con tasso di riconoscimento.
--
-- Slice: unit = PER, sex = T, age = TOTAL, decision = TOTAL, citizen = TOTAL.
-- L'aggregato geo = 'EU27_2020' e' usato quando pubblicato, altrimenti l'UE27 e'
-- la somma dei 27 stati membri.
-- posizione_it = rango dell'Italia per numero di decisioni tra i paesi con dato
-- (1 = piu' decisioni). quota_it_su_ue27_pct = quota dell'Italia sul totale UE27.
-- tasso_riconoscimento_*_pct = POS / (POS + NEG) * 100 (accolte sulle decisioni
-- di merito). Non imputiamo: se un lato manca, il valore resta NULL.

WITH nat AS (
    SELECT year, country, value
    FROM clean_input
    WHERE unit = 'PER'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND decision = 'TOTAL'
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
      AND decision = 'TOTAL'
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
),
-- POS e NEG per il tasso di riconoscimento (stessa slice, decision specifica).
merito AS (
    SELECT
        year,
        geo,
        MAX(value) FILTER (WHERE decision = 'POS') AS pos,
        MAX(value) FILTER (WHERE decision = 'NEG') AS neg
    FROM clean_input
    WHERE unit = 'PER'
      AND sex = 'T'
      AND age = 'TOTAL'
      AND citizen = 'TOTAL'
      AND decision IN ('POS', 'NEG')
      AND value IS NOT NULL
    GROUP BY year, geo
),
merito_ue_pub AS (
    SELECT year, pos, neg FROM merito WHERE geo = 'EU27_2020'
),
merito_ue_calc AS (
    SELECT m.year,
           SUM(m.pos) AS pos,
           SUM(m.neg) AS neg
    FROM merito m
    JOIN eu27 e ON e.geo = m.geo
    GROUP BY m.year
),
merito_ue AS (
    SELECT COALESCE(p.year, c.year) AS year,
           COALESCE(p.pos, c.pos) AS pos,
           COALESCE(p.neg, c.neg) AS neg
    FROM merito_ue_pub p
    FULL OUTER JOIN merito_ue_calc c ON c.year = p.year
)
SELECT
    r.year,
    CAST(r.value AS BIGINT) AS decisioni_it,
    r.posizione AS posizione_it,
    r.n_paesi,
    CAST(u.value AS BIGINT) AS decisioni_ue27,
    ROUND(r.value / NULLIF(u.value, 0) * 100, 2) AS quota_it_su_ue27_pct,
    ROUND(mi.pos / NULLIF(mi.pos + mi.neg, 0) * 100, 2) AS tasso_riconoscimento_it_pct,
    ROUND(mu.pos / NULLIF(mu.pos + mu.neg, 0) * 100, 2) AS tasso_riconoscimento_ue27_pct
FROM ranked r
LEFT JOIN ue u ON u.year = r.year
LEFT JOIN merito mi ON mi.year = r.year AND mi.geo = 'IT'
LEFT JOIN merito_ue mu ON mu.year = r.year
WHERE r.country = 'IT'
ORDER BY r.year
