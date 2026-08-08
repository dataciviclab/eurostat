-- mart_sintesi — Monthly heating degree days by country: national aggregates
-- and ranking.
--
-- One row per (country, year, month). Reference slice only (unit NR,
-- indic_nrg HDD):
--   • heating degree days (country-level value, monthly)
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
        month,
        geo AS country,
        geo IN (SELECT code FROM eu_countries) AS is_eu,
        MAX(CASE WHEN unit = 'NR' AND indic_nrg = 'HDD' THEN value END) AS hdd_mensile
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, month, geo
)
SELECT
    cv.year,
    cv.month,
    cv.country,
    cv.hdd_mensile,
    -- Cross-country rank (EU27 only, 1 = most heating)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.month, cv.is_eu ORDER BY cv.hdd_mensile DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.hdd_mensile - AVG(cv.hdd_mensile) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year, cv.month))
        / NULLIF(ABS(AVG(cv.hdd_mensile) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year, cv.month)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, cv.month, rank_procapite_eu
