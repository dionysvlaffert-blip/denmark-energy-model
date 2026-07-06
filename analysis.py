"""
analysis.py – Final version with all visual improvements
Run from the project root folder.
"""

import pypsa
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import os

NET_DIR = "results/networks"
OUT_DIR = "results/figures"
os.makedirs(OUT_DIR, exist_ok=True)

# Global font sizes
plt.rcParams.update({
    "font.size":        11,
    "axes.titlesize":   13,
    "axes.labelsize":   11,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
    "legend.fontsize":  10,
    "figure.titlesize": 14,
})

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
    return gen.groupby(n.generators.carrier).sum() / 1e6

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
    pcts, costs, caps_list, stor_list, nets = [], [], [], [], []
    for pct in sorted(files.keys(), reverse=True):
        try:
            n = load(files[pct])
            obj = get_objective(n)
            if obj is None:
                print(f"    ⚠ No objective: {files[pct]}")
                continue
            pcts.append(pct); costs.append(obj)
            caps, stor = get_caps(n)
            caps_list.append(caps); stor_list.append(stor); nets.append(n)
        except Exception as e:
            print(f"    ⚠ Could not load {files[pct]}: {e}")
    return pcts, costs, caps_list, stor_list, nets


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 00: Base Scenario Detail
# ═══════════════════════════════════════════════════════════════════════════════
def plot_00_base_scenario():
    print("\n[00] Base Scenario Detail")
    n = load("02_baseline.nc")
    weights = n.snapshot_weightings.generators

    fig = plt.figure(figsize=(20, 14))
    gs  = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.35)

    # ── 1. Electricity mix pie ─────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    mix = gen_mix(n); mix = mix[mix > 0].sort_values(ascending=False)
    explode = [0.08 if v < 2 else 0 for v in mix.values]
    wedges, texts, autotexts = ax1.pie(
        mix, labels=None, autopct="%1.1f%%",
        colors=[color(c) for c in mix.index],
        explode=explode, startangle=90, counterclock=False,
        pctdistance=0.78)
    for at in autotexts: at.set_fontsize(9)
    ax1.legend(mix.index, loc="lower left", fontsize=9,
               bbox_to_anchor=(-0.1, -0.15), ncol=2)
    ax1.set_title(f"Electricity Mix\n{mix.sum():.1f} TWh/year",
                  fontweight="bold", fontsize=12)

    # ── 2. Installed capacities ────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    caps, stor = get_caps(n)
    all_caps = pd.concat([caps, stor])
    all_caps = all_caps[all_caps > 0.001].sort_values(ascending=False)
    ax2.bar(range(len(all_caps)), all_caps.values,
            color=[color(c) for c in all_caps.index], edgecolor="white")
    ax2.set_xticks(range(len(all_caps)))
    ax2.set_xticklabels(all_caps.index, rotation=40, ha="right", fontsize=9)
    ax2.set_ylabel("Capacity (GW)")
    ax2.set_title("Installed Capacities", fontweight="bold")
    ax2.grid(alpha=0.3, axis="y")

    # ── 3. System cost breakdown ───────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    costs_by_carrier = {}
    for gen in n.generators.index:
        carrier  = n.generators.at[gen, "carrier"]
        cap_cost = n.generators.at[gen, "capital_cost"] * n.generators.at[gen, "p_nom_opt"]
        mar_cost = (n.generators_t.p[gen] * weights * n.generators.at[gen, "marginal_cost"]).sum()
        costs_by_carrier[carrier] = costs_by_carrier.get(carrier, 0) + (cap_cost + mar_cost) / 1e9
    cs = pd.Series(costs_by_carrier)
    cs = cs[cs > 0].sort_values(ascending=False)
    ax3.bar(range(len(cs)), cs.values,
            color=[color(c) for c in cs.index], edgecolor="white")
    ax3.set_xticks(range(len(cs)))
    ax3.set_xticklabels(cs.index, rotation=40, ha="right", fontsize=9)
    ax3.set_ylabel("Cost (B€/year)")
    ax3.set_title(f"Cost by Technology\nTotal: {get_objective(n):.2f} B€/year",
                  fontweight="bold")
    ax3.grid(alpha=0.3, axis="y")

    # ── 4. Dispatch winter week ────────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, :2])
    start = "2012-01-09"
    snap  = n.snapshots[(n.snapshots >= start) &
                        (n.snapshots < str(pd.Timestamp(start) + pd.Timedelta("7D")))]
    gen_t = n.generators_t.p.loc[snap].copy()
    gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
    gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
    load_ts = n.loads_t.p_set.loc[snap].sum(axis=1) / 1e3
    bottom = pd.Series(0.0, index=snap)
    for carrier in gen_t.columns:
        if gen_t[carrier].sum() > 0:
            ax4.fill_between(snap, bottom, bottom + gen_t[carrier],
                             label=carrier, color=color(carrier), alpha=0.85)
            bottom += gen_t[carrier]
    load_ts.plot(ax=ax4, color="black", linewidth=2, label="Load", zorder=10)
    ax4.set_title("Dispatch — Winter Week (January)", fontweight="bold")
    ax4.set_ylabel("Power (GW)")
    ax4.legend(loc="upper left", fontsize=9, ncol=5)
    ax4.grid(alpha=0.2)

    # ── 5. Regional generation ────────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 2])
    regional_gen = {}
    for gen in n.generators.index:
        bus     = n.generators.at[gen, "bus"]
        carrier = n.generators.at[gen, "carrier"]
        mwh     = (n.generators_t.p[gen] * weights).sum() / 1e6
        if bus not in regional_gen: regional_gen[bus] = {}
        regional_gen[bus][carrier] = regional_gen[bus].get(carrier, 0) + mwh

    regions  = list(regional_gen.keys())
    carriers = sorted(set(c for r in regional_gen.values() for c in r))
    carriers = [c for c in carriers if any(regional_gen[r].get(c,0)>0 for r in regions)]
    bottom_arr = np.zeros(len(regions))
    for carrier in carriers:
        vals = [regional_gen[r].get(carrier, 0) for r in regions]
        ax5.bar(regions, vals, bottom=bottom_arr,
                label=carrier, color=color(carrier), edgecolor="white")
        bottom_arr += np.array(vals)
    ax5.set_xticklabels(regions, rotation=40, ha="right", fontsize=9)
    ax5.set_ylabel("Generation (TWh/year)")
    ax5.set_title("Generation by Region", fontweight="bold")
    ax5.legend(fontsize=8, ncol=2)
    ax5.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Baseline Scenario: Full System Overview",
                 fontsize=15, fontweight="bold")
    save(fig, "00_base_scenario_detail")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 01: Mix Baseline vs Zero CO2 — exploded pie for small slices
