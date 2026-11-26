-- mart_sintesi — Enterprise internet access by country: national values and EU27 ranking.
-- Quota di imprese (10+ addetti, totale escluso settore finanziario) per indicatore di accesso (quota di addetti con internet).
--
-- SCOPE: rank_eu calcolato SOLO sui paesi EU27 (Grecia = 'EL'). I paesi
-- non-EU (es. NO, ME, BA, RS, TR) restano come riferimento con is_eu = false
-- e rank_eu NULL.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
country_vals AS (
    SELECT year, country, geo_label_en,
           country IN (SELECT code FROM eu_countries) AS is_eu,
           indic_is, indic_is_label_en,
           value AS quota_imprese_pct, flag
    FROM clean_input
    WHERE nuts_level = 'country'
      AND nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
      AND value IS NOT NULL
),
eu27 AS (
    SELECT year, indic_is, value AS valore_eu27
    FROM clean_input
    WHERE geo = 'EU27_2020' AND nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
)
SELECT
    c.*,
    e.valore_eu27,
    ROUND(c.quota_imprese_pct - e.valore_eu27, 2) AS distanza_eu27_pp,
    CASE WHEN c.is_eu
        THEN RANK() OVER (PARTITION BY c.year, c.indic_is, c.is_eu ORDER BY c.quota_imprese_pct DESC)
    END AS rank_eu
FROM country_vals c
LEFT JOIN eu27 e ON c.year = e.year AND c.indic_is = e.indic_is
ORDER BY c.year, c.indic_is, c.country
