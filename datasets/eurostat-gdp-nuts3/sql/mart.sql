-- mart.sql: PIL provinciale NUTS3 — Italia
-- Seleziona dati per province italiane, PIL pro-capite e PIL totale

SELECT
    anno,
    geo AS nuts_code,
    CASE
        WHEN unit = 'EUR_HAB' THEN 'PIL_procapite'
        WHEN unit = 'MIO_EUR' THEN 'PIL_totale'
        ELSE unit
    END AS indicatore,
    valore,
    flag,
    -- Livello NUTS
    CASE length(geo)
        WHEN 2 THEN 'paese'
        WHEN 3 THEN 'NUTS1'
        WHEN 4 THEN 'NUTS2'
        WHEN 5 THEN 'NUTS3'
        ELSE 'altro'
    END AS nuts_livello
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit IN ('EUR_HAB', 'MIO_EUR')
  AND valore IS NOT NULL
ORDER BY anno DESC, geo, unit
