import pandas as pd
import pypsa

from src.fixxed_values import (
    COUNTRY_CODE,
    LIMITED_GRID_MAX_CAPACITY_MW,
    TRANSMISSION_COST_EUR_PER_MW_KM,
    TRANSMISSION_LENGTH_FACTOR,
)


def load_regions(config):
    """
    Load model regions and create one bus name per region.

    Input: config with region_coordinates_file.
    Output: DataFrame with region data and a bus column.
    """
    if not config.region_coordinates_file.exists():
        raise FileNotFoundError(f"Region file not found: {config.region_coordinates_file}")

    regions = pd.read_csv(config.region_coordinates_file)
    regions["bus"] = COUNTRY_CODE + "_region_" + regions["region_id"].astype(str)
    return regions


def create_snapshots(config):
    """
    Create the model time index for the selected weather year.

    Input: config.weather_year and config.time_resolution.
    Output: pandas DatetimeIndex used as PyPSA snapshots.
    """
    return pd.date_range(
        f"{config.weather_year}-01-01 00:00",
        f"{config.weather_year + 1}-01-01 00:00",
        freq=config.time_resolution,
        inclusive="left",
    )


def create_network(config):
    """
    Initialize an empty PyPSA network with snapshots and snapshot weights.

    Input: project config.
    Output: empty pypsa.Network ready for components.
    """
    network = pypsa.Network()
    network.set_snapshots(create_snapshots(config))
    network.snapshot_weightings.loc[:, :] = pd.Timedelta(config.time_resolution) / pd.Timedelta(hours=1)
    return network


def add_carriers(network, config, technology_parameters=None):
    """
    Add carriers to the network and attach CO2 intensities if available.

    Inputs: network, config.carriers, optional technology parameter table.
    Output: modifies network.carriers in place.
    """
    for carrier in config.carriers:
        network.add("Carrier", carrier)

    if technology_parameters is None:
        return

    for carrier, values in technology_parameters.iterrows():
        if carrier in network.carriers.index:
            network.carriers.loc[carrier, "co2_emissions"] = values["co2_intensity"]


def add_buses(network, regions):
    """
    Add one AC bus for each model region.

    Inputs: network and regions DataFrame with bus_x, bus_y and bus.
    Output: modifies network.buses in place.
    """
    for _, region in regions.iterrows():
        network.add(
            "Bus",
            region["bus"],
            carrier="AC",
            x=region["bus_x"],
            y=region["bus_y"],
        )


def add_existing_conventional_generators(network, existing_power_plants, technology_parameters):
    """
    Add fixed existing conventional capacity from the prepared plant table.

    Inputs: network, existing plants by bus/carrier, technology parameters.
    Output: modifies network.generators in place.
    """
    if existing_power_plants is None:
        return

    for _, power_plants in existing_power_plants.iterrows():
        bus = power_plants["bus"]
        carrier = power_plants["carrier"]

        if bus not in network.buses.index:
            raise ValueError(f"Existing power plant bus not found in network: {bus}")
        if carrier not in technology_parameters.index:
            print(f"Warning: Missing technology parameters for existing carrier: {carrier}. Skipping.")
            continue

        values = technology_parameters.loc[carrier]
        generator_name = f"{bus}_existing_{carrier}"

        network.add(
            "Generator",
            generator_name,
            bus=bus,
            carrier=carrier,
            p_nom=power_plants["p_nom_mw"],
            p_nom_extendable=False,
            p_max_pu=power_plants["p_max_pu"],
            capital_cost=0,
            marginal_cost=values["marginal_cost"],
            efficiency=values["efficiency"],
        )


def add_storage_units(network, regions, storage_parameters):
    """
    Add extendable battery and hydrogen storage options to every bus.

    Inputs: network, regions and storage parameter table.
    Output: modifies network.storage_units in place.
    """
    if storage_parameters is None:
        return

    for _, region in regions.iterrows():
        bus = region["bus"]

        for _, storage in storage_parameters.iterrows():
            carrier = storage["carrier"]
            max_hours = int(storage["max_hours"])
            storage_name = f"{bus}_{carrier}_{max_hours}h_storage"

            network.add(
                "StorageUnit",
                storage_name,
                bus=bus,
                carrier=carrier,
                p_nom_extendable=True,
                max_hours=max_hours,
                capital_cost=storage["capital_cost"],
                marginal_cost=storage["marginal_cost"],
                efficiency_store=storage["efficiency_store"],
                efficiency_dispatch=storage["efficiency_dispatch"],
                cyclic_state_of_charge=True,
            )


