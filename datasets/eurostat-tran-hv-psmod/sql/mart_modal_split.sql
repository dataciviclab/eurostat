-- mart_modal_split.sql: quota % dei passeggeri-km per modo, per paese e anno.
--
-- Nota: TRN_BUS_TOT_AVD è un aggregato (treni + bus + metro/tram), NON va sommato
-- agli altri: viene escluso dal pivot. `residuo_pct` è quanto resta a 100 dopo
-- auto+bus+treno: in parte è metro/tram e navigazione, in parte è arrotondamento
-- della fonte. Non va interpretato come "altro" certificato.

WITH base AS (
    SELECT year, country, vehicle, value
    FROM clean_input
    WHERE country IS NOT NULL
      AND unit = 'PC'
      AND vehicle IN ('CAR', 'BUS_TOT', 'TRN')
),
pivoted AS (
    SELECT
        year,
        country,
        MAX(CASE WHEN vehicle = 'CAR' THEN value END) AS quota_auto_pct,
        MAX(CASE WHEN vehicle = 'BUS_TOT' THEN value END) AS quota_bus_pct,
        MAX(CASE WHEN vehicle = 'TRN' THEN value END) AS quota_treno_pct
    FROM base
    GROUP BY year, country
)
SELECT
    year,
    country,
    quota_auto_pct,
    quota_bus_pct,
    quota_treno_pct,
    ROUND(COALESCE(quota_auto_pct, 0) + COALESCE(quota_bus_pct, 0) + COALESCE(quota_treno_pct, 0), 2)
        AS somma_modi_pct,
    ROUND(100 - (COALESCE(quota_auto_pct, 0) + COALESCE(quota_bus_pct, 0) + COALESCE(quota_treno_pct, 0)), 2)
        AS residuo_pct
FROM pivoted
WHERE quota_auto_pct IS NOT NULL
ORDER BY year, country
