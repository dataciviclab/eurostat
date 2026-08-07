-- mart_sintesi — At-risk-of-poverty by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country:
--   • at-risk-of-poverty share (country-level PC value, %)
--   • rank among EU27 countries by poverty share
--   • % distance from the EU27 country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official PC value; NUTS2 rows are the regional breakdown.

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
        MAX(CASE WHEN unit = 'PC' THEN value END) AS rischio_poverta_pct
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.rischio_poverta_pct,
    -- Cross-country rank (EU27 only) by poverty share (1 = highest poverty, same year)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.rischio_poverta_pct DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.rischio_poverta_pct - AVG(cv.rischio_poverta_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.rischio_poverta_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
