import pandas as pd


def load_renewable_availability(config):
    """
    Load optional regional renewable availability or direct p_nom_max values.

    Input: config.renewable_availability_file.
    Output: DataFrame indexed by bus and carrier.
    """
    if not config.renewable_availability_file.exists():
        raise FileNotFoundError(f"Renewable availability file not found: {config.renewable_availability_file}")

    renewable_availability = pd.read_csv(config.renewable_availability_file)
    if "p_nom_max_mw" in renewable_availability.columns and "p_nom_max" not in renewable_availability.columns:
        renewable_availability = renewable_availability.rename(columns={"p_nom_max_mw": "p_nom_max"})

    required_columns = ["bus", "carrier"]

    for column in required_columns:
        if column not in renewable_availability.columns:
            raise ValueError(f"Missing column in renewable availability file: {column}")

    if "available_area_km2" not in renewable_availability.columns and "p_nom_max" not in renewable_availability.columns:
        raise ValueError("Renewable availability file must contain available_area_km2 or p_nom_max")

    return renewable_availability.set_index(["bus", "carrier"])


def load_renewable_potentials(config, regions):
    """
    Build regional renewable p_nom_max values from national totals.

    Inputs: config renewable potentials/multipliers and regions.
    Output: DataFrame indexed by bus and carrier with p_nom_max in MW.
    """
    rows = []
    multipliers = getattr(config, "renewable_potential_multipliers", {})
    distribution = getattr(config, "renewable_potential_distribution", "area")
    total_area_km2 = regions["area_km2"].sum()

    if distribution == "available_area":
        renewable_availability = load_renewable_availability(config)
    elif distribution == "area":
        renewable_availability = None
    else:
        raise ValueError(f"Unknown renewable_potential_distribution: {distribution}")

    for _, region in regions.iterrows():
        bus = region["bus"]

        for carrier, national_p_nom_max_mw in config.renewable_potentials_mw.items():
            if renewable_availability is None:
                potential_share = region["area_km2"] / total_area_km2
                available_area_km2 = region["area_km2"]
                p_nom_max_base_mw = national_p_nom_max_mw * potential_share
            elif "p_nom_max" in renewable_availability.columns:
                p_nom_max_base_mw = renewable_availability.loc[(bus, carrier), "p_nom_max"]
                potential_share = p_nom_max_base_mw / national_p_nom_max_mw
                if "available_area_km2" in renewable_availability.columns:
                    available_area_km2 = renewable_availability.loc[(bus, carrier), "available_area_km2"]
                else:
                    available_area_km2 = None
            else:
                available_area_km2 = renewable_availability.loc[(bus, carrier), "available_area_km2"]
                total_available_area_km2 = renewable_availability.xs(carrier, level="carrier")["available_area_km2"].sum()

                if total_available_area_km2 == 0:
                    raise ValueError(f"No available area for renewable carrier: {carrier}")

                potential_share = available_area_km2 / total_available_area_km2
                p_nom_max_base_mw = national_p_nom_max_mw * potential_share

            multiplier = multipliers.get(carrier, 1.0)
            rows.append(
                {
                    "bus": bus,
                    "carrier": carrier,
                    "potential_share": potential_share,
                    "available_area_km2": available_area_km2,
                    "p_nom_max_base_mw": p_nom_max_base_mw,
                    "p_nom_max": p_nom_max_base_mw * multiplier,
                }
            )

    return pd.DataFrame(rows).set_index(["bus", "carrier"])