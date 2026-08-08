-- mart_geo_benchmark — Employment by NUTS3 region: EU27-wide
-- benchmark
-- analytics.
--
-- One row per (year, geo, unit, nace_r2). Replaces the old pass-through
-- mart (Italy only) with EU27-wide comparative analytics:
--   • EU27 average per year (same nuts_level and unit comparison)
--   • country average per year
--   • percentile within EU27 (same year, nuts_level, unit)
--   • national rank within country
--   • % distance from the EU27 average
--
-- Benchmark columns are computed ONLY for the reference slice:
-- unit = 'THS' AND wstatus = 'EMP' AND nace_r2 = 'TOTAL' (total
-- employment, thousands). Other breakdown rows (sector B-E, O-U, ...)
-- carry no benchmark.
--
-- SCOPE: benchmark ONLY for EU27 countries (Greece = 'EL'). Non-EU rows
-- keep media_eu/distanza as reference but percentile/rank are NULL.

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
        unit,
        unit_label_en,
        nace_r2,
        nace_r2_label_en,
        wstatus,
        wstatus_label_en,
        value,
        flag,
        flag_desc_en
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
    b.unit,
    b.unit_label_en,
    b.nace_r2,
    b.nace_r2_label_en,
    b.wstatus,
    b.wstatus_label_en,
    b.value,
    -- EU27 average for the same year, NUTS level, unit and indicator (reference slice)
    CASE
        WHEN b.unit = 'THS' AND b.wstatus = 'EMP' AND b.nace_r2 = 'TOTAL'
        THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.wstatus, b.nace_r2), 2)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year, NUTS level, unit and indicator
    CASE
        WHEN b.unit = 'THS' AND b.wstatus = 'EMP' AND b.nace_r2 = 'TOTAL'
        THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit, b.wstatus, b.nace_r2), 2)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within EU27 (same year, nuts_level, unit, indicator); NULL outside
    CASE
        WHEN b.unit = 'THS' AND b.wstatus = 'EMP' AND b.nace_r2 = 'TOTAL' AND b.is_eu
        THEN ROUND(
            PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.wstatus, b.nace_r2, b.is_eu ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = highest fertility in the country, same year/level/unit/indicator)
    CASE
        WHEN b.unit = 'THS' AND b.wstatus = 'EMP' AND b.nace_r2 = 'TOTAL'
        THEN RANK() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit, b.wstatus, b.nace_r2 ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU27 average (same year, nuts_level, unit, indicator)
    CASE
        WHEN b.unit = 'THS' AND b.wstatus = 'EMP' AND b.nace_r2 = 'TOTAL'
        THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.wstatus, b.nace_r2))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.wstatus, b.nace_r2)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.unit, b.nace_r2
