"""
create_pdf_with_plots.py – Clean PDF combining all plots with interpretations.
Place in project root and run: python create_pdf_with_plots.py
Requires: pip install reportlab
"""

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os

FIG = "results/figures"
OUT = "results/denmark_complete_analysis.pdf"
os.makedirs("results", exist_ok=True)

# Page dimensions (landscape A4)
PW = landscape(A4)[0] - 4*cm   # usable width
PH = landscape(A4)[1] - 3*cm   # usable height
IMG_H = 13*cm                   # standard image height

# ── Colors ─────────────────────────────────────────────────────────────────────
DB  = HexColor("#1a3a5c")   # dark blue
MB  = HexColor("#2171b5")   # mid blue
LB  = HexColor("#deebf7")   # light blue
GR  = HexColor("#41ab5d")   # green
LG  = HexColor("#e5f5e0")   # light green
OR  = HexColor("#d94801")   # orange
LGR = HexColor("#f5f5f5")   # light grey
MGR = HexColor("#636363")   # mid grey

# ── Styles ─────────────────────────────────────────────────────────────────────
def S(name, **kw):
    defaults = dict(fontName="Helvetica", fontSize=10, leading=14,
                    textColor=HexColor("#222222"))
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

T_TITLE = S("tt", fontSize=21, fontName="Helvetica-Bold", textColor=DB,
            alignment=TA_CENTER, leading=27, spaceAfter=5)
T_SUB   = S("ts", fontSize=12, textColor=MGR, alignment=TA_CENTER, leading=16)
T_SEC   = S("tsec", fontSize=11, fontName="Helvetica-Bold", textColor=white, leading=15)
T_LBL   = S("tlbl", fontSize=9, fontName="Helvetica-Bold", textColor=MB,
            spaceAfter=2, leading=12)
T_COND  = S("tcond", fontSize=9, textColor=HexColor("#1a3a1a"), leading=13)
T_HL    = S("thl", fontSize=9, fontName="Helvetica-Bold", textColor=white,
            leading=13, wordWrap="CJK")
T_HT    = S("tht", fontSize=9, textColor=HexColor("#111111"), leading=14,
            wordWrap="CJK", alignment=TA_JUSTIFY)
T_KF    = S("tkf", fontSize=9, textColor=DB, leading=14, wordWrap="CJK")
T_FOOT  = S("tfoot", fontSize=7, textColor=MGR, alignment=TA_CENTER)
T_CK    = S("tck", fontSize=10, fontName="Helvetica-Bold", textColor=DB)
T_CV    = S("tcv", fontSize=10, textColor=HexColor("#333333"), wordWrap="CJK")

# ── Helpers ─────────────────────────────────────────────────────────────────────
def hdr(text, c=DB):
    t = Table([[Paragraph(text, T_SEC)]], colWidths=[PW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), c),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ]))
    return t

def cbox(items):
    rows = [[Paragraph(f"&#8226;  {i}", T_COND)] for i in items]
    t = Table(rows, colWidths=[PW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LG),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("BOX",           (0,0),(-1,-1), 0.5, GR),
        ("LINEBELOW",     (0,0),(-2,-1), 0.3, HexColor("#b7e4c7")),
    ]))
    return t

def htbl(hyps):
    rows = [[Paragraph(f"<b>{h}</b>", T_HL), Paragraph(t, T_HT)] for h,t in hyps]
    t = Table(rows, colWidths=[1.3*cm, PW-1.3*cm])
    cmds = [
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("GRID",          (0,0),(-1,-1), 0.3, HexColor("#cccccc")),
    ]
    for i in range(len(rows)):
        cmds += [("BACKGROUND",(0,i),(0,i), MB if i%2==0 else DB),
                 ("BACKGROUND",(1,i),(1,i), LB if i%2==0 else HexColor("#f0f7ff"))]
    t.setStyle(TableStyle(cmds))
    return t

def kfbox(text):
    t = Table([[Paragraph(f"<b>Key Finding:</b>  {text}", T_KF)]], colWidths=[PW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), HexColor("#fff8e1")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("BOX",           (0,0),(-1,-1), 1.2, HexColor("#ffc107")),
    ]))
    return t

