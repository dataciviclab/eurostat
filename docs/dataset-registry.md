# Dataset Registry

## Published

| Slug | Dataflow | Theme | DSD dims | Clean rows | Status |
|---|---|---|---|---|---|
| `eurostat-gdp-nuts3` | `NAMA_10R_3GDP` | Economy / GDP per capita | 3 (freq, unit, geo) | 308,950 | ✅ |
| `eurostat-gva-nuts3` | `NAMA_10R_3GVA` | Economy / Gross Value Added by NACE | 4 (freq, nace_r2, unit, geo) | 1,339,200 | ✅ |
| `eurostat-crime-nuts3` | `CRIM_GEN_REG` | Crime / Police-recorded offences by NUTS3 | 4 (freq, iccs, unit, geo) | 436,118 | ✅ |
| `eurostat-pop-nuts3` | `DEMO_R_D2JAN` | Demography / Population on 1 Jan | 5 (freq, unit, sex, age, geo) | 300,348 | ✅ |
| `eurostat-emp-nuts3` | `NAMA_10R_3EMPERS` | Economy / Employment by NACE | 5 (freq, unit, wstatus, nace_r2, geo) | 1,541,975 | ✅ |
| `eurostat-pop-density-nuts3` | `DEMO_R_D3DENS` | Demography / Population density | 3 (freq, unit, geo) | 73,010 | ✅ |
| `eurostat-demo-balance-nuts3` | `DEMO_R_GIND3` | Demography / Demographic balance | 3 (freq, indic_de, geo) | 608,088 | ✅ |
| `eurostat-tourism-nuts3` | `TOUR_OCC_NIN2` | Tourism / Nights spent by NUTS3 | 5 (freq, c_resid, unit, nace_r2, geo) | 1,161,108 | ✅ |
| `eurostat-tran-sf-roadnu` | `TRAN_SF_ROADNU` | Road accidents by NUTS3 | 3 (freq, unit, geo) | 53,419 | ✅ |
| `eurostat-demo-r-magec3-nuts3` | `DEMO_R_MAGEC3` | Demography / Deaths by age group and sex | 5 (freq, sex, unit, age, geo) | 1,618,272 | ✅ |
| `eurostat-demo-r-pjangrp3-nuts3` | `DEMO_R_PJANGRP3` | Demography / Population by age group | 5 (freq, sex, unit, age, geo) | 1,686,888 | ✅ |
| `eurostat-demo-r-fagec3-nuts3` | `DEMO_R_FAGEC3` | Demography / Live births by age group | 4 (freq, age, unit, geo) | 322,968 | ✅ |
| `eurostat-nrg-chddr2-a-nuts3` | `NRG_CHDDR2_A` | Energy / Heating and cooling degree days (annual) | 4 (freq, unit, indic_nrg, geo) | 165,600 | ✅ |
| `eurostat-nrg-chddr2-m-nuts3` | `NRG_CHDDR2_M` | Energy / Heating and cooling degree days (monthly) | 5 (freq, unit, indic_nrg, geo, month) | 1,987,200 | ✅ |
| `eurostat-bd-hgnace2-r3-nuts3` | `BD_HGNACE2_R3` | Business / Business demography & high-growth | 4 (freq, indic_sb, nace_r2, geo) | 4,391,569 | ✅ |
| `eurostat-pop-structure-nuts3` | `DEMO_R_PJANIND3` | Demography / Population structure indicators | 4 (freq, indic_de, unit, geo) | 1,327,452 | ✅ |
| `eurostat-labour-productivity-nuts3` | `NAMA_10R_3NLP` | Economy / Nominal Labour productivity | 4 (freq, na_item, unit, geo) | 121,725 | ✅ |
| `eurostat-soil-erosion-nuts3` | `AEI_PR_SOILER` | Environment / Estimated soil erosion by water | 5 (freq, levels, clc18, unit, geo) | 523,200 | ✅ |
| `eurostat-area-nuts3` | `REG_AREA3` | Geography / Area by land use category | 4 (freq, landuse, unit, geo) | 65,240 | ✅ |
| `eurostat-fertility-nuts3` | `DEMO_R_FIND3` | Demography / Fertility indicators | 4 (freq, indic_de, unit, geo) | 76,392 | ✅ |

All published datasets:
- Cover **all EU countries**, all available years (1990–2024 depending on dataflow)
- Mart filters for **Italy NUTS3** (provinces)
- Clean + mart parquet available locally in `out/data/` and on GCS via the [publish workflow](.github/workflows/publish.yml)

## Planned

Want to add one? Check the [good first issues](https://github.com/dataciviclab/eurostat/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) for datasets with ready-to-use templates.

| Dataflow | Theme | NUTS | Priority |
|---|---|---|---|
| `LFST_R_LFE2EMPRT` | Labour / Employment rates by sex & age | NUTS2 | high |
| `BD_HGNACE2_R3` | Business demography & high-growth | NUTS3 | ✅ published |
| `BD_SIZE_R3` | Business demography by size class | NUTS3 | medium |
| `TRAN_R_RAIL` | Transport / Rail passengers | NUTS3 | medium |
| `EDUC_UOE_ENRL_R3` | Education / Enrolment | NUTS3 | medium |
| `HLTH_RS_PHYSREG` | Health / Physicians | NUTS2 | low |
| ~~`DEMO_R_MAGEC3`~~ | Deaths by age group and sex | NUTS3 | ✅ published |
| `PAT_EP_RIPC` | Patent applications to the EPO | NUTS3 | medium |
| ~~`NRG_CHDDR2_A`~~ | Heating and cooling degree days (annual) | NUTS3 | ✅ published |
| ~~`NRG_CHDDR2_M`~~ | Heating and cooling degree days (monthly) | NUTS3 | ✅ published |
| ~~`DEMO_R_PJANIND3`~~ | Population structure indicators | NUTS3 | ✅ published |
| ~~`AEI_PR_SOILER`~~ | Estimated soil erosion by water | NUTS3 | ✅ published |
| ~~`REG_AREA3`~~ | Area by NUTS 3 region | NUTS3 | ✅ published |
| ~~`DEMO_R_FIND3`~~ | Fertility indicators | NUTS3 | ✅ published |

Total Eurostat catalog: ~8,200 dataflows — 121 at NUTS3 level.

## Dataflow anatomy

Each Eurostat dataflow has a unique DSD (Data Structure Definition) that defines its dimensions. The connector auto-detects them from the TSV header — no configuration needed.

Common dimensions:
- `freq` — frequency (A=annual, Q=quarterly, M=monthly)
- `unit` — unit of measure (EUR_HAB, MIO_EUR, NR, CP_MEUR, etc.)
- `geo` — geographic code (NUTS0/1/2/3)
- `sex` — sex (M, F, T)
- `age` — age class
- `nace_r2` — economic activity (NACE Rev. 2)
- `iccs` — crime classification
- `wstatus` — working status
- `c_resid` — country of residence (DOM/FOR/TOTAL)

Codelists for all resolved dimensions are in `codelists/`.
