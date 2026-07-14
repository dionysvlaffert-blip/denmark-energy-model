# Denmark 100% Renewable Electricity System — PyPSA Energy Model

**Data Science for Energy System Modelling — Summer Term 2026 | Group Assignment 4 | Group J**

---

## Overview

This repository contains the complete code to build, optimise and analyse scenarios for a **100% renewable electricity system for Denmark** using [PyPSA](https://pypsa.org/). The model covers 5 GADM Level 1 regions, uses ERA5 reanalysis weather data for 2012, 2016 and 2024, and runs over 70 scenarios including sensitivity analyses on technology costs, renewable potentials, nuclear costs, grid expansion and CO₂ reduction pathways.

---

## Repository Structure

```
pypsa_dn-main/
│
├── main.py                            # Main scenario runner — runs all model optimisations
├── analysis.py                        # Plotting script — generates all figures
├── create_pdf_with_plots.py           # PDF report generator (combines all plots)
├── Eligibility_analysis.ipynb         # Land eligibility analysis (Jupyter Notebook)
├── README.md                          # This file
│
├── config/
│   └── project_config.yaml            # Central configuration (regions, costs, potentials, solver)
│
├── data/
│   ├── raw/
│   │   ├── technolgy_parameters_2025.csv   # Technology costs — 2025 projection
│   │   ├── technolgy_parameters_2030.csv   # Technology costs — 2030 projection
│   │   ├── technolgy_parameters_2040.csv   # Technology costs — 2040 projection
│   │   ├── technolgy_parameters_2050.csv   # Technology costs — 2050 projection
│   │   ├── load.csv                        # National load time series (GEGIS)
│   │   ├── eez_v11.gpkg                    # Exclusive Economic Zone boundaries
│   │   ├── weather/                        # ERA5 weather cutouts
│   │   │   ├── 2012/denmark_era5_2012.nc
│   │   │   ├── 2016/denmark_era5_2016.nc
│   │   │   └── 2024/denmark_era5_2024.nc
│   │   └── global-power-plant-database/    # WRI existing power plant fleet
│   └── processed/
│       ├── weather/                        # Processed capacity factor time series (CSV)
│       ├── regions/                        # Region shapes and coordinates
│       └── renewable_potentials/           # Land eligibility analysis results
│           └── denmark_renewable_availability_level1.csv
│
├── results/
│   ├── networks/                      # Solved PyPSA networks (.nc files, not in git)
│   ├── figures/                       # Generated plots (.png files)
│   └── denmark_complete_analysis.pdf  # Full PDF report
│
├── scripts/
│   ├── analysis_functions.py          # Helper functions for loading weather profiles
│   ├── create_region_coordinates.py   # Generate region coordinate files
│   ├── download_era5_data.py          # Download ERA5 weather data from Copernicus CDS
│   ├── prepare_weather_profiles.py    # Generate capacity factor CSVs from ERA5 cutout
│   └── rename_networks.py             # Rename solved network files to numbered convention
├   |── run                            # Weather analysis runner — Dunkelflaute, FFT, rolling variance  
│
└── src/
    ├── build_basic_network.py         # Network construction and saving
    ├── existing_power_plants.py       # Load and add existing conventional fleet
    ├── fixxed_values.py               # Fixed constants (country code, turbine types, panels)
    ├── load_profiles.py               # Load time series loader and regional distribution
    ├── model_builder.py               # Main model builder (calls all src modules)
    ├── network_summary.py             # Results summary printer
    ├── project_config.py              # YAML configuration loader
    ├── renewable_potentials.py        # Renewable potential loader from eligibility CSV
    ├── scenario_variations.py         # Scenario modification functions (CAPEX, CO₂, nuclear)
    ├── technology_parameters.py       # Technology cost loader and annuity calculator
    ├── transmission_topology.py       # Grid topology builder (links between regions)
    └── weather_profiles.py            # Weather profile loader (capacity factor CSVs)
```

---

## Model Description

### Spatial Resolution
- **5 regions:** Hovedstaden, Sjælland, Syddanmark, Midtjylland, Nordjylland (GADM Level 1)
- Regions connected by **bidirectional transmission links**: 700 €/MW/km × 1.5 route factor
- Representative points: centroids of each region shape

### Temporal Resolution
- **3-hourly** time steps (2,920 snapshots per year)
- Primary weather year: **2012** (ERA5 reanalysis)
- Sensitivity weather years: 2016, 2024

### Technologies

| Category | Technology | Notes |
|---|---|---|
| Conventional | Coal, Gas (CCGT), Oil, Biomass, Hydro | Fixed existing fleet, not extendable |
| Solar PV | CdTe panel, latitude-optimal orientation | Extendable from 0 |
| Onshore Wind | Vestas V112 3MW turbine | Extendable from 0 |
| Offshore Wind | NREL ReferenceTurbine 5MW | Extendable from 0, within EEZ |
| Battery Storage | 2h / 4h / 6h energy-to-power ratio | Short-term balancing |
| Hydrogen Storage | 168h / 336h / 672h energy-to-power ratio | Seasonal balancing |
| Nuclear | Optional, sensitivity analysis only | Zero CO₂ emissions assumed |

### Renewable Potentials (from land eligibility analysis)

| Technology | Max. Potential | Deployment Density |
|---|---|---|
| Solar PV | **86,190 MW** | 3 MW/km² |
| Onshore Wind | **11,655 MW** | 3 MW/km² |
| Offshore Wind | **114,975 MW** | 3 MW/km² |

**Eligibility criteria:**
- **Onshore Wind:** >1km from settlements, >300m from roads, >10km from airports, max 2000m elevation, no protected areas, suitable land cover
- **Offshore Wind:** within EEZ, max 50m water depth, >10km from shore, no protected areas
- **Solar PV:** suitable land cover, no protected areas

### Cost Assumptions
- **Technology data:** [PyPSA/technology-data](https://github.com/PyPSA/technology-data) — 2025 projections
- **Discount rate:** 7%
- **Capital cost:** Annualised CAPEX + Fixed O&M (FOM)
- **Marginal cost:** Fuel costs + Variable O&M (VOM)

---

## How to Run

### Prerequisites

```bash
# Install dependencies
pip install pypsa atlite geopandas pandas numpy matplotlib reportlab
pip install cfgrib eccodes

# Gurobi solver (academic license required)
# https://www.gurobi.com/academia/academic-program-and-licenses/

# CDS API key for ERA5 download
# https://cds.climate.copernicus.eu → Register → API key → ~/.cdsapirc
```

### Step 1: Download ERA5 Weather Data

```bash
# Edit YEAR in the script (2012, 2016, or 2024), then run:
python scripts/download_era5_data.py
```

Requires a CDS API account and accepted ERA5 license at:
https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels

### Step 2: Prepare Weather Profiles

```bash
# Set weather_year and weather_cutout_file in config/project_config.yaml
# Then run for each year (2012, 2016, 2024):
python scripts/prepare_weather_profiles.py
# Reset config to 2012 after each year!
```

### Step 3: Run Land Eligibility Analysis

```bash
# Open and run the Jupyter notebook:
jupyter notebook Eligibility_analysis.ipynb
# Output: data/processed/renewable_potentials/denmark_renewable_availability_level1.csv
```

### Step 4: Run All Scenarios

```bash
# From the project root directory:
cd pypsa_dn-main
python main.py
```

⚠️ This runs ~70 optimisations. Runtime: **4–8 hours** with Gurobi (academic license).
Disable screen sleep before running: `powercfg /change standby-timeout-ac 0`

### Step 5: Rename Network Files

```bash
python scripts/rename_networks.py
```

### Step 6: Generate All Plots

```bash
python analysis.py
```

### Step 7: Generate PDF Report

```bash
python create_pdf_with_plots.py
# Output: results/denmark_complete_analysis.pdf
```

---

## Scenarios

### Base Scenarios
| # | File | Description |
|---|---|---|
| 02 | `02_baseline.nc` | No CO₂ limit — existing fossil fleet operates freely |
| 04 | `04_zero_co2.nc` | 100% CO₂ reduction — fully renewable system |

### Sensitivity 1: Grid Expansion
| # | File | Description |
|---|---|---|
| 05 | `05_grid_full_expansion.nc` | Unconstrained transmission |
| 06 | `06_grid_max_1GW.nc` | Max 1 GW per transmission line |
| 07 | `07_grid_autarky.nc` | No inter-regional transmission (autarky) |

### Sensitivity 2: Technology CAPEX (Zero CO₂)
| Technology | Files | Steps |
|---|---|---|
| Solar CAPEX | `08`–`12` | 100% → 75% → 50% → 25% → 0% |
| Wind CAPEX | `13`–`17` | 100% → 75% → 50% → 25% → 0% |
| Battery CAPEX | `18`–`22` | 100% → 75% → 50% → 25% → 0% |
| Transmission CAPEX | `23`–`27` | 100% → 75% → 50% → 25% → 0% |

### Sensitivity 3: Renewable Potentials (Zero CO₂)
| Technology | Files | Steps |
|---|---|---|
| Solar potential | `31`–`35` | 100% → 75% → 50% → 25% → 0% |
| Onshore wind potential | `36`, `42`–`45` | 100% → 75% → 50% → 25% → 0% |
| All renewables simultaneously | `37`–`41` | 100% → 75% → 50% → 25% → 0% |

### Sensitivity 4: Nuclear Costs
| # | File | CAPEX |
|---|---|---|
| 27–30 | Nuclear baseline | 2,500 / 5,000 / 7,500 / 10,000 €/kW |
| 46–49 | Nuclear + 1GW grid | 2,500 / 5,000 / 7,500 / 10,000 €/kW |
| 57–60 | Nuclear + Zero CO₂ | 2,500 / 5,000 / 7,500 / 10,000 €/kW |

### Sensitivity 5: Weather Years (Zero CO₂)
| # | File | Year |
|---|---|---|
| 61 | `61_weather_year_2012.nc` | 2012 (baseline year) |
| 62 | `62_weather_year_2016.nc` | 2016 |
| 63 | `63_weather_year_2024.nc` | 2024 |

### Sensitivity 6: Technology Cost Years (Zero CO₂)
| # | File | Year |
|---|---|---|
| 71 | `71_tec_cost_2030.nc` | 2030 projections |
| 72 | `72_tec_cost_2040.nc` | 2040 projections |
| 73 | `73_tec_cost_2050.nc` | 2050 projections |

### CO₂ Reduction Pathway
| # | File | CO₂ Reduction |
|---|---|---|
| 50 | `50_co2_reduction_0pct.nc` | 0% |
| 51 | `51_co2_reduction_20pct.nc` | 20% |
| 52 | `52_co2_reduction_40pct.nc` | 40% |
| 53 | `53_co2_reduction_60pct.nc` | 60% |
| 54 | `54_co2_reduction_80pct.nc` | 80% |
| 55 | `55_co2_reduction_95pct.nc` | 95% |
| 56 | `56_co2_reduction_100pct.nc` | 100% |

---

## Configuration

Key settings in `config/project_config.yaml`:

```yaml
paths:
  technology_parameters_file: data/raw/technolgy_parameters_2025.csv
  renewable_availability_file: data/processed/renewable_potentials/denmark_renewable_availability_level1.csv
  weather_cutout_file: data/raw/weather/2012/denmark_era5_2012.nc

settings:
  weather_year: 2012
  time_resolution: 3h
  solver_name: gurobi
  renewable_potentials_mw:
    solar: 86190.0
    onshore_wind: 11655.0
    offshore_wind: 114975.0
```

---

## Key Results

| Scenario | System Cost | Key Finding |
|---|---|---|
| Baseline | 1.36 B€/year | Coal dominates (92%), low cost due to sunk CAPEX |
| Zero CO₂ | 4.09 B€/year | Wind dominates (82%), costs triple due to new investment |
| Autarky | ~9 B€/year | No transmission is the most expensive scenario |
| Battery 0% CAPEX | ~1.6 B€/year | Cheap storage dramatically reduces system cost |
| CO₂ –60% | ~2.5 B€/year | First 60% reduction is cheap; last 40% is costly |

---

## Data Sources

| Dataset | Source | Year |
|---|---|---|
| Weather reanalysis | [ERA5 via Copernicus CDS](https://cds.climate.copernicus.eu) + [atlite](https://atlite.readthedocs.io/) | 2012, 2016, 2024 |
| Regional shapes | [GADM](https://gadm.org/) Level 1 | 2022 |
| Exclusive Economic Zone | [Marine Regions EEZ v11](https://www.marineregions.org/) | 2022 |
| Protected areas | [WDPA](https://www.protectedplanet.net/) | Oct 2022 |
| Land cover | [Copernicus Global Land Cover 100m](https://land.copernicus.eu/) | 2019 |
| Elevation / Water depth | [GEBCO](https://www.gebco.net/) | 2014 |
| Existing power plants | [WRI Global Power Plant Database](https://datasets.wri.org/dataset/globalpowerplantdatabase) | 2017 |
| Technology costs | [PyPSA/technology-data](https://github.com/PyPSA/technology-data) | 2025/2030/2040/2050 |
| Load time series | [GEGIS](https://github.com/PyPSA/pypsa-eur) | 2025 |
| Airport locations | [Natural Earth](https://www.naturalearthdata.com/) | — |
| Road network | [Natural Earth](https://www.naturalearthdata.com/) | — |

---

## Authors

**Group J** — Data Science for Energy System Modelling, Summer Term 2026, TU Berlin