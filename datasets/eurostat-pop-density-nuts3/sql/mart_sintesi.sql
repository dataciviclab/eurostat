-- mart_sintesi — Population density by country: national aggregates and ranking.
--
-- One row per (country, year). Reference unit PER_KM2:
--   • population density (country-level value)
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
        MAX(CASE WHEN unit = 'PER_KM2' THEN value END) AS densita_km2
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.densita_km2,
    -- Cross-country rank (EU27 only, 1 = highest density)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.densita_km2 DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.densita_km2 - AVG(cv.densita_km2) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.densita_km2) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