# ═══════════════════════════════════════════════════════════════════════════════
def plot_01_mix():
    print("\n[01] Baseline vs Zero CO2 Mix")
    n_base = load("02_baseline.nc")
    n_co2  = load("04_zero_co2.nc")

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, (n, label) in zip(axes, [(n_base,"Baseline (no limit)"), (n_co2,"Zero CO₂")]):
        mix = gen_mix(n); mix = mix[mix > 0].sort_values(ascending=False)
        explode = [0.08 if v < 2 else 0 for v in mix.values]
        wedges, texts, autotexts = ax.pie(
            mix, labels=None, autopct="%1.1f%%",
            colors=[color(c) for c in mix.index],
            explode=explode, startangle=90, counterclock=False,
            pctdistance=0.78)
        for at in autotexts: at.set_fontsize(10)
        ax.legend(mix.index, loc="lower left", fontsize=10,
                  bbox_to_anchor=(-0.05, -0.18), ncol=2)
        obj = get_objective(n)
        ax.set_title(f"{label}\nTotal: {mix.sum():.1f} TWh/year | Cost: {obj:.2f} B€/year",
                     fontsize=12, fontweight="bold")
    fig.suptitle("Denmark – Electricity Mix: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "01_mix_baseline_vs_zero_co2")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 02: Capacities
# ═══════════════════════════════════════════════════════════════════════════════
def plot_02_capacities():
    print("\n[02] Capacities")
    n_base = load("02_baseline.nc"); n_co2 = load("04_zero_co2.nc")
    all_carriers = set()
    data = {}
    for label, n in [("Baseline", n_base), ("Zero CO₂", n_co2)]:
        caps, stor = get_caps(n)
        combined = pd.concat([caps, stor]); combined = combined[combined > 0.01]
        data[label] = combined; all_carriers |= set(combined.index)
    all_carriers = sorted(all_carriers)
    df = pd.DataFrame({l: [data[l].get(c,0) for c in all_carriers]
                       for l in data}, index=all_carriers)
    df = df[df.sum(axis=1) > 0.01]

    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(df)); w = 0.35
    ax.bar(x - w/2, df["Baseline"], w, label="Baseline",
           color=[color(c) for c in df.index], alpha=0.5, edgecolor="white")
    ax.bar(x + w/2, df["Zero CO₂"], w, label="Zero CO₂",
           color=[color(c) for c in df.index], alpha=1.0, edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(df.index, rotation=35, ha="right", fontsize=11)
    ax.set_ylabel("Capacity (GW)", fontsize=12)
    ax.set_title("Denmark – Installed Capacities: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=12); ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    save(fig, "02_capacities_baseline_vs_zero_co2")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 03: Grid Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_03_grid():
    print("\n[03] Grid Sensitivity")
    scenarios = {"Full expansion": "05_grid_full_expansion.nc",
                 "Max 1 GW/line": "06_grid_max_1GW.nc",
                 "Autarky":       "07_grid_autarky.nc"}
    costs = {}; mixes = {}
    for label, fname in scenarios.items():
        try:
            n = load(fname); obj = get_objective(n)
            if obj: costs[label] = obj
            mixes[label] = gen_mix(n)
        except: pass

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    ax = axes[0]
    s = pd.Series(costs).dropna()
    bars = ax.bar(s.index, s.values,
                  color=["#2171b5","#74c476","#d94801"][:len(s)], edgecolor="white")
    for bar, val in zip(bars, s.values):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                f"{val:.2f}B€", ha="center", fontsize=11)
    ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost by Grid Scenario", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=11)

    ax = axes[1]
    all_c = sorted(set().union(*[m.index for m in mixes.values()]))
    df = pd.DataFrame({l: [mixes[l].get(c,0) for c in all_c]
                       for l in mixes}, index=all_c)
    df = df[df.sum(axis=1) > 0]
    bottom = np.zeros(len(mixes))
    for carrier in df.index:
        ax.bar(list(mixes.keys()), df.loc[carrier].values, bottom=bottom,
               label=carrier, color=color(carrier), edgecolor="white")
        bottom += df.loc[carrier].values
    ax.set_ylabel("Annual Generation (TWh)", fontsize=12)
    ax.set_title("Generation Mix by Grid Scenario", fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=11)
    fig.suptitle("Denmark – Grid Expansion Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "03_grid_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 03b: Annual Generation + Demand — BIGGER fonts
# ═══════════════════════════════════════════════════════════════════════════════
def plot_03b_annual():
    print("\n[03b] Annual Generation + Demand")
    fig, axes = plt.subplots(2, 1, figsize=(20, 14), sharex=True)
    for ax, (fname, label) in zip(axes, [
            ("02_baseline.nc", "Baseline"), ("04_zero_co2.nc", "Zero CO₂")]):
        try: n = load(fname)
        except: continue
        gen_t = n.generators_t.p.copy()
        gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
        gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
        gen_weekly = gen_t.resample("W").mean()
        load_ts = n.loads_t.p_set.sum(axis=1) / 1e3
        load_weekly = load_ts.resample("W").mean()
        bottom = pd.Series(0.0, index=gen_weekly.index)
        for carrier in gen_weekly.columns:
            if gen_weekly[carrier].sum() > 0:
                ax.fill_between(gen_weekly.index, bottom,
                                bottom + gen_weekly[carrier],
                                label=carrier, color=color(carrier), alpha=0.85)
                bottom += gen_weekly[carrier]
        load_weekly.plot(ax=ax, color="black", linewidth=2.5,
                         label="Demand", zorder=10, linestyle="--")
        ax.set_ylabel("Power (GW, weekly avg)", fontsize=13)
        ax.set_title(f"{label}", fontweight="bold", fontsize=14)
        ax.legend(loc="upper left", fontsize=11, ncol=5,
                  framealpha=0.9, edgecolor="grey")
        ax.grid(alpha=0.2)
        ax.tick_params(labelsize=11)
    fig.suptitle("Denmark – Annual Generation & Demand: Baseline vs Zero CO₂\n"
                 "(Weekly averages)", fontsize=15, fontweight="bold")
    plt.tight_layout()
    save(fig, "03b_annual_generation_demand")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Sensitivity plot with background bars
# ═══════════════════════════════════════════════════════════════════════════════
def plot_sensitivity_with_bars(title, fname_prefix, files, vary_carrier,
                                bg_carriers, x_label, invert_x=True):
    valid_pcts, costs, caps_list, stor_list, nets = safe_sensitivity_data(files)
    if not valid_pcts: print(f"  No data for {title}"); return

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    ax = axes[0]
    vc = color(vary_carrier)
    ax.plot(valid_pcts, costs, "o-", color=vc, linewidth=2.5,
            markersize=9, markeredgecolor="black")
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost", fontweight="bold")
    if invert_x: ax.invert_xaxis()
    ax.grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=10, ha="center")

    ax = axes[1]
    x_pos = np.arange(len(valid_pcts))
    bw = 0.15
    offsets = np.linspace(-bw*len(bg_carriers)/2, bw*len(bg_carriers)/2, len(bg_carriers))
    for i, bgc in enumerate(bg_carriers):
        bg_vals = [caps.get(bgc, stor.get(bgc, 0))
                   for caps, stor in zip(caps_list, stor_list)]
        ax.bar(x_pos + offsets[i], bg_vals, bw,
               color=color(bgc), alpha=0.4,
               label=f"{bgc} (bars)", edgecolor="white")
    vary_vals = [caps.get(vary_carrier, stor.get(vary_carrier, 0))
                 for caps, stor in zip(caps_list, stor_list)]
    ax.plot(x_pos, vary_vals, "o-", color=vc, linewidth=2.5,
            markersize=9, markeredgecolor="black",
            label=f"{vary_carrier} (line)", zorder=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"{p}%" for p in valid_pcts], fontsize=11)
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel("Installed Capacity (GW)", fontsize=12)
    ax.set_title("Varied (line) + Others (bars)", fontweight="bold")
    ax.legend(fontsize=10, ncol=2, loc="best")
    ax.grid(alpha=0.3, axis="y")

    fig.suptitle(f"Denmark – {title}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, fname_prefix)


# ═══════════════════════════════════════════════════════════════════════════════
# PLOTS 04–06, 11, 12
# ═══════════════════════════════════════════════════════════════════════════════
def plot_04_solar_capex():
    print("\n[04] Solar CAPEX")
    plot_sensitivity_with_bars(
        "Solar CAPEX Sensitivity", "04_solar_capex_sensitivity",
        {100:"08_solar_capex_100pct.nc", 75:"09_solar_capex_75pct.nc",
         50:"10_solar_capex_50pct.nc",   25:"11_solar_capex_25pct.nc",
         0:"12_solar_capex_0pct.nc"},
        "solar", ["onshore_wind","offshore_wind","battery"], "Solar CAPEX (% of base)")

def plot_05_wind_capex():
    print("\n[05] Wind CAPEX")
    files = {100:"13_wind_capex_100pct.nc", 75:"14_wind_capex_75pct.nc",
             50:"15_wind_capex_50pct.nc",   25:"16_wind_capex_25pct.nc",
             0:"17_wind_capex_0pct.nc"}
    valid_pcts, costs, caps_list, stor_list, _ = safe_sensitivity_data(files)
    if not valid_pcts: return

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(valid_pcts, costs, "o-", color=COLORS["onshore_wind"],
            linewidth=2.5, markersize=9, markeredgecolor="black")
    ax.set_xlabel("Wind CAPEX (% of base)", fontsize=12)
    ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost vs Wind CAPEX", fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=10, ha="center")

    ax = axes[1]
    x_pos = np.arange(len(valid_pcts))
    solar    = [c.get("solar",0)          for c in caps_list]
    onshore  = [c.get("onshore_wind",0)   for c in caps_list]
    offshore = [c.get("offshore_wind",0)  for c in caps_list]
    bat      = [s.get("battery",0)        for s in stor_list]
    w = 0.2
    ax.bar(x_pos - 1.5*w, solar, w, color=COLORS["solar"],   alpha=0.4, label="Solar (bars)",   edgecolor="white")
    ax.bar(x_pos - 0.5*w, bat,   w, color=COLORS["battery"], alpha=0.4, label="Battery (bars)", edgecolor="white")
    ax.plot(x_pos, onshore,  "o-", color=COLORS["onshore_wind"],  linewidth=2.5, markersize=8, label="Onshore Wind")
    ax.plot(x_pos, offshore, "s-", color=COLORS["offshore_wind"], linewidth=2.5, markersize=8, label="Offshore Wind")
    ax.set_xticks(x_pos); ax.set_xticklabels([f"{p}%" for p in valid_pcts], fontsize=11)
    ax.set_xlabel("Wind CAPEX (% of base)", fontsize=12)
    ax.set_ylabel("Installed Capacity (GW)", fontsize=12)
    ax.set_title("Wind (lines) + Others (bars)", fontweight="bold")
    ax.legend(fontsize=10); ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Wind CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "05_wind_capex_sensitivity")

