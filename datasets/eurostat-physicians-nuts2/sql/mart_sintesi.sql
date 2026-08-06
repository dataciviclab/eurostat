-- mart_sintesi — Physicians by country: national aggregates and ranking.
--
-- One row per (country, year). Built from NUTS2-level data of each country:
--   • physicians per 100k inhabitants (country-level HAB_P value)
--   • rank among EU countries by physicians per 100k
--   • % distance from the EU country average
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official HAB_P value; NUTS2 rows are the regional breakdown.

WITH country_values AS (
    SELECT
        year,
        geo AS country,
        MAX(CASE WHEN unit = 'HAB_P' THEN value END) AS medici_per_100k
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
)
SELECT
    cv.year,
    cv.country,
    cv.medici_per_100k,
    -- Cross-country rank by physicians per 100k (1 = best staffed, same year)
    ROW_NUMBER() OVER (PARTITION BY cv.year ORDER BY cv.medici_per_100k DESC) AS rank_procapite_eu,
    -- % distance from the EU country average
    ROUND(
        (cv.medici_per_100k - AVG(cv.medici_per_100k) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.medici_per_100k) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
ORDER BY cv.year DESC, rank_procapite_eu
