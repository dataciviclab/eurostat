-- clean.sql: JVS_Q_NACE2 — Job vacancy statistics by NACE Rev. 2.
-- Raw `year` column is "2001-Q1" — extract numeric year and quarter (pattern namq10-gdp).
-- No `unit` column: indic_em encodes the measure (JOBVAC, JOBOCC, JVR, JVRCH_Q).

SELECT
    r.freq,
    r.s_adj,
    r.nace_r2,
    r.sizeclas,
    r.indic_em,
    r.geo,
    CAST(SPLIT_PART(r.year, '-', 1) AS INTEGER) AS year,
    SPLIT_PART(r.year, '-', 2) AS quarter,
    f.label_en AS freq_label_en,
    g.label_en AS geo_label_en,
    g.nuts_level,
    CASE
        WHEN g.nuts_level IS NOT NULL AND g.nuts_level != '' THEN LEFT(r.geo, 2)
        ELSE NULL
    END AS country,
    CAST(r.value AS DOUBLE) AS value,
    r.flag,
    fl.label_en AS flag_desc_en
FROM raw_input r
LEFT JOIN read_parquet('{support.freq.path}') f ON r.freq = f.code
LEFT JOIN read_csv('{support.geo.path}', auto_detect=true, delim=',', header=true) g ON r.geo = g.code
LEFT JOIN read_parquet('{support.flag.path}') fl ON r.flag = fl.code
WHERE r.year IS NOT NULL
  AND r.value IS NOT NULL
