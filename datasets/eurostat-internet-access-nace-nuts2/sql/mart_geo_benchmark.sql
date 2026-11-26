-- mart_geo_benchmark — Enterprise internet access by region: EU27 benchmarks per access indicator.
-- Totale attività escluso settore finanziario (C10-S951_X_K), imprese con 10+ addetti.
-- NUTS 2 disponibile solo per alcuni paesi: per IT, DE, FR ecc. solo livello nazionale.
--
-- Per ogni (year, nuts_level, indic_is):
--   • media EU27 (stesso nuts_level), calcolata SOLO sui paesi EU27
--   • media paese (stesso nuts_level)
--   • percentile EU27 (stesso nuts_level); NULL fuori EU27
--   • distanza % dalla media EU27
--
-- SCOPE: i paesi non-EU restano come riferimento (is_eu = false) con
-- media_eu_value / distanza_media_eu_pct calcolate contro la media EU27,
-- ma percentile_eu NULL.

WITH eu_countries AS (
    SELECT unnest(['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','EL',
                   'HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK',
                   'SI','ES','SE']) AS code
),
base AS (
    SELECT
        year, geo, geo_label_en, nuts_level, country,
        country IN (SELECT code FROM eu_countries) AS is_eu,
        nuts_parent_code, nuts_parent_label_en,
        indic_is, indic_is_label_en,
        value, flag, flag_desc_en
    FROM clean_input
    WHERE nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
      AND country IS NOT NULL
      AND value IS NOT NULL
),
eu27 AS (
    SELECT year, indic_is, value AS valore_eu27
    FROM clean_input
    WHERE geo = 'EU27_2020' AND nace_r2 = 'C10-S951_X_K' AND size_emp = 'GE10' AND unit = 'PC_ENT'
)
SELECT
    b.*,
    e.valore_eu27,
    ROUND(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_is), 2) AS media_eu_value,
    ROUND(AVG(b.value) OVER (PARTITION BY b.year, b.country, b.nuts_level, b.indic_is), 2) AS media_paese_value,
    CASE WHEN b.is_eu
        THEN ROUND(PERCENT_RANK() OVER (PARTITION BY b.year, b.nuts_level, b.indic_is, b.is_eu ORDER BY b.value), 4)
    END AS percentile_eu,
    ROUND(b.value - e.valore_eu27, 2) AS distanza_eu27_pp,
    ROUND(
        (b.value - AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_is))
        / NULLIF(AVG(b.value) FILTER (WHERE b.is_eu) OVER (PARTITION BY b.year, b.nuts_level, b.indic_is), 0) * 100, 2
    ) AS distanza_media_eu_pct
FROM base b
LEFT JOIN eu27 e ON b.year = e.year AND b.indic_is = e.indic_is
ORDER BY b.year, b.geo, b.indic_is
