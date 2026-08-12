-- mart_geo_benchmark — Energy poverty (inability to heat home) by NUTS2 region: EU27-wide
-- benchmark analytics.
--
-- One row per (year, geo, unit). EU27-wide comparative analytics:
--   • EU27 average per year (same nuts_level and unit comparison)
--   • country average per year
--   • percentile within EU27 (same year, nuts_level, unit)
--   • national rank within country
--   • % distance from the EU27 average
--
-- SCOPE: benchmark columns are computed ONLY for EU27 countries (post-2020
-- composition, Greece = 'EL' in Eurostat geo codes). Non-EU rows (CH, NO,
-- TR, RS, ME, MK, AL, ...) stay in the mart with NULL benchmark so they
-- never distort EU averages/ranks/percentiles.
--
-- Benchmark columns are computed for unit = 'PC' (share of population at risk
-- of poverty, %). NOTE: higher value = worse. rank/percentile describe the
-- distribution, so a top rank means the highest poverty share.
--
-- NR (absolute count) rows carry no benchmark so they never distort.

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
    b.value,
    -- EU average for the same year, NUTS level and unit (PC only, meaningful benchmark)
    CASE
        WHEN b.unit = 'PC' THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit), 2)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year, NUTS level and unit
    CASE
        WHEN b.unit = 'PC' THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit), 2)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within the EU (same year, nuts_level, unit)
    CASE
        WHEN b.unit = 'PC' AND b.is_eu THEN ROUND(PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.is_eu ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = highest poverty share in the country, same year/level/unit)
    CASE
        WHEN b.unit = 'PC' THEN RANK() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU average (same year, nuts_level, unit)
    CASE
        WHEN b.unit = 'PC' THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.unit