def plot_06_battery_capex():
    print("\n[06] Battery CAPEX")
    files = {100:"18_battery_capex_100pct.nc", 75:"19_battery_capex_75pct.nc",
             50:"20_battery_capex_50pct.nc",   25:"21_battery_capex_25pct.nc",
             0:"22_battery_capex_0pct.nc"}
    valid_pcts, costs, caps_list, stor_list, _ = safe_sensitivity_data(files)
    if not valid_pcts: return

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(valid_pcts, costs, "o-", color=COLORS["battery"],
            linewidth=2.5, markersize=9, markeredgecolor="black")
    ax.set_xlabel("Battery CAPEX (% of base)", fontsize=12)
    ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost vs Battery CAPEX", fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=10, ha="center")

    ax = axes[1]
    x_pos = np.arange(len(valid_pcts))
    bat   = [s.get("battery",0)  for s in stor_list]
    hyd   = [s.get("hydrogen",0) for s in stor_list]
    wind  = [c.get("onshore_wind",0)+c.get("offshore_wind",0) for c in caps_list]
    solar = [c.get("solar",0)    for c in caps_list]
    w = 0.2
    ax.bar(x_pos - 0.5*w, wind,  w, color=COLORS["onshore_wind"], alpha=0.4, label="Wind (bars)",  edgecolor="white")
    ax.bar(x_pos + 0.5*w, solar, w, color=COLORS["solar"],        alpha=0.4, label="Solar (bars)", edgecolor="white")
    ax.plot(x_pos, bat, "o-", color=COLORS["battery"],  linewidth=2.5, markersize=8, label="Battery")
    ax.plot(x_pos, hyd, "s-", color=COLORS["hydrogen"], linewidth=2.5, markersize=8, label="Hydrogen")
    ax.set_xticks(x_pos); ax.set_xticklabels([f"{p}%" for p in valid_pcts], fontsize=11)
    ax.set_xlabel("Battery CAPEX (% of base)", fontsize=12)
    ax.set_ylabel("Installed Capacity (GW)", fontsize=12)
    ax.set_title("Storage (lines) + Renewables (bars)", fontweight="bold")
    ax.legend(fontsize=10); ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Battery CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "06_battery_capex_sensitivity")

