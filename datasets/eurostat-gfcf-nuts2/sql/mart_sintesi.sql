-- mart_sintesi.sql: Country-level GFCF summary with EU27 ranking.

WITH country_vals AS (
    SELECT year, country, value AS gfcf_totale_mio
    FROM clean_input
    WHERE nuts_level = 'country' AND sector = 'S1' AND currency = 'MIO_EUR' AND nace_r2 = 'TOTAL'
),
ranking AS (
    SELECT
        year, country, gfcf_totale_mio,
        RANK() OVER (PARTITION BY year ORDER BY gfcf_totale_mio DESC) AS rank_totale_eu
    FROM country_vals
)
SELECT * FROM ranking
ORDER BY year, country
