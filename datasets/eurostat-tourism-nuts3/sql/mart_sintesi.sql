-- mart_sintesi — Soil erosion by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit NR, c_resid
-- TOTAL, nace_r2 I551-I553):
--   • total nights spent (country-level)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- Country values are derived from NUTS3 rows (this dataflow has no
-- country-level geo — verified).

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
        MAX(CASE WHEN unit = 'NR' AND c_resid = 'TOTAL' AND nace_r2 = 'I551-I553'
                 THEN value END) AS pernottamenti
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.pernottamenti,
    -- Cross-country rank (EU27 only, 1 = most land at risk)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.pernottamenti DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.pernottamenti - AVG(cv.pernottamenti) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.pernottamenti) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
