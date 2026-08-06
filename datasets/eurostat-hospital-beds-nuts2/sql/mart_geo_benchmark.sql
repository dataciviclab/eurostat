-- mart_geo_benchmark — Hospital beds per 100k inhabitants by NUTS2 region:
-- EU-wide benchmark analytics.
--
-- One row per (year, geo, unit). Replaces the old pass-through mart
-- (Italy only) with EU-wide comparative analytics:
--   • EU average per year (same nuts_level and unit comparison)
--   • country average per year
--   • percentile within the EU (same year, nuts_level, unit)
--   • national rank within country
--   • % distance from the EU average
--
-- Benchmark columns are computed for unit = 'HAB_P' (hospital beds per 100k
-- inhabitants — the standard comparable measure). NR (absolute count) rows
-- carry no benchmark so they never distort the comparison.

WITH base AS (
    SELECT
        year,
        geo,
        geo_label_en,
        nuts_level,
        nuts_parent_code,
        nuts_parent_label_en,
        country,
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
    -- EU average for the same year, NUTS level and unit (HAB_P only, meaningful benchmark)
    CASE
        WHEN b.unit = 'HAB_P' THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.nuts_level, b.unit), 2)
        ELSE NULL
    END AS media_eu_value,
    -- Country average for the same year, NUTS level and unit
    CASE
        WHEN b.unit = 'HAB_P' THEN ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit), 2)
        ELSE NULL
    END AS media_paese_value,
    -- Percentile within the EU (same year, nuts_level, unit)
    CASE
        WHEN b.unit = 'HAB_P' THEN ROUND(PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.unit ORDER BY b.value), 4)
        ELSE NULL
    END AS percentile_eu,
    -- National rank (1 = most beds per 100k in the country, same year/level/unit)
    CASE
        WHEN b.unit = 'HAB_P' THEN ROW_NUMBER() OVER (PARTITION BY b.year, b.country, b.nuts_level, b.unit ORDER BY b.value DESC)
        ELSE NULL
    END AS rank_nazionale,
    -- % distance from the EU average (same year, nuts_level, unit)
    CASE
        WHEN b.unit = 'HAB_P' THEN ROUND(
            (b.value - AVG(b.value) OVER (PARTITION BY b.year, b.nuts_level, b.unit))
            / NULLIF(ABS(AVG(b.value) OVER (PARTITION BY b.year, b.nuts_level, b.unit)), 0) * 100, 1)
        ELSE NULL
    END AS distanza_media_eu_pct,
    b.flag,
    b.flag_desc_en
FROM base b
ORDER BY b.year DESC, b.nuts_level, b.country, b.geo, b.unit
