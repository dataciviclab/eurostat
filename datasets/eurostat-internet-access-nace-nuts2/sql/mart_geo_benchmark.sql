-- mart_geo_benchmark — Enterprise internet access by region: EU27 benchmarks per speed class.
-- Totale attività escluso settore finanziario (C10-S951_X_K), imprese con 10+ addetti.
-- NUTS 2 disponibile solo per alcuni paesi: per IT, DE, FR ecc. solo livello nazionale.

WITH base AS (
    SELECT
        year, geo, geo_label_en, nuts_level, country,
        nuts_parent_code, nuts_parent_label_en,
        indic_is, indic_is_label_en,
        value, flag, flag_desc_en
    FROM clean_input
    WHERE nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
      AND country IS NOT NULL
      AND value IS NOT NULL
),
eu27 AS (
    SELECT year, indic_is, value AS valore_eu27
    FROM clean_input
    WHERE geo = 'EU27_2020' AND nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
),
eu_ranked AS (
    SELECT year, geo, indic_is,
        PERCENT_RANK() OVER (
            PARTITION BY year, nuts_level, indic_is
            ORDER BY value
        ) AS percentile_eu
    FROM base
),
benchmarks AS (
    SELECT year, nuts_level, indic_is,
           AVG(value) AS media_eu_value
    FROM base
    GROUP BY year, nuts_level, indic_is
),
country_avg AS (
    SELECT year, country, indic_is,
           AVG(value) AS media_paese_value
    FROM base
    WHERE nuts_level = 'NUTS2'
    GROUP BY year, country, indic_is
)
SELECT
    b.*,
    e.valore_eu27,
    bm.media_eu_value,
    ca.media_paese_value,
    er.percentile_eu,
    ROUND(b.value - e.valore_eu27, 2) AS distanza_eu27_pp,
    CASE
        WHEN bm.media_eu_value IS NOT NULL AND bm.media_eu_value != 0
        THEN ROUND((b.value - bm.media_eu_value) / bm.media_eu_value * 100, 2)
        ELSE NULL
    END AS distanza_media_eu_pct
FROM base b
LEFT JOIN eu27 e ON b.year = e.year AND b.indic_is = e.indic_is
LEFT JOIN benchmarks bm ON b.year = bm.year AND b.nuts_level = bm.nuts_level AND b.indic_is = bm.indic_is
LEFT JOIN country_avg ca ON b.year = ca.year AND b.country = ca.country AND b.indic_is = ca.indic_is
LEFT JOIN eu_ranked er ON b.year = er.year AND b.geo = er.geo AND b.indic_is = er.indic_is
ORDER BY b.year, b.geo, b.indic_is
