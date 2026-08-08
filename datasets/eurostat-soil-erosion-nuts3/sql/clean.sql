-- clean.sql: AEI_PR_SOILER — estimated soil erosion by NUTS3 region, enriched.
--
-- Extra dimensions vs the base pattern: levels (erosion severity class)
-- and clc18 (Corine Land Cover class), enriched with labels from the
-- support codelists.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the
-- geo code, but ONLY for real NUTS geographies. Aggregated geographies get
-- NULL so they never pollute benchmarks.
--
-- NOTE: PC = % of agricultural land at erosion risk. Slice benchmark =
-- unit PC + levels TOTAL + clc18 CLC2_3X331_332_335.

SELECT
    r.freq,
    r.unit,
    r.levels,
    r.clc18,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
    l.label_en AS levels_label_en,
    c.label_en AS clc18_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    -- Derived country: ISO2 prefix for real geographies only
    CASE
        WHEN g.nuts_level IS NOT NULL AND g.nuts_level != '' THEN LEFT(r.geo, 2)
        ELSE NULL
    END AS country,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    r.value,
    r.flag,
    fl.label_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_parquet('{support.freq.path}') f ON r.freq = f.code
LEFT JOIN read_parquet('{support.unit.path}') u ON r.unit = u.code
LEFT JOIN read_parquet('{support.levels.path}') l ON r.levels = l.code
LEFT JOIN read_parquet('{support.clc18.path}') c ON r.clc18 = c.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
