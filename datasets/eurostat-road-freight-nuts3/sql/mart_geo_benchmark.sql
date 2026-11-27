-- mart_geo_benchmark — Road freight unloaded by NUTS region: EU27-wide
-- benchmark analytics.
--
-- One row per (year, geo, nst07, unit). All goods types are kept as
-- pass-through; benchmark columns are computed ONLY for the reference
-- slice nst07 = 'TOTAL' AND unit = 'THS_T' (all goods, thousand tonnes):
--   • EU27 average per year (same nuts_level)
--   • country average per year (same nuts_level)
--   • percentile within EU27 (same year, nuts_level)
--   • national rank within country
--   • % distance from the EU27 average
--
-- SCOPE: benchmark ONLY for EU27 countries (Greece = 'EL'). Non-EU rows
-- keep media_eu/distanza as reference but percentile is NULL.
--
-- NOTE: higher value = more tonnes unloaded in the region (national road
-- freight demand at destination). Absolute volume, not per capita.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
base AS (
    SELECT
        year,
        geo,
        geo_label_en,
        nuts_level,
        nuts_parent_code,
        nuts_parent_label_en,
        country,
        country IN (SELECT code FROM eu_countries) AS is_eu,
        nst07,
        nst07_label_en,
        unit,
        unit_label_en,
        value,
        flag,
        flag_desc_en,
        (nst07 = 'TOTAL' AND unit = 'THS_T') AS is_ref
    FROM clean_input
    WHERE value IS NOT NULL
      AND country IS NOT NULL
)
SELECT
    b.year,
    b.geo,
    b.geo_label_en,
    b.nuts_level,
    b.nuts_parent_code,
    b.nuts_parent_label_en,
    b.country,
    b.nst07,
    b.nst07_label_en,
    b.unit,
    b.unit_label_en,
    b.value,
    -- EU27 average for the same year and NUTS level (reference slice)
    CASE WHEN b.is_ref
        THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.nst07, b.unit), 2)
    END AS media_eu_value,
    -- Country average for the same year and NUTS level (reference slice)
    CASE WHEN b.is_ref
        THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.nst07, b.unit), 2)
    END AS media_paese_value,
    -- Percentile within EU27 (same year, nuts_level); NULL outside EU27
    CASE WHEN b.is_ref AND b.is_eu
        THEN ROUND(PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.nst07, b.unit, b.is_eu ORDER BY b.value), 4)
    END AS percentile_eu,
    -- National rank (1 = most tonnes unloaded in the country, same year/level)
    CASE WHEN b.is_ref
        THEN RANK() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.nst07, b.unit ORDER BY b.value DESC)
    END AS rank_nazionale,
    -- % distance from the EU27 average (same year, nuts_level)
    CASE WHEN b.is_ref
        THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.nst07, b.unit))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.nst07, b.unit)), 0) * 100, 1)
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.nst07
