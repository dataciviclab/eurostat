-- mart_sintesi — Fertility by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit NR, indic_de
-- TOTFERRT):
--   • total fertility rate (country-level value, children per woman)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- The country geo (nuts_level = 'country') holds the official value.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
country_values AS (
    SELECT
        year,
        geo AS country,
        geo IN (SELECT code FROM eu_countries) AS is_eu,
        MAX(CASE WHEN unit = 'NR' AND indic_de = 'TOTFERRT' THEN value END) AS tasso_fertilita
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.tasso_fertilita,
    -- Cross-country rank (EU27 only, 1 = highest fertility)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.tasso_fertilita DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.tasso_fertilita - AVG(cv.tasso_fertilita) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.tasso_fertilita) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
