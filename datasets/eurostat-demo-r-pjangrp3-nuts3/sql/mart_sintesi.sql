-- mart_sintesi — Population by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit NR, age TOTAL,
-- sex T).
--
-- NOTE: this dataflow (this dataflow) publishes NUTS2 only — there is no
-- country-level geo in the source (verified: nuts_level='country' has zero
-- rows). Country values are therefore aggregated from NUTS2 rows (simple
-- mean of the regional values).

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
    WHERE unit = 'NR'
      AND age = 'TOTAL'
      AND sex = 'T'
      AND nuts_level = 'NUTS2'
      AND value IS NOT NULL
      AND country IS NOT NULL
),
country_values AS (
    SELECT
        year,
        country,
        MAX(is_eu) AS is_eu,
        ROUND(SUM(value), 0) AS popolazione
    FROM region_values
    GROUP BY year, country
)
SELECT
    cv.year,
    cv.country,
    cv.popolazione,
    -- Cross-country rank (EU27 only, 1 = highest value)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.popolazione DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.popolazione - AVG(cv.popolazione) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.popolazione) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