def img(story, fname, h=IMG_H):
    path = f"{FIG}/{fname}"
    if os.path.exists(path):
        story.append(Image(path, width=PW, height=h))
    else:
        story.append(Paragraph(f"[Plot not yet available: {fname}]",
                               S("nf", fontSize=9, textColor=OR, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.15*cm))

def section(story, num, title, fname, color, conds, hyps, finding, img_h=IMG_H):
    story.append(hdr(f"Plot {num} — {title}", color))
    story.append(Spacer(1, 0.2*cm))
    img(story, fname, img_h)
    story.append(Paragraph("Modelling Conditions", T_LBL))
    story.append(cbox(conds))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph("Interpretation &amp; Hypotheses", T_LBL))
    story.append(htbl(hyps))
    story.append(Spacer(1, 0.15*cm))
    story.append(kfbox(finding))
    story.append(PageBreak())


# ══════════════════════════════════════════════════════════════════════════════
# CONTENT
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ── Cover ──────────────────────────────────────────────────────────────────────
story += [
    Spacer(1, 2*cm),
    Paragraph("Modelling a Zero-Carbon Electricity System for Denmark", T_TITLE),
    Paragraph("Scenarios, Sensitivities &amp; Key Findings",
              S("st2", fontSize=15, fontName="Helvetica-Bold", textColor=MB,
                alignment=TA_CENTER, leading=20, spaceAfter=5)),
    Spacer(1, 0.3*cm),
    HRFlowable(width="100%", thickness=2, color=MB),
    Spacer(1, 0.3*cm),
    Paragraph("Data Science for Energy System Modelling — Summer Term 2026 | Group Assignment 4",
              T_SUB),
    Spacer(1, 1.5*cm),
]
cd = [
    [Paragraph("Country", T_CK),
     Paragraph("Denmark — 5 GADM-1 regions: Hovedstaden, Sj&#230;lland, Syddanmark, Midtjylland, Nordjylland", T_CV)],
    [Paragraph("Weather Year", T_CK), Paragraph("2012 (ERA5 reanalysis via atlite)", T_CV)],
    [Paragraph("Temporal Resolution", T_CK), Paragraph("3-hourly (2,920 timesteps/year)", T_CV)],
    [Paragraph("Solver", T_CK), Paragraph("Gurobi 13 (academic license)", T_CV)],
    [Paragraph("Technology Data", T_CK), Paragraph("PyPSA/technology-data — 2025 projections", T_CV)],
    [Paragraph("Discount Rate", T_CK), Paragraph("7% (annualises all capital investment costs)", T_CV)],
    [Paragraph("Renewable Potentials", T_CK),
     Paragraph("From land eligibility analysis: solar 86,190 MW | onshore wind 11,655 MW | offshore wind 114,975 MW", T_CV)],
    [Paragraph("Sensitivities", T_CK),
     Paragraph("Grid expansion | Technology CAPEX (Solar/Wind/Battery/Transmission) | Renewable potentials | Nuclear costs | Technology cost years", T_CV)],
]
ct = Table(cd, colWidths=[5*cm, PW-5*cm])
ct.setStyle(TableStyle([
    ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),(-1,-1), 7),
    ("BOTTOMPADDING", (0,0),(-1,-1), 7),
    ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ("ROWBACKGROUNDS",(0,0),(-1,-1), [white, LGR]),
    ("BOX",           (0,0),(-1,-1), 1, MB),
    ("LINEBELOW",     (0,0),(-2,-1), 0.3, HexColor("#cccccc")),
]))
story += [ct, PageBreak()]

# ── Plot 00a ───────────────────────────────────────────────────────────────────
section(story, "00a", "Baseline Scenario (1/2): Mix, Capacities &amp; Costs",
    "00a_baseline_overview.png", DB,
    ["No CO<sub>2</sub> emission constraint — existing fossil fleet operates freely",
     "Fixed capacity: coal 5,089 MW | gas 571 MW | oil 664 MW | biomass 88 MW",
     "Renewables extendable from 0 MW | Technology costs: 2025 projections | Discount rate: 7%"],
    [("H1","Coal dominates (92%) because existing plants are fully amortised — only variable fuel costs apply."),
     ("H2","Storage is barely used — coal provides all balancing, making batteries economically unnecessary."),
     ("H3","System cost is low (1.36 B€/year) because sunk capital costs and carbon damage are excluded.")],
    "The Baseline is artificially cheap — it reflects operating costs of already-built infrastructure, not the true societal cost of fossil fuels.")

