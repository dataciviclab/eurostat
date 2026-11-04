-- mart_sintesi — LTC beds by country: national aggregates and EU27 ranking.
--
-- One row per (country, year):
--   • absolute beds (unit = NR)
--   • beds per 100k inhabitants (unit = P_HTHAB)
--   • inhabitants per bed (unit = HAB_P, inverse density)
--   • rank among EU27 countries by beds per 100k
--   • % distance from the EU27 country average

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
country_values AS (
    SELECT
        year,
        geo AS country,
        geo_label_en AS country_label_en,
        geo IN (SELECT code FROM eu_countries) AS is_eu,
        MAX(CASE WHEN unit = 'NR' THEN value END) AS posti_letto,
        MAX(CASE WHEN unit = 'P_HTHAB' THEN value END) AS posti_letto_per_100k,
        MAX(CASE WHEN unit = 'HAB_P' THEN value END) AS abitanti_per_posto_letto
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo, geo_label_en
)
SELECT
    cv.year,
    cv.country,
    cv.country_label_en,
    cv.posti_letto,
    cv.posti_letto_per_100k,
    cv.abitanti_per_posto_letto,
    -- Cross-country rank (EU27 only) by beds per 100k (1 = best staffed, same year)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.posti_letto_per_100k DESC) ELSE NULL END AS rank_eu,
    -- % distance from the EU27 country average
    ROUND(
        (cv.posti_letto_per_100k - AVG(cv.posti_letto_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.posti_letto_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct,
    cv.is_eu
FROM country_values cv
ORDER BY year DESC, rank_eu
