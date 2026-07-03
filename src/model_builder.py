from src.build_basic_network import (
    add_buses,
    add_carriers,
    add_existing_conventional_generators,
    add_loads,
    add_renewable_generators,
    add_storage_units,
    add_transmission_links,
    create_network,
    create_snapshots,
    load_regions,
)
from src.existing_power_plants import load_existing_power_plants
from src.load_profiles import load_national_load, prepare_load_profiles
from src.renewable_potentials import load_renewable_potentials
from src.technology_parameters import load_storage_parameters, load_technology_parameters
from src.transmission_topology import find_transmission_connections
from src.weather_profiles import load_weather_profiles, resample_weather_profiles


def build_network(config):
    """
    Build a complete unoptimized PyPSA network from the project config.

    Input: ProjectConfig instance.
    Output: tuple (network, model_data) where model_data stores loaded input tables.
    """
    regions = load_regions(config)
    technology_parameters = load_technology_parameters(config)
    storage_parameters = load_storage_parameters(config)
    weather_profiles_hourly = load_weather_profiles(config)
    national_load_hourly = load_national_load(config)
    existing_power_plants = load_existing_power_plants(config, regions)
    snapshots = create_snapshots(config)
    weather_profiles = resample_weather_profiles(weather_profiles_hourly, snapshots, config.time_resolution)
    load_profiles = prepare_load_profiles(
        national_load_hourly,
        regions,
        snapshots,
        config.time_resolution,
        config.load_distribution,
    )
    renewable_potentials = load_renewable_potentials(config, regions)

    if config.transmission_max_distance_km == 0:
        transmission_connections = []
        print("Transmission topology: autarky scenario, no transmission links between regions")
    else:
        transmission_connections = find_transmission_connections(
            regions,
            config.transmission_max_distance_km,
        )

    network = create_network(config)
    add_carriers(network, config, technology_parameters)
    add_buses(network, regions)
    add_existing_conventional_generators(network, existing_power_plants, technology_parameters)
    add_storage_units(network, regions, storage_parameters)
    add_renewable_generators(network, regions, technology_parameters, weather_profiles, renewable_potentials)
    add_loads(network, load_profiles)
    add_transmission_links(network, regions, config, transmission_connections)

    model_data = {
        "regions": regions,
        "technology_parameters": technology_parameters,
        "storage_parameters": storage_parameters,
        "weather_profiles": weather_profiles,
        "load_profiles": load_profiles,
        "renewable_potentials": renewable_potentials,
        "existing_power_plants": existing_power_plants,
        "transmission_connections": transmission_connections,
    }

    return network, model_data