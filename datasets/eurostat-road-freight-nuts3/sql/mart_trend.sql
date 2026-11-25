-- mart_trend — Road freight unloaded: multi-year trend and CAGR per region.
--
-- One row per geo. Reference slice only (nst07 TOTAL, unit THS_T).
-- NOTE: a positive CAGR means more tonnes unloaded over time (growing
-- national road freight demand at destination). first/last year are the
-- first and last years with a non-null value for that geo.

WITH yearly AS (
    SELECT
        geo,
        geo_label_en,
        nuts_level,
        country,
        year,
        value
    FROM clean_input
    WHERE nst07 = 'TOTAL'
      AND unit = 'THS_T'
      AND value IS NOT NULL
      AND country IS NOT NULL
),
per_geo AS (
    SELECT
        geo,
        geo_label_en,
        nuts_level,
        country,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM yearly
    GROUP BY geo, geo_label_en, nuts_level, country
),
endpoints AS (
    SELECT
        pg.*,
        yf.value AS first_value,
        yl.value AS last_value
    FROM per_geo pg
    JOIN yearly yf ON yf.geo = pg.geo AND yf.year = pg.first_year
    JOIN yearly yl ON yl.geo = pg.geo AND yl.year = pg.last_year
)
SELECT
    e.geo,
    e.geo_label_en,
    e.nuts_level,
    e.country,
    e.first_year,
    e.last_year,
    (e.last_year - e.first_year) AS years_observed,
    e.first_value,
    e.last_value,
    ROUND(e.last_value - e.first_value, 2) AS delta_abs,
    ROUND((e.last_value / NULLIF(e.first_value, 0) - 1) * 100, 1) AS delta_pct,
    CASE
        WHEN e.last_year > e.first_year AND e.first_value > 0 AND e.last_value >= 0
        THEN ROUND((POWER(e.last_value / e.first_value, 1.0 / (e.last_year - e.first_year)) - 1) * 100, 3)
    END AS cagr_pct
FROM endpoints e
ORDER BY e.country, e.nuts_level, e.geo