# ── Plot 00b ───────────────────────────────────────────────────────────────────
section(story, "00b", "Baseline Scenario (2/2): Dispatch &amp; Regional Generation",
    "00b_baseline_dispatch.png", DB,
    ["Winter week dispatch: Jan 9–16, 2012 (3-hourly resolution)",
     "Regional generation: annual totals per GADM-1 region",
     "5 regions covering Jutland and the Danish islands"],
    [("H1","Coal runs as near-constant baseload — a simple, predictable system with wind as top-up."),
     ("H2","Midtjylland and Syddanmark dominate regional generation — most existing plants are in western Jutland."),
     ("H3","Wind contributes mainly in winter; solar is negligible in the Baseline.")],
    "The Baseline dispatch illustrates why coal is so attractive without carbon pricing: perfectly controllable, no storage needed, no grid coordination required.")

# ── Plot 01 ────────────────────────────────────────────────────────────────────
section(story, "01", "Electricity Mix: Baseline vs Zero CO<sub>2</sub>",
    "01_mix_baseline_vs_zero_co2.png", DB,
    ["Baseline: no CO<sub>2</sub> limit | Zero CO<sub>2</sub>: emissions = 0 tonnes/year",
     "Updated potentials from eligibility analysis: solar 86,190 MW | onshore 11,655 MW | offshore 114,975 MW",
     "Small slices (oil, gas, biomass &lt;2%) may appear crowded — values given as percentages"],
    [("H1","Coal dominates Baseline (92%); Zero CO₂ shifts to offshore wind (40%) + onshore wind (41%) + solar (18%)."),
     ("H2","Zero CO₂ produces slightly more electricity due to renewable overproduction charging storage (round-trip losses)."),
     ("H3","Biomass remains in Zero CO₂ — it has zero CO₂ emissions in the model and provides dispatchable backup.")],
    "The 379% cost increase (1.36 → 6.50 B€/year) represents the investment cost of the energy transition — not its true societal cost, since carbon damage is not priced in.")

# ── Plot 02 ────────────────────────────────────────────────────────────────────
section(story, "02", "Installed Capacities: Baseline vs Zero CO<sub>2</sub>",
    "02_capacities_comparison.png", DB,
    ["Baseline: fixed conventional fleet | Zero CO₂: full renewable buildout required",
     "Battery storage (2h/4h/6h) and hydrogen (168h/336h/672h) available in both scenarios"],
    [("H1","Zero CO₂ requires massive new renewable capacity while fossil plants remain installed but idle — stranded assets."),
     ("H2","Battery storage is the largest new capacity addition — needed to balance variable wind and solar output."),
     ("H3","Offshore wind dominates the Zero CO₂ capacity mix due to Denmark's exceptional North Sea resource.")],
    "Zero CO₂ does not demolish existing plants — it builds a complete parallel renewable system on top, making fossil capacity economically worthless.")

# ── Plot 03 ────────────────────────────────────────────────────────────────────
section(story, "03", "Annual Generation &amp; Demand Throughout the Year",
    "03_annual_generation_demand.png", MB,
    ["Weekly averages of hourly generation and demand for the full 2012 weather year",
     "Top: Baseline | Bottom: Zero CO₂ | Demand = dashed black line"],
    [("H1","Baseline: coal provides flat, predictable baseload all year. Zero CO₂: strong seasonal variation — wind dominates winter, solar peaks in summer."),
     ("H2","Zero CO₂ frequently shows generation exceeding demand — these surpluses charge storage or are curtailed."),
     ("H3","Wind and solar complement each other seasonally: wind covers winter demand, solar reduces storage needs in summer.")],
    "The annual profile reveals the core challenge of variable renewables: large seasonal imbalances require either seasonal storage (hydrogen) or cross-border exchange.")

# ── Plot 04 ────────────────────────────────────────────────────────────────────
section(story, "04", "Capacity Factors by Region: Solar &amp; Wind",
    "04_capacity_factors_per_region.png", MB,
    ["Monthly average capacity factors for each of the 5 GADM-1 regions",
     "Calculated from ERA5 2012 weather data via atlite",
     "Solar: CdTe panel, latitude-optimal orientation | Onshore: Vestas V112 3MW | Offshore: NREL 5MW"],
    [("H1","Offshore wind has the highest and most consistent capacity factors (~40–50%) — Denmark's primary renewable advantage."),
     ("H2","Solar capacity factors peak in summer (June–August) at ~15–20% and drop to near zero in December — typical for 55°N."),
     ("H3","Onshore wind shows less regional variation than solar, confirming wind's reliability across all Danish regions.")],
    "The capacity factor profiles directly explain why offshore wind dominates the Zero CO₂ system — it produces significantly more energy per installed MW than solar at Denmark's latitude.")

