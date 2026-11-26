-- mart_sintesi — Road freight unloaded by country: national totals and ranking.
--
-- One row per (country, year). Reference slice only (nst07 TOTAL, unit
-- THS_T):
--   • thousand tonnes unloaded, summed over the country's NUTS3 regions
--   • regional coverage (NUTS3 with a value / NUTS3 present in the year)
--   • rank among EU27 countries (1 = most tonnes unloaded), computed
--     ONLY on country-years with full NUTS3 coverage
--   • % distance from the EU27 average (same full-coverage subset)
--
-- Country values are derived from NUTS3 rows: this dataflow publishes a
-- country-level geo only for MK (verified). Regions with missing or
-- confidential values make the sum a lower bound, hence the coverage
-- columns (e.g. IT 2008-2011: 53 of 107 NUTS3 with a value).
-- MK is therefore NOT in this mart (no NUTS3 rows): its country-level row
-- is available in mart_geo_benchmark and mart_trend.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
country_values AS (
    SELECT
        year,
        country,
        country IN (SELECT code FROM eu_countries) AS is_eu,
        SUM(value) AS tonnellate_migliaia,
        COUNT(DISTINCT geo) FILTER (WHERE value IS NOT NULL) AS n_nuts3_con_dato,
        COUNT(DISTINCT geo) AS n_nuts3
    FROM clean_input
    WHERE nuts_level = 'NUTS3'
      AND nst07 = 'TOTAL'
      AND unit = 'THS_T'
      AND country IS NOT NULL
    GROUP BY year, country
),
scored AS (
    SELECT
        *,
        ROUND(n_nuts3_con_dato * 100.0 / NULLIF(n_nuts3, 0), 1) AS copertura_pct,
        is_eu AND n_nuts3_con_dato = n_nuts3 AS is_rankable
    FROM country_values
    WHERE tonnellate_migliaia IS NOT NULL
)
SELECT
    s.year,
    s.country,
    s.tonnellate_migliaia,
    s.n_nuts3_con_dato,
    s.n_nuts3,
    s.copertura_pct,
    -- Cross-country rank (EU27, full coverage only; 1 = most tonnes unloaded)
    CASE WHEN s.is_rankable
        THEN RANK() OVER (PARTITION BY s.year, s.is_rankable ORDER BY s.tonnellate_migliaia DESC)
    END AS rank_eu,
    -- % distance from the EU27 full-coverage average
    CASE WHEN s.is_rankable THEN ROUND(
        (s.tonnellate_migliaia - AVG(s.tonnellate_migliaia) FILTER (WHERE s.is_rankable) OVER (PARTITION BY s.year))
        / NULLIF(ABS(AVG(s.tonnellate_migliaia) FILTER (WHERE s.is_rankable) OVER (PARTITION BY s.year)), 0) * 100, 1
    ) END AS distanza_media_eu_pct
FROM scored s
ORDER BY s.year DESC, rank_eu, s.country
