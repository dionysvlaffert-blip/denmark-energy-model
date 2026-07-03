def print_network_summary(
    config,
    model_data,
    network,
):
    """
    Print a compact overview of input data and network components.

    Inputs: config, model_data from build_network and pypsa.Network.
    Output: prints to console; returns nothing.
    """
    regions = model_data["regions"]
    technology_parameters = model_data["technology_parameters"]
    storage_parameters = model_data["storage_parameters"]
    renewable_potentials = model_data["renewable_potentials"]
    existing_power_plants = model_data["existing_power_plants"]
    transmission_connections = model_data["transmission_connections"]

    print("\n=== Model summary ===")
    print(f"Setting: {config.setting_name}")
    print(f"Region level: {config.region_level}")
    print(f"Weather year: {config.weather_year}")
    print(f"Time resolution: {config.time_resolution}")
    print(f"Transmission scenario: {config.transmission_scenario}")

    print("\n--- Input data ---")
    print(f"Regions: {len(regions)}")
    print(f"Technologies: {len(technology_parameters)}")
    print(f"Storage options: {len(storage_parameters)}")
    print(f"Existing conventional plants/groups: {len(existing_power_plants)}")
    print(f"Transmission connections: {len(transmission_connections)}")

    print("\n--- Renewable potentials MW ---")
    print(renewable_potentials.groupby("carrier")["p_nom_max"].sum().round(1))

    print("\n--- Network components ---")
    print(f"Buses: {len(network.buses)}")
    print(f"Generators: {len(network.generators)}")
    print(f"Loads: {len(network.loads)}")
    print(f"Links: {len(network.links)}")
    print(f"Storage units: {len(network.storage_units)}")

    print("\n--- Generators by carrier ---")
    print(network.generators.groupby("carrier").size())

    print("\n--- Extendable generator capacity limits MW ---")
    generator_limits = network.generators[network.generators["p_nom_max"] < float("inf")]
    if generator_limits.empty:
        print("No generator p_nom_max limits set")
    else:
        print(generator_limits.groupby("carrier")["p_nom_max"].sum().round(1))

    print("\n--- Storage by carrier ---")
    if network.storage_units.empty:
        print("No storage units")
    else:
        print(network.storage_units.groupby("carrier").size())

    print("\n--- Transmission ---")
    if network.links.empty:
        print("No transmission links")
    else:
        print(f"Total link length km: {network.links['length'].sum():.1f}")
        print(f"Extendable links: {network.links['p_nom_extendable'].sum()}")

    print("=== End summary ===\n")


def print_optimization_results(network, status=None, condition=None):
    """
    Print key optimization results from a solved PyPSA network.

    Inputs: optimized network and optional solver status/condition.
    Output: prints result tables to console; returns nothing.
    """
    print("\n=== Optimization results ===")

    if status is not None:
        print(f"Status: {status}")
    if condition is not None:
        print(f"Condition: {condition}")

    print(f"Total system cost: {network.objective}")

    print("\n--- Optimized generator capacity by technology MW ---")
    print(network.generators.groupby("carrier")["p_nom_opt"].sum().sort_values(ascending=False))

    print("\n--- New extendable generator capacity by technology MW ---")
    extendable_generators = network.generators[network.generators["p_nom_extendable"]]
    print(extendable_generators.groupby("carrier")["p_nom_opt"].sum().sort_values(ascending=False))

    print("\n--- Existing fixed generator capacity by technology MW ---")
    fixed_generators = network.generators[~network.generators["p_nom_extendable"]]
    print(fixed_generators.groupby("carrier")["p_nom"].sum().sort_values(ascending=False))

    print("\n--- Optimized storage power capacity by technology MW ---")
    if network.storage_units.empty:
        print("No storage units")
    else:
        print(network.storage_units.groupby("carrier")["p_nom_opt"].sum().sort_values(ascending=False))

    print("\n--- Optimized storage energy capacity by technology MWh ---")
    if network.storage_units.empty:
        print("No storage units")
    else:
        storage_energy_capacity = network.storage_units["p_nom_opt"] * network.storage_units["max_hours"]
        print(storage_energy_capacity.groupby(network.storage_units["carrier"]).sum().sort_values(ascending=False))

    print("\n--- Optimized transmission capacity MW ---")
    if network.links.empty:
        print("No transmission links")
    else:
        print(network.links.groupby("carrier")["p_nom_opt"].sum().sort_values(ascending=False))

    weights = network.snapshot_weightings.generators

    print("\n--- Annual generation by technology MWh ---")
    generation = network.generators_t.p.mul(weights, axis=0).sum()
    generation_by_carrier = generation.groupby(network.generators["carrier"]).sum()
    print(generation_by_carrier.sort_values(ascending=False))

    print("\n--- Annual load MWh ---")
    load = network.loads_t.p_set.mul(weights, axis=0).sum().sum()
    print(load)

    print("=== End optimization results ===\n")