import pandas as pd

from src.fixxed_values import EEZ_COUNTRY_CODE


FUEL_TO_CARRIER = {
    "Biomass": "biomass",
    "Coal": "coal",
    "Gas": "gas",
    "Hydro": "hydro",
    "Oil": "oil",
}


def find_nearest_bus(plant, regions):
    """
    Find the closest model bus for one power plant by coordinate distance.

    Inputs: one plant row and regions with bus_x/bus_y.
    Output: bus name string.
    """
    distances = (regions["bus_x"] - plant["longitude"]) ** 2 + (regions["bus_y"] - plant["latitude"]) ** 2
    return regions.loc[distances.idxmin(), "bus"]


def load_existing_power_plants(config, regions):
    """
    Load and aggregate existing Danish conventional plants from the WRI database.

    Inputs: config with plant file/year and model regions.
    Output: DataFrame by bus and carrier with p_nom_mw, p_max_pu and plant_count.
    """
    if not config.existing_power_plants_file.exists():
        raise FileNotFoundError(f"Existing power plant file not found: {config.existing_power_plants_file}")

    raw = pd.read_csv(config.existing_power_plants_file, low_memory=False)  # load WRI power plant database
    plants = raw[(raw["country"] == EEZ_COUNTRY_CODE) & raw["primary_fuel"].isin(FUEL_TO_CARRIER)].copy()  # keep Denmark and supported fuels
    plants["carrier"] = plants["primary_fuel"].map(FUEL_TO_CARRIER)  # map WRI fuels to model carriers
    plants = plants[plants["carrier"].isin(config.carrier_technology_map)].copy()  # keep carriers with technology parameters
    plants["capacity_mw"] = pd.to_numeric(plants["capacity_mw"], errors="coerce")  # convert capacity to numbers
    plants = plants[plants["capacity_mw"] > 0].copy()  # remove plants without positive capacity

    generation_year = config.existing_power_plants_generation_year
    generation_column = f"generation_gwh_{generation_year}"
    estimated_generation_column = f"estimated_generation_gwh_{generation_year}"

    if generation_column not in plants.columns or estimated_generation_column not in plants.columns:
        raise ValueError(f"Missing generation columns for year {generation_year} in existing power plant file")

    generation = pd.to_numeric(plants[generation_column], errors="coerce")  # historical generation if available
    estimated_generation = pd.to_numeric(plants[estimated_generation_column], errors="coerce")  # fallback estimate
    plants["generation_gwh"] = generation.fillna(estimated_generation)  # prefer historical, else estimated generation

    plants["bus"] = plants.apply(lambda plant: find_nearest_bus(plant, regions), axis=1)  # assign each plant to nearest region bus

    existing_power_plants = (
        plants.groupby(["bus", "carrier"], as_index=False)  # aggregate to one plant per bus and carrier
        .agg(
            p_nom_mw=("capacity_mw", "sum"),
            generation_gwh=("generation_gwh", lambda values: values.sum(min_count=1)),
            plant_count=("name", "count"),
        )
        .sort_values(["bus", "carrier"])
        .reset_index(drop=True)
    )

    existing_power_plants["p_max_pu"] = 1.0  # conventional plants are available at full capacity by default
    hydro = existing_power_plants["carrier"] == "hydro"

    if hydro.any():
        existing_power_plants.loc[hydro, "p_max_pu"] = (
            existing_power_plants.loc[hydro, "generation_gwh"] * 1000
            / (existing_power_plants.loc[hydro, "p_nom_mw"] * 8760)
        ).clip(0, 1)  # hydro uses constant capacity factor from annual generation

    return existing_power_plants
