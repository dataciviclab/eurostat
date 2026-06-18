-- mart.sql: vista Italia su clean arricchito
-- Il clean è già il prodotto: label, NUTS, flag.
-- Il mart filtra per comodità e aggiunge logica di business.

SELECT
    anno,
    geo,
    geo_label_en,
    nuts_level,
    nuts_parent_code,
    nuts_parent_label_en,
    unit,
    unit_label_en,
    valore,
    flag,
    flag_desc_en,
    -- PIL pro-capite vs totale (decodifica unità)
    CASE unit
        WHEN 'EUR_HAB' THEN 'PIL_procapite'
        WHEN 'MIO_EUR' THEN 'PIL_totale'
        ELSE unit
    END AS indicatore
FROM clean_input
WHERE geo LIKE 'IT%'
  AND unit IN ('EUR_HAB', 'MIO_EUR')
  AND valore IS NOT NULL
ORDER BY anno DESC, geo, unit
