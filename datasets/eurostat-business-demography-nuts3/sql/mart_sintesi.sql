-- mart_sintesi — Business demography by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (indic_sb V11920,
-- sizeclas TOTAL, nace_r2 B-S_X_K642):
--   • enterprise births (country-level value)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- Births are SUMMED from NUTS2 rows (this dataflow has no country-level
-- geo — verified).

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
region_values AS (
    SELECT
        year,
        country,
        country IN (SELECT code FROM eu_countries) AS is_eu,
        value
    FROM clean_input
    WHERE indic_sb = 'V11920'
      AND sizeclas = 'TOTAL'
      AND nace_r2 = 'B-S_X_K642'
      AND nuts_level = 'NUTS2'
      AND value IS NOT NULL
      AND country IS NOT NULL
),
country_values AS (
    SELECT
        year,
        country,
        MAX(is_eu) AS is_eu,
        ROUND(SUM(value), 0) AS nascite_imprese
    FROM region_values
    GROUP BY year, country
)
SELECT
    cv.year,
    cv.country,
    cv.nascite_imprese,
    -- Cross-country rank (EU27 only, 1 = most births)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.nascite_imprese DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.nascite_imprese - AVG(cv.nascite_imprese) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.nascite_imprese) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
