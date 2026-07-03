import pandas as pd

from src.fixxed_values import COUNTRY_CODE


def load_national_load(config):
    """
    Load the national Danish load time series from CSV.

    Input: config.load_file and COUNTRY_CODE column.
    Output: pandas Series indexed by timestamp.
    """
    if not config.load_file.exists():
        raise FileNotFoundError(f"Load file not found: {config.load_file}")

    load = pd.read_csv(
        config.load_file,
        usecols=["time", COUNTRY_CODE],
        parse_dates=["time"],
        index_col="time",
    )
    load = load[COUNTRY_CODE]
    load.name = f"load_{config.load_year}"
    return load


def move_load_to_model_year(load, hourly_snapshots):
    """
    Align one load year to the model year length.

    Inputs: hourly load Series and target hourly snapshots.
    Output: load Series indexed by the target snapshots.
    """
    values = list(load.values)
    n_hours_load = len(values)
    n_hours_target = len(hourly_snapshots)

    # Wenn das Modelljahr ein Schaltjahr ist, wiederholen wir den letzten Tag als Tag 366.
    if n_hours_load < n_hours_target:
        missing_hours = n_hours_target - n_hours_load
        if missing_hours != 24:
            raise ValueError(f"Expected 24 missing load hours, but found {missing_hours}")

        day_366 = values[-24:]
        values = values + day_366

    values = values[:n_hours_target]
    return pd.Series(values, index=hourly_snapshots, name="load")


def resample_load(load, snapshots, time_resolution):
    """
    Resample hourly load to the model time resolution.

    Inputs: load Series, model snapshots and time resolution string.
    Output: resampled load Series without missing values.
    """
    year = snapshots[0].year
    hourly_snapshots = pd.date_range(
        f"{year}-01-01 00:00",
        f"{year + 1}-01-01 00:00",
        freq="1h",
        inclusive="left",
    )
    # aligne weather_year and load_year( add/remove values if "schaltjahr")
    load = move_load_to_model_year(load, hourly_snapshots)
    load = load.resample(time_resolution).mean()        # mean as there is an inherint  upsampeling logic for the load within pypsa
    if load.isna().any():
        raise ValueError("Load profile does not match the network snapshots")

    return load


def distribute_load_to_regions(load, regions, method="area"):
    """
    Split national load across regional buses.

    Inputs: national load Series, regions and method "area" or "equal".
    Output: DataFrame with one load column per bus.
    """
    regions = regions.set_index("bus")
    # distribute load to regions based on relative area or equally around all regions
    if method == "area":
        shares = regions["area_km2"] / regions["area_km2"].sum()
    elif method == "equal":
        shares = pd.Series(1 / len(regions), index=regions.index)
    else:
        raise ValueError(f"Unknown load distribution method: {method}")

    return pd.DataFrame({bus: load * share for bus, share in shares.items()})


def prepare_load_profiles(load, regions, snapshots, time_resolution, distribution_method):
    """
    Prepare regional load profiles for direct use in PyPSA.

    Inputs: raw national load, regions, snapshots, time resolution and distribution method.
    Output: DataFrame indexed by model snapshots with bus columns.
    """
    load = resample_load(load, snapshots, time_resolution)
    return distribute_load_to_regions(load, regions, distribution_method)