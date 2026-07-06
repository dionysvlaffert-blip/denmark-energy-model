from src.build_basic_network import save_network
from src.model_builder import build_network
from src.network_summary import print_network_summary, print_optimization_results
from src.project_config import ProjectConfig
from src.scenario_variations import (
	add_co2_emissions_limit,
	add_no_co2_emissions_constraint,
	add_nuclear_generators,
	scale_capital_cost,
	scale_generator_capital_cost,
	scale_link_capital_cost,
	scale_renewable_potential,
	scale_storage_capital_cost,
	set_nuclear_capital_cost,
)

# Ablauf:
# 1. Pro Szenario eine frische Config laden, damit der Dateiname sauber bleibt.
# 2. Netzwerk mit build_network(config) komplett aufbauen.
# 3. Optional eine Szenariofunktion auf network anwenden.
# 4. Hier spaeter den Solver laufen lassen.
# 5. Netzwerk mit dem aktuellen setting_name speichern.

# Baseline scenario
config = ProjectConfig("config/project_config.yaml")
network, model_data = build_network(config)
print_network_summary(config, model_data, network)
status, condition = network.optimize(solver_name=config.solver_name)
print_optimization_results(network, status, condition)
save_network(network, config)

#100 percent CO2 reduction scenario
config = ProjectConfig("config/project_config.yaml")
network, model_data = build_network(config)
add_no_co2_emissions_constraint(network, config, suffix="no_co2_emissions")
print_network_summary(config, model_data, network)
status, condition = network.optimize(solver_name=config.solver_name)
print_optimization_results(network, status, condition)
save_network(network, config)


# Nuclear cost scenarios
for nuclear_price_eur_per_kw in [2500, 5000, 7500, 10000]:
	config = ProjectConfig("config/project_config.yaml")
	network, model_data = build_network(config)
	add_nuclear_generators(network, nuclear_price_eur_per_kw, config)
	print_network_summary(config, model_data, network)
	status, condition = network.optimize(solver_name=config.solver_name)
	print_optimization_results(network, status, condition)
	save_network(network, config)

# ── Sensitivity 1: Grid expansion ─────────────────────────────────────────────
# Full expansion (already default, but explicit)
config = ProjectConfig("config/project_config.yaml")
network, model_data = build_network(config)
add_no_co2_emissions_constraint(network, config)
config.add_setting_name_suffix("grid_full_expansion")
status, condition = network.optimize(solver_name=config.solver_name)
print_optimization_results(network, status, condition)
save_network(network, config)

# Max 1 GW per transmission line
config = ProjectConfig("config/project_config.yaml")
network, model_data = build_network(config)
add_no_co2_emissions_constraint(network, config)
network.links.loc[network.links.carrier == "AC", "p_nom_max"] = 1000  # MW
config.add_setting_name_suffix("grid_max_1GW_per_line")
status, condition = network.optimize(solver_name=config.solver_name)
print_optimization_results(network, status, condition)
save_network(network, config)

# Autarky: no transmission allowed
config = ProjectConfig("config/project_config.yaml")
network, model_data = build_network(config)
add_no_co2_emissions_constraint(network, config)
network.links.loc[network.links.carrier == "AC", "p_nom_extendable"] = False
network.links.loc[network.links.carrier == "AC", "p_nom_max"] = 0.0
config.add_setting_name_suffix("grid_autarky")
status, condition = network.optimize(solver_name=config.solver_name)
print_optimization_results(network, status, condition)
save_network(network, config)

