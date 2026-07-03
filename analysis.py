"""
analysis.py – Complete plotting script for Denmark 100% Renewable Energy Model
Run from the project root folder.
"""

import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os

# ── Settings ──────────────────────────────────────────────────────────────────
NET_DIR = "results/networks"
OUT_DIR = "results/figures"
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = {
    "solar":         "#f9d71c",
    "onshore_wind":  "#74c476",
    "offshore_wind": "#2171b5",
    "battery":       "#d94801",
    "hydrogen":      "#756bb1",
    "coal":          "#252525",
    "gas":           "#fd8d3c",
    "oil":           "#969696",
    "biomass":       "#41ab5d",
    "hydro":         "#6baed6",
    "nuclear":       "#a1d99b",
    "transmission":  "#636363",
}

def color(carrier):
    for k, v in COLORS.items():
        if k in str(carrier).lower():
            return v
    return "#aaaaaa"

def load(filename):
    return pypsa.Network(f"{NET_DIR}/{filename}")

def get_objective(n):
    try:
        if n.objective is None:
            return None
        return float(n.objective) / 1e9
    except Exception:
        return None

def gen_mix(n):
    weights = n.snapshot_weightings.generators
    gen = n.generators_t.p.mul(weights, axis=0).sum()
    return gen.groupby(n.generators.carrier).sum() / 1e6  # TWh

def get_caps(n):
    caps = n.generators.groupby("carrier")["p_nom_opt"].sum() / 1e3
    stor = n.storage_units.groupby("carrier")["p_nom_opt"].sum() / 1e3
    return caps, stor

def save(fig, name):
    path = f"{OUT_DIR}/{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {name}.png")

def safe_sensitivity_data(files):
    pcts       = sorted(files.keys(), reverse=True)
    valid_pcts = []
    costs      = []
    caps_list  = []
    stor_list  = []
    for pct in pcts:
        n = load(files[pct])
        obj = get_objective(n)
        if obj is None:
            print(f"    ⚠ Skipping {files[pct]} — no objective")
            continue
        valid_pcts.append(pct)
        costs.append(obj)
        caps, stor = get_caps(n)
        caps_list.append(caps)
        stor_list.append(stor)
    return valid_pcts, costs, caps_list, stor_list


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 01: Baseline vs Zero CO2 — Electricity Mix
# ═══════════════════════════════════════════════════════════════════════════════
def plot_01_mix_baseline_vs_zero_co2():
    n_base = load("02_baseline.nc")
    n_co2  = load("04_zero_co2.nc")

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax, (n, label) in zip(axes, [(n_base, "Baseline (no limit)"), (n_co2, "Zero CO₂")]):
        mix = gen_mix(n)
        mix = mix[mix > 0]
        ax.pie(mix, labels=mix.index, autopct="%1.1f%%",
               colors=[color(c) for c in mix.index],
               startangle=90, counterclock=False)
        obj = get_objective(n)
        ax.set_title(f"{label}\nTotal: {mix.sum():.1f} TWh/year | Cost: {obj:.2f} B€/year",
                     fontsize=11, fontweight="bold")

    fig.suptitle("Denmark – Electricity Mix: Baseline vs Zero CO₂", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "01_mix_baseline_vs_zero_co2")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 02: Baseline vs Zero CO2 — Installed Capacities
