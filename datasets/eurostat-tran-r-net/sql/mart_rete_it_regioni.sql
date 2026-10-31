-- mart_rete_it_regioni.sql: dettaglio italiano NUTS1/NUTS2 delle reti + densità.
-- Serve per la domanda "le alternative di mobilità sono diseguali tra territori":
-- km di ferrovia per 1000 km2 e quota di rete elettrificata per regione.

WITH km AS (
    SELECT year, geo, geo_label_en, nuts_level, tra_infr, value
    FROM clean_input
    WHERE unit = 'KM'
      AND geo LIKE 'IT%'
      AND nuts_level IN ('NUTS1', 'NUTS2')
),
dens AS (
    SELECT year, geo, tra_infr, value AS per_1000_km2
    FROM clean_input
    WHERE unit = 'KM_TKM2'
      AND geo LIKE 'IT%'
      AND nuts_level IN ('NUTS1', 'NUTS2')
),
base AS (
    SELECT
        year, geo, geo_label_en, nuts_level, tra_infr,
        value AS km
    FROM km
)
SELECT
    b.year,
    b.geo,
    b.geo_label_en,
    b.nuts_level,
    b.tra_infr,
    b.km,
    d.per_1000_km2
FROM base b
LEFT JOIN dens d
    ON d.year = b.year
   AND d.geo = b.geo
   AND d.tra_infr = b.tra_infr
WHERE b.km IS NOT NULL
ORDER BY b.year, b.geo, b.tra_infr
