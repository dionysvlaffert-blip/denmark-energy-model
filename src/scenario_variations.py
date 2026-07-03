from src.fixxed_values import (
    DISCOUNT_RATE,
    NUCLEAR_CO2_INTENSITY,
    NUCLEAR_EFFICIENCY,
    NUCLEAR_FIXED_OM_PERCENT,
    NUCLEAR_FUEL_EUR_PER_MWH_TH,
    NUCLEAR_LIFETIME,
    NUCLEAR_VARIABLE_OM_EUR_PER_MWH,
)
from src.technology_parameters import annuity


def carrier_list(carriers):
    """
    Normalize a single carrier string or iterable to a carrier list.

    Input: carrier string or iterable of carrier strings.
    Output: list-like carrier collection.
    """
    if isinstance(carriers, str):
        return [carriers]
    return carriers


def carrier_suffix(carriers):
    carriers = carrier_list(carriers)
    return "_".join(str(carrier) for carrier in carriers)


def factor_suffix(factor):
    return str(factor).replace(".", "p")


def scale_generator_capital_cost(network, carriers, factor, config, suffix=None):
    """
    Scale generator capital costs for selected carriers.

    Inputs: network, carrier or carrier list, multiplication factor, config and optional suffix.
    Output: modifies network.generators in place.
    """
    if suffix is None:
        suffix = f"generator_cost_{carrier_suffix(carriers)}_{factor_suffix(factor)}"
    config.add_setting_name_suffix(suffix)

    carriers = carrier_list(carriers)
    network.generators.loc[
        network.generators["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor


def scale_storage_capital_cost(network, carriers, factor, config, suffix=None):
    """
    Scale storage-unit capital costs for selected carriers.

    Inputs: network, carrier or carrier list, multiplication factor, config and optional suffix.
    Output: modifies network.storage_units in place.
    """
    if suffix is None:
        suffix = f"storage_cost_{carrier_suffix(carriers)}_{factor_suffix(factor)}"
    config.add_setting_name_suffix(suffix)

    carriers = carrier_list(carriers)
    network.storage_units.loc[
        network.storage_units["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor


def scale_link_capital_cost(network, carriers, factor, config, suffix=None):
    """
    Scale link capital costs for selected carriers, e.g. AC transmission.

    Inputs: network, carrier or carrier list, multiplication factor, config and optional suffix.
    Output: modifies network.links in place.
    """
    if suffix is None:
        suffix = f"link_cost_{carrier_suffix(carriers)}_{factor_suffix(factor)}"
    config.add_setting_name_suffix(suffix)

    carriers = carrier_list(carriers)
    network.links.loc[
        network.links["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor


def scale_capital_cost(network, carriers, factor, config, suffix=None):
    """
    Scale capital costs across generators, storage units and links.

    Inputs: network, carrier or carrier list, multiplication factor, config and optional suffix.
    Output: modifies matching PyPSA component tables in place.
    """
    if suffix is None:
        suffix = f"capital_cost_{carrier_suffix(carriers)}_{factor_suffix(factor)}"
    config.add_setting_name_suffix(suffix)

    carriers = carrier_list(carriers)
    network.generators.loc[
        network.generators["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor
    network.storage_units.loc[
        network.storage_units["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor
    network.links.loc[
        network.links["carrier"].isin(carriers),
        "capital_cost",
    ] *= factor


def scale_renewable_potential(network, carriers, factor, config, suffix=None):
    """
    Scale renewable p_nom_max limits for selected generator carriers.

    Inputs: network, carrier or carrier list, multiplication factor, config and optional suffix.
    Output: modifies network.generators.p_nom_max in place.
    """
    if suffix is None:
        suffix = f"renewable_potential_{carrier_suffix(carriers)}_{factor_suffix(factor)}"
    config.add_setting_name_suffix(suffix)

    carriers = carrier_list(carriers)
    network.generators.loc[
        network.generators["carrier"].isin(carriers),
        "p_nom_max",
    ] *= factor


def set_co2_emissions_limit(network, co2_limit_tonnes):
    constraint_name = "co2_emissions_limit"
    constraint_values = {
        "type": "primary_energy",
        "carrier_attribute": "co2_emissions",
        "sense": "<=",
        "constant": co2_limit_tonnes,
    }

    if constraint_name in network.global_constraints.index:
        for key, value in constraint_values.items():
            network.global_constraints.loc[constraint_name, key] = value
    else:
        network.add("GlobalConstraint", constraint_name, **constraint_values)


def add_co2_emissions_limit(network, co2_limit_tonnes, config, suffix=None):
    """
    Add or update a global CO2 emissions limit.

    Inputs: network, allowed CO2 emissions in tonnes, config and optional suffix.
    Output: modifies network.global_constraints in place.
    """
    if suffix is None:
        suffix = f"co2_limit_{factor_suffix(co2_limit_tonnes)}_tonnes"
    config.add_setting_name_suffix(suffix)

    set_co2_emissions_limit(network, co2_limit_tonnes)


def add_no_co2_emissions_constraint(network, config, suffix="no_co2_emissions"):
    """
    Add a 100 percent CO2 reduction constraint.

    Inputs: network, config and optional suffix.
    Output: modifies network.global_constraints in place.
    """
    config.add_setting_name_suffix(suffix)
    set_co2_emissions_limit(network, 0)


def annualized_nuclear_capital_cost(investment_eur_per_kw):
    """
    Convert nuclear investment cost to annualized PyPSA capital cost.

    Input: nuclear investment in EUR/kW.
    Output: annualized cost in EUR/MW/year.
    """
    annualized_investment = investment_eur_per_kw * 1000 * annuity(NUCLEAR_LIFETIME, DISCOUNT_RATE)
    fixed_om = investment_eur_per_kw * 1000 * NUCLEAR_FIXED_OM_PERCENT / 100
    return annualized_investment + fixed_om


def nuclear_marginal_cost():
    """
    Calculate nuclear marginal cost from VOM, fuel cost and efficiency.

    Input: fixed nuclear assumptions from fixxed_values.py.
    Output: marginal cost in EUR/MWh_el.
    """
    return NUCLEAR_VARIABLE_OM_EUR_PER_MWH + NUCLEAR_FUEL_EUR_PER_MWH_TH / NUCLEAR_EFFICIENCY


def set_nuclear_capital_cost(network, investment_eur_per_kw, config, suffix=None):
    """
    Update capital cost for already existing nuclear generators.

    Inputs: network, nuclear investment in EUR/kW, config and optional suffix.
    Output: modifies nuclear rows in network.generators in place.
    """
    if suffix is None:
        suffix = f"nuclear_cost_{investment_eur_per_kw}_eur_per_kw"
    config.add_setting_name_suffix(suffix)

    network.generators.loc[
        network.generators["carrier"] == "nuclear",
        "capital_cost",
    ] = annualized_nuclear_capital_cost(investment_eur_per_kw)


def add_nuclear_generators(network, investment_eur_per_kw, config, suffix=None):
    """
    Add one extendable nuclear generator to every bus.

    Inputs: network, nuclear investment in EUR/kW, config and optional suffix.
    Output: modifies network.carriers and network.generators in place.
    """
    if suffix is None:
        suffix = f"nuclear_{investment_eur_per_kw}_eur_per_kw"
    config.add_setting_name_suffix(suffix)

    if "nuclear" not in network.carriers.index:
        network.add("Carrier", "nuclear", co2_emissions=NUCLEAR_CO2_INTENSITY)
    else:
        network.carriers.loc["nuclear", "co2_emissions"] = NUCLEAR_CO2_INTENSITY

    for bus in network.buses.index:
        generator_name = f"{bus}_nuclear"
        generator_values = {
            "bus": bus,
            "carrier": "nuclear",
            "p_nom_extendable": True,
            "capital_cost": annualized_nuclear_capital_cost(investment_eur_per_kw),
            "marginal_cost": nuclear_marginal_cost(),
            "efficiency": NUCLEAR_EFFICIENCY,
        }

        if generator_name in network.generators.index:
            for key, value in generator_values.items():
                network.generators.loc[generator_name, key] = value
        else:
            network.add("Generator", generator_name, **generator_values)