# ═══════════════════════════════════════════════════════════════════════════════
def plot_02_capacities_comparison():
    n_base = load("02_baseline.nc")
    n_co2  = load("04_zero_co2.nc")

    all_carriers = set()
    data = {}
    for label, n in [("Baseline", n_base), ("Zero CO₂", n_co2)]:
        caps, stor = get_caps(n)
        combined = pd.concat([caps, stor])
        combined = combined[combined > 0.01]
        data[label] = combined
        all_carriers |= set(combined.index)

    all_carriers = sorted(all_carriers)
    df = pd.DataFrame({l: [data[l].get(c, 0) for c in all_carriers]
                       for l in data}, index=all_carriers)
    df = df[df.sum(axis=1) > 0.01]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df))
    w = 0.35
    ax.bar(x - w/2, df["Baseline"], w, label="Baseline",
           color=[color(c) for c in df.index], alpha=0.5, edgecolor="white")
    ax.bar(x + w/2, df["Zero CO₂"], w, label="Zero CO₂",
           color=[color(c) for c in df.index], alpha=1.0, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=30, ha="right")
    ax.set_ylabel("Capacity (GW)")
    ax.set_title("Denmark – Installed Capacities: Baseline vs Zero CO₂", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    save(fig, "02_capacities_baseline_vs_zero_co2")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 03: Grid Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_03_grid_sensitivity():
    scenarios = {
        "Full expansion": "05_grid_full_expansion.nc",
        "Max 1 GW/line":  "06_grid_max_1GW.nc",
        "Autarky":        "07_grid_autarky.nc",
    }

    costs = {}
    mixes = {}
    for label, fname in scenarios.items():
        n = load(fname)
        obj = get_objective(n)
        if obj is not None:
            costs[label] = obj
        mixes[label] = gen_mix(n)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ax = axes[0]
    s = pd.Series(costs).dropna()
    bar_colors = ["#2171b5", "#74c476", "#d94801"][:len(s)]
    bars = ax.bar(s.index, s.values, color=bar_colors, edgecolor="white")
    for bar, val in zip(bars, s.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{val:.2f}B€", ha="center", fontsize=10)
    ax.set_ylabel("Total System Cost (Billion €/year)")
    ax.set_title("System Cost by Grid Scenario", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    ax = axes[1]
    all_carriers = sorted(set().union(*[m.index for m in mixes.values()]))
    df = pd.DataFrame({l: [mixes[l].get(c, 0) for c in all_carriers]
                       for l in mixes}, index=all_carriers)
    df = df[df.sum(axis=1) > 0]
    bottom = np.zeros(len(mixes))
    for carrier in df.index:
        ax.bar(list(mixes.keys()), df.loc[carrier].values, bottom=bottom,
               label=carrier, color=color(carrier), edgecolor="white")
        bottom += df.loc[carrier].values
    ax.set_ylabel("Annual Generation (TWh)")
    ax.set_title("Generation Mix by Grid Scenario", fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    fig.suptitle("Denmark – Grid Expansion Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "03_grid_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 04: Solar CAPEX Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_04_solar_capex():
    files = {100: "08_solar_capex_100pct.nc", 75: "09_solar_capex_75pct.nc",
             50:  "10_solar_capex_50pct.nc",  25: "11_solar_capex_25pct.nc",
             0:   "12_solar_capex_0pct.nc"}

    valid_pcts, costs, caps_list, _ = safe_sensitivity_data(files)
    solar    = [c.get("solar", 0)         for c in caps_list]
    wind     = [c.get("onshore_wind", 0)  for c in caps_list]
    offshore = [c.get("offshore_wind", 0) for c in caps_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["solar"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Solar CAPEX (% of base cost)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Solar CAPEX", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, solar,    "o-", color=COLORS["solar"],         label="Solar",         linewidth=2)
    axes[1].plot(valid_pcts, wind,     "s-", color=COLORS["onshore_wind"],  label="Onshore Wind",  linewidth=2)
    axes[1].plot(valid_pcts, offshore, "^-", color=COLORS["offshore_wind"], label="Offshore Wind", linewidth=2)
    axes[1].set_xlabel("Solar CAPEX (% of base cost)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Solar CAPEX", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Solar CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "04_solar_capex_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 05: Wind CAPEX Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_05_wind_capex():
    files = {100: "13_wind_capex_100pct.nc", 75: "14_wind_capex_75pct.nc",
             50:  "15_wind_capex_50pct.nc",  25: "16_wind_capex_25pct.nc",
             0:   "17_wind_capex_0pct.nc"}

    valid_pcts, costs, caps_list, _ = safe_sensitivity_data(files)
    solar    = [c.get("solar", 0)         for c in caps_list]
    wind     = [c.get("onshore_wind", 0)  for c in caps_list]
    offshore = [c.get("offshore_wind", 0) for c in caps_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["onshore_wind"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Wind CAPEX (% of base cost)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Wind CAPEX", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, solar,    "o-", color=COLORS["solar"],         label="Solar",         linewidth=2)
    axes[1].plot(valid_pcts, wind,     "s-", color=COLORS["onshore_wind"],  label="Onshore Wind",  linewidth=2)
    axes[1].plot(valid_pcts, offshore, "^-", color=COLORS["offshore_wind"], label="Offshore Wind", linewidth=2)
    axes[1].set_xlabel("Wind CAPEX (% of base cost)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Wind CAPEX", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Wind CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "05_wind_capex_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 06: Battery CAPEX Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_06_battery_capex():
    files = {100: "18_battery_capex_100pct.nc", 75: "19_battery_capex_75pct.nc",
             50:  "20_battery_capex_50pct.nc",  25: "21_battery_capex_25pct.nc",
             0:   "22_battery_capex_0pct.nc"}

    valid_pcts, costs, caps_list, stor_list = safe_sensitivity_data(files)
    bat = [s.get("battery", 0)  for s in stor_list]
    hyd = [s.get("hydrogen", 0) for s in stor_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["battery"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Battery CAPEX (% of base cost)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Battery CAPEX", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, bat, "o-", color=COLORS["battery"],  label="Battery",  linewidth=2)
    axes[1].plot(valid_pcts, hyd, "s-", color=COLORS["hydrogen"], label="Hydrogen", linewidth=2)
    axes[1].set_xlabel("Battery CAPEX (% of base cost)")
    axes[1].set_ylabel("Storage Power Capacity (GW)")
    axes[1].set_title("Storage vs Battery CAPEX", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Battery CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "06_battery_capex_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 07: Transmission CAPEX Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_07_transmission_capex():
    files = {100: "23_transmission_capex_100pct.nc", 75: "24_transmission_capex_75pct.nc",
             50:  "25_transmission_capex_50pct.nc",  25: "26_transmission_capex_25pct.nc",
             0:   "27_transmission_capex_0pct.nc"}

    valid_pcts, costs, _, _ = safe_sensitivity_data(files)
    trans = []
    for pct in valid_pcts:
        n = load(files[pct])
        trans.append(n.links["p_nom_opt"].sum() / 1e3)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["transmission"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Transmission CAPEX (% of base cost)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Transmission CAPEX", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, trans, "o-", color=COLORS["transmission"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[1].set_xlabel("Transmission CAPEX (% of base cost)")
    axes[1].set_ylabel("Total Transmission Capacity (GW)")
    axes[1].set_title("Transmission Capacity vs CAPEX", fontweight="bold")
    axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Transmission CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "07_transmission_capex_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 08: Nuclear Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_08_nuclear():
    files = {2500: "27_nuclear_2500_eur_per_kw.nc", 5000: "28_nuclear_5000_eur_per_kw.nc",
             7500: "29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}

    prices       = sorted(files.keys())
    valid_prices = []
    costs, nuc, solar, wind = [], [], [], []

    for price in prices:
        n = load(files[price])
        obj = get_objective(n)
        if obj is None: continue
        valid_prices.append(price)
        costs.append(obj)
        caps, _ = get_caps(n)
        nuc.append(caps.get("nuclear", 0))
        solar.append(caps.get("solar", 0))
        wind.append(caps.get("onshore_wind", 0) + caps.get("offshore_wind", 0))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_prices, costs, "o-", color=COLORS["nuclear"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Nuclear CAPEX", fontweight="bold")
    axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))
    for x, y in zip(valid_prices, costs):
        axes[0].annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_prices, nuc,   "o-", color=COLORS["nuclear"],       label="Nuclear",      linewidth=2)
    axes[1].plot(valid_prices, wind,  "s-", color=COLORS["offshore_wind"], label="Wind (total)", linewidth=2)
    axes[1].plot(valid_prices, solar, "^-", color=COLORS["solar"],         label="Solar",        linewidth=2)
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Nuclear CAPEX", fontweight="bold")
    axes[1].legend(); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.suptitle("Denmark – Nuclear CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "08_nuclear_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 09: Nuclear + Grid Combined
# ═══════════════════════════════════════════════════════════════════════════════
def plot_09_nuclear_grid():
    free_files = {2500: "27_nuclear_2500_eur_per_kw.nc", 5000: "28_nuclear_5000_eur_per_kw.nc",
                  7500: "29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}
    grid_files = {2500: "46_nuclear_2500eurkw_grid_1GW.nc", 5000: "47_nuclear_5000eurkw_grid_1GW.nc",
                  7500: "48_nuclear_7500eurkw_grid_1GW.nc", 10000:"49_nuclear_10000eurkw_grid_1GW.nc"}

    prices       = sorted(free_files.keys())
    valid_prices = []
    costs_free, costs_1gw = [], []
    nuc_free,   nuc_1gw   = [], []

    for price in prices:
        n1 = load(free_files[price]); n2 = load(grid_files[price])
        o1 = get_objective(n1);       o2 = get_objective(n2)
        if o1 is None or o2 is None: continue
        valid_prices.append(price)
        costs_free.append(o1); costs_1gw.append(o2)
        caps1, _ = get_caps(n1); caps2, _ = get_caps(n2)
        nuc_free.append(caps1.get("nuclear", 0))
        nuc_1gw.append(caps2.get("nuclear", 0))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_prices, costs_free, "o-", color=COLORS["nuclear"], label="Free grid",    linewidth=2)
    axes[0].plot(valid_prices, costs_1gw,  "s-", color=COLORS["battery"], label="Max 1GW grid", linewidth=2)
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)"); axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("Cost: Free Grid vs 1GW Grid Limit", fontweight="bold")
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))

    axes[1].plot(valid_prices, nuc_free, "o-", color=COLORS["nuclear"], label="Free grid",    linewidth=2)
    axes[1].plot(valid_prices, nuc_1gw,  "s-", color=COLORS["battery"], label="Max 1GW grid", linewidth=2)
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)"); axes[1].set_ylabel("Nuclear Capacity (GW)")
    axes[1].set_title("Nuclear Capacity: Free vs 1GW Grid", fontweight="bold")
    axes[1].legend(); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.suptitle("Denmark – Nuclear + Grid Expansion Combined", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "09_nuclear_grid_combined")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 10: Solar Potential Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_10_solar_potential():
    files = {100: "31_solar_potential_100pct.nc", 75: "32_solar_potential_75pct.nc",
             50:  "33_solar_potential_50pct.nc",  25: "34_solar_potential_25pct.nc",
             0:   "35_solar_potential_0pct.nc"}

    valid_pcts, costs, caps_list, stor_list = safe_sensitivity_data(files)
    solar = [c.get("solar", 0)                                    for c in caps_list]
    wind  = [c.get("onshore_wind", 0) + c.get("offshore_wind", 0) for c in caps_list]
    bat   = [s.get("battery", 0)                                   for s in stor_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["solar"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Solar Potential (% of max)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Solar Potential", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, solar, "o-", color=COLORS["solar"],        label="Solar",      linewidth=2)
    axes[1].plot(valid_pcts, wind,  "s-", color=COLORS["onshore_wind"], label="Wind total", linewidth=2)
    axes[1].plot(valid_pcts, bat,   "^-", color=COLORS["battery"],      label="Battery",    linewidth=2)
    axes[1].set_xlabel("Solar Potential (% of max)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Solar Potential", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Solar Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "10_solar_potential_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 11: Onshore Wind Potential Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_11_onshore_potential():
    files = {100: "36_onshore_potential_100pct.nc", 75: "42_onshore_potential_75pct.nc",
             50:  "43_onshore_potential_50pct.nc",  25: "44_onshore_potential_25pct.nc",
             0:   "45_onshore_potential_0pct.nc"}

    valid_pcts, costs, caps_list, _ = safe_sensitivity_data(files)
    solar    = [c.get("solar", 0)         for c in caps_list]
    wind     = [c.get("onshore_wind", 0)  for c in caps_list]
    offshore = [c.get("offshore_wind", 0) for c in caps_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["onshore_wind"], linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("Onshore Wind Potential (% of max)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Onshore Wind Potential", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, solar,    "o-", color=COLORS["solar"],         label="Solar",         linewidth=2)
    axes[1].plot(valid_pcts, wind,     "s-", color=COLORS["onshore_wind"],  label="Onshore Wind",  linewidth=2)
    axes[1].plot(valid_pcts, offshore, "^-", color=COLORS["offshore_wind"], label="Offshore Wind", linewidth=2)
    axes[1].set_xlabel("Onshore Wind Potential (% of max)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Onshore Wind Potential", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Onshore Wind Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "11_onshore_potential_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 12: All Renewables Potential Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_12_all_renewables_potential():
    files = {100: "37_all_ren_potential_100pct.nc", 75: "38_all_ren_potential_75pct.nc",
             50:  "39_all_ren_potential_50pct.nc",  25: "40_all_ren_potential_25pct.nc",
             0:   "41_all_ren_potential_0pct.nc"}

    valid_pcts, costs, caps_list, stor_list = safe_sensitivity_data(files)
    solar = [c.get("solar", 0)                                    for c in caps_list]
    wind  = [c.get("onshore_wind", 0) + c.get("offshore_wind", 0) for c in caps_list]
    bat   = [s.get("battery", 0)                                   for s in stor_list]
    hyd   = [s.get("hydrogen", 0)                                  for s in stor_list]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(valid_pcts, costs, "o-", color="#41ab5d", linewidth=2.5,
                 markersize=8, markeredgecolor="black")
    axes[0].set_xlabel("All Renewables Potential (% of max)")
    axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs All Renewables Potential", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[1].plot(valid_pcts, solar, "o-", color=COLORS["solar"],        label="Solar",      linewidth=2)
    axes[1].plot(valid_pcts, wind,  "s-", color=COLORS["onshore_wind"], label="Wind total", linewidth=2)
    axes[1].plot(valid_pcts, bat,   "^-", color=COLORS["battery"],      label="Battery",    linewidth=2)
    axes[1].plot(valid_pcts, hyd,   "D-", color=COLORS["hydrogen"],     label="Hydrogen",   linewidth=2)
    axes[1].set_xlabel("All Renewables Potential (% of max)")
    axes[1].set_ylabel("Installed Capacity (GW)")
    axes[1].set_title("Capacity Mix vs All Renewables Potential", fontweight="bold")
    axes[1].legend(); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – All Renewables Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "12_all_renewables_potential_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 13: CO2 Reduction Pathway
# ═══════════════════════════════════════════════════════════════════════════════
def plot_13_co2_pathway():
    files = {0:   "50_co2_reduction_0pct.nc",  20: "51_co2_reduction_20pct.nc",
             40:  "52_co2_reduction_40pct.nc",  60: "53_co2_reduction_60pct.nc",
             80:  "54_co2_reduction_80pct.nc",  95: "55_co2_reduction_95pct.nc",
             100: "56_co2_reduction_100pct.nc"}

    pcts       = sorted(files.keys())
    valid_pcts = []
    costs, solar, wind, coal_gen, bat = [], [], [], [], []

    for pct in pcts:
        n   = load(files[pct])
        obj = get_objective(n)
        if obj is None: continue
        valid_pcts.append(pct)
        costs.append(obj)
        caps, stor = get_caps(n)
        mix = gen_mix(n)
        solar.append(caps.get("solar", 0))
        wind.append(caps.get("onshore_wind", 0) + caps.get("offshore_wind", 0))
        coal_gen.append(mix.get("coal", 0))
        bat.append(stor.get("battery", 0))

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0,0].plot(valid_pcts, costs, "o-", color="#d94801", linewidth=2.5,
                   markersize=8, markeredgecolor="black")
    axes[0,0].set_xlabel("CO₂ Reduction (%)")
    axes[0,0].set_ylabel("System Cost (B€/year)")
    axes[0,0].set_title("System Cost vs CO₂ Reduction", fontweight="bold")
    axes[0,0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0,0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 8), fontsize=8, ha="center")

    axes[0,1].plot(valid_pcts, coal_gen, "o-", color=COLORS["coal"], linewidth=2.5,
                   markersize=8, markeredgecolor="black")
    axes[0,1].set_xlabel("CO₂ Reduction (%)")
    axes[0,1].set_ylabel("Coal Generation (TWh/year)")
    axes[0,1].set_title("Coal Generation vs CO₂ Reduction", fontweight="bold")
    axes[0,1].grid(alpha=0.3)

    axes[1,0].plot(valid_pcts, solar, "o-", color=COLORS["solar"],        label="Solar",      linewidth=2)
    axes[1,0].plot(valid_pcts, wind,  "s-", color=COLORS["onshore_wind"], label="Wind total", linewidth=2)
    axes[1,0].set_xlabel("CO₂ Reduction (%)")
    axes[1,0].set_ylabel("Capacity (GW)")
    axes[1,0].set_title("Renewable Capacity vs CO₂ Reduction", fontweight="bold")
    axes[1,0].legend(); axes[1,0].grid(alpha=0.3)

    axes[1,1].plot(valid_pcts, bat, "o-", color=COLORS["battery"], linewidth=2.5,
                   markersize=8, markeredgecolor="black")
    axes[1,1].set_xlabel("CO₂ Reduction (%)")
    axes[1,1].set_ylabel("Battery Capacity (GW)")
    axes[1,1].set_title("Battery Storage vs CO₂ Reduction", fontweight="bold")
    axes[1,1].grid(alpha=0.3)

    fig.suptitle("Denmark – CO₂ Decarbonisation Pathway", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "13_co2_reduction_pathway")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 14: Dispatch — Winter & Summer Week (shared y-axis scale)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_14_dispatch(filename, label):
    n = load(filename)

    # Collect data for both weeks first to get shared scale
    all_data = []
    periods  = [("2012-01-09", "Winter"), ("2012-07-09", "Summer")]

    for start, season in periods:
        end  = pd.Timestamp(start) + pd.Timedelta("7D")
        snap = n.snapshots[(n.snapshots >= start) & (n.snapshots < str(end))]
        gen  = n.generators_t.p.loc[snap].copy()
        gen.columns = n.generators.loc[gen.columns, "carrier"]
        gen  = gen.T.groupby(level=0).sum().T / 1e3
        load_ts = n.loads_t.p_set.loc[snap].sum(axis=1) / 1e3
        all_data.append((snap, gen, load_ts, season))

    # Shared y-axis max across both weeks
    y_max = max(
        max(gen.sum(axis=1).max(), load_ts.max())
        for _, gen, load_ts, _ in all_data
    ) * 1.1

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharey=True)  # ← sharey=True

    all_carriers = sorted(set().union(*[gen.columns.tolist() for _, gen, _, _ in all_data]))

    for ax, (snap, gen, load_ts, season) in zip(axes, all_data):
        bottom = pd.Series(0.0, index=snap)
        for carrier in all_carriers:
            if carrier in gen.columns and gen[carrier].sum() > 0:
                ax.fill_between(snap, bottom, bottom + gen[carrier],
                                label=carrier, color=color(carrier), alpha=0.85)
                bottom += gen[carrier]
        load_ts.plot(ax=ax, color="black", linewidth=2, label="Load", zorder=10)
        ax.set_title(f"{season} Week", fontweight="bold")
        ax.set_ylabel("Power (GW)")
        ax.set_ylim(0, y_max)  # ← same scale for both
        ax.grid(alpha=0.2)

    # Single legend outside
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=8, ncol=2,
               bbox_to_anchor=(0.99, 0.98))

    fig.suptitle(f"Denmark – Dispatch: {label}", fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    safe_label = label.lower().replace(" ", "_").replace("₂", "2")
    save(fig, f"14_dispatch_{safe_label}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 15: Storage Filling Levels
# ═══════════════════════════════════════════════════════════════════════════════
def plot_15_storage(filename, label):
    n = load(filename)
    if n.storage_units_t.state_of_charge.empty:
        print(f"  No storage data for {label}"); return
    soc      = n.storage_units_t.state_of_charge
    bat_cols = [c for c in soc.columns if "battery"  in c.lower()]
    hyd_cols = [c for c in soc.columns if "hydrogen" in c.lower()]

    fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
    if bat_cols:
        s = soc[bat_cols].sum(axis=1) / 1e3
        s.plot(ax=axes[0], color=COLORS["battery"], linewidth=1)
        axes[0].fill_between(soc.index, s, alpha=0.3, color=COLORS["battery"])
        axes[0].set_ylabel("GWh")
        axes[0].set_title("Battery – State of Charge", fontweight="bold")
        axes[0].grid(alpha=0.3)
    if hyd_cols:
        s = soc[hyd_cols].sum(axis=1) / 1e3
        s.plot(ax=axes[1], color=COLORS["hydrogen"], linewidth=1)
        axes[1].fill_between(soc.index, s, alpha=0.3, color=COLORS["hydrogen"])
        axes[1].set_ylabel("GWh")
        axes[1].set_title("Hydrogen – State of Charge", fontweight="bold")
        axes[1].grid(alpha=0.3)

    fig.suptitle(f"Denmark – Storage Levels: {label}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    safe_label = label.lower().replace(" ", "_").replace("₂", "2")
    save(fig, f"15_storage_{safe_label}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 16: Cost Summary — sorted by scenario group
# ═══════════════════════════════════════════════════════════════════════════════
def plot_16_cost_summary():
    # Sorted by group: Baseline first, then Zero CO2, then sensitivities
    scenarios_ordered = [
        # ── Reference ─────────────────────────────────────────────────────────
        ("Baseline",           "02_baseline.nc",                   "#636363"),
        ("Zero CO₂",           "04_zero_co2.nc",                   "#41ab5d"),
        # ── Grid ──────────────────────────────────────────────────────────────
        ("Grid – Full",        "05_grid_full_expansion.nc",        "#2171b5"),
        ("Grid – 1GW/line",    "06_grid_max_1GW.nc",              "#6baed6"),
        ("Grid – Autarky",     "07_grid_autarky.nc",              "#d94801"),
        # ── Solar CAPEX ───────────────────────────────────────────────────────
        ("Solar CAPEX 100%",   "08_solar_capex_100pct.nc",        "#f9d71c"),
        ("Solar CAPEX 50%",    "10_solar_capex_50pct.nc",         "#f9d71c"),
        ("Solar CAPEX 0%",     "12_solar_capex_0pct.nc",          "#f9d71c"),
        # ── Wind CAPEX ────────────────────────────────────────────────────────
        ("Wind CAPEX 100%",    "13_wind_capex_100pct.nc",         "#74c476"),
        ("Wind CAPEX 50%",     "15_wind_capex_50pct.nc",          "#74c476"),
        ("Wind CAPEX 0%",      "17_wind_capex_0pct.nc",           "#74c476"),
        # ── Battery CAPEX ─────────────────────────────────────────────────────
        ("Battery CAPEX 100%", "18_battery_capex_100pct.nc",      "#d94801"),
        ("Battery CAPEX 0%",   "22_battery_capex_0pct.nc",        "#d94801"),
        # ── Transmission CAPEX ────────────────────────────────────────────────
        ("Trans. CAPEX 100%",  "23_transmission_capex_100pct.nc", "#636363"),
        ("Trans. CAPEX 0%",    "27_transmission_capex_0pct.nc",   "#636363"),
        # ── Nuclear ───────────────────────────────────────────────────────────
        ("Nuclear 2500 €/kW",  "27_nuclear_2500_eur_per_kw.nc",  "#a1d99b"),
        ("Nuclear 5000 €/kW",  "28_nuclear_5000_eur_per_kw.nc",  "#a1d99b"),
        ("Nuclear 10000 €/kW", "30_nuclear_10000_eur_per_kw.nc", "#a1d99b"),
        # ── Solar Potential ───────────────────────────────────────────────────
        ("Solar Pot. 100%",    "31_solar_potential_100pct.nc",    "#f9d71c"),
        ("Solar Pot. 50%",     "33_solar_potential_50pct.nc",     "#f9d71c"),
        # ── Wind Potential ────────────────────────────────────────────────────
        ("Wind Pot. 100%",     "36_onshore_potential_100pct.nc",  "#74c476"),
        ("Wind Pot. 0%",       "45_onshore_potential_0pct.nc",    "#74c476"),
        # ── CO₂ Pathway ───────────────────────────────────────────────────────
        ("CO₂ -0%",            "50_co2_reduction_0pct.nc",        "#41ab5d"),
        ("CO₂ -20%",           "51_co2_reduction_20pct.nc",       "#41ab5d"),
        ("CO₂ -60%",           "53_co2_reduction_60pct.nc",       "#41ab5d"),
        ("CO₂ -95%",           "55_co2_reduction_95pct.nc",       "#41ab5d"),
        ("CO₂ -100%",          "56_co2_reduction_100pct.nc",      "#41ab5d"),
    ]

    labels, values, colors_list = [], [], []
    for label, fname, clr in scenarios_ordered:
        try:
            n = load(fname)
            obj = get_objective(n)
            if obj is not None:
                labels.append(label)
                values.append(obj)
                colors_list.append(clr)
        except Exception:
            pass

    fig, ax = plt.subplots(figsize=(14, 11))
    bars = ax.barh(labels, values, color=colors_list, edgecolor="white", height=0.7)
    for bar, val in zip(bars, values):
        ax.text(val + 0.05, bar.get_y() + bar.get_height()/2,
                f"{val:.2f} B€", va="center", fontsize=8.5)

    # Add group separator lines
    group_boundaries = [2, 5, 8, 11, 13, 15, 18, 20, 22]
    for b in group_boundaries:
        if b < len(labels):
            ax.axhline(y=b - 0.5, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)

    ax.set_xlabel("Total System Cost (Billion €/year)", fontsize=11)
    ax.set_title("Denmark – System Cost Overview: All Scenarios\n"
                 "Grouped by: Reference | Grid | Solar CAPEX | Wind CAPEX | Battery | Transmission | Nuclear | Potentials | CO₂ Pathway",
                 fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3, axis="x")
    ax.invert_yaxis()  # Baseline on top
    plt.tight_layout()
    save(fig, "16_cost_summary_all_scenarios")


# ═══════════════════════════════════════════════════════════════════════════════
# RUN ALL PLOTS
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("Denmark Energy Model – Generating all plots")
    print("=" * 60)

    plot_01_mix_baseline_vs_zero_co2()
    plot_02_capacities_comparison()
    plot_03_grid_sensitivity()
    plot_04_solar_capex()
    plot_05_wind_capex()
    plot_06_battery_capex()
    plot_07_transmission_capex()
    plot_08_nuclear()
    plot_09_nuclear_grid()
    plot_10_solar_potential()
    plot_11_onshore_potential()
    plot_12_all_renewables_potential()
    plot_13_co2_pathway()
    plot_14_dispatch("04_zero_co2.nc",  "Zero CO2")
    plot_14_dispatch("02_baseline.nc",  "Baseline")
    plot_15_storage("04_zero_co2.nc",   "Zero CO2")
    plot_15_storage("02_baseline.nc",   "Baseline")
    plot_16_cost_summary()

    print("\n" + "=" * 60)
    print(f"✓ All plots saved to {OUT_DIR}/")
    print("=" * 60)