# ── Plot 05 ────────────────────────────────────────────────────────────────────
section(story, "05", "CO<sub>2</sub> Shadow Price &amp; System Cost",
    "05_co2_shadow_price.png", HexColor("#145a32"),
    ["CO₂ shadow price = marginal cost of the last tonne of CO₂ abatement (from global constraint dual)",
     "CO₂ reduced in steps: 0%, 20%, 40%, 60%, 80%, 95%, 100%",
     "Shadow price of 0 = constraint not binding (no CO₂ limit or coal already phased out)"],
    [("H1","The shadow price rises exponentially — the last tonnes of CO₂ are far more expensive to eliminate than the first."),
     ("H2","At 95–100% reduction, the shadow price reflects the cost of eliminating rare dark-doldrums through massive battery investment."),
     ("H3","Low shadow prices at 0–60% reduction confirm that the first phase of decarbonisation (replacing coal with wind) is inexpensive.")],
    "The CO₂ shadow price is the implicit carbon price required to achieve each reduction target — it rises from near zero to hundreds of €/tCO₂ for the last 5% of emissions, informing optimal carbon pricing policy.")

# ── Plot 06 ────────────────────────────────────────────────────────────────────
section(story, "06", "Price Duration Curves: Baseline vs Zero CO<sub>2</sub>",
    "06_price_duration_curve.png", DB,
    ["Nodal marginal prices (dual variables of energy balance constraint) for each region",
     "Sorted from highest to lowest — x-axis shows percentage of hours",
     "Price spikes indicate scarcity events; near-zero prices indicate surplus (curtailment risk)"],
    [("H1","Baseline: price duration curve is flat — coal sets a near-constant marginal price throughout the year."),
     ("H2","Zero CO₂: prices show high volatility — near-zero during wind/solar surplus, high spikes during dark-doldrums."),
     ("H3","Regional price differences in Zero CO₂ reflect transmission constraints — regions with more renewables have lower average prices.")],
    "Price duration curves reveal the fundamental change from a fossil to a renewable system: predictable flat prices give way to highly variable prices, creating both curtailment challenges and scarcity events.")

# ── Plot 07 ────────────────────────────────────────────────────────────────────
section(story, "07", "Grid Expansion Sensitivity",
    "07_grid_sensitivity.png", MB,
    ["Three scenarios: full expansion (unconstrained) | max 1 GW/line | autarky (no transmission)",
     "Zero CO₂ constraint active | 5 regions, 5 links | 700 €/MW/km × 1.5 route factor"],
    [("H1","Full expansion and Max 1 GW cost identically (6.50 B€) — Denmark is compact enough that 1 GW per corridor is fully sufficient."),
     ("H2","Autarky costs 41% more (9.18 B€) — each region must independently balance supply and demand without sharing surpluses."),
     ("H3","Transmission and storage are economic substitutes: without a grid, expensive local storage replaces cheap inter-regional exchange.")],
    "Regional interconnection is highly valuable but reaches diminishing returns quickly. Denmark needs at most 1 GW per transmission corridor — beyond this, no further savings are achieved.")

# ── Plot 08 ────────────────────────────────────────────────────────────────────
section(story, "08", "Solar CAPEX Sensitivity",
    "08_solar_capex.png", HexColor("#b8860b"),
    ["Solar CAPEX reduced 100% → 0% in 25% steps | Zero CO₂ constraint active",
     "Lines = solar capacity (varied) | Bars = other technologies (context)",
     "Solar maximum from eligibility analysis: 86,190 MW"],
    [("H1","Solar CAPEX reduction has a moderate effect on system cost — cheaper solar displaces some wind."),
     ("H2","Solar capacity grows as CAPEX falls, substituting partly for offshore wind and reducing storage needs."),
     ("H3","Even free solar leaves significant wind and battery capacity — Denmark's system cannot rely on solar alone at 55°N.")],
    "With correct (larger) potentials from the eligibility analysis, solar CAPEX sensitivity shows meaningful results. Previously the system was at its area limit, making cost reduction irrelevant.")

# ── Plot 09 ────────────────────────────────────────────────────────────────────
section(story, "09", "Wind CAPEX Sensitivity",
    "09_wind_capex.png", GR,
    ["Onshore and offshore wind CAPEX reduced simultaneously 100% → 0% in 25% steps",
     "Lines = wind capacities | Bars = solar and battery (context)",
     "Onshore max: 11,655 MW | Offshore max: 114,975 MW"],
    [("H1","Wind CAPEX reduction delivers the largest system cost savings — wind dominates Denmark's renewable mix."),
     ("H2","Offshore wind capacity increases strongly as CAPEX falls — the enormous North Sea potential (115 GW) becomes economical."),
     ("H3","Battery storage decreases as wind becomes cheaper — overbuilding wind is more economic than investing in storage.")],
    "Offshore wind cost reduction is the single most impactful lever for Denmark. The enormous offshore potential means cost reductions translate directly into large deployment increases.")

