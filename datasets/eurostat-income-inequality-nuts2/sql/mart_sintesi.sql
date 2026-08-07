-- mart_sintesi — Income inequality by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country:
--   • S80/S20 quintile share ratio (country-level INX value)
--   • rank among EU27 countries by inequality
--   • % distance from the EU27 country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official INX value; NUTS2 rows are the regional breakdown.

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
        MAX(CASE WHEN unit = 'INX' THEN value END) AS s80s20_ratio
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.s80s20_ratio,
    -- Cross-country rank by inequality (EU27 only, 1 = highest inequality)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.s80s20_ratio DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.s80s20_ratio - AVG(cv.s80s20_ratio) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.s80s20_ratio) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
