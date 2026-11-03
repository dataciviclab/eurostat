-- mart_modal_split_merci.sql: quota % delle tonnellate-km per modo, paese x anno.
--
-- Nota: RAIL_IWW_AVD è un aggregato (ferrovia + vie navigabili) e viene escluso
-- dal pivot. `residuo_pct` è quanto resta a 100: in parte è navigazione
-- internazionale e oleodotti (fuori perimetro Eurostat), in parte arrotondamento.

WITH base AS (
    SELECT year, country, tra_mode, value
    FROM clean_input
    WHERE country IS NOT NULL
      AND unit = 'PC'
      AND tra_mode IN ('ROAD', 'RAIL', 'IWW')
),
pivoted AS (
    SELECT
        year,
        country,
        MAX(CASE WHEN tra_mode = 'ROAD' THEN value END) AS quota_strada_pct,
        MAX(CASE WHEN tra_mode = 'RAIL' THEN value END) AS quota_ferrovia_pct,
        MAX(CASE WHEN tra_mode = 'IWW' THEN value END) AS quota_vie_navigabili_pct
    FROM base
    GROUP BY year, country
)
SELECT
    year,
    country,
    quota_strada_pct,
    quota_ferrovia_pct,
    quota_vie_navigabili_pct,
    ROUND(100 - (COALESCE(quota_strada_pct, 0) + COALESCE(quota_ferrovia_pct, 0)
        + COALESCE(quota_vie_navigabili_pct, 0)), 2) AS residuo_pct
FROM pivoted
WHERE quota_strada_pct IS NOT NULL
ORDER BY year, country
