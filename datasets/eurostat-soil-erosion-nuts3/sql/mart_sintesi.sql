-- mart_sintesi — Soil erosion by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit PC, levels
-- TOTAL, clc18 CLC2_3X331_332_335):
--   • total soil erosion (country-level, tonnes)
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
        MAX(CASE WHEN unit = 'T' AND levels = 'TOTAL' AND clc18 = 'CLC2_3X331_332_335'
                 THEN value END) AS erosione_tonn
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.erosione_tonn,
    -- Cross-country rank (EU27 only, 1 = most land at risk)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.erosione_tonn DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.erosione_tonn - AVG(cv.erosione_tonn) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.erosione_tonn) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
