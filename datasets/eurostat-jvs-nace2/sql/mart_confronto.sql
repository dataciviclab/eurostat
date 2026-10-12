-- mart_confronto: tasso vacanza (JVR) Italia vs EU27 e principali economie.
-- NACE aggregate: B-N per l'IT, _T per gli altri — copre entrambe le convenzioni.
SELECT
    year,
    quarter,
    geo,
    geo_label_en,
    value AS vacancy_rate_pct
FROM clean_input
WHERE geo IN ('IT', 'EU27_2020', 'DE', 'FR', 'ES', 'NL', 'BE', 'AT', 'PL', 'SE', 'DK', 'FI')
  AND nace_r2 IN ('B-N', '_T')
  AND s_adj = 'NSA'
  AND indic_em = 'JVR'
  AND sizeclas = 'TOTAL'
ORDER BY geo, year, quarter