def add_renewable_generators(network, regions, technology_parameters, weather_profiles, renewable_potentials=None):
    """
    Add solar, onshore wind and offshore wind generators with weather profiles.

    Inputs: network, regions, technology parameters, p_max_pu profiles and optional p_nom_max potentials.
    Output: modifies network.generators and network.generators_t.p_max_pu in place.
    """
    if technology_parameters is None or weather_profiles is None:
        print("Warning: Technology parameters or weather profiles are None. Skipping renewable generator addition.")
        return

    renewable_carriers = ["solar", "onshore_wind", "offshore_wind"]

    for _, region in regions.iterrows():
        bus = region["bus"]

        for carrier in renewable_carriers:
            if carrier not in technology_parameters.index:
                continue
            if carrier not in weather_profiles:
                print(f"Warning: Missing weather profile for carrier: {carrier}. Skipping generator addition.")
                continue
            if bus not in weather_profiles[carrier].columns:
                print(f"Warning: Missing weather profile column for bus: {bus}. Skipping generator addition.")
                continue

            values = technology_parameters.loc[carrier]
            generator_name = f"{bus}_{carrier}"
            generator_values = {
                "bus": bus,
                "carrier": carrier,
                "p_nom_extendable": True,
                "capital_cost": values["capital_cost"],
                "marginal_cost": values["marginal_cost"],
                "efficiency": values["efficiency"],
            }

            if renewable_potentials is not None:
                generator_values["p_nom_max"] = renewable_potentials.loc[(bus, carrier), "p_nom_max"]

            network.add("Generator", generator_name, **generator_values)        #** = unzip diconary
            network.generators_t.p_max_pu[generator_name] = weather_profiles[carrier][bus]


def add_loads(network, load_profiles):
    """
    Add regional loads and attach their time series.

    Inputs: network and load_profiles DataFrame indexed by network snapshots.
    Output: modifies network.loads and network.loads_t.p_set in place.
    """
    if load_profiles is None:
        return

    if not load_profiles.index.equals(network.snapshots):
        raise ValueError("Load profiles do not match network snapshots")

    for bus in load_profiles.columns:
        if bus not in network.buses.index:
            raise ValueError(f"Load profile bus not found in network: {bus}")

        load_name = f"{bus}_load"
        network.add("Load", load_name, bus=bus)
        network.loads_t.p_set[load_name] = load_profiles[bus]


def add_transmission_links(network, regions, config, connections):
    """
    Add bidirectional transmission links between connected regions.

    Inputs: network, regions, config transmission settings and distance-based connections.
    Output: modifies network.links in place.
    """
    regions_by_id = regions.set_index("region_id")

    for region_i, region_j, distance_km in connections:
        bus_i = regions_by_id.loc[region_i, "bus"]
        bus_j = regions_by_id.loc[region_j, "bus"]
        link_name = f"{bus_i}_{bus_j}_transmission"
        length_km = distance_km * TRANSMISSION_LENGTH_FACTOR

        link_values = {
            "bus0": bus_i,
            "bus1": bus_j,
            "carrier": "AC",
            "p_nom": config.transmission_initial_capacity_mw,
            "p_min_pu": -1,
            "efficiency": 1,
            "capital_cost": TRANSMISSION_COST_EUR_PER_MW_KM * length_km,
        }

        if config.transmission_scenario == "full_grid_expansion":
            link_values["p_nom_extendable"] = True
        elif config.transmission_scenario == "limited_grid_expansion":
            link_values["p_nom_extendable"] = True
            link_values["p_nom_max"] = LIMITED_GRID_MAX_CAPACITY_MW
        else:
            raise ValueError(f"Unknown transmission_scenario: {config.transmission_scenario}")

        network.add("Link", link_name, **link_values)
        network.links.loc[link_name, "length"] = length_km


def save_network(network, config):
    """
    Save the current PyPSA network to the configured NetCDF output file.

    Inputs: network and config.network_output_file.
    Output: writes a .nc file; returns nothing.
    """
    config.network_output_file.parent.mkdir(parents=True, exist_ok=True)
    network.export_to_netcdf(config.network_output_file)
    print(f"Saved network to {config.network_output_file}")