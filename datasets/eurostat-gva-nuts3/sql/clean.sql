-- clean.sql: NAMA_10R_3GVA — 4 dimensioni (freq,unit,nace_r2,geo)
WITH unpivoted AS (
    SELECT *
    FROM (
        UNPIVOT raw_input
            ON COLUMNS(* EXCLUDE "freq,unit,nace_r2,geo\TIME_PERIOD")
            INTO
                NAME anno
                VALUE valore_raw
    )
),
parsed AS (
    SELECT
        trim(split_part("freq,unit,nace_r2,geo\TIME_PERIOD", ',', 1)) AS freq,
        trim(split_part("freq,unit,nace_r2,geo\TIME_PERIOD", ',', 2)) AS unit,
        trim(split_part("freq,unit,nace_r2,geo\TIME_PERIOD", ',', 3)) AS nace_r2,
        trim(split_part("freq,unit,nace_r2,geo\TIME_PERIOD", ',', 4)) AS geo,
        try_cast(trim(anno) AS INTEGER) AS anno,
        CASE
            WHEN regexp_matches(trim(valore_raw), '^\d+(\.\d+)?')
            THEN try_cast(regexp_extract(trim(valore_raw), '^\d+(\.\d+)?', 0) AS DOUBLE)
        END AS valore,
        regexp_extract(trim(valore_raw), '\s+([a-z])$', 1) AS flag
    FROM unpivoted
    WHERE anno IS NOT NULL
)
SELECT
    p.freq,
    f.label_en AS freq_label_en,
    p.unit,
    u.label_en AS unit_label_en,
    u.label_it AS unit_label_it,
    p.nace_r2,
    CASE p.nace_r2
        WHEN 'A' THEN 'Agriculture, forestry and fishing'
        WHEN 'B-E' THEN 'Industry (except construction)'
        WHEN 'F' THEN 'Construction'
        WHEN 'G-J' THEN 'Wholesale, retail, transport, ICT'
        WHEN 'K-N' THEN 'Financial and business services'
        WHEN 'O-U' THEN 'Public admin, education, health'
        WHEN 'TOTAL' THEN 'All NACE activities'
        ELSE p.nace_r2
    END AS nace_label_en,
    p.geo,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,
    p.anno,
    p.valore,
    p.flag,
    fl.description_en AS flag_desc_en
FROM parsed p
LEFT JOIN read_csv_auto('codelists/freq.csv') f ON p.freq = f.freq
LEFT JOIN read_csv_auto('codelists/units.csv') u ON p.unit = u.unit
LEFT JOIN read_csv_auto('codelists/geo.csv') g ON p.geo = g.code
LEFT JOIN read_csv_auto('codelists/geo.csv') gp ON g.parent_code = gp.code
LEFT JOIN read_csv_auto('codelists/flags.csv') fl ON p.flag = fl.flag
