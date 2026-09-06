-- mart_geo_benchmark.sql: GFCF by NUTS 2 with EU27 benchmarks.

WITH base AS (
    SELECT
        year, geo, geo_label_en, nuts_level, country,
        nuts_parent_code, nuts_parent_label_en,
        nace_r2, nace_r2_label_en, currency,
        value, flag, flag_desc_en
    FROM clean_input
    WHERE sector = 'S1' AND currency = 'MIO_EUR' AND nace_r2 = 'TOTAL'
      AND country IS NOT NULL
),
eu_ranked AS (
    SELECT *,
        PERCENT_RANK() OVER (
            PARTITION BY year, nuts_level
            ORDER BY value
        ) AS percentile_eu
    FROM base
),
benchmarks AS (
    SELECT year, nuts_level,
           AVG(value) AS media_eu_value
    FROM base
    GROUP BY year, nuts_level
),
country_avg AS (
    SELECT year, country,
           AVG(value) AS media_paese_value,
           RANK() OVER (PARTITION BY year ORDER BY AVG(value) DESC) AS rank_nazionale
    FROM base
    GROUP BY year, country
)
SELECT
    b.*,
    bm.media_eu_value,
    ca.media_paese_value,
    er.percentile_eu,
    ca.rank_nazionale,
    CASE
        WHEN bm.media_eu_value IS NOT NULL AND bm.media_eu_value != 0
        THEN ROUND((b.value - bm.media_eu_value) / bm.media_eu_value * 100, 2)
        ELSE NULL
    END AS distanza_media_eu_pct
FROM base b
LEFT JOIN benchmarks bm ON b.year = bm.year AND b.nuts_level = bm.nuts_level
LEFT JOIN country_avg ca ON b.year = ca.year AND b.country = ca.country
LEFT JOIN eu_ranked er ON b.year = er.year AND b.geo = er.geo AND b.nuts_level = er.nuts_level
ORDER BY b.year, b.geo
