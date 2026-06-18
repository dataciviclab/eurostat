-- Standard clean.sql for Eurostat TSV bulk (multi-dimension)
-- Unpivots years from columns to rows, parses flags and missing values
WITH unpivoted AS (
    SELECT *
    FROM (
        UNPIVOT raw_input
            ON COLUMNS(* EXCLUDE "freq,unit,geo\TIME_PERIOD")
            INTO
                NAME anno
                VALUE valore_raw
    )
)
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
