-- mart_sintesi — Physicians by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country:
--   • physicians per 100k inhabitants (country-level HAB_P value)
--   • rank among EU27 countries by physicians per 100k
--   • % distance from the EU27 country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official HAB_P value; NUTS2 rows are the regional breakdown.

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
        MAX(CASE WHEN unit = 'HAB_P' THEN value END) AS medici_per_100k
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.medici_per_100k,
    -- Cross-country rank (EU27 only) by physicians per 100k (1 = best staffed, same year)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.medici_per_100k DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.medici_per_100k - AVG(cv.medici_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.medici_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