# ── Plot 10 ────────────────────────────────────────────────────────────────────
section(story, "10", "Battery CAPEX Sensitivity",
    "10_battery_capex.png", OR,
    ["Battery CAPEX reduced 100% → 0% in 25% steps | 2h/4h/6h variants available",
     "Lines = storage capacities | Bars = wind and solar (context)",
     "Hydrogen storage (168h/336h/672h) also available as competing option"],
    [("H1","Batteries are the largest cost driver in Zero CO₂ — halving battery costs nearly halves total system cost."),
     ("H2","At 0% battery CAPEX, ~500 GW of batteries are installed, replacing hydrogen and substituting for transmission."),
     ("H3","Hydrogen storage decreases as batteries get cheaper — batteries can serve seasonal storage when sufficiently cheap.")],
    "Battery storage cost is the critical variable for Denmark's energy transition. Breakthroughs in battery technology would be more transformative than equivalent cost reductions in wind or solar.")

# ── Plot 11 ────────────────────────────────────────────────────────────────────
section(story, "11", "Transmission CAPEX Sensitivity",
    "11_transmission_capex.png", MGR,
    ["Transmission cost reduced from 700 €/MW/km × 1.5 to 0 in 25% steps",
     "Zero CO₂ constraint active"],
    [("H1","Cheaper transmission leads to more grid buildout and slightly lower system costs."),
     ("H2","The effect is modest — Denmark's compact geography is already well-interconnected at current line costs."),
     ("H3","Transmission and storage are economic substitutes — cheaper lines reduce the need for local storage.")],
    "Transmission costs matter less for Denmark's compact geography. The key benefit of cheaper lines is reduced storage requirements rather than enabling new renewable deployment.")

# ── Plot 12 ────────────────────────────────────────────────────────────────────
section(story, "12", "Solar Potential Sensitivity",
    "12_solar_potential.png", HexColor("#b8860b"),
    ["Solar p_nom_max reduced from 100% to 0% of eligible area (base: 86,190 MW)",
     "Wind potentials remain at maximum | Zero CO₂ active",
     "Lines = solar (varied) | Bars = wind and battery (context)"],
    [("H1","System costs rise steeply as solar is restricted — wind is near its maximum and cannot fully compensate."),
     ("H2","Battery storage increases as solar decreases, compensating for the loss of daytime solar generation."),
     ("H3","Solar is systemically critical despite its low CF — its daytime profile complements wind, reducing storage needs.")],
    "Solar area restrictions are very costly. Although solar has a modest capacity factor at 55°N, its complementarity with wind is essential for reducing storage requirements.")

# ── Plot 13 ────────────────────────────────────────────────────────────────────
section(story, "13", "Onshore Wind Potential Sensitivity",
    "13_onshore_potential.png", GR,
    ["Onshore wind p_nom_max reduced 100% → 0% (base: 11,655 MW)",
     "Offshore wind (114,975 MW) and solar (86,190 MW) remain at maximum",
     "Lines = onshore wind (varied) | Bars = other technologies (context)"],
    [("H1","Restricting onshore wind forces more offshore wind and solar as substitutes."),
     ("H2","With updated larger potentials, the system can compensate for onshore restrictions — offshore wind is the natural substitute."),
     ("H3","Setback distances and residential proximity rules are the key limiting factors for onshore wind area.")],
    "With correct potentials, onshore wind restrictions are no longer immediately infeasible. Offshore wind can substitute effectively, though at moderately higher cost.")

# ── Plot 14 ────────────────────────────────────────────────────────────────────
section(story, "14", "All Renewables Potential Sensitivity",
    "14_all_renewables_potential.png", GR,
    ["Solar, onshore wind, and offshore wind all reduced simultaneously",
     "Worst-case land scarcity scenario | Zero CO₂ active",
     "Lines = renewables | Bars = storage (context)"],
    [("H1","When all renewables are restricted together, costs rise sharply — no substitution between technologies is possible."),
     ("H2","Storage increases dramatically to time-shift the scarce renewable generation to cover all demand hours."),
     ("H3","This scenario quantifies the cost of poor spatial planning — proactive renewable zone designation is essential.")],
    "Spatial planning for renewable energy is as important as technology cost reductions. A coordinated national strategy for renewable zone designation is fundamental to affordable decarbonisation.")