def plot_07_transmission_capex():
    print("\n[07] Transmission CAPEX")
    files = {100:"23_transmission_capex_100pct.nc", 75:"24_transmission_capex_75pct.nc",
             50:"25_transmission_capex_50pct.nc",   25:"26_transmission_capex_25pct.nc",
             0:"27_transmission_capex_0pct.nc"}
    valid_pcts, costs, _, _, nets = safe_sensitivity_data(files)
    trans = [n.links["p_nom_opt"].sum()/1e3 for n in nets]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, y_vals, ylabel, title in zip(
            axes,
            [costs, trans],
            ["System Cost (B€/year)", "Total Transmission (GW)"],
            ["System Cost vs Transmission CAPEX", "Transmission Capacity vs CAPEX"]):
        ax.plot(valid_pcts, y_vals, "o-", color=COLORS["transmission"],
                linewidth=2.5, markersize=9, markeredgecolor="black")
        ax.set_xlabel("Transmission CAPEX (% of base)", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontweight="bold")
        ax.invert_xaxis(); ax.grid(alpha=0.3)
        for x, y in zip(valid_pcts, y_vals):
            ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                        xytext=(0,10), fontsize=10, ha="center")
    fig.suptitle("Denmark – Transmission CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "07_transmission_capex_sensitivity")

def plot_08_nuclear():
    print("\n[08] Nuclear Sensitivity")
    files = {2500:"27_nuclear_2500_eur_per_kw.nc", 5000:"28_nuclear_5000_eur_per_kw.nc",
             7500:"29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}
    prices = sorted(files.keys())
    vp, costs, nuc, solar, wind = [], [], [], [], []
    for price in prices:
        try:
            n = load(files[price]); obj = get_objective(n)
            if obj is None: continue
            vp.append(price); costs.append(obj)
            caps, _ = get_caps(n)
            nuc.append(caps.get("nuclear",0)); solar.append(caps.get("solar",0))
            wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
        except: pass

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(vp, costs, "o-", color=COLORS["nuclear"], linewidth=2.5,
                 markersize=9, markeredgecolor="black")
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)", fontsize=12)
    axes[0].set_ylabel("System Cost (B€/year)", fontsize=12)
    axes[0].set_title("System Cost vs Nuclear CAPEX", fontweight="bold"); axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    for x, y in zip(vp, costs):
        axes[0].annotate(f"{y:.2f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=10, ha="center")

    axes[1].plot(vp, nuc,   "o-", color=COLORS["nuclear"],       linewidth=2, markersize=8, label="Nuclear")
    axes[1].plot(vp, wind,  "s-", color=COLORS["offshore_wind"], linewidth=2, markersize=8, label="Wind total")
    axes[1].plot(vp, solar, "^-", color=COLORS["solar"],         linewidth=2, markersize=8, label="Solar")
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)", fontsize=12)
    axes[1].set_ylabel("Installed Capacity (GW)", fontsize=12)
    axes[1].set_title("Capacity Mix vs Nuclear CAPEX", fontweight="bold")
    axes[1].legend(fontsize=11); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    fig.suptitle("Denmark – Nuclear CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "08_nuclear_sensitivity")

def plot_09_nuclear_grid():
    print("\n[09] Nuclear + Grid")
    free_f = {2500:"27_nuclear_2500_eur_per_kw.nc", 5000:"28_nuclear_5000_eur_per_kw.nc",
              7500:"29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}
    grid_f = {2500:"46_nuclear_2500eurkw_grid_1GW.nc", 5000:"47_nuclear_5000eurkw_grid_1GW.nc",
              7500:"48_nuclear_7500eurkw_grid_1GW.nc", 10000:"49_nuclear_10000eurkw_grid_1GW.nc"}
    prices = sorted(free_f.keys())
    vp, cf, cg, nf, ng = [], [], [], [], []
    for p in prices:
        try:
            n1=load(free_f[p]); n2=load(grid_f[p])
            o1=get_objective(n1); o2=get_objective(n2)
            if o1 is None or o2 is None: continue
            vp.append(p); cf.append(o1); cg.append(o2)
            c1,_=get_caps(n1); c2,_=get_caps(n2)
            nf.append(c1.get("nuclear",0)); ng.append(c2.get("nuclear",0))
        except: pass

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(vp, cf, "o-", color=COLORS["nuclear"], label="Baseline network", linewidth=2, markersize=8)
    axes[0].plot(vp, cg, "s-", color=COLORS["battery"], label="Max 1GW/line",     linewidth=2, markersize=8)
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)", fontsize=12); axes[0].set_ylabel("System Cost (B€/year)", fontsize=12)
    axes[0].set_title("Cost: Baseline Network vs 1GW Grid Limit", fontweight="bold")
    axes[0].legend(fontsize=11); axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))

    axes[1].plot(vp, nf, "o-", color=COLORS["nuclear"], label="Baseline network", linewidth=2, markersize=8)
    axes[1].plot(vp, ng, "s-", color=COLORS["battery"], label="Max 1GW/line",     linewidth=2, markersize=8)
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)", fontsize=12); axes[1].set_ylabel("Nuclear Capacity (GW)", fontsize=12)
    axes[1].set_title("Nuclear Capacity: Baseline vs 1GW Grid", fontweight="bold")
    axes[1].legend(fontsize=11); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    fig.suptitle("Denmark – Nuclear + Grid Expansion Combined", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "09_nuclear_grid_combined")