# ── Sensitivity 2: Solar capital cost reduction ────────────────────────────────
for cost_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_generator_capital_cost(network, "solar", cost_fraction, config)
    config.add_setting_name_suffix(f"solar_capex_{int(cost_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 2b: Wind capital cost reduction ───────────────────────────────
for cost_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_generator_capital_cost(network, "onshore_wind", cost_fraction, config)
    scale_generator_capital_cost(network, "offshore_wind", cost_fraction, config)
    config.add_setting_name_suffix(f"wind_capex_{int(cost_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 2c: Battery storage capital cost reduction ────────────────────
for cost_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_storage_capital_cost(network, "battery", cost_fraction, config)
    config.add_setting_name_suffix(f"battery_capex_{int(cost_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 2d: Transmission capital cost reduction ───────────────────────
for cost_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_link_capital_cost(network, "AC", cost_fraction, config)
    config.add_setting_name_suffix(f"transmission_capex_{int(cost_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 3: Solar potential reduction ──────────────────────────────────
for potential_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_renewable_potential(network, "solar", potential_fraction, config)
    config.add_setting_name_suffix(f"solar_potential_{int(potential_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 3b: Onshore wind potential reduction ─────────────────────────
for potential_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_renewable_potential(network, "onshore_wind", potential_fraction, config)
    config.add_setting_name_suffix(f"onshore_potential_{int(potential_fraction * 100)}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── Sensitivity 3c: All renewables potential reduction ────────────────────────
import os
for potential_fraction in [1.0, 0.75, 0.50, 0.25, 0.0]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    scale_renewable_potential(network, "solar",         potential_fraction, config)
    scale_renewable_potential(network, "onshore_wind",  potential_fraction, config)
    scale_renewable_potential(network, "offshore_wind", potential_fraction, config)
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    # Direkt mit kurzem Namen speichern
    short_path = f"results/networks/all_ren_potential_{int(potential_fraction * 100)}pct.nc"
    network.export_to_netcdf(short_path)
    print(f"Saved to {short_path}")

# ── Sensitivity 4: Nuclear + grid expansion combined ─────────────────────────
for nuclear_price_eur_per_kw in [2500, 5000, 7500, 10000]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    add_nuclear_generators(network, nuclear_price_eur_per_kw, config)
    scale_link_capital_cost(network, "AC", 1.0, config)
    network.links.loc[network.links.carrier == "AC", "p_nom_max"] = 1000
    config.add_setting_name_suffix(f"nuclear_{nuclear_price_eur_per_kw}eurkw_grid_1GW")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)

# ── CO2 reduction steps (partial decarbonisation) ────────────────────────────
for co2_reduction_pct in [0, 20, 40, 60, 80, 95, 100]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    # Berechne absolutes CO2 Limit basierend auf Reduktionsprozentsatz
    baseline_co2 = 1e7  # Beispielwert — anpassen falls bekannt
    co2_limit = baseline_co2 * (1 - co2_reduction_pct / 100)
    add_co2_emissions_limit(network, co2_limit, config)
    config.add_setting_name_suffix(f"co2_reduction_{co2_reduction_pct}pct")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)


# ── Nuclear in Zero CO2 network ───────────────────────────────────────────────
for nuclear_price_eur_per_kw in [2500, 5000, 7500, 10000]:
    config = ProjectConfig("config/project_config.yaml")
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    add_nuclear_generators(network, nuclear_price_eur_per_kw, config)
    config.add_setting_name_suffix(f"zero_co2_nuclear_{nuclear_price_eur_per_kw}eurkw")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)
    
# ── Sensitivity 5: Weather year variations ────────────────────────────────────
for weather_year in [2012, 2013, 2014]:
    config = ProjectConfig("config/project_config.yaml")
    config.update_setting("weather_year", weather_year)
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    config.add_setting_name_suffix(f"weather_year_{weather_year}")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)
    
# ── Sensitivity 6: Technology cost year ───────────────────────────────────────
for tech_year in [2020, 2025, 2030, 2040, 2050]:
    config = ProjectConfig("config/project_config.yaml")
    config.update_setting("technology_year", tech_year)
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    config.add_setting_name_suffix(f"tech_year_{tech_year}")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)
    
# ── Sensitivity 7: Temporal granularity ───────────────────────────────────────
for resolution in ["1h", "2h", "3h", "6h"]:
    config = ProjectConfig("config/project_config.yaml")
    config.update_setting("time_resolution", resolution)
    network, model_data = build_network(config)
    add_no_co2_emissions_constraint(network, config)
    config.add_setting_name_suffix(f"resolution_{resolution}")
    status, condition = network.optimize(solver_name=config.solver_name)
    print_optimization_results(network, status, condition)
    save_network(network, config)