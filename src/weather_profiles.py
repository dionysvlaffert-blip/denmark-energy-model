import pandas as pd


def load_weather_profiles(config):
    """
    Load prepared renewable capacity-factor profiles from CSV files.

    Input: config weather profile directory, region level and weather year.
    Output: dict mapping carrier to DataFrame indexed by snapshot.
    """
    profiles = {}

    for carrier in ["solar", "onshore_wind", "offshore_wind"]:
        profile_file = config.weather_profiles_output_dir / f"{carrier}_p_max_pu_{config.region_level}_{config.weather_year}.csv"

        if not profile_file.exists():
            raise FileNotFoundError(f"Weather profile file not found: {profile_file}")

        profiles[carrier] = pd.read_csv(profile_file, index_col="snapshot", parse_dates=True)

    return profiles


def resample_weather_profiles(weather_profiles, snapshots, time_resolution):
    """
    Resample renewable profiles to the network snapshots.

    Inputs: profile dict, target snapshots and time resolution.
    Output: resampled profile dict with values checked in [0, 1].
    """
    resampled_profiles = {}

    for carrier, profile in weather_profiles.items():
        profile = profile.resample(time_resolution).mean()
        profile = profile.reindex(snapshots)

        # Überprüfen ob resampleing richrtiges format hat und ob es NaN Werte gibt
        if len(profile) != len(snapshots):
            raise ValueError(f"Resampled weather profile for {carrier} does not match the number of snapshots")
        if profile.isna().any().any():
            raise ValueError(f"Weather profile for {carrier} does not match the network snapshots")
        if profile.min().min() < -0.001 or profile.max().max() > 1.001:
            raise ValueError(f"Weather profile for {carrier} contains values outside the range [0, 1]")

        resampled_profiles[carrier] = profile

    return resampled_profiles