-- mart_rete.sql: estensione delle reti in km, geo x anno x tipo di infrastruttura.
-- Solo unit KM (la densità per km2 vive nel mart regionale dedicato).

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    tra_infr,
    tra_infr_label_en,
    value AS km
FROM clean_input
WHERE unit = 'KM'
  AND value IS NOT NULL
ORDER BY year, geo, tra_infr