def plot_10_solar_potential():
    print("\n[10] Solar Potential")
    files = {100:"31_solar_potential_100pct.nc", 75:"32_solar_potential_75pct.nc",
             50:"33_solar_potential_50pct.nc",   25:"34_solar_potential_25pct.nc",
             0:"35_solar_potential_0pct.nc"}
    valid_pcts, costs, caps_list, stor_list, _ = safe_sensitivity_data(files)
    solar = [c.get("solar",0)                                     for c in caps_list]
    wind  = [c.get("onshore_wind",0)+c.get("offshore_wind",0)     for c in caps_list]
    bat   = [s.get("battery",0)                                    for s in stor_list]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(valid_pcts, costs, "o-", color=COLORS["solar"],
                 linewidth=2.5, markersize=9, markeredgecolor="black")
    axes[0].set_xlabel("Solar Potential (% of max)", fontsize=12)
    axes[0].set_ylabel("System Cost (B€/year)", fontsize=12)
    axes[0].set_title("System Cost vs Solar Potential", fontweight="bold")
    axes[0].invert_xaxis(); axes[0].grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        axes[0].annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=10, ha="center")

    axes[1].plot(valid_pcts, solar, "o-", color=COLORS["solar"],        linewidth=2, markersize=8, label="Solar")
    axes[1].plot(valid_pcts, wind,  "s-", color=COLORS["onshore_wind"], linewidth=2, markersize=8, label="Wind total")
    axes[1].plot(valid_pcts, bat,   "^-", color=COLORS["battery"],      linewidth=2, markersize=8, label="Battery")
    axes[1].set_xlabel("Solar Potential (% of max)", fontsize=12)
    axes[1].set_ylabel("Installed Capacity (GW)", fontsize=12)
    axes[1].set_title("Capacity Mix vs Solar Potential", fontweight="bold")
    axes[1].legend(fontsize=11); axes[1].invert_xaxis(); axes[1].grid(alpha=0.3)
    fig.suptitle("Denmark – Solar Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "10_solar_potential_sensitivity")

def plot_11_onshore_potential():
    print("\n[11] Onshore Wind Potential")
    plot_sensitivity_with_bars(
        "Onshore Wind Potential Sensitivity", "11_onshore_potential_sensitivity",
        {100:"36_onshore_potential_100pct.nc", 75:"42_onshore_potential_75pct.nc",
         50:"43_onshore_potential_50pct.nc",   25:"44_onshore_potential_25pct.nc",
         0:"45_onshore_potential_0pct.nc"},
        "onshore_wind", ["solar","offshore_wind","battery"],
        "Onshore Wind Potential (% of max)")

def plot_12_all_renewables():
    print("\n[12] All Renewables Potential")
    files = {100:"37_all_ren_potential_100pct.nc", 75:"38_all_ren_potential_75pct.nc",
             50:"39_all_ren_potential_50pct.nc",   25:"40_all_ren_potential_25pct.nc",
             0:"41_all_ren_potential_0pct.nc"}
    valid_pcts, costs, caps_list, stor_list, _ = safe_sensitivity_data(files)
    solar = [c.get("solar",0)                                 for c in caps_list]
    wind  = [c.get("onshore_wind",0)+c.get("offshore_wind",0) for c in caps_list]
    bat   = [s.get("battery",0)  for s in stor_list]
    hyd   = [s.get("hydrogen",0) for s in stor_list]

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(valid_pcts, costs, "o-", color="#41ab5d",
            linewidth=2.5, markersize=9, markeredgecolor="black")
    ax.set_xlabel("All Renewables Potential (% of max)", fontsize=12)
    ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost vs All Renewables Potential", fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(valid_pcts, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=10, ha="center")

    ax = axes[1]
    x_pos = np.arange(len(valid_pcts)); w = 0.2
    ax.bar(x_pos - 0.5*w, bat, w, color=COLORS["battery"],  alpha=0.4, label="Battery (bars)",  edgecolor="white")
    ax.bar(x_pos + 0.5*w, hyd, w, color=COLORS["hydrogen"], alpha=0.4, label="Hydrogen (bars)", edgecolor="white")
    ax.plot(x_pos, solar, "o-", color=COLORS["solar"],        linewidth=2.5, markersize=8, label="Solar")
    ax.plot(x_pos, wind,  "s-", color=COLORS["onshore_wind"], linewidth=2.5, markersize=8, label="Wind total")
    ax.set_xticks(x_pos); ax.set_xticklabels([f"{p}%" for p in valid_pcts], fontsize=11)
    ax.set_xlabel("All Renewables Potential (% of max)", fontsize=12)
    ax.set_ylabel("Installed Capacity (GW)", fontsize=12)
    ax.set_title("Renewables (lines) + Storage (bars)", fontweight="bold")
    ax.legend(fontsize=10); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Denmark – All Renewables Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "12_all_renewables_potential_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 13: CO2 Pathway — BIGGER (2 separate figures)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_13_co2_pathway():
    print("\n[13] CO2 Pathway")
    files = {0:"50_co2_reduction_0pct.nc",   20:"51_co2_reduction_20pct.nc",
             40:"52_co2_reduction_40pct.nc", 60:"53_co2_reduction_60pct.nc",
             80:"54_co2_reduction_80pct.nc", 95:"55_co2_reduction_95pct.nc",
             100:"56_co2_reduction_100pct.nc"}
    pcts = sorted(files.keys())
    vp, costs, solar, wind, coal_gen, bat = [], [], [], [], [], []
    for pct in pcts:
        try:
            n = load(files[pct]); obj = get_objective(n)
            if obj is None: continue
            vp.append(pct); costs.append(obj)
            caps, stor = get_caps(n); mix = gen_mix(n)
            solar.append(caps.get("solar",0))
            wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
            coal_gen.append(mix.get("coal",0)); bat.append(stor.get("battery",0))
        except: pass

    # Figure 1: Cost + Coal
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    axes[0].plot(vp, costs, "o-", color="#d94801", linewidth=2.5,
                 markersize=10, markeredgecolor="black")
    axes[0].set_xlabel("CO₂ Reduction (%)", fontsize=13)
    axes[0].set_ylabel("System Cost (B€/year)", fontsize=13)
    axes[0].set_title("System Cost vs CO₂ Reduction", fontweight="bold", fontsize=13)
    axes[0].grid(alpha=0.3)
    for x, y in zip(vp, costs):
        axes[0].annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=10, ha="center")

    axes[1].plot(vp, coal_gen, "o-", color=COLORS["coal"], linewidth=2.5,
                 markersize=10, markeredgecolor="black")
    axes[1].set_xlabel("CO₂ Reduction (%)", fontsize=13)
    axes[1].set_ylabel("Coal Generation (TWh/year)", fontsize=13)
    axes[1].set_title("Coal Generation vs CO₂ Reduction", fontweight="bold", fontsize=13)
    axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – CO₂ Decarbonisation Pathway (1/2): Cost & Coal",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    save(fig, "13a_co2_reduction_cost_coal")

    # Figure 2: Renewables + Battery
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    axes[0].plot(vp, solar, "o-", color=COLORS["solar"],        linewidth=2, markersize=9, label="Solar")
    axes[0].plot(vp, wind,  "s-", color=COLORS["onshore_wind"], linewidth=2, markersize=9, label="Wind total")
    axes[0].set_xlabel("CO₂ Reduction (%)", fontsize=13)
    axes[0].set_ylabel("Capacity (GW)", fontsize=13)
    axes[0].set_title("Renewable Capacity vs CO₂ Reduction", fontweight="bold", fontsize=13)
    axes[0].legend(fontsize=12); axes[0].grid(alpha=0.3)

    axes[1].plot(vp, bat, "o-", color=COLORS["battery"], linewidth=2.5,
                 markersize=10, markeredgecolor="black")
    axes[1].set_xlabel("CO₂ Reduction (%)", fontsize=13)
    axes[1].set_ylabel("Battery Capacity (GW)", fontsize=13)
    axes[1].set_title("Battery Storage vs CO₂ Reduction", fontweight="bold", fontsize=13)
    axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – CO₂ Decarbonisation Pathway (2/2): Capacity & Storage",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    save(fig, "13b_co2_reduction_capacity_storage")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 14: Dispatch seasonal averages — BIGGER legend
