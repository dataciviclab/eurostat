-- mart_expenditure.sql: GDP expenditure components pivoted per year x country.

WITH base AS (
    SELECT year, country, na_item, na_item_label_en, unit, value
    FROM clean_input
    WHERE country IS NOT NULL
      AND unit IN ('CP_MEUR', 'CLV_PCH_PRE', 'PC_GDP')
),
pivoted AS (
    SELECT
        year, country, unit,
        MAX(CASE WHEN na_item = 'B1GQ' THEN value END) AS pil,
        MAX(CASE WHEN na_item = 'P3' THEN value END) AS consumi_finali,
        MAX(CASE WHEN na_item = 'P31_S14' THEN value END) AS consumi_famiglie,
        MAX(CASE WHEN na_item = 'P3_S13' THEN value END) AS consumi_governo,
        MAX(CASE WHEN na_item = 'P51G' THEN value END) AS gfcf,
        MAX(CASE WHEN na_item = 'P5G' THEN value END) AS formazione_capitale,
        MAX(CASE WHEN na_item = 'P6' THEN value END) AS export,
        MAX(CASE WHEN na_item = 'P7' THEN value END) AS import,
        MAX(CASE WHEN na_item = 'P6X7' THEN value END) AS saldo_commerciale,
        MAX(CASE WHEN na_item = 'YA0' THEN value END) AS errore_omissione,
        MAX(CASE WHEN na_item = 'B1GQ' THEN value END)
            - MAX(CASE WHEN na_item = 'P6' THEN value END)
            + MAX(CASE WHEN na_item = 'P7' THEN value END) AS domanda_interna
    FROM base
    GROUP BY year, country, unit
)
SELECT * FROM pivoted
ORDER BY year, country, unit
