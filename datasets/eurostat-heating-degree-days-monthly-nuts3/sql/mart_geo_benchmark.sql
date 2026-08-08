-- mart_geo_benchmark — Monthly heating degree days by NUTS3 region:
-- EU27-wide benchmark analytics.
--
-- One row per (year, month, geo, unit, indic_nrg). Replaces the old
-- pass-through mart (Italy only) with EU27-wide comparative analytics:
--   • EU27 average per year+month (same nuts_level and dims comparison)
--   • country average per year+month
--   • percentile within EU27 (same year, month, nuts_level)
--   • national rank within country
--   • % distance from the EU27 average
--
-- Benchmark columns are computed ONLY for the reference slice:
-- unit = 'NR' AND indic_nrg = 'HDD' (heating degree days). CDD rows
-- (cooling) carry no benchmark.
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
        month,
        geo,
        geo_label_en,
        nuts_level,
        nuts_parent_code,
        nuts_parent_label_en,
        country,
        country IN (SELECT code FROM eu_countries) AS is_eu,
        unit,
        unit_label_en,
        indic_nrg,
        indic_nrg_label_en,
        value,
        flag,
        flag_desc_en
    FROM clean_input
    WHERE value IS NOT NULL
      AND country IS NOT NULL
)
SELECT
    b.year,
    b.month,
    b.geo,
    b.geo_label_en,
    b.nuts_level,
    b.nuts_parent_code,
    b.nuts_parent_label_en,
    b.country,
    b.unit,
    b.unit_label_en,
    b.indic_nrg,
    b.indic_nrg_label_en,
    b.value,
    -- EU27 average for the same year+month, NUTS level, unit and dims (reference slice)
    CASE
        WHEN b.unit = 'NR' AND b.indic_nrg = 'HDD'
        THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.month, b.nuts_level, b.unit, b.indic_nrg), 1)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year+month, NUTS level, unit and dims
    CASE
        WHEN b.unit = 'NR' AND b.indic_nrg = 'HDD'
        THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.month, b.country, b.nuts_level, b.unit, b.indic_nrg), 1)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within EU27 (same year+month, nuts_level, unit, dims); NULL outside
    CASE
        WHEN b.unit = 'NR' AND b.indic_nrg = 'HDD' AND b.is_eu
        THEN ROUND(
            PERCENT_RANK() OVER (PARTITION BY b.year, b.month, b.nuts_level, b.unit, b.indic_nrg, b.is_eu ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = most heating in the country, same year+month/level/unit/dims)
    CASE
        WHEN b.unit = 'NR' AND b.indic_nrg = 'HDD'
        THEN RANK() OVER (PARTITION BY b.year, b.month, b.country, b.nuts_level, b.unit, b.indic_nrg ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU27 average (same year+month, nuts_level, unit, dims)
    CASE
        WHEN b.unit = 'NR' AND b.indic_nrg = 'HDD'
        THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.month, b.nuts_level, b.unit, b.indic_nrg))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.month, b.nuts_level, b.unit, b.indic_nrg)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.month, b.nuts_level, b.country, b.geo, b.unit, b.indic_nrg
