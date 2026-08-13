-- mart_sintesi — Employment rate by country: national aggregates and ranking.
--
-- One row per (country, year). Reference slice only (unit PC, age Y15-64,
-- sex T — total working-age employment rate):
--   • employment rate (country-level %)
--   • rank among EU27 countries (1 = highest employment)
--   • % distance from the EU27 country average
--
-- LFST_R_LFE2EMPRT HAS country-level geo (36 countries, verified) — the
-- employment rate is a percentage, so country values are taken directly
-- (no NUTS2 aggregation; summing percentages would be wrong).

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
)
SELECT
    year,
    country,
    country IN (SELECT code FROM eu_countries) AS is_eu,
    ROUND(value, 1) AS employment_rate_pct,
    -- Cross-country rank (EU27 only, 1 = highest employment rate)
    CASE
        WHEN country IN (SELECT code FROM eu_countries)
        THEN RANK() OVER (PARTITION BY year, country IN (SELECT code FROM eu_countries)
                          ORDER BY ROUND(value, 1) DESC)
        ELSE NULL
    END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (ROUND(value, 1) - AVG(ROUND(value, 1)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year))
        / NULLIF(ABS(AVG(ROUND(value, 1)) FILTER (WHERE country IN (SELECT code FROM eu_countries)) OVER (PARTITION BY year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM clean_input
WHERE unit = 'PC'
  AND age = 'Y15-64'
  AND sex = 'T'
  AND nuts_level = 'country'
  AND value IS NOT NULL
  AND country IS NOT NULL
ORDER BY year DESC, rank_procapite_eu
