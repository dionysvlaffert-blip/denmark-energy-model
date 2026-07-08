import os

network_dir = "results/networks"

rename_map = {
    # ── Basis ─────────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion.nc":
        "02_baseline.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions.nc":
        "04_zero_co2.nc",

    # ── Nuclear ───────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_nuclear_2500_eur_per_kw.nc":
        "27_nuclear_2500_eur_per_kw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_nuclear_5000_eur_per_kw.nc":
        "28_nuclear_5000_eur_per_kw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_nuclear_7500_eur_per_kw.nc":
        "29_nuclear_7500_eur_per_kw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_nuclear_10000_eur_per_kw.nc":
        "30_nuclear_10000_eur_per_kw.nc",

    # ── Grid ──────────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_grid_full_expansion.nc":
        "05_grid_full_expansion.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_grid_max_1GW_per_line.nc":
        "06_grid_max_1GW.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_grid_autarky.nc":
        "07_grid_autarky.nc",

    # ── Solar CAPEX ───────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_solar_1p0_solar_capex_100pct.nc":
        "08_solar_capex_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_solar_0p75_solar_capex_75pct.nc":
        "09_solar_capex_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_solar_0p5_solar_capex_50pct.nc":
        "10_solar_capex_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_solar_0p25_solar_capex_25pct.nc":
        "11_solar_capex_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_solar_0p0_solar_capex_0pct.nc":
        "12_solar_capex_0pct.nc",

    # ── Wind CAPEX ────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_onshore_wind_1p0_generator_cost_offshore_wind_1p0_wind_capex_100pct.nc":
        "13_wind_capex_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_onshore_wind_0p75_generator_cost_offshore_wind_0p75_wind_capex_75pct.nc":
        "14_wind_capex_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_onshore_wind_0p5_generator_cost_offshore_wind_0p5_wind_capex_50pct.nc":
        "15_wind_capex_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_onshore_wind_0p25_generator_cost_offshore_wind_0p25_wind_capex_25pct.nc":
        "16_wind_capex_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_generator_cost_onshore_wind_0p0_generator_cost_offshore_wind_0p0_wind_capex_0pct.nc":
        "17_wind_capex_0pct.nc",

    # ── Battery CAPEX ─────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_storage_cost_battery_1p0_battery_capex_100pct.nc":
        "18_battery_capex_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_storage_cost_battery_0p75_battery_capex_75pct.nc":
        "19_battery_capex_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_storage_cost_battery_0p5_battery_capex_50pct.nc":
        "20_battery_capex_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_storage_cost_battery_0p25_battery_capex_25pct.nc":
        "21_battery_capex_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_storage_cost_battery_0p0_battery_capex_0pct.nc":
        "22_battery_capex_0pct.nc",

    # ── Transmission CAPEX ────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_link_cost_AC_1p0_transmission_capex_100pct.nc":
        "23_transmission_capex_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_link_cost_AC_0p75_transmission_capex_75pct.nc":
        "24_transmission_capex_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_link_cost_AC_0p5_transmission_capex_50pct.nc":
        "25_transmission_capex_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_link_cost_AC_0p25_transmission_capex_25pct.nc":
        "26_transmission_capex_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_link_cost_AC_0p0_transmission_capex_0pct.nc":
        "27_transmission_capex_0pct.nc",

    # ── Solar Potential ───────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_solar_1p0_solar_potential_100pct.nc":
        "31_solar_potential_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_solar_0p75_solar_potential_75pct.nc":
        "32_solar_potential_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_solar_0p5_solar_potential_50pct.nc":
        "33_solar_potential_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_solar_0p25_solar_potential_25pct.nc":
        "34_solar_potential_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_solar_0p0_solar_potential_0pct.nc":
        "35_solar_potential_0pct.nc",

    # ── Onshore Wind Potential ────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_onshore_wind_1p0_onshore_potential_100pct.nc":
        "36_onshore_potential_100pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_onshore_wind_0p75_onshore_potential_75pct.nc":
        "42_onshore_potential_75pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_onshore_wind_0p5_onshore_potential_50pct.nc":
        "43_onshore_potential_50pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_onshore_wind_0p25_onshore_potential_25pct.nc":
        "44_onshore_potential_25pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_renewable_potential_onshore_wind_0p0_onshore_potential_0pct.nc":
        "45_onshore_potential_0pct.nc",

    # ── Nuclear + Grid ────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_2500_eur_per_kw_link_cost_AC_1p0_nuclear_2500eurkw_grid_1GW.nc":
        "46_nuclear_2500eurkw_grid_1GW.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_5000_eur_per_kw_link_cost_AC_1p0_nuclear_5000eurkw_grid_1GW.nc":
        "47_nuclear_5000eurkw_grid_1GW.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_7500_eur_per_kw_link_cost_AC_1p0_nuclear_7500eurkw_grid_1GW.nc":
        "48_nuclear_7500eurkw_grid_1GW.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_10000_eur_per_kw_link_cost_AC_1p0_nuclear_10000eurkw_grid_1GW.nc":
        "49_nuclear_10000eurkw_grid_1GW.nc",

    # ── CO2 Reduction ─────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_10000000p0_tonnes_co2_reduction_0pct.nc":
        "50_co2_reduction_0pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_8000000p0_tonnes_co2_reduction_20pct.nc":
        "51_co2_reduction_20pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_6000000p0_tonnes_co2_reduction_40pct.nc":
        "52_co2_reduction_40pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_4000000p0_tonnes_co2_reduction_60pct.nc":
        "53_co2_reduction_60pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_1999999p9999999995_tonnes_co2_reduction_80pct.nc":
        "54_co2_reduction_80pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_500000p00000000047_tonnes_co2_reduction_95pct.nc":
        "55_co2_reduction_95pct.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_co2_limit_0p0_tonnes_co2_reduction_100pct.nc":
        "56_co2_reduction_100pct.nc",

    # ── Zero CO2 Nuclear ──────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_2500_eur_per_kw_zero_co2_nuclear_2500eurkw.nc":
        "57_zero_co2_nuclear_2500eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_5000_eur_per_kw_zero_co2_nuclear_5000eurkw.nc":
        "58_zero_co2_nuclear_5000eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_7500_eur_per_kw_zero_co2_nuclear_7500eurkw.nc":
        "59_zero_co2_nuclear_7500eurkw.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_nuclear_10000_eur_per_kw_zero_co2_nuclear_10000eurkw.nc":
        "60_zero_co2_nuclear_10000eurkw.nc",

    # ── Weather Year ──────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_weather_year_2012.nc":
        "61_weather_year_2012.nc",
        
     
    # ── All Renewables ────────────────────────────────────────────────────────
    "all_ren_potential_100pct.nc": "37_all_ren_potential_100pct.nc",
    "all_ren_potential_75pct.nc":  "38_all_ren_potential_75pct.nc",
    "all_ren_potential_50pct.nc":  "39_all_ren_potential_50pct.nc",
    "all_ren_potential_25pct.nc":  "40_all_ren_potential_25pct.nc",
    "all_ren_potential_0pct.nc":   "41_all_ren_potential_0pct.nc",

    # ── Resolution ────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_resolution_1h.nc":
        "62_resolution_1h.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_resolution_2h.nc":
        "63_resolution_2h.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_resolution_3h.nc":
        "64_resolution_3h.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_resolution_6h.nc":
        "65_resolution_6h.nc",

    # ── Tech Years ────────────────────────────────────────────────────────────
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_tech_year_2020.nc":
        "66_tech_year_2020.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_tech_year_2025.nc":
        "67_tech_year_2025.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_tech_year_2030.nc":
        "68_tech_year_2030.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_tech_year_2040.nc":
        "69_tech_year_2040.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_no_co2_emissions_tech_year_2050.nc":
        "70_tech_year_2050.nc",

}

rename_map = {
    "denmark_basic_network_level1_2012_full_grid_expansion_tec_cost_2030.nc":
        "71_tec_cost_2030.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_tec_cost_2040.nc":
        "72_tec_cost_2040.nc",
    "denmark_basic_network_level1_2012_full_grid_expansion_tec_cost_2050.nc":
        "73_tec_cost_2050.nc",
}

# Umbenennen
renamed = 0
skipped = 0
for old_name, new_name in rename_map.items():
    old_path = os.path.join(network_dir, old_name)
    new_path = os.path.join(network_dir, new_name)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        print(f"✓ {old_name[:50]}... → {new_name}")
        renamed += 1
    else:
        print(f"✗ nicht gefunden: {old_name[:50]}...")
        skipped += 1

print(f"\nFertig: {renamed} umbenannt, {skipped} nicht gefunden")

