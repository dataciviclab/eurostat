-- mart_quarterly.sql: Quarterly GDP by NUTS 2, filtered to headline indicators.

SELECT
    year, quarter, country, geo, geo_label_en, nuts_level,
    na_item, na_item_label_en, unit, value
FROM clean_input
WHERE country IS NOT NULL
  AND s_adj = 'SCA'           -- seasonally adjusted
  AND na_item IN ('B1GQ', 'P3', 'P5g', 'P6', 'P7')  -- GDP, consumption, GFCF, exports, imports
  AND unit = 'CLV_PCH_PRE'    -- chain-linked volumes, percentage change on previous quarter
ORDER BY country, geo, year, quarter, na_item
