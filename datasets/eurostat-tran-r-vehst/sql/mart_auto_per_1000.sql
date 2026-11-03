-- mart_auto_per_1000.sql: autovetture per 1000 abitanti, geo x anno.
-- Include UE27_2020 come riga di confronto (country resta NULL per gli aggregati).
-- Solo unit P_THAB: nessuna divisione calcolata da noi, il valore è della fonte.
--
-- ⚠️ CAVEAT VERIFICATO (2026-10-31): a livello regionale NUTS il rapporto è
-- gonfiato dove hanno sede società di noleggio/leasing e flotte aziendali, perché
-- il veicolo è registrato alla sede legale e non alla residenza dell'utilizzatore.
-- Valori 2024: Valle d'Aosta 1936 e Prov. Trento 1610 auto/1000 ab., contro una
-- media italiana di 701. Non sono errori della fonte: sono indirizzi di
-- immatricolazione. Usare il dato regionale solo con questa avvertenza, oppure
-- aggregare a livello di paese per il confronto europeo.

SELECT
    year,
    geo,
    geo_label_en,
    nuts_level,
    country,
    value AS auto_per_1000
FROM clean_input
WHERE unit = 'P_THAB'
  AND vehicle = 'CAR'
  AND value IS NOT NULL
ORDER BY year, geo
