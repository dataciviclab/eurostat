-- mart_italia: tasso vacanza (JVR) Italia per trimestre.
-- NACE aggregate per l'Italia: B-N (industria e servizi) è il totale equivalente a _T.
-- Alcuni paesi usano _T, altri B-N — il mart copre entrambi.
SELECT
    year,
    quarter,
    value AS vacancy_rate_pct
FROM clean_input
WHERE geo = 'IT'
  AND nace_r2 IN ('B-N', '_T')
  AND s_adj = 'NSA'
  AND indic_em = 'JVR'
  AND sizeclas = 'TOTAL'
ORDER BY year, quarter