# ── Plot 15 ────────────────────────────────────────────────────────────────────
section(story, "15", "Nuclear CAPEX Sensitivity (No CO<sub>2</sub> Limit)",
    "15_nuclear_sensitivity.png", HexColor("#2d6a4f"),
    ["Nuclear added to each region with CAPEX from 2,500 to 10,000 €/kW",
     "No CO₂ constraint — nuclear competes with coal and gas",
     "Nuclear: zero CO₂ emissions, 60-year lifetime, 2% FOM"],
    [("H1","Nuclear is competitive only below ~5,000 €/kW — above this, coal's low operating cost wins."),
     ("H2","At 2,500 €/kW nuclear displaces almost all wind — it provides firm baseload without requiring storage."),
     ("H3","Current European nuclear costs (8,000–12,000 €/kW) are far above the competitive threshold without a carbon price.")],
    "Without a carbon price, nuclear is only economic at capital costs well below current European build costs. A CO₂ price would substantially alter this calculation.")

# ── Plot 16 ────────────────────────────────────────────────────────────────────
section(story, "16", "Nuclear + Grid Expansion Combined",
    "16_nuclear_grid_combined.png", HexColor("#1b4332"),
    ["Nuclear at varying CAPEX + 1 GW/line grid limit | Zero CO₂ active",
     "Compared against baseline network (full expansion) with nuclear"],
    [("H1","With the baseline network, nuclear is barely needed even at 2,500 €/kW — wind can be transported efficiently from anywhere."),
     ("H2","With a 1 GW/line grid limit, nuclear is built at ALL tested capital costs — regions need local firm capacity."),
     ("H3","Transmission and nuclear are strategic substitutes — grid expansion reduces nuclear's value; grid constraints make nuclear more valuable.")],
    "The nuclear vs. renewables debate cannot be separated from grid policy. Grid expansion and nuclear power serve the same function — regional supply security — and compete directly for investment.")

# ── Plot 17a ───────────────────────────────────────────────────────────────────
section(story, "17a", "CO<sub>2</sub> Decarbonisation Pathway (1/2): Cost &amp; Coal",
    "17a_co2_pathway_cost_coal.png", HexColor("#145a32"),
    ["CO₂ reduced in steps: 0%, 20%, 40%, 60%, 80%, 95%, 100%",
     "Existing fossil fleet included | Full grid expansion | All technologies available"],
    [("H1","The first 60% of CO₂ reduction is cheap (1.7 → 2.5 B€/year) — wind directly displaces coal with minimal storage."),
     ("H2","The last 5% (95% → 100%) costs 2.3 B€/year alone — more than the entire first 80% combined."),
     ("H3","Coal generation falls linearly until ~95%, then drops to zero — the final phase requires complete storage coverage.")],
    "The law of increasing marginal abatement costs is stark. A pragmatic 80–95% target is dramatically cheaper than 100% — the residual emissions could be addressed through imports or demand response.")

# ── Plot 17b ───────────────────────────────────────────────────────────────────
section(story, "17b", "CO<sub>2</sub> Decarbonisation Pathway (2/2): Capacity &amp; Storage",
    "17b_co2_pathway_capacity_storage.png", HexColor("#145a32"),
    ["Same scenarios as 17a: CO₂ reduced 0% → 100%",
     "Focus on renewable capacity buildout and battery storage requirements"],
    [("H1","Renewable capacity grows steadily from 0% to 80% CO₂ reduction as wind replaces coal."),
     ("H2","Battery storage stays near zero until 80% reduction, then rises sharply to ~17 GW at 100%."),
     ("H3","Storage is only needed when ALL fossil backup is removed — confirming coal's role as the system's flexibility provider.")],
    "Storage is the final barrier to full decarbonisation. The first 80% is cheap (wind replaces coal); the last 20% requires expensive storage for rare but critical dark-doldrum events.")

# ── Plot 18a: Dispatch Zero CO2 ────────────────────────────────────────────────
section(story, "18a", "Average Daily Dispatch: Zero CO<sub>2</sub> Scenario",
    "18_dispatch_zero_co2.png", MB,
    ["Average daily dispatch profile by season: Winter (Dec–Feb) | Summer (Jun–Aug)",
     "X-axis: hour of day (0–23) | Y-axis: average power (GW) | Demand = dashed line",
     "Shared y-axis for direct winter/summer comparison"],
    [("H1","Winter: wind-dominated with flat hourly profile — wind does not follow daily patterns."),
     ("H2","Summer: clear solar peak at midday, with wind providing baseload and storage smoothing the evening ramp."),
     ("H3","Demand is relatively constant throughout the day — storage must bridge the gap at all hours.")],
    "The seasonal dispatch reveals the core operational challenge: in winter the system needs rapid daily storage cycling; in summer solar creates a midday surplus requiring afternoon/evening discharge.")

