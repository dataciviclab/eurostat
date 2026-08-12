-- mart_sintesi — Business demography by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (indic_sb V11920,
-- nace_r2 B-S_X_K642):
--   • enterprise births (country-level value)
--   • rank among EU27 countries
--   • % distance from the EU27 country average
--
-- BD_HGNACE2_R3 HAS country-level geo (verified: country value == sum of
-- NUTS2 rows, complete coverage 2008-2020) — no aggregation needed.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
)
SELECT
    year,
    country,
    country IN (SELECT code FROM eu_countries) AS is_eu,
    ROUND(value, 0) AS nascite_imprese,
    -- Cross-country rank (EU27 only, 1 = most births)
    CASE
        WHEN country IN (SELECT code FROM eu_countries)
        THEN RANK() OVER (PARTITION BY year, country IN (SELECT code FROM eu_countries)
                          ORDER BY ROUND(value, 0) DESC)
        ELSE NULL
    END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (ROUND(value, 0) - AVG(ROUND(value, 0)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year))
        / NULLIF(ABS(AVG(ROUND(value, 0)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM clean_input
WHERE indic_sb = 'V11920'
  AND nace_r2 = 'B-S_X_K642'
  AND nuts_level = 'country'
  AND value IS NOT NULL
  AND country IS NOT NULL
ORDER BY year DESC, rank_procapite_eu
