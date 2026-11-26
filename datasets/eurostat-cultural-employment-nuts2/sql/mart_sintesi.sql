-- mart_sintesi — Cultural employment by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country:
--   • cultural employment share (country-level PC_EMP value)
--   • rank among EU27 countries by cultural employment share
--   • % distance from the EU27 country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official PC_EMP value; NUTS2 rows are the regional breakdown.

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
        MAX(CASE WHEN unit = 'PC_EMP' THEN value END) AS quota_occupazione_culturale_pct
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.quota_occupazione_culturale_pct,
    -- Cross-country rank (EU27 only) by cultural employment share (1 = highest, same year)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.quota_occupazione_culturale_pct DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.quota_occupazione_culturale_pct - AVG(cv.quota_occupazione_culturale_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.quota_occupazione_culturale_pct) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