# ── Plot 18b: Dispatch Baseline ────────────────────────────────────────────────
section(story, "18b", "Average Daily Dispatch: Baseline Scenario",
    "18_dispatch_baseline.png", HexColor("#252525"),
    ["Same format as Plot 18a — Baseline scenario",
     "Coal provides near-constant baseload throughout the day"],
    [("H1","Coal runs as flat baseload in both seasons — a simple, predictable system requiring no storage."),
     ("H2","Storage is invisible — coal absorbs all variability cheaply, eliminating any economic role for batteries."),
     ("H3","The contrast with Zero CO₂ quantifies how much flexibility coal eliminates: no storage, no grid coordination needed.")],
    "The Baseline dispatch illustrates why coal is so economically attractive without carbon pricing: perfectly controllable, no complementary investments required.")

# ── Plot 19a: Storage Zero CO2 ─────────────────────────────────────────────────
section(story, "19a", "Generation &amp; Storage Levels: Zero CO<sub>2</sub>",
    "19_storage_zero_co2.png", OR,
    ["Three panels (weekly averages): Wind &amp; Solar generation | Battery SOC | Hydrogen SOC",
     "Cyclic SOC constraint: storage level at year-end must equal year-start",
     "Battery = short-term (2h/4h/6h) | Hydrogen = seasonal (168h/336h/672h)"],
    [("H1","Wind peaks in winter, solar in summer — their complementarity reduces total storage requirements."),
     ("H2","Hydrogen accumulates in spring/summer (renewable surplus) and discharges in winter (dark doldrums) — classic seasonal pattern."),
     ("H3","Battery cycles weekly following wind patterns; hydrogen cycles seasonally — efficient division of labour between storage types.")],
    "The two-tier storage system is clearly visible: batteries for short-term (days/weeks) balancing, hydrogen for seasonal (months) balancing — each driven by a different timescale of renewable variability.")

# ── Plot 19b: Storage Baseline ─────────────────────────────────────────────────
section(story, "19b", "Generation &amp; Storage Levels: Baseline",
    "19_storage_baseline.png", HexColor("#252525"),
    ["Same format as Plot 19a — Baseline scenario",
     "Note: battery and hydrogen panels may appear empty — this is correct and expected"],
    [("H1","Battery activity is minimal — only brief winter periods when wind produces small surpluses."),
     ("H2","Hydrogen storage is essentially unused (0 GWh) — coal makes seasonal storage completely unnecessary."),
     ("H3","The near-zero storage in the Baseline quantifies exactly how much flexibility coal provides: it replaces all storage needs.")],
    "Coal is a near-perfect substitute for storage. Removing coal transfers its entire balancing function to batteries and hydrogen — directly explaining why storage is the largest cost driver in Zero CO₂.")

# ── Plot 20 ────────────────────────────────────────────────────────────────────
section(story, "20", "Renewable Curtailment: Baseline vs Zero CO<sub>2</sub>",
    "20_curtailment_rate.png", DB,
    ["Curtailment = potential generation (CF × p_nom) minus actual generation",
     "Shows how much renewable energy is wasted due to grid/storage constraints"],
    [("H1","Baseline: minimal curtailment — coal adjusts to absorb any renewable surplus, no wasted generation."),
     ("H2","Zero CO₂: higher curtailment especially for offshore wind — storage and grid cannot always absorb all production."),
     ("H3","Curtailment is a signal that additional storage or grid capacity would increase system value.")],
    "Curtailment reveals the efficiency of the system: in Zero CO₂, some renewable generation is wasted because storage and transmission cannot always absorb surplus production. Reducing curtailment reduces effective system costs.")

# ── Plot 21 ────────────────────────────────────────────────────────────────────
section(story, "21", "System Cost Overview: All Scenarios",
    "21_cost_summary.png", DB,
    ["All solved scenarios | Costs in B€/year (annualised investment + operating costs at 7%)",
     "Scenarios grouped by category: Reference | Grid | CAPEX sensitivities | Nuclear | CO₂ pathway",
     "Technology costs: 2025 projections | Weather: 2012 | Resolution: 3h"],
    [("H1","Autarky is the most expensive real-world scenario (9.18 B€) — transmission is more valuable than any technology cost reduction."),
     ("H2","Wind CAPEX reduction delivers the largest savings of any sensitivity — wind dominates Denmark's zero-carbon mix."),
     ("H3","CO₂ pathway: 60% decarbonisation (2.45 B€) costs little more than Baseline (1.36 B€); 100% costs 6.50 B€.")],
    "Three policy recommendations: (1) invest in transmission before local storage; (2) prioritise offshore wind cost reduction; (3) consider 80–95% target supplemented by imports or demand response.")

