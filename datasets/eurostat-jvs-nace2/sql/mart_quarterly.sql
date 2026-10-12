-- mart_quarterly: posti vacanti e tasso vacanza per geo × NACE × trimestre.
-- Solo NSA, tutte le NACE, tutti gli indicatori.
SELECT
    year, quarter, geo, geo_label_en, nuts_level, country,
    nace_r2, indic_em, sizeclas, s_adj, value
FROM clean_input
WHERE s_adj = 'NSA'
ORDER BY geo, year, quarter, nace_r2, indic_em
