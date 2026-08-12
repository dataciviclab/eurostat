-- mart_sintesi — Population by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit NR, age TOTAL,
-- sex T):
--   • total population (country-level value)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- DEMO_R_D2JAN HAS country-level geo (verified: country value == sum of
-- NUTS2 rows, complete coverage 1990-2025) — no aggregation needed.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
)
SELECT
    year,
    country,
    country IN (SELECT code FROM eu_countries) AS is_eu,
    ROUND(value, 0) AS popolazione,
    -- Cross-country rank (EU27 only, 1 = highest value)
    CASE
        WHEN country IN (SELECT code FROM eu_countries)
        THEN RANK() OVER (PARTITION BY year, country IN (SELECT code FROM eu_countries)
                          ORDER BY ROUND(value, 0) DESC)
        ELSE NULL
    END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (ROUND(value, 0) - AVG(ROUND(value, 0)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year))
        / NULLIF(ABS(AVG(ROUND(value, 0)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM clean_input
WHERE unit = 'NR'
  AND age = 'TOTAL'
  AND sex = 'T'
  AND nuts_level = 'country'
  AND value IS NOT NULL
  AND country IS NOT NULL
ORDER BY year DESC, rank_procapite_eu