# ═══════════════════════════════════════════════════════════════════════════════
def plot_14_dispatch(filename, label):
    print(f"\n[14] Dispatch – {label}")
    n = load(filename)
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), sharey=True)

    seasons = {
        "Winter (Dec–Feb)": ("2012-12-01", "2013-02-28"),
        "Summer (Jun–Aug)": ("2012-06-01", "2012-08-31"),
    }
    all_carriers = set()
    season_data  = {}
    for season, (start, end) in seasons.items():
        snap = n.snapshots[(n.snapshots >= start) & (n.snapshots <= end)]
        if len(snap) == 0:
            snap = n.snapshots[(n.snapshots >= start[:7])][:1000]
        gen_t = n.generators_t.p.loc[snap].copy()
        gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
        gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
        gen_avg  = gen_t.groupby(gen_t.index.hour).mean()
        load_ts  = n.loads_t.p_set.loc[snap].sum(axis=1) / 1e3
        load_avg = load_ts.groupby(load_ts.index.hour).mean()
        season_data[season] = (gen_avg, load_avg)
        all_carriers |= set(gen_avg.columns)

    y_max = max(
        max(ga.sum(axis=1).max(), la.max())
        for ga, la in season_data.values()
    ) * 1.12

    for ax, (season, (gen_avg, load_avg)) in zip(axes, season_data.items()):
        bottom = pd.Series(0.0, index=gen_avg.index)
        for carrier in all_carriers:
            if carrier in gen_avg.columns and gen_avg[carrier].sum() > 0:
                ax.fill_between(gen_avg.index, bottom,
                                bottom + gen_avg[carrier],
                                label=carrier, color=color(carrier), alpha=0.85)
                bottom += gen_avg[carrier]
        load_avg.plot(ax=ax, color="black", linewidth=2.5,
                      label="Demand", zorder=10, linestyle="--")
        ax.set_title(f"{season}", fontweight="bold", fontsize=13)
        ax.set_ylabel("Average Power (GW)", fontsize=12)
        ax.set_xlabel("Hour of Day", fontsize=12)
        ax.set_ylim(0, y_max)
        ax.set_xticks(range(0, 24, 2))
        ax.tick_params(labelsize=11)
        ax.grid(alpha=0.2)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=11, ncol=2,
               bbox_to_anchor=(0.99, 0.98), framealpha=0.9)
    fig.suptitle(f"Denmark – Average Daily Dispatch: {label}\n"
                 "(Seasonal averages — Winter Dec–Feb, Summer Jun–Aug)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 0.87, 1])
    safe_label = label.lower().replace(" ", "_").replace("₂", "2")
    save(fig, f"14_dispatch_seasonal_{safe_label}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 15: Storage + Wind/Solar generation — with legend, explain empty baseline
# ═══════════════════════════════════════════════════════════════════════════════
def plot_15_storage(filename, label):
    print(f"\n[15] Storage – {label}")
    n = load(filename)

    # Wind and solar generation (weekly avg)
    freq = "W"
    wind_gen  = pd.Series(0.0, index=n.snapshots)
    solar_gen = pd.Series(0.0, index=n.snapshots)
    for gen in n.generators.index:
        carrier = n.generators.at[gen, "carrier"]
        if "wind"  in carrier: wind_gen  += n.generators_t.p[gen]
        elif "solar" in carrier: solar_gen += n.generators_t.p[gen]
    wind_weekly  = wind_gen.resample(freq).mean()  / 1e3
    solar_weekly = solar_gen.resample(freq).mean() / 1e3

    # Storage SOC
    if n.storage_units_t.state_of_charge.empty:
        bat_soc = pd.Series(0.0, index=wind_weekly.index)
        hyd_soc = pd.Series(0.0, index=wind_weekly.index)
        no_storage = True
    else:
        soc      = n.storage_units_t.state_of_charge
        bat_cols = [c for c in soc.columns if "battery"  in c.lower()]
        hyd_cols = [c for c in soc.columns if "hydrogen" in c.lower()]
        bat_soc  = soc[bat_cols].sum(axis=1).resample(freq).mean()/1e3 if bat_cols else pd.Series(0.0, index=wind_weekly.index)
        hyd_soc  = soc[hyd_cols].sum(axis=1).resample(freq).mean()/1e3 if hyd_cols else pd.Series(0.0, index=wind_weekly.index)
        no_storage = bat_soc.max() < 0.01 and hyd_soc.max() < 0.01

    fig, axes = plt.subplots(3, 1, figsize=(18, 14), sharex=True)

    # Panel 1: Wind + Solar
    ax = axes[0]
    ax.fill_between(wind_weekly.index,  wind_weekly,  color=COLORS["onshore_wind"], alpha=0.7, label="Wind total")
    ax.fill_between(solar_weekly.index, solar_weekly, color=COLORS["solar"],        alpha=0.7, label="Solar")
    ax.set_ylabel("Generation (GW, weekly avg)", fontsize=12)
    ax.set_title("Wind & Solar Generation", fontweight="bold", fontsize=13)
    ax.legend(loc="upper right", fontsize=12, framealpha=0.9)
    ax.grid(alpha=0.3); ax.tick_params(labelsize=11)

    # Panel 2: Battery
    ax = axes[1]
    if no_storage and "baseline" in label.lower():
        ax.text(0.5, 0.5, "Battery storage not used in Baseline\n"
                "(Coal provides all balancing — storage has no economic role)",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=12, color=COLORS["battery"],
                bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.8))
    else:
        bat_soc.plot(ax=ax, color=COLORS["battery"], linewidth=1.5, label="Battery SOC")
        ax.fill_between(bat_soc.index, bat_soc, alpha=0.3, color=COLORS["battery"])
        ax.legend(loc="upper right", fontsize=12, framealpha=0.9)
    ax.set_ylabel("GWh (weekly avg)", fontsize=12)
    ax.set_title("Battery Storage – State of Charge", fontweight="bold", fontsize=13)
    ax.grid(alpha=0.3); ax.tick_params(labelsize=11)

    # Panel 3: Hydrogen
    ax = axes[2]
    if no_storage and "baseline" in label.lower():
        ax.text(0.5, 0.5, "Hydrogen storage not used in Baseline\n"
                "(Coal eliminates the need for seasonal storage entirely)",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=12, color=COLORS["hydrogen"],
                bbox=dict(boxstyle="round", facecolor="#f0e6ff", alpha=0.8))
    else:
        hyd_soc.plot(ax=ax, color=COLORS["hydrogen"], linewidth=1.5, label="Hydrogen SOC")
        ax.fill_between(hyd_soc.index, hyd_soc, alpha=0.3, color=COLORS["hydrogen"])
        ax.legend(loc="upper right", fontsize=12, framealpha=0.9)
    ax.set_ylabel("GWh (weekly avg)", fontsize=12)
    ax.set_title("Hydrogen Storage – State of Charge", fontweight="bold", fontsize=13)
    ax.grid(alpha=0.3); ax.tick_params(labelsize=11)

    fig.suptitle(f"Denmark – Generation & Storage Levels: {label}",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    safe_label = label.lower().replace(" ", "_").replace("₂","2")
    save(fig, f"15_storage_{safe_label}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 16: Cost Summary — logically grouped, descending within groups
# ═══════════════════════════════════════════════════════════════════════════════
def plot_16_cost_summary():
    print("\n[16] Cost Summary")

    # Grouped logically: Reference first, then sensitivities by category
    groups = [
        ("── Reference ──────────────────────────────────────", None, None),
        ("Baseline",          "02_baseline.nc",                  "#636363"),
        ("Zero CO₂",          "04_zero_co2.nc",                  "#41ab5d"),
        ("── Grid Sensitivity ───────────────────────────────", None, None),
        ("Grid – Full expand","05_grid_full_expansion.nc",       "#2171b5"),
        ("Grid – 1GW/line",   "06_grid_max_1GW.nc",             "#6baed6"),
        ("Grid – Autarky",    "07_grid_autarky.nc",             "#d94801"),
        ("── Solar CAPEX ────────────────────────────────────", None, None),
        ("Solar CAPEX 100%",  "08_solar_capex_100pct.nc",       "#f9d71c"),
        ("Solar CAPEX 50%",   "10_solar_capex_50pct.nc",        "#f9d71c"),
        ("Solar CAPEX 0%",    "12_solar_capex_0pct.nc",         "#f9d71c"),
        ("── Wind CAPEX ─────────────────────────────────────", None, None),
        ("Wind CAPEX 100%",   "13_wind_capex_100pct.nc",        "#74c476"),
        ("Wind CAPEX 50%",    "15_wind_capex_50pct.nc",         "#74c476"),
        ("Wind CAPEX 0%",     "17_wind_capex_0pct.nc",          "#74c476"),
        ("── Battery CAPEX ──────────────────────────────────", None, None),
        ("Battery 100%",      "18_battery_capex_100pct.nc",     "#d94801"),
        ("Battery 0%",        "22_battery_capex_0pct.nc",       "#d94801"),
        ("── Nuclear ────────────────────────────────────────", None, None),
        ("Nuclear 2,500 €/kW","27_nuclear_2500_eur_per_kw.nc",  "#a1d99b"),
        ("Nuclear 5,000 €/kW","28_nuclear_5000_eur_per_kw.nc",  "#a1d99b"),
        ("Nuclear 10,000 €/kW","30_nuclear_10000_eur_per_kw.nc","#a1d99b"),
        ("── CO₂ Pathway ────────────────────────────────────", None, None),
        ("CO₂ reduction 0%",  "50_co2_reduction_0pct.nc",       "#41ab5d"),
        ("CO₂ reduction 20%", "51_co2_reduction_20pct.nc",      "#41ab5d"),
        ("CO₂ reduction 60%", "53_co2_reduction_60pct.nc",      "#41ab5d"),
        ("CO₂ reduction 95%", "55_co2_reduction_95pct.nc",      "#41ab5d"),
        ("CO₂ reduction 100%","56_co2_reduction_100pct.nc",     "#41ab5d"),
    ]

    labels, values, clrs = [], [], []
    for label, fname, clr in groups:
        if fname is None:
            # Section divider — add as empty bar
            labels.append(label); values.append(0); clrs.append("white")
            continue
        try:
            n = load(fname); obj = get_objective(n)
            if obj is not None:
                labels.append(label); values.append(obj); clrs.append(clr)
        except: pass

    fig, ax = plt.subplots(figsize=(16, 13))
    bars = ax.barh(labels, values, color=clrs, edgecolor="white", height=0.7)
    for bar, val, lbl in zip(bars, values, labels):
        if val > 0:
            ax.text(val + 0.05, bar.get_y() + bar.get_height()/2,
                    f"{val:.2f} B€", va="center", fontsize=10)
        if val == 0 and "──" in lbl:
            ax.axhline(y=bar.get_y() + bar.get_height()/2,
                       color="#cccccc", linewidth=0.8, linestyle="--")

    ax.set_xlabel("Total System Cost (Billion €/year)", fontsize=13)
    ax.set_title("Denmark – System Cost Overview: All Scenarios\n"
                 "Grouped by scenario category",
                 fontsize=14, fontweight="bold")
    ax.grid(alpha=0.3, axis="x")
    ax.invert_yaxis()
    ax.tick_params(labelsize=10)
    ax.set_xlim(0, max(v for v in values if v > 0) * 1.15)
    plt.tight_layout()
    save(fig, "16_cost_summary_descending")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 17: Weather Years (if available)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_17_weather_years():
    print("\n[17] Weather Years")
    year_files = {}
    for year in [2012, 2013, 2014]:
        for fname in [f"61_weather_year_{year}.nc", f"weather_year_{year}.nc"]:
            try: load(fname); year_files[year] = fname; break
            except: pass
    if len(year_files) < 2:
        print("  Not enough weather year scenarios — skipping"); return

    years = sorted(year_files.keys())
    costs, solar, wind, bat = [], [], [], []
    for yr in years:
        n = load(year_files[yr]); obj = get_objective(n)
        if obj is None: continue
        costs.append(obj)
        caps, stor = get_caps(n)
        solar.append(caps.get("solar",0))
        wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
        bat.append(stor.get("battery",0))

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].bar(years, costs,
                color=[COLORS["offshore_wind"],COLORS["onshore_wind"],COLORS["solar"]][:len(years)],
                edgecolor="white")
    for yr, c in zip(years, costs):
        axes[0].text(yr, c+0.02, f"{c:.2f}B€", ha="center", fontsize=11)
    axes[0].set_xlabel("Weather Year", fontsize=12); axes[0].set_ylabel("System Cost (B€/year)", fontsize=12)
    axes[0].set_title("System Cost by Weather Year", fontweight="bold"); axes[0].grid(alpha=0.3, axis="y")

    x = np.arange(len(years)); w = 0.25
    axes[1].bar(x-w,   solar, w, color=COLORS["solar"],        label="Solar",      edgecolor="white")
    axes[1].bar(x,     wind,  w, color=COLORS["onshore_wind"], label="Wind total", edgecolor="white")
    axes[1].bar(x+w,   bat,   w, color=COLORS["battery"],      label="Battery",    edgecolor="white")
    axes[1].set_xticks(x); axes[1].set_xticklabels(years, fontsize=11)
    axes[1].set_xlabel("Weather Year", fontsize=12); axes[1].set_ylabel("Installed Capacity (GW)", fontsize=12)
    axes[1].set_title("Capacity Mix by Weather Year", fontweight="bold")
    axes[1].legend(fontsize=11); axes[1].grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Sensitivity 5: Weather Year Variations", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "17_sensitivity_weather_years")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 18: Tech Years
# ═══════════════════════════════════════════════════════════════════════════════
def plot_18_tech_years():
    print("\n[18] Tech Years")
    tech_years = [2020, 2025, 2030, 2040, 2050]
    year_files = {}
    for yr in tech_years:
        for fname in [f"66_tech_year_{yr}.nc", f"67_tech_year_{yr}.nc",
                      f"68_tech_year_{yr}.nc", f"69_tech_year_{yr}.nc",
                      f"70_tech_year_{yr}.nc"]:
            try: load(fname); year_files[yr] = fname; break
            except: pass
    if len(year_files) < 2:
        print("  Not enough tech year scenarios — skipping"); return

    years = sorted(year_files.keys())
    costs, solar, wind, bat = [], [], [], []
    for yr in years:
        n = load(year_files[yr]); obj = get_objective(n)
        if obj is None: continue
        costs.append(obj)
        caps, stor = get_caps(n)
        solar.append(caps.get("solar",0))
        wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
        bat.append(stor.get("battery",0))

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(years, costs, "o-", color=COLORS["offshore_wind"],
                 linewidth=2.5, markersize=9, markeredgecolor="black")
    axes[0].set_xlabel("Technology Cost Year", fontsize=12)
    axes[0].set_ylabel("System Cost (B€/year)", fontsize=12)
    axes[0].set_title("System Cost vs Technology Year", fontweight="bold"); axes[0].grid(alpha=0.3)
    for x, y in zip(years, costs):
        axes[0].annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=10, ha="center")

    axes[1].plot(years, solar, "o-", color=COLORS["solar"],        linewidth=2, markersize=8, label="Solar")
    axes[1].plot(years, wind,  "s-", color=COLORS["onshore_wind"], linewidth=2, markersize=8, label="Wind total")
    axes[1].plot(years, bat,   "^-", color=COLORS["battery"],      linewidth=2, markersize=8, label="Battery")
    axes[1].set_xlabel("Technology Cost Year", fontsize=12)
    axes[1].set_ylabel("Installed Capacity (GW)", fontsize=12)
    axes[1].set_title("Capacity Mix vs Technology Year", fontweight="bold")
    axes[1].legend(fontsize=11); axes[1].grid(alpha=0.3)

    fig.suptitle("Denmark – Sensitivity 6: Technology Cost Year Variations",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "18_sensitivity_tech_years")


# ═══════════════════════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("Denmark Energy Model – Generating all plots")
    print("=" * 60)

    plot_00_base_scenario()
    plot_01_mix()
    plot_02_capacities()
    plot_03_grid()
    plot_03b_annual()
    plot_04_solar_capex()
    plot_05_wind_capex()
    plot_06_battery_capex()
    plot_07_transmission_capex()
    plot_08_nuclear()
    plot_09_nuclear_grid()
    plot_10_solar_potential()
    plot_11_onshore_potential()
    plot_12_all_renewables()
    plot_13_co2_pathway()
    plot_14_dispatch("04_zero_co2.nc",  "Zero CO2")
    plot_14_dispatch("02_baseline.nc",  "Baseline")
    plot_15_storage("04_zero_co2.nc",   "Zero CO2")
    plot_15_storage("02_baseline.nc",   "Baseline")
    plot_16_cost_summary()
    plot_17_weather_years()
    plot_18_tech_years()

    print("\n" + "=" * 60)
    print(f"✓ All plots saved to {OUT_DIR}/")
    print("=" * 60)