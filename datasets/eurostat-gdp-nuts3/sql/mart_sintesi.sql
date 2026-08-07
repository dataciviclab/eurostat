-- mart_sintesi — GDP by country: national aggregates and cross-country ranking.
--
-- One row per (country, year). Built from NUTS3-level data of each country:
--   • total GDP (sum of MIO_EUR across all NUTS3 of the country)
--   • GDP per capita (country-level EUR_HAB value, i.e. country geo)
--   • rank among EU27 countries by GDP per capita and by total GDP
--
-- The country geo (geo = country code, nuts_level = 'country') holds the
-- official EUR_HAB value; NUTS3 rows hold MIO_EUR parts of the total.

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
        MAX(CASE WHEN unit = 'EUR_HAB' THEN value END) AS gdp_procapite,
        MAX(CASE WHEN unit = 'MIO_EUR' THEN value END) AS gdp_totale_mio
    FROM clean_input
    WHERE nuts_level = 'country'
      AND value IS NOT NULL
    GROUP BY year, geo
),
nuts3_total AS (
    SELECT
        year,
        country,
        SUM(value) AS gdp_nuts3_sum_mio
    FROM clean_input
    WHERE unit = 'MIO_EUR'
      AND nuts_level = 'NUTS3'
      AND value IS NOT NULL
      AND country IS NOT NULL
    GROUP BY year, country
)
SELECT
    cv.year,
    cv.country,
    cv.gdp_procapite,
    cv.gdp_totale_mio,
    nt.gdp_nuts3_sum_mio,
    -- Cross-country rank (EU27 only) by GDP per capita (1 = richest in the EU, same year)
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.gdp_procapite DESC) ELSE NULL END AS rank_procapite_eu,
    -- Cross-country rank (EU27 only) by total GDP
    CASE WHEN cv.is_eu THEN RANK() OVER (PARTITION BY cv.year, cv.is_eu ORDER BY cv.gdp_totale_mio DESC) ELSE NULL END AS rank_totale_eu,
    -- % distance from the EU27 country average by GDP per capita
    ROUND(
        (cv.gdp_procapite - AVG(cv.gdp_procapite) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year))
        / NULLIF(ABS(AVG(cv.gdp_procapite) FILTER (WHERE cv.is_eu) OVER (PARTITION BY cv.year)), 0) * 100, 1
    ) AS distanza_media_eu_pct
FROM country_values cv
LEFT JOIN nuts3_total nt ON cv.year = nt.year AND cv.country = nt.country
ORDER BY cv.year DESC, rank_procapite_eu
