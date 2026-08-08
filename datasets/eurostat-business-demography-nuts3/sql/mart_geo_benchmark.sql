-- mart_geo_benchmark — Business demography (enterprise births) by NUTS3
-- region: EU27-wide benchmark analytics.
--
-- One row per (year, geo, indic_sb, sizeclas, nace_r2). Replaces the old
-- pass-through mart (Italy only) with EU27-wide comparative analytics:
--   • EU27 average per year (same nuts_level and dimensions comparison)
--   • country average per year
--   • percentile within EU27 (same year, nuts_level)
--   • national rank within country
--   • % distance from the EU27 average
--
-- Benchmark columns are computed ONLY for the reference slice:
-- indic_sb = 'V11920' AND sizeclas = 'TOTAL' AND nace_r2 = 'B-S_X_K642'
-- (enterprise births, all sectors — the standard measure). Other
-- breakdown rows carry no benchmark.
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
        indic_sb,
        indic_sb_label_en,
        sizeclas,
        sizeclas_label_en,
        nace_r2,
        nace_r2_label_en,
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
    b.indic_sb,
    b.indic_sb_label_en,
    b.sizeclas,
    b.sizeclas_label_en,
    b.nace_r2,
    b.nace_r2_label_en,
    b.value,
    -- EU27 average for the same year, NUTS level and dims (reference slice)
    CASE
        WHEN b.indic_sb = 'V11920' AND b.sizeclas = 'TOTAL' AND b.nace_r2 = 'B-S_X_K642'
        THEN ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2), 1)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year, NUTS level and dims
    CASE
        WHEN b.indic_sb = 'V11920' AND b.sizeclas = 'TOTAL' AND b.nace_r2 = 'B-S_X_K642'
        THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2), 1)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within EU27 (same year, nuts_level, dims); NULL outside
    CASE
        WHEN b.indic_sb = 'V11920' AND b.sizeclas = 'TOTAL' AND b.nace_r2 = 'B-S_X_K642' AND b.is_eu
        THEN ROUND(
            PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2, b.is_eu ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = most births in the country, same year/level/dims)
    CASE
        WHEN b.indic_sb = 'V11920' AND b.sizeclas = 'TOTAL' AND b.nace_r2 = 'B-S_X_K642'
        THEN RANK() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2 ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU27 average (same year, nuts_level, dims)
    CASE
        WHEN b.indic_sb = 'V11920' AND b.sizeclas = 'TOTAL' AND b.nace_r2 = 'B-S_X_K642'
        THEN ROUND(
            (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2))
            / NULLIF(ABS(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_sb, b.sizeclas, b.nace_r2)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.indic_sb, b.sizeclas, b.nace_r2
