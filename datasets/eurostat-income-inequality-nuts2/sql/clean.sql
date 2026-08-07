-- clean.sql: ILC_DI11_R — income inequality S80/S20 by NUTS2 region, enriched.
--
-- Contract note: `country` is derived from the 2-letter ISO prefix of the geo
-- code, but ONLY for real NUTS geographies (nuts_level in country/NUTS1/NUTS2/NUTS3).
-- Aggregated geographies (EU, EA, G20, ACP, ...) get NULL so they never pollute
-- country-level benchmarks.
--
-- NOTE: higher S80/S20 value = worse (wider income inequality). Unit INX.

SELECT
    r.freq,
    r.unit,
    r.geo,
    r.year,
    f.label_en AS freq_label_en,
    u.label_en AS unit_label_en,
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
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_csv('codelists/geo.csv', auto_detect=true, delim=',', header=true) gp ON g.parent_code = gp.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
