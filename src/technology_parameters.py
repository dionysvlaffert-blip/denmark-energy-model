import pandas as pd

from src.fixxed_values import BATTERY_STORAGE_HOURS, DISCOUNT_RATE, HYDROGEN_STORAGE_HOURS

# initalised t omark the technolgy paramters taht can not be missing, if they are missing, the code will raise an error
REQUIRED = object()


def annuity(lifetime, discount_rate):
    """
    Calculate the annualization factor for investment costs.

    Inputs: lifetime in years and discount rate as decimal value.
    Output: annuity factor in 1/year.
    """
    if discount_rate == 0:
        return 1 / lifetime  # [1/year] = 1 / lifetime
    return discount_rate / (1 - (1 + discount_rate) ** (-lifetime))  # [1/year] = r / (1 - (1 + r)^-n)


def get_parameter(parameters, name, technology, default=REQUIRED, warn=True):
    """
    Read one numeric technology parameter with optional default handling.

    Inputs: parameter Series, parameter name, technology name and optional default.
    Output: float parameter value or default value.
    """
    if name not in parameters.index:
        if default is REQUIRED:
            raise ValueError(f"Missing parameter '{name}' for technology '{technology}'")
        if warn:
            print(f"Warning: Missing parameter '{name}' for technology '{technology}', using default value {default}")
        return default

    value = parameters.loc[name]
    if isinstance(value, pd.Series):
        if len(value) > 1:
            raise ValueError(f"Parameter '{name}' appears multiple times for technology '{technology}'")
        value = value.iloc[0]

    return float(value)


def load_technology_parameters(config):
    """
    Load generator technology costs, efficiencies and CO2 intensities.

    Input: config.technology_parameters_file and carrier_technology_map.
    Output: DataFrame indexed by carrier with capital_cost and marginal_cost.
    """
    if not config.technology_parameters_file.exists():
        raise FileNotFoundError(f"Technology parameter file not found: {config.technology_parameters_file}")

    raw = pd.read_csv(config.technology_parameters_file)
    rows = []

    for carrier, technology in config.carrier_technology_map.items():
        technology_rows = raw[raw["technology"] == technology]
        carrier_rows = raw[raw["technology"] == carrier]    # für manche technologien stehen werte hier 

        if technology_rows.empty:
            raise ValueError(f"Technology not found in parameter file: {technology}")

        parameters = technology_rows.set_index("parameter")["value"]
        carrier_parameters = carrier_rows.set_index("parameter")["value"]

        investment = get_parameter(parameters, "investment", technology)  # EUR/kW: Investitionskosten pro installierter Leistung
        lifetime = get_parameter(parameters, "lifetime", technology)  # years: technische Lebensdauer
        fom = get_parameter(parameters, "FOM", technology, default=0)  # %/year: fixe Betriebskosten als Anteil der Investition
        vom = get_parameter(parameters, "VOM", technology, default=0)  # EUR/MWh_el: variable Betriebskosten pro erzeugter Energie
        fuel = get_parameter(parameters, "fuel", technology, default=None, warn=False)  # EUR/MWh_th: Brennstoffkosten pro thermischer Energie
        efficiency = get_parameter(parameters, "efficiency", technology, default=1)  # MWh_el/MWh_th: elektrischer Wirkungsgrad
        co2_intensity = get_parameter(parameters, "CO2 intensity", technology, default=None, warn=False)  # tCO2/MWh_th: Emissionen pro Brennstoffeinsatz

        if fuel is None:
            fuel = get_parameter(carrier_parameters, "fuel", carrier, default=0, warn=False)  # z.B. gas/coal/oil: Brennstoffkosten stehen beim Carrier

        if co2_intensity is None:
            co2_intensity = get_parameter(carrier_parameters, "CO2 intensity", carrier, default=0, warn=False)  # z.B. gas/coal/oil: CO2 steht beim Carrier

        annualized_investment = investment * 1000 * annuity(lifetime, DISCOUNT_RATE)  # EUR/kW * 1000 kW/MW * 1/year = EUR/MW/year
        fixed_om = investment * 1000 * fom / 100  # EUR/kW * 1000 kW/MW * %/year = EUR/MW/year; /100 := %-->dezimalzahl
        capital_cost = annualized_investment + fixed_om  # cap_cost = yearly_payment + yearl fixed operation and maintenance cost

        marginal_cost = vom  # EUR/MWh_el: variable Kosten ohne Brennstoff
        if fuel > 0 and efficiency > 0:
            marginal_cost = marginal_cost + fuel / efficiency  # marg_cost =  price_per_consumed_energy * vom

        rows.append(
            {
                "carrier": carrier,
                "technology": technology,
                "investment": investment,
                "lifetime": lifetime,
                "FOM": fom,
                "VOM": vom,
                "fuel": fuel,
                "efficiency": efficiency,
                "co2_intensity": co2_intensity,
                "capital_cost": capital_cost,
                "marginal_cost": marginal_cost,
            }
        )

    return pd.DataFrame(rows).set_index("carrier")


