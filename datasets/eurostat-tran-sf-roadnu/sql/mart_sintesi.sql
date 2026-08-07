-- mart_sintesi — Road accidents by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS3-level data of each country:
--   • accidents per million inhabitants (country-level P_MHAB value)
--   • rank among EU27 countries by accident rate
--   • % distance from the EU27 country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official P_MHAB value; NUTS3 rows are the regional breakdown.

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
        MAX(CASE WHEN unit = 'P_MHAB' THEN value END) AS incidenti_per_milione
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.incidenti_per_milione,
    -- Cross-country rank by accident rate (EU27 only, 1 = most accidents)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.incidenti_per_milione DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.incidenti_per_milione - AVG(cv.incidenti_per_milione) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.incidenti_per_milione) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
