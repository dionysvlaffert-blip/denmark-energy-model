from pathlib import Path
import sys

import atlite
import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.project_config import ProjectConfig
from src.fixxed_values import (
    COUNTRY,
    COUNTRY_CODE,
    EEZ_COUNTRY_CODE,
    OFFSHORE_WIND_TURBINE,
    ONSHORE_WIND_TURBINE,
    SOLAR_ORIENTATION,
    SOLAR_PANEL,
)


def load_region_shapes(config):
    """
    Load regional geometries and attach model bus names.

    Input: config.region_shapes_file.
    Output: GeoDataFrame with geometry and bus column.
    """
    if not config.region_shapes_file.exists():
        raise FileNotFoundError(f"Region shapes file not found: {config.region_shapes_file}")

    regions = gpd.read_file(config.region_shapes_file)
    regions["bus"] = COUNTRY_CODE + "_region_" + regions["region_id"].astype(str)
    return regions


def load_danish_eez(config):
    """
    Load the Danish exclusive economic zone geometry.

    Input: config.eez_file.
    Output: GeoDataFrame in EPSG:4326 for Denmark's EEZ.
    """
    if not config.eez_file.exists():
        raise FileNotFoundError(f"EEZ file not found: {config.eez_file}")

    eez = gpd.read_file(config.eez_file)
    eez = eez[(eez["ISO_TER1"] == EEZ_COUNTRY_CODE) & (eez["TERRITORY1"] == COUNTRY)]

    if eez.empty:
        raise ValueError(f"No EEZ geometry found for {COUNTRY}")

    return eez.to_crs("EPSG:4326")


def create_region_matrix(cutout, regions):
    """
    Create an atlite indicator matrix for onshore regions.

    Inputs: atlite cutout and region geometries.
    Output: tuple (matrix, buses) for profile aggregation.
    """
    matrix = cutout.indicatormatrix(regions.geometry)
    buses = pd.Index(regions["bus"], name="bus")
    return matrix, buses


def create_offshore_region_matrix(cutout, regions, config):
    """
    Assign offshore cutout cells in the Danish EEZ to nearest regional buses.

    Inputs: atlite cutout, region geometries and project config.
    Output: tuple (matrix, buses) for offshore wind aggregation.
    """
    eez = load_danish_eez(config)
    grid = cutout.grid.set_crs(cutout.crs, allow_override=True)
    offshore_cells = gpd.overlay(grid, eez[["geometry"]], how="intersection")

    if offshore_cells.empty:
        raise ValueError("No cutout grid cells overlap with the Danish EEZ")
    #initialize locations for offshore
    offshore_cell_points = offshore_cells.to_crs("EPSG:3035").copy()
    offshore_cell_points["geometry"] = offshore_cell_points.geometry.centroid

    bus_points = gpd.GeoDataFrame(
        {"bus": regions["bus"]},
        geometry=gpd.points_from_xy(regions["bus_x"], regions["bus_y"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:3035")
    #merge offshore punkte mit dem gebiet, was am nähsten
    nearest_bus = gpd.sjoin_nearest(
        offshore_cell_points[["geometry"]],
        bus_points[["bus", "geometry"]],
        how="left",
    ).sort_index()

    offshore_cells["bus"] = nearest_bus["bus"].to_numpy()
    offshore_regions = offshore_cells.dissolve(by="bus").reset_index().to_crs("EPSG:4326")

    matrix = cutout.indicatormatrix(offshore_regions.geometry)
    buses = pd.Index(offshore_regions["bus"], name="bus")
    return matrix, buses


def profile_to_dataframe(profile, config):
    """
    Convert an atlite profile to a clipped DataFrame.

    Inputs: atlite/xarray profile and config.
    Output: pandas DataFrame with values clipped to [0, 1].
    """
    profile = profile.to_pandas()
    profile.index.name = "snapshot"


    return profile.clip(lower=0, upper=1)


def save_profile(profile, output_file):
    """
    Save one weather profile table to CSV.

    Inputs: profile DataFrame and output path.
    Output: writes CSV file; returns nothing.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(output_file)
    print(f"Saved {output_file}")


def create_weather_profiles(config):
    """
    Generate solar, onshore wind and offshore wind p_max_pu profiles.

    Input: project config with cutout, region and output paths.
    Output: writes three CSV profile files.
    """
    if not config.weather_cutout_file.exists():
        raise FileNotFoundError(f"Weather cutout file not found: {config.weather_cutout_file}")
    #load weather data
    cutout = atlite.Cutout(config.weather_cutout_file)
    #load region shapes
    regions = load_region_shapes(config)
    #matrix mathces the cutout data to the regions
    matrix, buses = create_region_matrix(cutout, regions)
    offshore_matrix, offshore_buses = create_offshore_region_matrix(cutout, regions, config)

    solar = cutout.pv(
        panel=SOLAR_PANEL,
        orientation=SOLAR_ORIENTATION,
        matrix=matrix,
        index=buses,
        per_unit=True,      # --> translates values into capacity factor (0-1) instead of absolute power values
        aggregate_time=None,
    )
    solar = profile_to_dataframe(solar, config)
    save_profile(
        solar,
        config.weather_profiles_output_dir / f"solar_p_max_pu_{config.region_level}_{config.weather_year}.csv",
    )

    onshore_wind = cutout.wind(
        turbine=ONSHORE_WIND_TURBINE,
        matrix=matrix,
        index=buses,
        per_unit=True,
        aggregate_time=None,
    )
    onshore_wind = profile_to_dataframe(onshore_wind, config)
    save_profile(
        onshore_wind,
        config.weather_profiles_output_dir / f"onshore_wind_p_max_pu_{config.region_level}_{config.weather_year}.csv",
    )

    offshore_wind = cutout.wind(
        turbine=OFFSHORE_WIND_TURBINE,
        matrix=offshore_matrix,
        index=offshore_buses,
        per_unit=True,
        aggregate_time=None,
    )
    offshore_wind = profile_to_dataframe(offshore_wind, config)
    save_profile(
        offshore_wind,
        config.weather_profiles_output_dir / f"offshore_wind_p_max_pu_{config.region_level}_{config.weather_year}.csv",
    )


config = ProjectConfig("config/project_config.yaml")
create_weather_profiles(config)