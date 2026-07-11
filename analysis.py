"""
analysis.py – Final complete plotting script for Denmark Energy Model
Covers all required visualisations from the assignment brief.
Run from project root: python analysis.py
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

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11,
    "xtick.labelsize": 10, "ytick.labelsize": 10,
    "legend.fontsize": 10, "figure.titlesize": 14,
})

COLORS = {
    "solar": "#f9d71c", "onshore_wind": "#74c476", "offshore_wind": "#2171b5",
    "battery": "#d94801", "hydrogen": "#756bb1", "coal": "#252525",
    "gas": "#fd8d3c", "oil": "#969696", "biomass": "#41ab5d",
    "hydro": "#6baed6", "nuclear": "#a1d99b", "transmission": "#636363",
}

def color(c):
    for k, v in COLORS.items():
        if k in str(c).lower(): return v
    return "#aaaaaa"

def load(f): return pypsa.Network(f"{NET_DIR}/{f}")

def get_obj(n):
    try: return float(n.objective) / 1e9 if n.objective else None
    except: return None

def gen_mix(n):
    w = n.snapshot_weightings.generators
    return (n.generators_t.p.mul(w, axis=0).sum()
            .groupby(n.generators.carrier).sum() / 1e6)

def get_caps(n):
    return (n.generators.groupby("carrier")["p_nom_opt"].sum() / 1e3,
            n.storage_units.groupby("carrier")["p_nom_opt"].sum() / 1e3)

def save(fig, name):
    fig.savefig(f"{OUT_DIR}/{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {name}.png")

def safe_load(files):
    """Load sensitivity data, skip missing/failed networks."""
    pcts, costs, caps_l, stor_l, nets = [], [], [], [], []
    for pct in sorted(files.keys(), reverse=True):
        try:
            n = load(files[pct]); obj = get_obj(n)
            if obj is None: continue
            pcts.append(pct); costs.append(obj)
            c, s = get_caps(n); caps_l.append(c); stor_l.append(s); nets.append(n)
        except Exception as e:
            print(f"    ⚠ {files[pct]}: {e}")
    return pcts, costs, caps_l, stor_l, nets


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 00a: Baseline — Mix, Capacities, Costs
# ═══════════════════════════════════════════════════════════════════════════════
def plot_00a():
    print("\n[00a] Baseline Overview")
    n = load("02_baseline.nc")
    w = n.snapshot_weightings.generators
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))

    # Pie
    ax = axes[0]
    mix = gen_mix(n); mix = mix[mix > 0].sort_values(ascending=False)
    exp = [0.08 if v < 2 else 0 for v in mix.values]
    _, _, at = ax.pie(mix, labels=None, autopct="%1.1f%%",
                      colors=[color(c) for c in mix.index],
                      explode=exp, startangle=90, counterclock=False, pctdistance=0.78)
    for a in at: a.set_fontsize(9)
    ax.legend(mix.index, loc="lower center", fontsize=9,
              bbox_to_anchor=(0.5, -0.18), ncol=3)
    ax.set_title(f"Electricity Mix\n{mix.sum():.1f} TWh/year", fontweight="bold")

    # Capacities
    ax = axes[1]
    caps, stor = get_caps(n)
    ac = pd.concat([caps, stor]); ac = ac[ac > 0.001].sort_values(ascending=False)
    ax.bar(range(len(ac)), ac.values, color=[color(c) for c in ac.index], edgecolor="white")
    ax.set_xticks(range(len(ac)))
    ax.set_xticklabels(ac.index, rotation=40, ha="right", fontsize=9)
    ax.set_ylabel("Capacity (GW)"); ax.set_title("Installed Capacities", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")

    # Costs
    ax = axes[2]
    cb = {}
    for g in n.generators.index:
        car = n.generators.at[g, "carrier"]
        cc = n.generators.at[g, "capital_cost"] * n.generators.at[g, "p_nom_opt"]
        mc = (n.generators_t.p[g] * w * n.generators.at[g, "marginal_cost"]).sum()
        cb[car] = cb.get(car, 0) + (cc + mc) / 1e9
    cs = pd.Series(cb); cs = cs[cs > 0].sort_values(ascending=False)
    ax.bar(range(len(cs)), cs.values, color=[color(c) for c in cs.index], edgecolor="white")
    ax.set_xticks(range(len(cs)))
    ax.set_xticklabels(cs.index, rotation=40, ha="right", fontsize=9)
    ax.set_ylabel("Cost (B€/year)")
    ax.set_title(f"Cost by Technology\nTotal: {get_obj(n):.2f} B€/year", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Baseline Scenario (1/2): Mix, Capacities & Costs",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "00a_baseline_overview")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 00b: Baseline — Dispatch + Regional Generation
# ═══════════════════════════════════════════════════════════════════════════════
def plot_00b():
    print("\n[00b] Baseline Dispatch + Regional")
    n = load("02_baseline.nc")
    w = n.snapshot_weightings.generators
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    # Dispatch winter week
    ax = axes[0]
    start = "2012-01-09"
    snap = n.snapshots[(n.snapshots >= start) &
                       (n.snapshots < str(pd.Timestamp(start) + pd.Timedelta("7D")))]
    gen_t = n.generators_t.p.loc[snap].copy()
    gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
    gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
    load_ts = n.loads_t.p_set.loc[snap].sum(axis=1) / 1e3
    bot = pd.Series(0.0, index=snap)
    for car in gen_t.columns:
        if gen_t[car].sum() > 0:
            ax.fill_between(snap, bot, bot + gen_t[car],
                            label=car, color=color(car), alpha=0.85)
            bot += gen_t[car]
    load_ts.plot(ax=ax, color="black", lw=2, label="Load", zorder=10)
    ax.set_title("Dispatch — Winter Week (Jan 9–16)", fontweight="bold")
    ax.set_ylabel("Power (GW)")
    ax.legend(loc="upper left", fontsize=9, ncol=3, framealpha=0.9)
    ax.grid(alpha=0.2)

    # Regional generation
    ax = axes[1]
    rg = {}
    for g in n.generators.index:
        bus = n.generators.at[g, "bus"]; car = n.generators.at[g, "carrier"]
        mwh = (n.generators_t.p[g] * w).sum() / 1e6
        if bus not in rg: rg[bus] = {}
        rg[bus][car] = rg[bus].get(car, 0) + mwh
    regions = list(rg.keys())
    carriers = [c for c in sorted(set(c for r in rg.values() for c in r))
                if any(rg[r].get(c, 0) > 0 for r in regions)]
    bot_arr = np.zeros(len(regions))
    for car in carriers:
        vals = [rg[r].get(car, 0) for r in regions]
        ax.bar(regions, vals, bottom=bot_arr, label=car,
               color=color(car), edgecolor="white")
        bot_arr += np.array(vals)
    ax.set_xticklabels(regions, rotation=35, ha="right", fontsize=10)
    ax.set_ylabel("Generation (TWh/year)")
    ax.set_title("Annual Generation by Region", fontweight="bold")
    ax.legend(fontsize=9, ncol=2, loc="upper right", framealpha=0.9)
    ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Baseline Scenario (2/2): Dispatch & Regional Generation",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "00b_baseline_dispatch")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 01: Mix Baseline vs Zero CO2
# ═══════════════════════════════════════════════════════════════════════════════
def plot_01():
    print("\n[01] Mix Baseline vs Zero CO2")
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    for ax, (fname, label) in zip(axes, [
            ("02_baseline.nc", "Baseline (no limit)"),
            ("04_zero_co2.nc", "Zero CO₂")]):
        n = load(fname); mix = gen_mix(n); mix = mix[mix > 0].sort_values(ascending=False)
        exp = [0.08 if v < 2 else 0 for v in mix.values]
        _, _, at = ax.pie(mix, labels=None, autopct="%1.1f%%",
                          colors=[color(c) for c in mix.index],
                          explode=exp, startangle=90, counterclock=False, pctdistance=0.78)
        for a in at: a.set_fontsize(10)
        ax.legend(mix.index, loc="lower center", fontsize=10,
                  bbox_to_anchor=(0.5, -0.18), ncol=3)
        ax.set_title(f"{label}\n{mix.sum():.1f} TWh/year | {get_obj(n):.2f} B€/year",
                     fontsize=12, fontweight="bold")
    fig.suptitle("Denmark – Electricity Mix: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "01_mix_baseline_vs_zero_co2")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 02: Capacities Baseline vs Zero CO2
# ═══════════════════════════════════════════════════════════════════════════════
def plot_02():
    print("\n[02] Capacities")
    n_b = load("02_baseline.nc"); n_z = load("04_zero_co2.nc")
    all_c = set()
    data = {}
    for lbl, n in [("Baseline", n_b), ("Zero CO₂", n_z)]:
        caps, stor = get_caps(n)
        comb = pd.concat([caps, stor]); comb = comb[comb > 0.01]
        data[lbl] = comb; all_c |= set(comb.index)
    all_c = sorted(all_c)
    df = pd.DataFrame({l: [data[l].get(c, 0) for c in all_c]
                       for l in data}, index=all_c)
    df = df[df.sum(axis=1) > 0.01]

    fig, ax = plt.subplots(figsize=(14, 7))
    x = np.arange(len(df)); w = 0.35
    ax.bar(x - w/2, df["Baseline"], w, label="Baseline",
           color=[color(c) for c in df.index], alpha=0.5, edgecolor="white")
    ax.bar(x + w/2, df["Zero CO₂"], w, label="Zero CO₂",
           color=[color(c) for c in df.index], alpha=1.0, edgecolor="white")
    ax.set_xticks(x); ax.set_xticklabels(df.index, rotation=35, ha="right")
    ax.set_ylabel("Capacity (GW)"); ax.legend(fontsize=12)
    ax.set_title("Denmark – Installed Capacities: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    save(fig, "02_capacities_comparison")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 03: Annual Generation + Demand
# ═══════════════════════════════════════════════════════════════════════════════
def plot_03():
    print("\n[03] Annual Generation + Demand")
    fig, axes = plt.subplots(2, 1, figsize=(20, 12), sharex=True)
    for ax, (fname, label) in zip(axes, [
            ("02_baseline.nc", "Baseline"),
            ("04_zero_co2.nc", "Zero CO₂")]):
        try: n = load(fname)
        except: continue
        gen_t = n.generators_t.p.copy()
        gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
        gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
        gw = gen_t.resample("W").mean()
        lw = n.loads_t.p_set.sum(axis=1).resample("W").mean() / 1e3
        bot = pd.Series(0.0, index=gw.index)
        for car in gw.columns:
            if gw[car].sum() > 0:
                ax.fill_between(gw.index, bot, bot + gw[car],
                                label=car, color=color(car), alpha=0.85)
                bot += gw[car]
        lw.plot(ax=ax, color="black", lw=2.5, label="Demand", zorder=10, ls="--")
        ax.set_ylabel("Power (GW, weekly avg)", fontsize=12)
        ax.set_title(label, fontweight="bold", fontsize=13)
        ax.legend(loc="upper left", fontsize=10, ncol=5, framealpha=0.9)
        ax.grid(alpha=0.2)
    fig.suptitle("Denmark – Annual Generation & Demand: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "03_annual_generation_demand")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 04: Capacity Factors per Region (Solar + Wind)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_04():
    print("\n[04] Capacity Factors per Region")
    n = load("04_zero_co2.nc")
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    titles = {"solar": "Solar PV", "onshore_wind": "Onshore Wind", "offshore_wind": "Offshore Wind"}

    for ax, (carrier, title) in zip(axes, titles.items()):
        gens = [g for g in n.generators.index
                if n.generators.at[g, "carrier"] == carrier
                and g in n.generators_t.p_max_pu.columns]
        if not gens:
            ax.text(0.5, 0.5, f"No data for {title}", transform=ax.transAxes,
                    ha="center", va="center", fontsize=12)
            ax.set_title(title, fontweight="bold"); continue

        cf_data = {}
        for g in gens:
            bus = n.generators.at[g, "bus"]
            cf_monthly = n.generators_t.p_max_pu[g].resample("ME").mean()
            cf_data[bus] = cf_monthly

        df = pd.DataFrame(cf_data)
        df.index = df.index.strftime("%b")
        df.plot(ax=ax, marker="o", markersize=5, linewidth=1.8)
        ax.set_title(f"{title}\nMonthly avg. capacity factor", fontweight="bold")
        ax.set_ylabel("Capacity Factor"); ax.set_xlabel("")
        ax.legend(title="Region", fontsize=9, loc="best")
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 1)
        ax.tick_params(axis="x", rotation=45)

    fig.suptitle("Denmark – Capacity Factors by Region: Solar & Wind",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "04_capacity_factors_per_region")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 05: CO2 Shadow Price across scenarios
# ═══════════════════════════════════════════════════════════════════════════════
def plot_05():
    print("\n[05] CO2 Shadow Price")
    co2_files = {
        0:   "50_co2_reduction_0pct.nc",
        20:  "51_co2_reduction_20pct.nc",
        40:  "52_co2_reduction_40pct.nc",
        60:  "53_co2_reduction_60pct.nc",
        80:  "54_co2_reduction_80pct.nc",
        95:  "55_co2_reduction_95pct.nc",
        100: "56_co2_reduction_100pct.nc",
    }
    pcts, shadow_prices, costs = [], [], []
    for pct, fname in sorted(co2_files.items()):
        try:
            n = load(fname)
            obj = get_obj(n)
            if obj is None: continue
            # Get CO2 shadow price from global constraint dual
            if "co2_limit" in n.global_constraints.index:
                mu = n.global_constraints.at["co2_limit", "mu"]
            else:
                mu = 0.0
            pcts.append(pct); shadow_prices.append(abs(mu)); costs.append(obj)
        except Exception as e:
            print(f"    ⚠ {fname}: {e}")

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    ax = axes[0]
    # Check if we have any non-zero shadow prices
    nonzero = [(p, sp) for p, sp in zip(pcts, shadow_prices) if sp > 0]
    if nonzero:
        # Use log scale if values span many orders of magnitude
        bars = ax.bar(pcts, shadow_prices, color=COLORS["coal"], edgecolor="white", width=12)
        if max(shadow_prices) / max(0.01, min(sp for sp in shadow_prices if sp > 0)) > 100:
            ax.set_yscale("log")
            ax.set_ylabel("CO₂ Shadow Price (€/tCO₂, log scale)", fontsize=12)
        else:
            ax.set_ylabel("CO₂ Shadow Price (€/tCO₂)", fontsize=12)
        for bar, val in zip(bars, shadow_prices):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.05,
                        f"{val:.0f}", ha="center", fontsize=9)
    else:
        # Shadow prices not stored — show marginal cost proxy instead
        # Use system cost difference as marginal abatement cost proxy
        if len(pcts) >= 2 and len(costs) >= 2:
            mac = []
            for i in range(1, len(pcts)):
                delta_co2_pct = pcts[i] - pcts[i-1]
                delta_cost    = (costs[i] - costs[i-1]) * 1e9  # B€ → €
                # rough CO2 in baseline (from first scenario coal generation)
                try:
                    n0 = load(co2_files[pcts[0]])
                    w0 = n0.snapshot_weightings.generators
                    coal_gen = sum(
                        (n0.generators_t.p[g] * w0).sum()
                        for g in n0.generators.index
                        if n0.generators.at[g, "carrier"] == "coal"
                    )  # MWh
                    baseline_co2_t = coal_gen * 0.34  # tCO2/MWh_th approx
                    delta_co2_t = baseline_co2_t * delta_co2_pct / 100
                    mac.append(delta_cost / max(delta_co2_t, 1))
                except:
                    mac.append(0)
            mid_pcts = [(pcts[i]+pcts[i-1])/2 for i in range(1, len(pcts))]
            ax.bar(mid_pcts, mac, color=COLORS["coal"], edgecolor="white", width=12)
            ax.set_ylabel("Marginal Abatement Cost (€/tCO₂, approx.)", fontsize=11)
        else:
            ax.text(0.5, 0.5, "Shadow price not stored\nin network files",
                    transform=ax.transAxes, ha="center", va="center", fontsize=12,
                    bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.9))
            ax.set_ylabel("CO₂ Shadow Price (€/tCO₂)", fontsize=12)

    ax.set_xlabel("CO₂ Reduction (%)", fontsize=12)
    ax.set_title("CO₂ Shadow / Marginal Abatement Cost", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")

    ax = axes[1]
    ax.plot(pcts, costs, "o-", color="#d94801", lw=2.5, markersize=9,
            markeredgecolor="black")
    ax.set_xlabel("CO₂ Reduction (%)", fontsize=12)
    ax.set_ylabel("Total System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost vs CO₂ Reduction Target", fontweight="bold")
    ax.grid(alpha=0.3)
    for x, y in zip(pcts, costs):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, 10), fontsize=9, ha="center")

    fig.suptitle("Denmark – CO₂ Shadow Price & System Cost",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "05_co2_shadow_price")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 06: Price Duration Curve
# ═══════════════════════════════════════════════════════════════════════════════
def plot_06():
    print("\n[06] Price Duration Curve")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, (fname, label, c) in zip(axes, [
            ("02_baseline.nc", "Baseline", "#252525"),
            ("04_zero_co2.nc", "Zero CO₂", "#2171b5")]):
        try: n = load(fname)
        except: continue
        if not hasattr(n.buses_t, "marginal_price") or n.buses_t.marginal_price.empty:
            ax.text(0.5, 0.5, "No marginal price data available",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11)
            ax.set_title(f"Price Duration Curve – {label}", fontweight="bold"); continue

        prices = n.buses_t.marginal_price
        duration = np.linspace(0, 100, len(prices))
        for col in prices.columns:
            sorted_p = np.sort(prices[col].values)[::-1]
            # Clip extreme outliers to 99th percentile for readability
            p99 = np.percentile(sorted_p, 99)
            p01 = np.percentile(sorted_p, 1)
            sorted_p_clipped = np.clip(sorted_p, p01, p99)
            ax.plot(duration, sorted_p_clipped, linewidth=1.5, alpha=0.8, label=col)
        ax.set_xlabel("% of time", fontsize=12)
        ax.set_ylabel("Electricity Price (€/MWh)", fontsize=12)
        
        ax.legend(title="Region", fontsize=9, loc="upper right")
        ax.set_xlim(0, 100); ax.grid(alpha=0.3)
        ax.axhline(y=0, color="red", lw=0.8, ls="--", alpha=0.5, label="Zero price")

    fig.suptitle("Denmark – Price Duration Curves: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "06_price_duration_curve")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 07: Grid Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_07():
    print("\n[07] Grid Sensitivity")
    scenarios = {"Full expansion": "05_grid_full_expansion.nc",
                 "Max 1 GW/line": "06_grid_max_1GW.nc",
                 "Autarky":       "07_grid_autarky.nc"}
    costs = {}; mixes = {}
    for lbl, f in scenarios.items():
        try:
            n = load(f); obj = get_obj(n)
            if obj: costs[lbl] = obj
            mixes[lbl] = gen_mix(n)
        except: pass

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    ax = axes[0]
    s = pd.Series(costs).dropna()
    bars = ax.bar(s.index, s.values,
                  color=["#2171b5", "#74c476", "#d94801"][:len(s)], edgecolor="white")
    for bar, val in zip(bars, s.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val:.2f}B€", ha="center", fontsize=11)
    ax.set_ylabel("System Cost (B€/year)"); ax.set_title("System Cost", fontweight="bold")
    ax.grid(alpha=0.3, axis="y")
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")

    ax = axes[1]
    all_c = sorted(set().union(*[m.index for m in mixes.values()]))
    df = pd.DataFrame({l: [mixes[l].get(c, 0) for c in all_c]
                       for l in mixes}, index=all_c)
    df = df[df.sum(axis=1) > 0]
    bot = np.zeros(len(mixes))
    for car in df.index:
        ax.bar(list(mixes.keys()), df.loc[car].values, bottom=bot,
               label=car, color=color(car), edgecolor="white")
        bot += df.loc[car].values
    ax.set_ylabel("Annual Generation (TWh)"); ax.set_title("Generation Mix", fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.suptitle("Denmark – Grid Expansion Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "07_grid_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Sensitivity with background bars
# ═══════════════════════════════════════════════════════════════════════════════
def sens_plot(title, fname, files, vary, bg, xlabel, invert=True):
    vp, costs, caps_l, stor_l, _ = safe_load(files)
    if not vp: print(f"  No data for {title}"); return

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    vc = color(vary)
    ax.plot(vp, costs, "o-", color=vc, lw=2.5, markersize=9, markeredgecolor="black")
    ax.set_xlabel(xlabel, fontsize=12); ax.set_ylabel("System Cost (B€/year)", fontsize=12)
    ax.set_title("System Cost", fontweight="bold")
    if invert: ax.invert_xaxis()
    ax.grid(alpha=0.3)
    for x, y in zip(vp, costs):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, 10), fontsize=9, ha="center")

    ax = axes[1]
    xp = np.arange(len(vp)); bw = 0.15
    offs = np.linspace(-bw*len(bg)/2, bw*len(bg)/2, len(bg))
    for i, bgc in enumerate(bg):
        bgv = [c.get(bgc, s.get(bgc, 0)) for c, s in zip(caps_l, stor_l)]
        ax.bar(xp + offs[i], bgv, bw, color=color(bgc), alpha=0.4,
               label=f"{bgc}", edgecolor="white")
    vv = [c.get(vary, s.get(vary, 0)) for c, s in zip(caps_l, stor_l)]
    ax.plot(xp, vv, "o-", color=vc, lw=2.5, markersize=9,
            markeredgecolor="black", label=f"{vary} (line)", zorder=10)
    ax.set_xticks(xp); ax.set_xticklabels([f"{p}%" for p in vp])
    ax.set_xlabel(xlabel, fontsize=12); ax.set_ylabel("Capacity (GW)", fontsize=12)
    ax.set_title("Varied technology (line) + Others (bars)", fontweight="bold")
    ax.legend(fontsize=9, ncol=2); ax.grid(alpha=0.3, axis="y")

    fig.suptitle(f"Denmark – {title}", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, fname)


# ═══════════════════════════════════════════════════════════════════════════════
# PLOTS 08–12: CAPEX Sensitivities
# ═══════════════════════════════════════════════════════════════════════════════
def plot_08(): print("\n[08] Solar CAPEX"); sens_plot(
    "Solar CAPEX Sensitivity", "08_solar_capex",
    {100:"08_solar_capex_100pct.nc", 75:"09_solar_capex_75pct.nc",
     50:"10_solar_capex_50pct.nc", 25:"11_solar_capex_25pct.nc", 0:"12_solar_capex_0pct.nc"},
    "solar", ["onshore_wind","offshore_wind","battery"], "Solar CAPEX (% of base)")

def plot_09():
    print("\n[09] Wind CAPEX")
    files = {100:"13_wind_capex_100pct.nc", 75:"14_wind_capex_75pct.nc",
             50:"15_wind_capex_50pct.nc", 25:"16_wind_capex_25pct.nc", 0:"17_wind_capex_0pct.nc"}
    vp, costs, caps_l, stor_l, _ = safe_load(files)
    if not vp: return
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(vp, costs, "o-", color=COLORS["onshore_wind"], lw=2.5, markersize=9,
            markeredgecolor="black")
    ax.set_xlabel("Wind CAPEX (% of base)"); ax.set_ylabel("System Cost (B€/year)")
    ax.set_title("System Cost vs Wind CAPEX", fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(vp, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=9, ha="center")
    ax = axes[1]
    xp = np.arange(len(vp)); w = 0.2
    solar = [c.get("solar",0) for c in caps_l]
    on  = [c.get("onshore_wind",0) for c in caps_l]
    off = [c.get("offshore_wind",0) for c in caps_l]
    bat = [s.get("battery",0) for s in stor_l]
    ax.bar(xp-1.5*w, solar, w, color=COLORS["solar"],   alpha=0.4, label="Solar",   edgecolor="white")
    ax.bar(xp-0.5*w, bat,   w, color=COLORS["battery"], alpha=0.4, label="Battery", edgecolor="white")
    ax.plot(xp, on,  "o-", color=COLORS["onshore_wind"],  lw=2.5, markersize=8, label="Onshore Wind")
    ax.plot(xp, off, "s-", color=COLORS["offshore_wind"], lw=2.5, markersize=8, label="Offshore Wind")
    ax.set_xticks(xp); ax.set_xticklabels([f"{p}%" for p in vp])
    ax.set_xlabel("Wind CAPEX (% of base)"); ax.set_ylabel("Capacity (GW)")
    ax.set_title("Wind (lines) + Others (bars)", fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Denmark – Wind CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "09_wind_capex")

def plot_10():
    print("\n[10] Battery CAPEX")
    files = {100:"18_battery_capex_100pct.nc", 75:"19_battery_capex_75pct.nc",
             50:"20_battery_capex_50pct.nc", 25:"21_battery_capex_25pct.nc", 0:"22_battery_capex_0pct.nc"}
    vp, costs, caps_l, stor_l, _ = safe_load(files)
    if not vp: return
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(vp, costs, "o-", color=COLORS["battery"], lw=2.5, markersize=9,
            markeredgecolor="black")
    ax.set_xlabel("Battery CAPEX (% of base)"); ax.set_ylabel("System Cost (B€/year)")
    ax.set_title("System Cost vs Battery CAPEX", fontweight="bold")
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(vp, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=9, ha="center")
    ax = axes[1]
    xp = np.arange(len(vp)); w = 0.2
    bat = [s.get("battery",0) for s in stor_l]
    hyd = [s.get("hydrogen",0) for s in stor_l]
    wnd = [c.get("onshore_wind",0)+c.get("offshore_wind",0) for c in caps_l]
    sol = [c.get("solar",0) for c in caps_l]
    ax.bar(xp-0.5*w, wnd, w, color=COLORS["onshore_wind"], alpha=0.4, label="Wind",  edgecolor="white")
    ax.bar(xp+0.5*w, sol, w, color=COLORS["solar"],        alpha=0.4, label="Solar", edgecolor="white")
    ax.plot(xp, bat, "o-", color=COLORS["battery"],  lw=2.5, markersize=8, label="Battery")
    ax.plot(xp, hyd, "s-", color=COLORS["hydrogen"], lw=2.5, markersize=8, label="Hydrogen")
    ax.set_xticks(xp); ax.set_xticklabels([f"{p}%" for p in vp])
    ax.set_xlabel("Battery CAPEX (% of base)"); ax.set_ylabel("Capacity (GW)")
    ax.set_title("Storage (lines) + Renewables (bars)", fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Denmark – Battery CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "10_battery_capex")

def plot_11():
    print("\n[11] Transmission CAPEX")
    files = {100:"23_transmission_capex_100pct.nc", 75:"24_transmission_capex_75pct.nc",
             50:"25_transmission_capex_50pct.nc", 25:"26_transmission_capex_25pct.nc",
             0:"27_transmission_capex_0pct.nc"}
    vp, costs, _, _, nets = safe_load(files)
    trans = [n.links["p_nom_opt"].sum()/1e3 for n in nets]
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, yv, yl, t in zip(axes, [costs, trans],
                              ["System Cost (B€/year)", "Transmission Capacity (GW)"],
                              ["System Cost", "Transmission Capacity"]):
        ax.plot(vp, yv, "o-", color=COLORS["transmission"], lw=2.5, markersize=9,
                markeredgecolor="black")
        ax.set_xlabel("Transmission CAPEX (% of base)"); ax.set_ylabel(yl)
        ax.set_title(t, fontweight="bold"); ax.invert_xaxis(); ax.grid(alpha=0.3)
        for x, y in zip(vp, yv):
            ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                        xytext=(0,10), fontsize=9, ha="center")
    fig.suptitle("Denmark – Transmission CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "11_transmission_capex")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOTS 12–13: Potential Sensitivities
# ═══════════════════════════════════════════════════════════════════════════════
def plot_12(): print("\n[12] Solar Potential"); sens_plot(
    "Solar Potential Sensitivity", "12_solar_potential",
    {100:"31_solar_potential_100pct.nc", 75:"32_solar_potential_75pct.nc",
     50:"33_solar_potential_50pct.nc", 25:"34_solar_potential_25pct.nc", 0:"35_solar_potential_0pct.nc"},
    "solar", ["onshore_wind","offshore_wind","battery"], "Solar Potential (% of max)")

def plot_13(): print("\n[13] Onshore Wind Potential"); sens_plot(
    "Onshore Wind Potential Sensitivity", "13_onshore_potential",
    {100:"36_onshore_potential_100pct.nc", 75:"42_onshore_potential_75pct.nc",
     50:"43_onshore_potential_50pct.nc", 25:"44_onshore_potential_25pct.nc", 0:"45_onshore_potential_0pct.nc"},
    "onshore_wind", ["solar","offshore_wind","battery"], "Onshore Wind Potential (% of max)")

def plot_14():
    print("\n[14] All Renewables Potential")
    files = {100:"37_all_ren_potential_100pct.nc", 75:"38_all_ren_potential_75pct.nc",
             50:"39_all_ren_potential_50pct.nc", 25:"40_all_ren_potential_25pct.nc", 0:"41_all_ren_potential_0pct.nc"}
    vp, costs, caps_l, stor_l, _ = safe_load(files)
    if not vp: return
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    ax.plot(vp, costs, "o-", color="#41ab5d", lw=2.5, markersize=9, markeredgecolor="black")
    ax.set_xlabel("All Renewables Potential (% of max)"); ax.set_ylabel("System Cost (B€/year)")
    ax.set_title("System Cost", fontweight="bold"); ax.invert_xaxis(); ax.grid(alpha=0.3)
    for x, y in zip(vp, costs):
        ax.annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                    xytext=(0,10), fontsize=9, ha="center")
    ax = axes[1]
    xp = np.arange(len(vp)); w = 0.2
    sol = [c.get("solar",0) for c in caps_l]
    wnd = [c.get("onshore_wind",0)+c.get("offshore_wind",0) for c in caps_l]
    bat = [s.get("battery",0) for s in stor_l]
    hyd = [s.get("hydrogen",0) for s in stor_l]
    ax.bar(xp-0.5*w, bat, w, color=COLORS["battery"],  alpha=0.4, label="Battery",  edgecolor="white")
    ax.bar(xp+0.5*w, hyd, w, color=COLORS["hydrogen"], alpha=0.4, label="Hydrogen", edgecolor="white")
    ax.plot(xp, sol, "o-", color=COLORS["solar"],        lw=2.5, markersize=8, label="Solar")
    ax.plot(xp, wnd, "s-", color=COLORS["onshore_wind"], lw=2.5, markersize=8, label="Wind total")
    ax.set_xticks(xp); ax.set_xticklabels([f"{p}%" for p in vp])
    ax.set_xlabel("All Renewables Potential (% of max)"); ax.set_ylabel("Capacity (GW)")
    ax.set_title("Renewables (lines) + Storage (bars)", fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Denmark – All Renewables Potential Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "14_all_renewables_potential")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 15: Nuclear Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_15():
    print("\n[15] Nuclear Sensitivity")
    files = {2500:"27_nuclear_2500_eur_per_kw.nc", 5000:"28_nuclear_5000_eur_per_kw.nc",
             7500:"29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}
    vp, costs, nuc, solar, wind = [], [], [], [], []
    for p in sorted(files.keys()):
        try:
            n = load(files[p]); obj = get_obj(n)
            if obj is None: continue
            vp.append(p); costs.append(obj)
            caps, _ = get_caps(n)
            nuc.append(caps.get("nuclear",0)); solar.append(caps.get("solar",0))
            wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
        except: pass
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(vp, costs, "o-", color=COLORS["nuclear"], lw=2.5, markersize=9,
                 markeredgecolor="black")
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)"); axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Nuclear CAPEX", fontweight="bold"); axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    for x, y in zip(vp, costs):
        axes[0].annotate(f"{y:.2f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=9, ha="center")
    axes[1].plot(vp, nuc,   "o-", color=COLORS["nuclear"],       lw=2, markersize=8, label="Nuclear")
    axes[1].plot(vp, wind,  "s-", color=COLORS["offshore_wind"], lw=2, markersize=8, label="Wind total")
    axes[1].plot(vp, solar, "^-", color=COLORS["solar"],         lw=2, markersize=8, label="Solar")
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)"); axes[1].set_ylabel("Capacity (GW)")
    axes[1].set_title("Capacity Mix vs Nuclear CAPEX", fontweight="bold")
    axes[1].legend(fontsize=10); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    fig.suptitle("Denmark – Nuclear CAPEX Sensitivity", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "15_nuclear_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 16: Nuclear + Grid Combined
# ═══════════════════════════════════════════════════════════════════════════════
def plot_16():
    print("\n[16] Nuclear + Grid")
    ff = {2500:"27_nuclear_2500_eur_per_kw.nc", 5000:"28_nuclear_5000_eur_per_kw.nc",
          7500:"29_nuclear_7500_eur_per_kw.nc", 10000:"30_nuclear_10000_eur_per_kw.nc"}
    gf = {2500:"46_nuclear_2500eurkw_grid_1GW.nc", 5000:"47_nuclear_5000eurkw_grid_1GW.nc",
          7500:"48_nuclear_7500eurkw_grid_1GW.nc", 10000:"49_nuclear_10000eurkw_grid_1GW.nc"}
    vp, cf, cg, nf, ng = [], [], [], [], []
    for p in sorted(ff.keys()):
        try:
            n1=load(ff[p]); n2=load(gf[p])
            o1=get_obj(n1); o2=get_obj(n2)
            if o1 is None or o2 is None: continue
            vp.append(p); cf.append(o1); cg.append(o2)
            c1,_=get_caps(n1); c2,_=get_caps(n2)
            nf.append(c1.get("nuclear",0)); ng.append(c2.get("nuclear",0))
        except: pass
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(vp, cf, "o-", color=COLORS["nuclear"], lw=2, markersize=8, label="Baseline network")
    axes[0].plot(vp, cg, "s-", color=COLORS["battery"], lw=2, markersize=8, label="Max 1GW/line")
    axes[0].set_xlabel("Nuclear CAPEX (€/kW)"); axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("Cost: Baseline vs 1GW Grid", fontweight="bold")
    axes[0].legend(fontsize=10); axes[0].grid(alpha=0.3)
    axes[0].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    axes[1].plot(vp, nf, "o-", color=COLORS["nuclear"], lw=2, markersize=8, label="Baseline network")
    axes[1].plot(vp, ng, "s-", color=COLORS["battery"], lw=2, markersize=8, label="Max 1GW/line")
    axes[1].set_xlabel("Nuclear CAPEX (€/kW)"); axes[1].set_ylabel("Nuclear Capacity (GW)")
    axes[1].set_title("Nuclear Capacity", fontweight="bold")
    axes[1].legend(fontsize=10); axes[1].grid(alpha=0.3)
    axes[1].xaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{int(x):,}"))
    fig.suptitle("Denmark – Nuclear + Grid Expansion Combined", fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "16_nuclear_grid_combined")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 17: CO2 Pathway (split into 2 plots)
# ═══════════════════════════════════════════════════════════════════════════════
def plot_17():
    print("\n[17] CO2 Pathway")
    files = {0:"50_co2_reduction_0pct.nc", 20:"51_co2_reduction_20pct.nc",
             40:"52_co2_reduction_40pct.nc", 60:"53_co2_reduction_60pct.nc",
             80:"54_co2_reduction_80pct.nc", 95:"55_co2_reduction_95pct.nc",
             100:"56_co2_reduction_100pct.nc"}
    vp, costs, solar, wind, coal_gen, bat = [], [], [], [], [], []
    for pct in sorted(files.keys()):
        try:
            n = load(files[pct]); obj = get_obj(n)
            if obj is None: continue
            vp.append(pct); costs.append(obj)
            caps, stor = get_caps(n); mix = gen_mix(n)
            solar.append(caps.get("solar",0))
            wind.append(caps.get("onshore_wind",0)+caps.get("offshore_wind",0))
            coal_gen.append(mix.get("coal",0)); bat.append(stor.get("battery",0))
        except: pass

    # Plot 17a: Cost + Coal
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    axes[0].plot(vp, costs, "o-", color="#d94801", lw=2.5, markersize=10,
                 markeredgecolor="black")
    axes[0].set_xlabel("CO₂ Reduction (%)"); axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs CO₂ Reduction", fontweight="bold"); axes[0].grid(alpha=0.3)
    for x, y in zip(vp, costs):
        axes[0].annotate(f"{y:.1f}", (x,y), textcoords="offset points",
                         xytext=(0,10), fontsize=9, ha="center")
    axes[1].plot(vp, coal_gen, "o-", color=COLORS["coal"], lw=2.5, markersize=10,
                 markeredgecolor="black")
    axes[1].set_xlabel("CO₂ Reduction (%)"); axes[1].set_ylabel("Coal Generation (TWh/year)")
    axes[1].set_title("Coal Generation vs CO₂ Reduction", fontweight="bold"); axes[1].grid(alpha=0.3)
    fig.suptitle("Denmark – CO₂ Decarbonisation Pathway (1/2): Cost & Coal",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "17a_co2_pathway_cost_coal")

    # Plot 17b: Renewables + Battery
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    axes[0].plot(vp, solar, "o-", color=COLORS["solar"],        lw=2, markersize=9, label="Solar")
    axes[0].plot(vp, wind,  "s-", color=COLORS["onshore_wind"], lw=2, markersize=9, label="Wind total")
    axes[0].set_xlabel("CO₂ Reduction (%)"); axes[0].set_ylabel("Capacity (GW)")
    axes[0].set_title("Renewable Capacity vs CO₂ Reduction", fontweight="bold")
    axes[0].legend(fontsize=11); axes[0].grid(alpha=0.3)
    axes[1].plot(vp, bat, "o-", color=COLORS["battery"], lw=2.5, markersize=10,
                 markeredgecolor="black")
    axes[1].set_xlabel("CO₂ Reduction (%)"); axes[1].set_ylabel("Battery Capacity (GW)")
    axes[1].set_title("Battery Storage vs CO₂ Reduction", fontweight="bold"); axes[1].grid(alpha=0.3)
    fig.suptitle("Denmark – CO₂ Decarbonisation Pathway (2/2): Capacity & Storage",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(); save(fig, "17b_co2_pathway_capacity_storage")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 18: Dispatch seasonal averages
# ═══════════════════════════════════════════════════════════════════════════════
def plot_18(fname, label):
    print(f"\n[18] Dispatch – {label}")
    n = load(fname)
    fig, axes = plt.subplots(2, 1, figsize=(18, 12), sharey=True)
    seasons = {"Winter (Dec–Feb)": ("2012-12-01","2013-02-28"),
               "Summer (Jun–Aug)": ("2012-06-01","2012-08-31")}
    all_c = set(); sd = {}
    for s, (st, en) in seasons.items():
        snap = n.snapshots[(n.snapshots >= st) & (n.snapshots <= en)]
        if len(snap) == 0: snap = n.snapshots[:1000]
        gen_t = n.generators_t.p.loc[snap].copy()
        gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
        gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
        ga = gen_t.groupby(gen_t.index.hour).mean()
        la = n.loads_t.p_set.loc[snap].sum(axis=1).groupby(
            n.loads_t.p_set.loc[snap].index.hour).mean() / 1e3
        sd[s] = (ga, la); all_c |= set(ga.columns)

    ym = max(max(ga.sum(axis=1).max(), la.max()) for ga, la in sd.values()) * 1.12
    for ax, (s, (ga, la)) in zip(axes, sd.items()):
        bot = pd.Series(0.0, index=ga.index)
        for car in all_c:
            if car in ga.columns and ga[car].sum() > 0:
                ax.fill_between(ga.index, bot, bot+ga[car],
                                label=car, color=color(car), alpha=0.85)
                bot += ga[car]
        la.plot(ax=ax, color="black", lw=2.5, label="Demand", zorder=10, ls="--")
        ax.set_title(s, fontweight="bold", fontsize=13)
        ax.set_ylabel("Average Power (GW)"); ax.set_xlabel("Hour of Day")
        ax.set_ylim(0, ym); ax.set_xticks(range(0, 24, 2)); ax.grid(alpha=0.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", fontsize=10, ncol=2,
               bbox_to_anchor=(0.99, 0.98), framealpha=0.9)
    fig.suptitle(f"Denmark – Average Daily Dispatch: {label}",
                 fontsize=14, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 0.87, 1])
    save(fig, f"18_dispatch_{label.lower().replace(' ','_').replace('₂','2')}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 19: Storage + Wind/Solar generation
# ═══════════════════════════════════════════════════════════════════════════════
def plot_19(fname, label):
    print(f"\n[19] Storage – {label}")
    n = load(fname)
    freq = "W"
    wg = pd.Series(0.0, index=n.snapshots)
    sg = pd.Series(0.0, index=n.snapshots)
    for g in n.generators.index:
        car = n.generators.at[g, "carrier"]
        if "wind" in car: wg += n.generators_t.p[g]
        elif "solar" in car: sg += n.generators_t.p[g]
    ww = wg.resample(freq).mean() / 1e3
    sw = sg.resample(freq).mean() / 1e3

    fig, axes = plt.subplots(3, 1, figsize=(18, 13), sharex=True)

    # Wind + Solar
    ax = axes[0]
    ax.fill_between(ww.index, ww, color=COLORS["onshore_wind"], alpha=0.7, label="Wind total")
    ax.fill_between(sw.index, sw, color=COLORS["solar"],        alpha=0.7, label="Solar")
    ax.set_ylabel("Generation (GW, weekly avg)")
    ax.set_title("Wind & Solar Generation", fontweight="bold")
    ax.legend(loc="upper right", fontsize=11, framealpha=0.9); ax.grid(alpha=0.3)

    # Battery SOC
    ax = axes[1]
    if not n.storage_units_t.state_of_charge.empty:
        soc = n.storage_units_t.state_of_charge
        bc = [c for c in soc.columns if "battery" in c.lower()]
        if bc:
            bs = soc[bc].sum(axis=1).resample(freq).mean() / 1e3
            bs.plot(ax=ax, color=COLORS["battery"], lw=1.5, label="Battery SOC")
            ax.fill_between(bs.index, bs, alpha=0.3, color=COLORS["battery"])
            ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        else:
            ax.text(0.5, 0.5, "Battery not used (coal provides balancing)",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11,
                    bbox=dict(boxstyle="round", facecolor="#fff3cd", alpha=0.8))
    ax.set_ylabel("GWh (weekly avg)")
    ax.set_title("Battery Storage – State of Charge", fontweight="bold"); ax.grid(alpha=0.3)

    # Hydrogen SOC
    ax = axes[2]
    if not n.storage_units_t.state_of_charge.empty:
        soc = n.storage_units_t.state_of_charge
        hc = [c for c in soc.columns if "hydrogen" in c.lower()]
        if hc:
            hs = soc[hc].sum(axis=1).resample(freq).mean() / 1e3
            hs.plot(ax=ax, color=COLORS["hydrogen"], lw=1.5, label="Hydrogen SOC")
            ax.fill_between(hs.index, hs, alpha=0.3, color=COLORS["hydrogen"])
            ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        else:
            ax.text(0.5, 0.5, "Hydrogen not used (coal eliminates seasonal storage need)",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11,
                    bbox=dict(boxstyle="round", facecolor="#f0e6ff", alpha=0.8))
    ax.set_ylabel("GWh (weekly avg)")
    ax.set_title("Hydrogen Storage – State of Charge", fontweight="bold"); ax.grid(alpha=0.3)

    fig.suptitle(f"Denmark – Generation & Storage Levels: {label}",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, f"19_storage_{label.lower().replace(' ','_').replace('₂','2')}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 20: Curtailment Rate
# ═══════════════════════════════════════════════════════════════════════════════
def plot_20():
    print("\n[20] Curtailment Rate")
    scenarios = {"Baseline": "02_baseline.nc", "Zero CO₂": "04_zero_co2.nc"}
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, (label, fname) in zip(axes, scenarios.items()):
        try: n = load(fname)
        except: continue
        w = n.snapshot_weightings.generators
        curtailment = {}
        for g in n.generators.index:
            car = n.generators.at[g, "carrier"]
            if car not in ["solar", "onshore_wind", "offshore_wind"]: continue
            if g not in n.generators_t.p_max_pu.columns: continue
            p_nom = n.generators.at[g, "p_nom_opt"]
            if p_nom == 0:
                p_nom = n.generators.at[g, "p_nom"]
            if p_nom == 0: continue
            potential = (n.generators_t.p_max_pu[g] * p_nom * w).sum()
            actual    = (n.generators_t.p[g] * w).sum() if g in n.generators_t.p.columns else 0
            curt = max(0, potential - actual)
            if curt > 0:
                curtailment[car] = curtailment.get(car, 0) + curt / 1e6  # TWh

        if not curtailment:
            ax.text(0.5, 0.5, "No curtailment detected\n(all potential generation was used)",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11,
                    bbox=dict(boxstyle="round", facecolor="#e5f5e0", alpha=0.9))
            ax.set_title(f"Curtailment – {label}", fontweight="bold"); continue

        cs = pd.Series(curtailment).sort_values(ascending=False)
        bars = ax.bar(cs.index, cs.values,
                      color=[color(c) for c in cs.index], edgecolor="white")
        for bar, val in zip(bars, cs.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{val:.2f} TWh", ha="center", fontsize=10)
        ax.set_ylabel("Curtailed Energy (TWh/year)")
        ax.set_title(f"Curtailment – {label}", fontweight="bold")
        ax.grid(alpha=0.3, axis="y")

    fig.suptitle("Denmark – Renewable Curtailment: Baseline vs Zero CO₂",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "20_curtailment_rate")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 21: Cost Summary — logically grouped
# ═══════════════════════════════════════════════════════════════════════════════
def plot_21():
    print("\n[21] Cost Summary")
    groups = [
        ("── Reference ──────────────", None, None),
        ("Baseline",           "02_baseline.nc",                "#636363"),
        ("Zero CO₂",           "04_zero_co2.nc",                "#41ab5d"),
        ("── Grid ───────────────────", None, None),
        ("Grid – Full",        "05_grid_full_expansion.nc",     "#2171b5"),
        ("Grid – 1GW/line",    "06_grid_max_1GW.nc",           "#6baed6"),
        ("Grid – Autarky",     "07_grid_autarky.nc",           "#d94801"),
        ("── Solar CAPEX ────────────", None, None),
        ("Solar CAPEX 100%",   "08_solar_capex_100pct.nc",     "#f9d71c"),
        ("Solar CAPEX 50%",    "10_solar_capex_50pct.nc",      "#f9d71c"),
        ("Solar CAPEX 0%",     "12_solar_capex_0pct.nc",       "#f9d71c"),
        ("── Wind CAPEX ─────────────", None, None),
        ("Wind CAPEX 100%",    "13_wind_capex_100pct.nc",      "#74c476"),
        ("Wind CAPEX 50%",     "15_wind_capex_50pct.nc",       "#74c476"),
        ("Wind CAPEX 0%",      "17_wind_capex_0pct.nc",        "#74c476"),
        ("── Battery CAPEX ──────────", None, None),
        ("Battery 100%",       "18_battery_capex_100pct.nc",   "#d94801"),
        ("Battery 0%",         "22_battery_capex_0pct.nc",     "#d94801"),
        ("── Nuclear ────────────────", None, None),
        ("Nuclear 2,500 €/kW", "27_nuclear_2500_eur_per_kw.nc","#a1d99b"),
        ("Nuclear 10,000 €/kW","30_nuclear_10000_eur_per_kw.nc","#a1d99b"),
        ("── CO₂ Pathway ────────────", None, None),
        ("CO₂ –0%",            "50_co2_reduction_0pct.nc",     "#41ab5d"),
        ("CO₂ –20%",           "51_co2_reduction_20pct.nc",    "#41ab5d"),
        ("CO₂ –60%",           "53_co2_reduction_60pct.nc",    "#41ab5d"),
        ("CO₂ –95%",           "55_co2_reduction_95pct.nc",    "#41ab5d"),
        ("CO₂ –100%",          "56_co2_reduction_100pct.nc",   "#41ab5d"),
    ]
    labels, values, clrs = [], [], []
    for lbl, fname, clr in groups:
        if fname is None:
            labels.append(lbl); values.append(0); clrs.append("white")
            continue
        try:
            obj = get_obj(load(fname))
            if obj is not None:
                labels.append(lbl); values.append(obj); clrs.append(clr)
        except: pass

    fig, ax = plt.subplots(figsize=(16, 13))
    bars = ax.barh(labels, values, color=clrs, edgecolor="white", height=0.7)
    for bar, val, lbl in zip(bars, values, labels):
        if val > 0:
            ax.text(val + 0.05, bar.get_y() + bar.get_height()/2,
                    f"{val:.2f} B€", va="center", fontsize=9)
        if val == 0 and "──" in lbl:
            ax.axhline(y=bar.get_y() + bar.get_height()/2,
                       color="#dddddd", lw=0.8, ls="--")
    ax.set_xlabel("Total System Cost (Billion €/year)", fontsize=12)
    ax.set_title("Denmark – System Cost: All Scenarios (grouped by category)",
                 fontsize=13, fontweight="bold")
    ax.grid(alpha=0.3, axis="x"); ax.invert_yaxis()
    ax.set_xlim(0, max(v for v in values if v > 0) * 1.15)
    plt.tight_layout()
    save(fig, "21_cost_summary")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 22: Tech Years sensitivity
# ═══════════════════════════════════════════════════════════════════════════════
def plot_22():
    print("\n[22] Tech Years")
    year_map = {
        2025: "02_baseline.nc",        # Baseline = 2025 costs
        2030: "71_tec_cost_2030.nc",
        2040: "72_tec_cost_2040.nc",
        2050: "73_tec_cost_2050.nc",
    }
    yrs, costs, solar, wind, bat = [], [], [], [], []
    for yr, fname in sorted(year_map.items()):
        try:
            n = load(fname); obj = get_obj(n)
            if obj is None: continue
            yrs.append(yr); costs.append(obj)
            caps, stor = get_caps(n)
            solar.append(caps.get("solar", 0))
            wind.append(caps.get("onshore_wind", 0) + caps.get("offshore_wind", 0))
            bat.append(stor.get("battery", 0))
        except: pass
    if len(yrs) < 2: print("  Not enough data — skipping"); return

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    axes[0].plot(yrs, costs, "o-", color=COLORS["offshore_wind"], lw=2.5,
                 markersize=9, markeredgecolor="black")
    axes[0].set_xlabel("Technology Cost Year"); axes[0].set_ylabel("System Cost (B€/year)")
    axes[0].set_title("System Cost vs Technology Year", fontweight="bold")
    axes[0].grid(alpha=0.3)
    for x, y in zip(yrs, costs):
        axes[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                         xytext=(0, 10), fontsize=9, ha="center")

    axes[1].plot(yrs, solar, "o-", color=COLORS["solar"],        lw=2, markersize=8, label="Solar")
    axes[1].plot(yrs, wind,  "s-", color=COLORS["onshore_wind"], lw=2, markersize=8, label="Wind total")
    axes[1].plot(yrs, bat,   "^-", color=COLORS["battery"],      lw=2, markersize=8, label="Battery")
    axes[1].set_xlabel("Technology Cost Year")
    axes[1].set_ylabel("Capacity (GW)", fontsize=12)
    axes[1].set_title("Capacity Mix + System Cost vs Technology Year", fontweight="bold")
    axes[1].legend(fontsize=10, loc="upper left"); axes[1].grid(alpha=0.3)

    # Second y-axis for costs
    ax2 = axes[1].twinx()
    ax2.plot(yrs, costs, "D--", color="#d94801", lw=2, markersize=8,
             label="System Cost", alpha=0.8)
    ax2.set_ylabel("System Cost (B€/year)", fontsize=12, color="#d94801")
    ax2.tick_params(axis="y", labelcolor="#d94801")
    ax2.legend(loc="upper right", fontsize=10)

    fig.suptitle("Denmark – Sensitivity 6: Technology Cost Year Variations\n"
                 "2025 = Baseline | 2030/2040/2050 = future cost projections",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "22_tech_years")


#  New Plot

def plot_annual_generation_with_storage():
    print("\n[plot] Annual Generation + Storage + Demand")
    fig, axes = plt.subplots(2, 1, figsize=(20, 14), sharex=True)
    for ax, (fname, label) in zip(axes, [
            ("02_baseline.nc", "Baseline"),
            ("04_zero_co2.nc", "Zero CO₂")]):
        try: n = load(fname)
        except: continue

        # Generation weekly avg
        gen_t = n.generators_t.p.copy()
        gen_t.columns = n.generators.loc[gen_t.columns, "carrier"]
        gen_t = gen_t.T.groupby(level=0).sum().T / 1e3
        gw = gen_t.resample("W").mean()

        # Battery dispatch (positive = discharging)
        bat_cols = [c for c in n.storage_units.index
                    if "battery" in n.storage_units.at[c, "carrier"].lower()]
        if bat_cols:
            bat_dispatch = n.storage_units_t.p[bat_cols].sum(axis=1).resample("W").mean() / 1e3
        else:
            bat_dispatch = None

        # Demand
        lw = n.loads_t.p_set.sum(axis=1).resample("W").mean() / 1e3

        bot = pd.Series(0.0, index=gw.index)
        for car in gw.columns:
            if gw[car].sum() > 0:
                ax.fill_between(gw.index, bot, bot + gw[car],
                                label=car, color=color(car), alpha=0.85)
                bot += gw[car]

        # Battery discharge on top
        if bat_dispatch is not None and bat_dispatch.max() > 0:
            ax.fill_between(gw.index,
                            bot,
                            bot + bat_dispatch.clip(lower=0),
                            label="battery (discharge)",
                            color=COLORS["battery"], alpha=0.6)

        lw.plot(ax=ax, color="black", lw=2.5, label="Demand",
                zorder=10, ls="--")
        ax.set_ylabel("Power (GW, weekly avg)", fontsize=12)
        ax.set_title(label, fontweight="bold", fontsize=13)
        ax.legend(loc="upper left", fontsize=10, ncol=5, framealpha=0.9)
        ax.grid(alpha=0.2)

    fig.suptitle("Denmark – Annual Generation (incl. Battery Discharge) & Demand",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    save(fig, "03c_annual_generation_with_battery")

# # ═══════════════════════════════════════════════════════════════════════════════
# # RUN ALL
# # ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("Denmark Energy Model – Generating all plots")
    print("=" * 60)

    # plot_00a()
    # plot_00b()
    # plot_01()
    # plot_02()
    # plot_03()
    # plot_04()
    # plot_05()
    plot_06()
    # plot_07()
    # plot_08()
    # plot_09()
    # plot_10()
    # plot_11()
    # plot_12()
    # plot_13()
    # plot_14()
    # plot_15()
    # plot_16()
    # plot_17()
    # plot_18("04_zero_co2.nc",  "Zero CO2")
    # plot_18("02_baseline.nc",  "Baseline")
    # plot_19("04_zero_co2.nc",  "Zero CO2")
    # plot_19("02_baseline.nc",  "Baseline")
    # plot_20()
    # plot_21()
    plot_22()
    #plot_annual_generation_with_storage()

    print("\n" + "=" * 60)
    print(f"✓ All plots saved to {OUT_DIR}/")
    print("=" * 60)