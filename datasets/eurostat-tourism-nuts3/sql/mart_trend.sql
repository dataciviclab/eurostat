-- mart_trend — Soil erosion: multi-year trend and CAGR per region.
--
-- One row per (geo, unit). Reference slice only (unit NR, c_resid TOTAL,
-- nace_r2 I551-I553). NOTE: a positive CAGR means more land at
-- erosion risk (worse).

WITH yearly AS (
    SELECT
        geo,
        geo_label_en,
        nuts_level,
        country,
        year,
        value
    FROM clean_input
    WHERE unit = 'NR'
      AND c_resid = 'TOTAL'
      AND nace_r2 = 'I551-I553'
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
)
SELECT
    pg.geo,
    pg.geo_label_en,
    pg.nuts_level,
    pg.country,
    pg.first_year,
    pg.last_year,
    (pg.last_year - pg.first_year) AS years_observed,
    (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.first_year) AS first_value,
    (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.last_year) AS last_value,
    ROUND(
        (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.last_year)
        - (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.first_year), 2
    ) AS delta_abs,
    ROUND(
        ((SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.last_year)
         / NULLIF((SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.first_year), 0) - 1) * 100, 1
    ) AS delta_pct,
    CASE
        WHEN pg.last_year > pg.first_year
             AND (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.first_year) > 0
        THEN ROUND(
            (POWER(
                (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.last_year)
                / (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.year = pg.first_year),
                1.0 / (pg.last_year - pg.first_year)
            ) - 1) * 100, 3)
        ELSE NULL
    END AS cagr_pct
FROM per_geo pg
ORDER BY pg.country, pg.nuts_level, pg.geo
