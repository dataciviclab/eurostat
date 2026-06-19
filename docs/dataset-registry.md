# Dataset Registry

## Published

| Slug | Dataflow | Theme | DSD dims | Clean rows | Status |
|---|---|---|---|---|---|
| `eurostat-gdp-nuts3` | `NAMA_10R_3GDP` | Economy / GDP per capita | 3 (freq, unit, geo) | 308,950 | ✅ |
| `eurostat-gva-nuts3` | `NAMA_10R_3GVA` | Economy / Gross Value Added by NACE | 4 (freq, nace_r2, unit, geo) | 1,339,200 | ✅ |
| `eurostat-crime-nuts3` | `CRIM_GEN` | Crime / Recorded offences by ICCS | 4 (freq, iccs, unit, geo) | 4,035 | ✅ |
| `eurostat-pop-nuts3` | `DEMO_R_D2JAN` | Demography / Population on 1 Jan | 5 (freq, unit, sex, age, geo) | 300,348 | ✅ |
| `eurostat-emp-nuts3` | `NAMA_10R_3EMPERS` | Economy / Employment by NACE | 5 (freq, unit, wstatus, nace_r2, geo) | 1,541,975 | ✅ |
| `eurostat-pop-density-nuts3` | `DEMO_R_D3DENS` | Demography / Population density | 3 (freq, unit, geo) | 73,010 | ✅ |
| `eurostat-demo-balance-nuts3` | `DEMO_R_GIND3` | Demography / Demographic balance | 3 (freq, indic_de, geo) | 608,088 | ✅ |
| `eurostat-tourism-nuts3` | `TOUR_OCC_NIN2` | Tourism / Nights spent by NUTS3 | 5 (freq, c_resid, unit, nace_r2, geo) | 1,161,108 | ✅ |

All published datasets:
- Cover **all EU countries**, all available years (1990–2024 depending on dataflow)
- Mart filters for **Italy NUTS3** (provinces)
- Clean + mart parquet available locally in `out/data/` and on GCS via the [publish workflow](.github/workflows/publish.yml)

## Planned

| Dataflow | Theme | NUTS | Priority |
|---|---|---|---|
| `LFST_R_LFE2EMPRT` | Labour / Employment rates by sex & age | NUTS3 | high |
| `TOUR_OCC_NIN2` | Tourism / Nights spent by NUTS3 | NUTS3 | published ✅ |
| `BD_SIZE_R3` | Business demography | NUTS3 | medium |
| `TRAN_R_RAIL` | Transport / Rail passengers | NUTS3 | medium |
| `EDUC_UOE_ENRL_R3` | Education / Enrolment | NUTS3 | medium |
| `HLTH_RS_PHYSREG` | Health / Physicians | NUTS2 | low |

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
