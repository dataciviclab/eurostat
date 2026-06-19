# Dataset Shortlist — Eurostat NUTS3

Source: Eurostat SDMX catalog (8,234 dataflows, 116 at NUTS3 level).
Generated: 2026-06-18

## Coverage (5/5 ✓)

| Dataset | NUTS | Rows | Period | Theme |
|---|---|---|---|---|
| NAMA_10R_3GDP | NUTS3 | 309K | 2000-2024 | GDP per capita |
| NAMA_10R_3GVA | NUTS3 | 1.3M | 2000-2024 | Gross Value Added by NACE |
| NAMA_10R_3EMPERS | NUTS3 | 1.5M | 2000-2024 | Employment by NACE |
| DEMO_R_D2JAN | NUTS2 | 5.8M | 1990-2025 | Population by sex/age |
| CRIM_GEN | NUTS3 | 4K | 1993-2007 | Recorded crimes |

## Tier 1 — High priority, low effort

| Dataflow | Theme | Rows | Period | NUTS | Effort | Why |
|---|---|---|---|---|---|---|
| DEMO_R_D3DENS | Population density | 57K | 1990-2024 | **NUTS3** | Very low | Tiny dataset, immediate storytelling (maps) |
| DEMO_R_GIND3 | Demographic balance | 490K | 2000-2025 | **NUTS3** | Low | Births, deaths, migration — explains population decline |
| LFST_R_LFE2EMPRT | Employment rates | 427K | 1999-2025 | NUTS2 | Low | Same dimensions as POP (sex, age, geo) |
| DEMO_R_PJANGRP3 | Population by age group | 1.5M | 2014-2025 | **NUTS3** | Low | NUTS3 version of POP, recent data |

## Tier 2 — Medium effort, high value

| Dataflow | Theme | Rows | Period | NUTS | Why |
|---|---|---|---|---|---|
| TOUR_OCC_ARN2 | Tourist arrivals | 281K | 1990-2025 | NUTS2 | Very high civic value for Italy. New dim: c_resid |
| NRG_CHDDR2_M | Heating/cooling degree days | 2M | 1980-2025 | **NUTS3** | Monthly! Climate change storytelling |
| PAT_EP_RIPC | Patent applications | 4M | 1977-2012 | **NUTS3** | Innovation gap analysis |
| TRAN_R_RAIL | Rail passengers | ~200K | ? | NUTS3 | Public transport, Italian relevance |

## Tier 3 — Niche but valuable

| Dataflow | Theme | Rows | Period | NUTS | Why |
|---|---|---|---|---|---|
| BD_SIZE_R3 | Business demography | 980K | 2008-2020 | **NUTS3** | Firm birth/death by size class |
| BD_HGNACE2_R3 | High-growth enterprises | 2.7M | 2008-2020 | **NUTS3** | Innovation ecosystems |
| DEMO_R_MAGEC3 | Deaths by age/sex | 1.3M | 2013-2024 | **NUTS3** | Mortality analysis, COVID impact |
| DEMO_R_PJANIND3 | Population structure | 1.2M | 2014-2025 | **NUTS3** | Dependency ratios, aging index |
| HLTH_RS_PHYSREG | Physicians | 22K | 1993-2024 | NUTS2 | Healthcare access, very light |

## Selection criteria

1. **Civic value**: how tellable / useful for citizens and policy
2. **NUTS3**: prefer NUTS3 over NUTS2 for granular analysis
3. **Freshness**: prefer datasets with recent data (2024-2025)
4. **Technical fit**: prefer dimensions already handled by existing clean.sql patterns (sex, age, geo, unit, freq)
5. **Complementarity**: avoid overlap with existing 5 datasets