def get_technology_parameters(raw, technology):
    """
    Extract all parameter rows for one technology from the raw cost table.

    Inputs: raw technology table and technology name.
    Output: Series indexed by parameter name.
    """
    technology_rows = raw[raw["technology"] == technology]

    if technology_rows.empty:
        raise ValueError(f"Technology not found in parameter file: {technology}")

    return technology_rows.set_index("parameter")["value"]


def annualized_parameter_cost(parameters, technology):
    """
    Convert one investment cost from EUR/kW to annualized EUR/MW/year.

    Inputs: parameter Series and technology name.
    Output: annualized capital cost.
    """
    investment = get_parameter(parameters, "investment", technology)
    lifetime = get_parameter(parameters, "lifetime", technology)
    fom = get_parameter(parameters, "FOM", technology, default=0)
    return investment * 1000 * annuity(lifetime, DISCOUNT_RATE) + investment * 1000 * fom / 100


def load_storage_parameters(config):
    """
    Build battery and hydrogen storage parameter rows.

    Input: config.technology_parameters_file and fixed storage-hour assumptions.
    Output: DataFrame with carrier, max_hours, costs and efficiencies.
    """
    if not config.technology_parameters_file.exists():
        raise FileNotFoundError(f"Technology parameter file not found: {config.technology_parameters_file}")

    raw = pd.read_csv(config.technology_parameters_file)
    battery_inverter = get_technology_parameters(raw, "battery inverter")
    battery_storage = get_technology_parameters(raw, "battery storage")
    electrolyzer = get_technology_parameters(raw, "Alkaline electrolyzer large size")
    fuel_cell = get_technology_parameters(raw, "fuel cell")
    hydrogen_storage = get_technology_parameters(raw, "hydrogen storage underground")

    battery_power_cost = annualized_parameter_cost(battery_inverter, "battery inverter")
    battery_energy_cost = annualized_parameter_cost(battery_storage, "battery storage")
    hydrogen_power_cost = annualized_parameter_cost(electrolyzer, "Alkaline electrolyzer large size")
    hydrogen_power_cost += annualized_parameter_cost(fuel_cell, "fuel cell")
    hydrogen_energy_cost = annualized_parameter_cost(hydrogen_storage, "hydrogen storage underground")

    battery_roundtrip_efficiency = get_parameter(battery_inverter, "efficiency", "battery inverter")
    battery_one_way_efficiency = battery_roundtrip_efficiency ** 0.5
    hydrogen_store_efficiency = 1 / get_parameter(electrolyzer, "electricity-input", "Alkaline electrolyzer large size")
    hydrogen_dispatch_efficiency = get_parameter(fuel_cell, "efficiency", "fuel cell")

    rows = []

    for max_hours in BATTERY_STORAGE_HOURS:
        rows.append(
            {
                "carrier": "battery",
                "max_hours": max_hours,
                "capital_cost": battery_power_cost + max_hours * battery_energy_cost,
                "marginal_cost": 0,
                "efficiency_store": battery_one_way_efficiency,
                "efficiency_dispatch": battery_one_way_efficiency,
            }
        )

    for max_hours in HYDROGEN_STORAGE_HOURS:
        rows.append(
            {
                "carrier": "hydrogen",
                "max_hours": max_hours,
                "capital_cost": hydrogen_power_cost + max_hours * hydrogen_energy_cost,
                "marginal_cost": 0,
                "efficiency_store": hydrogen_store_efficiency,
                "efficiency_dispatch": hydrogen_dispatch_efficiency,
            }
        )

    return pd.DataFrame(rows)