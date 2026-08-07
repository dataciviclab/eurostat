-- mart_sintesi — Offences by country: national aggregates and ranking.
--
-- One row per (country, year, iccs). Built from NUTS3-level data of each
-- country:
--   • offence rate per 100k inhabitants (country-level P_HTHAB value)
--   • rank among EU countries by offence rate per 100k
--   • % distance from the EU country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official P_HTHAB value; NUTS3 rows are the regional breakdown.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
country_values AS (
    SELECT
        year,
        iccs,
        iccs_label_en,
        geo AS country,
        geo IN (SELECT code FROM eu_countries) AS is_eu,
        MAX(CASE WHEN unit = 'P_HTHAB' THEN value END) AS reati_per_100k
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, iccs, iccs_label_en, geo
)
SELECT
    cv.year,
    cv.country,
    cv.iccs,
    cv.iccs_label_en,
    cv.reati_per_100k,
    -- Cross-country rank by offence rate (EU27 only, 1 = highest rate, same year/iccs)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.iccs, cv.is_eu ORDER BY cv.reati_per_100k DESC) ELSE NULL END AS rank_procapite_eu,
    -- % distance from the EU27 country average (same year/iccs)
    ROUND(
        (cv.reati_per_100k - AVG(cv.reati_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year, cv.iccs))
        / NULLIF(ABS(AVG(cv.reati_per_100k) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year, cv.iccs)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, cv.iccs, rank_procapite_eu