# ── Plot 22 ────────────────────────────────────────────────────────────────────
section(story, "22", "Sensitivity 6: Technology Cost Year Variations",
    "22_tech_years.png", MB,
    ["Technology costs from 2020, 2025, 2030, 2040, 2050 (PyPSA/technology-data)",
     "Zero CO₂ active | Weather: 2012 | Resolution: 3h",
     "Shows how the optimal zero-carbon system changes as technologies become cheaper"],
    [("H1","System costs decrease substantially from 2020 to 2050 — all technologies follow learning curves."),
     ("H2","Renewable capacity increases in later years — falling costs make overbuilding more economic than storage investment."),
     ("H3","Battery storage increases in later years — cheaper batteries make short-term storage more economical relative to hydrogen.")],
    "Technology learning curves substantially reduce zero-carbon electricity costs over time. Continued R&D investment and scale-up accelerates the transition — timing and policy ambition matter significantly.")

# ── Summary ────────────────────────────────────────────────────────────────────
story.append(hdr("Overall Conclusions &amp; Policy Implications"))
story.append(Spacer(1, 0.3*cm))
sh = S("sh", fontSize=9, fontName="Helvetica-Bold", textColor=white, leading=13, wordWrap="CJK")
sb = S("sb", fontSize=9, leading=14, wordWrap="CJK")
sd = [
    [Paragraph("Key Finding", sh), Paragraph("Policy Implication", sh)],
    [Paragraph("Wind is Denmark's key technology", sb),
     Paragraph("Prioritise offshore wind cost reduction and protect North Sea wind zones", sb)],
    [Paragraph("Storage is the main cost driver", sb),
     Paragraph("Battery R&amp;D is critical — halving battery costs halves system costs", sb)],
    [Paragraph("Transmission replaces storage", sb),
     Paragraph("Grid buildout delivers better value than local autarky", sb)],
    [Paragraph("Last 5% CO₂ reduction is very expensive", sb),
     Paragraph("A 95% target + imports or demand response may be more cost-effective than 100% local", sb)],
    [Paragraph("Solar is systemically critical despite low CF", sb),
     Paragraph("Protect solar area — complementarity with wind reduces storage needs", sb)],
    [Paragraph("Nuclear only competitive below ~5,000 €/kW", sb),
     Paragraph("Current European projects not justified without an explicit CO₂ price", sb)],
    [Paragraph("Technology costs fall dramatically by 2050", sb),
     Paragraph("Continued R&amp;D investment accelerates the transition — timing matters", sb)],
    [Paragraph("Spatial planning is critical", sb),
     Paragraph("Proactive designation of renewable zones is as important as technology cost reductions", sb)],
]
st = Table(sd, colWidths=[6*cm, PW-6*cm])
st.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),(-1,0), DB),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LB]),
    ("TOPPADDING",    (0,0),(-1,-1), 6),
    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ("RIGHTPADDING",  (0,0),(-1,-1), 8),
    ("BOX",           (0,0),(-1,-1), 0.5, MB),
    ("LINEBELOW",     (0,0),(-1,-1), 0.3, HexColor("#cccccc")),
    ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ("FONTNAME",      (0,1),(0,-1), "Helvetica-Bold"),
    ("TEXTCOLOR",     (0,1),(0,-1), DB),
]))
story.append(st)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "Model: PyPSA | Solver: Gurobi 13 | Weather: ERA5 2012 | "
    "Eligibility: Copernicus Land Cover, WDPA, GEBCO, Marine Regions EEZ | "
    "Technology costs: PyPSA/technology-data 2025 | Discount rate: 7%",
    T_FOOT))

# ── Build ──────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=landscape(A4),
    topMargin=1.5*cm, bottomMargin=1.5*cm,
    leftMargin=2*cm, rightMargin=2*cm,
    title="Modelling a Zero-Carbon Electricity System for Denmark",
    author="Group Assignment 4 — Data Science for Energy System Modelling SS2026",
)
doc.build(story)
print(f"✓ PDF saved to {OUT}")