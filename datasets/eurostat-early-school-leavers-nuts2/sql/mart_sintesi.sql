-- mart_sintesi — Early school leavers by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country,
-- reference slice only (unit PC, sex T):
--   • early leaving share (country-level PC value, %)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- The country geo (nuts_level = 'country') holds the official PC value.

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
        MAX(CASE WHEN unit = 'PC' AND sex = 'T' THEN value END) AS abbandono_pct
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.abbandono_pct,
    -- Cross-country rank (EU27 only, 1 = highest early leaving)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.abbandono_pct DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.abbandono_pct - AVG(cv.abbandono_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.abbandono_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
