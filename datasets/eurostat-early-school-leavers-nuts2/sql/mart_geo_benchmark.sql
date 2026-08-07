-- mart_geo_benchmark — Early school leavers by NUTS2 region: EU27-wide
-- benchmark analytics.
--
-- One row per (year, geo, unit, sex, age). Replaces the old pass-through
-- mart (Italy only) with EU27-wide comparative analytics:
--   • EU27 average per year (same nuts_level and unit comparison)
--   • country average per year
--   • percentile within EU27 (same year, nuts_level, unit)
--   • national rank within country
--   • % distance from the EU27 average
--
-- Benchmark columns are computed ONLY for the reference slice:
-- unit = 'PC' AND sex = 'T' (total) — the standard comparable measure.
-- Sex/age breakdown rows (M/F) carry no benchmark so they never distort.
--
-- SCOPE: benchmark ONLY for EU27 countries (Greece = 'EL'). Non-EU rows
-- keep media_eu/distanza as reference but percentile/rank are NULL.
--
-- NOTE: higher value = worse (higher early leaving share).

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
        sex,
        sex_label_en,
        age,
        age_label_en,
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
    b.sex,
    b.sex_label_en,
    b.age,
    b.age_label_en,
    b.value,
    -- EU27 average for the same year, NUTS level, unit and sex (PC + sex T only)
    CASE
        WHEN b.unit = 'PC' AND b.sex = 'T' THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.sex), 2)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year, NUTS level, unit and sex
    CASE
        WHEN b.unit = 'PC' AND b.sex = 'T' THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit, b.sex), 2)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within EU27 (same year, nuts_level, unit, sex); NULL outside
    -- EU27 or non-T rows
    CASE
        WHEN b.unit = 'PC' AND b.sex = 'T' AND b.is_eu THEN ROUND(
            PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.sex, b.is_eu ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = highest early leaving in the country, same year/level/unit/sex)
    CASE
        WHEN b.unit = 'PC' AND b.sex = 'T' THEN RANK() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit, b.sex ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU27 average (same year, nuts_level, unit, sex)
    CASE
        WHEN b.unit = 'PC' AND b.sex = 'T' THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.sex))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.unit, b.sex)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.unit, b.sex, b.age
