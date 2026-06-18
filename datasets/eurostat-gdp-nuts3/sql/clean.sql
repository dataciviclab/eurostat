-- clean.sql: TSV Eurostat → UNPIVOT + arricchimento codelist
--
-- Pattern: come open-siope, il clean è il prodotto finito.
-- Le label (geo, unità, flag, frequenza) arrivano da LEFT JOIN con codelist CSV.
-- Il mart può essere un semplice SELECT * da clean_input o una vista specializzata.

WITH unpivoted AS (
    SELECT *
    FROM (
        UNPIVOT raw_input
            ON COLUMNS(* EXCLUDE "freq,unit,geo\TIME_PERIOD")
            INTO
                NAME anno
                VALUE valore_raw
    )
),
parsed AS (
    SELECT
        trim(split_part("freq,unit,geo\TIME_PERIOD", ',', 1)) AS freq,
        trim(split_part("freq,unit,geo\TIME_PERIOD", ',', 2)) AS unit,
        trim(split_part("freq,unit,geo\TIME_PERIOD", ',', 3)) AS geo,
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
    -- Dimensioni SDMX + label
    p.freq,
    f.label_en AS freq_label_en,
    p.unit,
    u.label_en AS unit_label_en,
    u.label_it AS unit_label_it,

    -- Geo + label + gerarchia NUTS
    p.geo,
    g.label_en AS geo_label_en,
    g.nuts_level,
    g.parent_code AS nuts_parent_code,
    gp.label_en AS nuts_parent_label_en,

    -- Dati
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
