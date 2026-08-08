-- mart_trend — Monthly heating degree days: multi-year trend and CAGR per
-- region and month.
--
-- One row per (geo, month). Reference slice only (unit NR, indic_nrg HDD).
-- The monthly series is decomposed per calendar month: CAGR compares the
-- same month across years (e.g. January 1980 vs January 2024), removing
-- seasonality.
-- NOTE: a positive CAGR means heating demand is RISING for that month.

WITH yearly AS (
    SELECT
        geo,
        geo_label_en,
        nuts_level,
        country,
        month,
        year,
        value
    FROM clean_input
    WHERE unit = 'NR'
      AND indic_nrg = 'HDD'
      AND value IS NOT NULL
      AND country IS NOT NULL
),
per_geo AS (
    SELECT
        geo,
        geo_label_en,
        nuts_level,
        country,
        month,
        MIN(year) AS first_year,
        MAX(year) AS last_year
    FROM yearly
    GROUP BY geo, geo_label_en, nuts_level, country, month
)
SELECT
    pg.geo,
    pg.geo_label_en,
    pg.nuts_level,
    pg.country,
    pg.month,
    pg.first_year,
    pg.last_year,
    (pg.last_year - pg.first_year) AS years_observed,
    (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.first_year) AS first_value,
    (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.last_year) AS last_value,
    ROUND(
        (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.last_year)
        - (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.first_year), 1
    ) AS delta_abs,
    ROUND(
        ((SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.last_year)
         / NULLIF((SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.first_year), 0) - 1) * 100, 1
    ) AS delta_pct,
    CASE
        WHEN pg.last_year > pg.first_year
             AND (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.first_year) > 0
        THEN ROUND(
            (POWER(
                (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.last_year)
                / (SELECT y.value FROM yearly y WHERE y.geo = pg.geo AND y.month = pg.month AND y.year = pg.first_year),
                1.0 / (pg.last_year - pg.first_year)
            ) - 1) * 100, 3)
        ELSE NULL
    END AS cagr_pct
FROM per_geo pg
ORDER BY pg.country, pg.month, pg.nuts_level, pg.geo
