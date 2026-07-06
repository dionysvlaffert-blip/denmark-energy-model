"""
create_pdf_with_plots.py
Creates a complete PDF report combining all plots with interpretations.
Place in project root and run:
    python create_pdf_with_plots.py
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
FIG_DIR = "results/figures"
PDF_PATH = "results/denmark_complete_analysis.pdf"
os.makedirs("results", exist_ok=True)

# ── Colors ─────────────────────────────────────────────────────────────────────
DARK_BLUE   = HexColor("#1a3a5c")
MID_BLUE    = HexColor("#2171b5")
LIGHT_BLUE  = HexColor("#deebf7")
GREEN       = HexColor("#41ab5d")
LIGHT_GREEN = HexColor("#e5f5e0")
ORANGE      = HexColor("#d94801")
LIGHT_GREY  = HexColor("#f5f5f5")
MID_GREY    = HexColor("#636363")

PAGE_W = landscape(A4)[0] - 4*cm

# ── Styles ─────────────────────────────────────────────────────────────────────
title_style = ParagraphStyle(
    "T", fontSize=22, fontName="Helvetica-Bold",
    textColor=DARK_BLUE, alignment=TA_CENTER, leading=28, spaceAfter=6,
)
subtitle_style = ParagraphStyle(
    "S", fontSize=12, fontName="Helvetica",
    textColor=MID_GREY, alignment=TA_CENTER, leading=16, spaceAfter=4,
)
section_para = ParagraphStyle(
    "SP", fontSize=11, fontName="Helvetica-Bold",
    textColor=white, leading=15,
)
label_style = ParagraphStyle(
    "L", fontSize=8, fontName="Helvetica-Bold",
    textColor=MID_BLUE, spaceAfter=2, leading=11,
)
cond_style = ParagraphStyle(
    "C", fontSize=8.5, fontName="Helvetica",
    textColor=HexColor("#1a3a1a"), leading=13, wordWrap="CJK",
)
h_label_style = ParagraphStyle(
    "HL", fontSize=8.5, fontName="Helvetica-Bold",
    textColor=white, leading=12, wordWrap="CJK",
)
h_text_style = ParagraphStyle(
    "HT", fontSize=8.5, fontName="Helvetica",
    textColor=HexColor("#111111"), leading=13,
    wordWrap="CJK", alignment=TA_JUSTIFY,
)
kf_style = ParagraphStyle(
    "KF", fontSize=8.5, fontName="Helvetica",
    textColor=DARK_BLUE, leading=13, wordWrap="CJK",
)
caption_style = ParagraphStyle(
    "CAP", fontSize=8, fontName="Helvetica",
    textColor=MID_GREY, alignment=TA_CENTER, leading=11,
)

# ── Helpers ────────────────────────────────────────────────────────────────────
def section_header(text, color=DARK_BLUE):
    data = [[Paragraph(text, section_para)]]
    t = Table(data, colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), color),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ]))
    return t

def conditions_box(conditions):
    rows = [[Paragraph(f"&#8226;  {c}", cond_style)] for c in conditions]
    t = Table(rows, colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_GREEN),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 0.5, GREEN),
        ("LINEBELOW",     (0,0), (-2,-1), 0.3, HexColor("#b7e4c7")),
    ]))
    return t

def hypothesis_table(hypotheses):
    rows = [[Paragraph(f"<b>{h}</b>", h_label_style),
             Paragraph(text, h_text_style)] for h, text in hypotheses]
    t = Table(rows, colWidths=[1.2*cm, PAGE_W - 1.2*cm])
    cmds = [
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("GRID",          (0,0), (-1,-1), 0.3, HexColor("#cccccc")),
    ]
    for i in range(len(rows)):
        cmds.append(("BACKGROUND", (0,i), (0,i), MID_BLUE if i%2==0 else DARK_BLUE))
        cmds.append(("BACKGROUND", (1,i), (1,i), LIGHT_BLUE if i%2==0 else HexColor("#f0f7ff")))
    t.setStyle(TableStyle(cmds))
    return t

def key_finding(text):
    data = [[Paragraph(f"<b>Key Finding:</b>  {text}", kf_style)]]
    t = Table(data, colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), HexColor("#fff8e1")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 1, HexColor("#ffc107")),
    ]))
    return t

def add_plot(story, filename, caption="", width=25*cm, height=15*cm):
    """Add a plot image if it exists."""
    path = f"{FIG_DIR}/{filename}"
    if os.path.exists(path):
        story.append(Image(path, width=width, height=height))
        if caption:
            story.append(Paragraph(caption, caption_style))
        story.append(Spacer(1, 0.2*cm))
    else:
        story.append(Paragraph(f"[Plot not found: {filename}]",
                                ParagraphStyle("NF", fontSize=8, textColor=ORANGE)))

# ══════════════════════════════════════════════════════════════════════════════
# PLOT DATA
# ══════════════════════════════════════════════════════════════════════════════
plots = [
    {
        "num": "00",
        "title": "Baseline Scenario — Full System Overview",
        "file": "00_base_scenario_detail.png",
        "color": DARK_BLUE,
        "conditions": [
            "No CO<sub>2</sub> emission constraint — existing fossil fleet operates freely",
            "Existing coal (5,089 MW), gas (571 MW), oil (664 MW), biomass (88 MW) as fixed capacity",
            "Renewables (solar, onshore wind, offshore wind) extendable from 0 MW",
            "Technology costs: PyPSA/technology-data 2025 projections, 7% discount rate",
        ],
        "hypotheses": [
            ("H1", "Coal dominates (92% of generation) because existing plants are fully amortised — only variable fuel costs apply, making coal the cheapest dispatchable option."),
            ("H2", "Storage is barely used — coal provides all balancing services, making batteries and hydrogen economically unnecessary."),
            ("H3", "Regional generation reflects population distribution — Midtjylland and Syddanmark (large Jutland regions) contribute most generation."),
        ],
        "finding": "The Baseline reveals Denmark's current system reality: fossil plants built decades ago still define the electricity mix due to their low operating costs. The energy transition requires replacing this 'free' baseload with new renewable investment.",
    },
    {
        "num": "01",
        "title": "Electricity Mix: Baseline vs Zero CO<sub>2</sub>",
        "file": "01_mix_baseline_vs_zero_co2.png",
        "color": DARK_BLUE,
        "conditions": [
            "Baseline: no CO<sub>2</sub> limit — existing fossil fleet operates freely",
            "Zero CO<sub>2</sub>: emissions constrained to exactly 0 tonnes/year",
            "New renewables (solar max 86,190 MW, onshore wind 11,655 MW, offshore wind 114,975 MW) — updated from eligibility analysis",
        ],
        "hypotheses": [
            ("H1", "Without a CO<sub>2</sub> limit, coal dominates because existing plants are fully amortised — only variable fuel costs apply."),
            ("H2", "Zero CO<sub>2</sub> requires building large amounts of wind and solar capacity and storage, driving up total system cost."),
            ("H3", "Zero CO<sub>2</sub> produces slightly more electricity than the Baseline because renewable overproduction charges storage, leading to curtailment losses."),
        ],
        "finding": "The 379% cost increase represents the investment cost of the energy transition — not its true societal cost, since carbon damage from the Baseline is not priced into the model.",
    },
    {
        "num": "02",
        "title": "Installed Capacities: Baseline vs Zero CO<sub>2</sub>",
        "file": "02_capacities_baseline_vs_zero_co2.png",
        "color": DARK_BLUE,
        "conditions": [
            "Baseline: fixed conventional fleet + minimal new renewables",
            "Zero CO<sub>2</sub>: full renewable buildout required",
            "Updated potentials from eligibility analysis (86 GW solar, 11.6 GW onshore, 115 GW offshore)",
        ],
        "hypotheses": [
            ("H1", "Zero CO<sub>2</sub> requires massive new renewable capacity while fossil plants remain physically installed but idle."),
            ("H2", "Battery storage is the largest new capacity addition in Zero CO<sub>2</sub> — needed to balance variable wind and solar output."),
            ("H3", "Offshore wind dominates the Zero CO<sub>2</sub> capacity mix because Denmark has exceptional North Sea and Baltic Sea wind resources."),
        ],
        "finding": "Zero CO<sub>2</sub> does not demolish existing plants — it builds a parallel renewable system on top. The fossil fleet remains as stranded assets.",
    },
    {
        "num": "03",
        "title": "Grid Expansion Sensitivity",
        "file": "03_grid_sensitivity.png",
        "color": MID_BLUE,
        "conditions": [
            "Three scenarios: full expansion (unconstrained), max 1 GW per line, autarky (no transmission)",
            "Zero CO<sub>2</sub> constraint active in all scenarios",
            "5 regions connected by 5 bidirectional links; 700 &#8364;/MW/km x 1.5 route factor",
        ],
        "hypotheses": [
            ("H1", "Full expansion and Max 1 GW cost identically — Denmark is small enough that 1 GW per corridor is sufficient."),
            ("H2", "Autarky costs 41% more because each region must independently balance its own supply and demand without importing surpluses from neighbours."),
            ("H3", "The generation mix is similar across scenarios — the difference is the cost of balancing, not the amount of renewables built."),
        ],
        "finding": "Transmission is highly valuable but reaches diminishing returns quickly. Denmark needs at most 1 GW per corridor — further grid expansion beyond this yields no cost savings.",
    },
    {
        "num": "03b",
        "title": "Annual Generation &amp; Demand Throughout the Year",
        "file": "03b_annual_generation_demand.png",
        "color": MID_BLUE,
        "conditions": [
            "Weekly averages of hourly generation and demand for the full 2012 weather year",
            "Baseline (top panel) and Zero CO<sub>2</sub> (bottom panel) compared",
            "Demand shown as dashed black line",
        ],
        "hypotheses": [
            ("H1", "In the Baseline, coal provides flat baseload throughout the year while wind provides variable top-up. The system is simple and predictable."),
            ("H2", "In Zero CO<sub>2</sub>, wind dominates winter months (high wind speeds) while solar contributes in summer. The system has strong seasonal variation."),
            ("H3", "Zero CO<sub>2</sub> shows generation frequently exceeding demand — these surpluses charge storage or are curtailed, explaining the higher total generation."),
        ],
        "finding": "The annual generation profile reveals the complementarity of wind (winter) and solar (summer) — together they provide more uniform coverage than either alone, reducing storage requirements.",
    },
    {
        "num": "04",
        "title": "Solar CAPEX Sensitivity",
        "file": "04_solar_capex_sensitivity.png",
        "color": HexColor("#b8860b"),
        "conditions": [
            "Solar capital cost reduced from 100% to 0% in 25% steps",
            "Zero CO<sub>2</sub> constraint active",
            "Solar maximum: 86,190 MW (from updated eligibility analysis)",
            "Other technologies remain at base costs",
        ],
        "hypotheses": [
            ("H1", "System cost falls as solar becomes cheaper, but the effect is moderate because solar has a low capacity factor (~11%) at Denmark's 55&#176;N latitude."),
            ("H2", "Solar capacity increases as CAPEX falls — unlike before with the old (too low) potential limits, the system can now build more solar."),
            ("H3", "Wind and battery capacities adjust as solar fills more of the generation mix, showing the substitution relationship between technologies."),
        ],
        "finding": "With corrected (larger) solar potentials, solar CAPEX reduction now has a meaningful effect. Denmark can deploy significantly more solar than previously modelled.",
    },
    {
        "num": "05",
        "title": "Wind CAPEX Sensitivity",
        "file": "05_wind_capex_sensitivity.png",
        "color": HexColor("#41ab5d"),
        "conditions": [
            "Onshore and offshore wind CAPEX reduced simultaneously from 100% to 0%",
            "Zero CO<sub>2</sub> constraint active",
            "Onshore max: 11,655 MW; Offshore max: 114,975 MW (from eligibility analysis)",
        ],
        "hypotheses": [
            ("H1", "Wind CAPEX reduction delivers the largest system cost savings of all CAPEX sensitivities, confirming wind as Denmark's dominant renewable technology."),
            ("H2", "Offshore wind deployment increases strongly as CAPEX falls — the North Sea has enormous potential that becomes economical at lower costs."),
            ("H3", "Battery storage decreases as wind becomes cheaper, because cheaper wind reduces the cost of overbuilding to cover demand gaps."),
        ],
        "finding": "Offshore wind cost reduction is the single most impactful lever for Denmark's energy system. The enormous offshore potential (115 GW) means cost reductions translate directly into large deployment increases.",
    },
    {
        "num": "06",
        "title": "Battery CAPEX Sensitivity",
        "file": "06_battery_capex_sensitivity.png",
        "color": ORANGE,
        "conditions": [
            "Battery storage capital cost reduced from 100% to 0% in 25% steps",
            "Battery storage in 2h, 4h, 6h variants; hydrogen storage also available",
            "Zero CO<sub>2</sub> constraint active",
        ],
        "hypotheses": [
            ("H1", "Batteries are the largest cost driver in Zero CO<sub>2</sub> — halving battery costs nearly halves total system costs."),
            ("H2", "At 0% battery CAPEX, enormous battery capacity is installed, replacing hydrogen and even substituting for transmission."),
            ("H3", "Hydrogen storage decreases as batteries get cheaper — batteries can serve both short-term and long-term storage when cost allows."),
        ],
        "finding": "Battery storage cost is the critical variable for Denmark's energy transition. Technological breakthroughs in batteries would be more transformative than equivalent reductions in wind or solar costs.",
    },
    {
        "num": "07",
        "title": "Transmission CAPEX Sensitivity",
        "file": "07_transmission_capex_sensitivity.png",
        "color": MID_GREY,
        "conditions": [
            "Transmission cost reduced from 700 &#8364;/MW/km (x1.5) to 0 in 25% steps",
            "Zero CO<sub>2</sub> constraint active",
        ],
        "hypotheses": [
            ("H1", "Cheaper transmission leads to more grid buildout and slightly lower system costs."),
            ("H2", "The effect is modest because Denmark's compact geography is already well-interconnected at current costs."),
            ("H3", "Transmission and storage are economic substitutes — cheaper lines reduce storage needs."),
        ],
        "finding": "Transmission costs matter less for Denmark's compact geography. The key benefit of cheaper lines is reduced local storage requirements rather than enabling new renewable deployment.",
    },
    {
        "num": "08",
        "title": "Nuclear CAPEX Sensitivity (No CO<sub>2</sub> Limit)",
        "file": "08_nuclear_sensitivity.png",
        "color": HexColor("#2d6a4f"),
        "conditions": [
            "Nuclear generators added with capital costs from 2,500 to 10,000 &#8364;/kW",
            "No CO<sub>2</sub> constraint — nuclear competes with coal and gas",
            "Nuclear: zero CO<sub>2</sub> emissions, 60-year lifetime, 2% FOM",
        ],
        "hypotheses": [
            ("H1", "Nuclear is competitive only below ~5,000 &#8364;/kW when competing against coal — above this threshold coal's low operating cost wins."),
            ("H2", "At 2,500 &#8364;/kW, nuclear displaces wind almost entirely because it provides firm baseload without requiring storage."),
            ("H3", "Current European nuclear costs (8,000-12,000 &#8364;/kW) are well above the competitive threshold against fossil fuels."),
        ],
        "finding": "Without a carbon price, nuclear is only economic at capital costs well below current European build costs. A CO<sub>2</sub> price would substantially alter this calculation.",
    },
    {
        "num": "09",
        "title": "Nuclear + Grid Expansion Combined",
        "file": "09_nuclear_grid_combined.png",
        "color": HexColor("#1b4332"),
        "conditions": [
            "Nuclear at varying CAPEX combined with 1 GW/line grid limit",
            "Zero CO<sub>2</sub> constraint active",
            "Compared against baseline network (full expansion) nuclear scenarios",
        ],
        "hypotheses": [
            ("H1", "With the baseline network, nuclear is barely needed even at 2,500 &#8364;/kW — wind can be transported efficiently from anywhere."),
            ("H2", "With a 1 GW grid limit, nuclear is built at ALL tested capital costs because regions need local firm capacity."),
            ("H3", "Transmission and nuclear are strategic substitutes — grid expansion makes nuclear less necessary; grid constraints make nuclear more valuable."),
        ],
        "finding": "The nuclear vs. renewables debate cannot be separated from grid policy. Grid expansion and nuclear power serve the same function — ensuring regional supply security.",
    },
    {
        "num": "10",
        "title": "Solar Potential Sensitivity",
        "file": "10_solar_potential_sensitivity.png",
        "color": HexColor("#b8860b"),
        "conditions": [
            "Solar p_nom_max reduced from 100% to 0% of eligible area",
            "Wind potentials remain at maximum throughout",
            "Zero CO<sub>2</sub> constraint active",
        ],
        "hypotheses": [
            ("H1", "System costs rise steeply as solar area is restricted because wind is already near its maximum and cannot compensate."),
            ("H2", "Battery storage increases dramatically as solar decreases — the system compensates with more storage."),
            ("H3", "Solar is systemically critical despite its low capacity factor — it provides complementary daytime generation that reduces storage needs."),
        ],
        "finding": "Solar area restrictions are very costly. Even though solar has a low capacity factor at 55&#176;N, its complementarity with wind is essential for the system.",
    },
    {
        "num": "11",
        "title": "Onshore Wind Potential Sensitivity",
        "file": "11_onshore_potential_sensitivity.png",
        "color": HexColor("#41ab5d"),
        "conditions": [
            "Onshore wind p_nom_max reduced from 100% to 0%",
            "Offshore wind and solar remain at maximum",
            "Zero CO<sub>2</sub> constraint active",
        ],
        "hypotheses": [
            ("H1", "Restricting onshore wind forces more offshore wind and solar deployment as substitutes."),
            ("H2", "With the updated larger potentials, the system can now compensate for onshore restrictions — unlike previously when all technologies were at their limits simultaneously."),
            ("H3", "Offshore wind is the natural substitute for onshore wind in Denmark, given the enormous North Sea potential."),
        ],
        "finding": "With correct (larger) potentials, onshore wind restrictions are no longer immediately infeasible. Offshore wind can substitute effectively, though at higher cost.",
    },
    {
        "num": "12",
        "title": "All Renewables Potential Sensitivity",
        "file": "12_all_renewables_potential_sensitivity.png",
        "color": HexColor("#41ab5d"),
        "conditions": [
            "Solar, onshore and offshore wind all reduced simultaneously",
            "Worst-case land scarcity scenario",
            "Zero CO<sub>2</sub> constraint active",
        ],
        "hypotheses": [
            ("H1", "When all renewables are restricted together, costs rise sharply as no substitution is possible between technologies."),
            ("H2", "Storage (batteries and hydrogen) increases dramatically to time-shift the scarce renewable generation."),
            ("H3", "This scenario illustrates the importance of proactive spatial planning — protecting renewable energy zones is critical for affordable decarbonisation."),
        ],
        "finding": "Spatial planning for renewable energy is as important as technology cost reductions. A coordinated national strategy for wind and solar zones is essential.",
    },
    {
        "num": "13",
        "title": "CO<sub>2</sub> Decarbonisation Pathway",
        "file": "13_co2_reduction_pathway.png",
        "color": HexColor("#145a32"),
        "conditions": [
            "CO<sub>2</sub> reduced in steps: 0%, 20%, 40%, 60%, 80%, 95%, 100%",
            "Existing fossil fleet included; CO<sub>2</sub> limit as global constraint",
            "Full grid expansion, all technologies available",
        ],
        "hypotheses": [
            ("H1", "The first 60% of CO<sub>2</sub> reduction is cheap because wind directly replaces coal with minimal storage needs."),
            ("H2", "The last 5% (95% to 100%) costs more than the first 80% combined — rare winter dark-doldrums require enormous storage for very few hours."),
            ("H3", "Battery storage stays near zero until 80% reduction, then rises sharply — storage is only needed when all fossil backup is removed."),
        ],
        "finding": "The law of increasing marginal abatement costs is stark. A pragmatic 80-95% target is dramatically cheaper than 100%, and remaining emissions could be addressed through imports or demand response.",
    },
    {
        "num": "14a",
        "title": "Dispatch Profile: Zero CO<sub>2</sub> Scenario",
        "file": "14_dispatch_seasonal_zero_co2.png",
        "color": MID_BLUE,
        "conditions": [
            "Average daily dispatch profile by season (winter Dec-Feb, summer Jun-Aug)",
            "Zero CO<sub>2</sub> scenario — no fossil generation",
            "X-axis: hour of day (0-23); Y-axis: average power in GW",
        ],
        "hypotheses": [
            ("H1", "Winter dispatch is dominated by wind with relatively flat profile — wind does not follow daily patterns like solar."),
            ("H2", "Summer dispatch shows a clear solar peak at midday, with wind providing baseload and storage smoothing the evening ramp-down."),
            ("H3", "Demand (dashed line) is relatively constant throughout the day, meaning storage must bridge the gap between variable renewable output and stable demand."),
        ],
        "finding": "The seasonal dispatch reveals the fundamental challenge: in winter the system is wind-heavy and storage cycles rapidly; in summer solar creates a midday surplus that must be stored for evening and night.",
    },
    {
        "num": "14b",
        "title": "Dispatch Profile: Baseline Scenario",
        "file": "14_dispatch_seasonal_baseline.png",
        "color": HexColor("#252525"),
        "conditions": [
            "Average daily dispatch profile by season",
            "Baseline scenario — coal provides flat baseload",
            "Wind provides variable supplementary generation",
        ],
        "hypotheses": [
            ("H1", "Coal runs as near-constant baseload in both seasons, with wind providing variable top-up."),
            ("H2", "Storage is barely visible in the Baseline — coal absorbs all variability, making storage economically unnecessary."),
            ("H3", "The contrast with Zero CO<sub>2</sub> dispatch is stark: the Baseline system is simple and predictable; Zero CO<sub>2</sub> is complex and storage-dependent."),
        ],
        "finding": "The Baseline dispatch illustrates why coal is so economically attractive in models without carbon pricing — it is perfectly controllable and requires no complementary investments in storage or grid.",
    },
    {
        "num": "15a",
        "title": "Storage Levels &amp; Generation: Zero CO<sub>2</sub>",
        "file": "15_storage_zero_co2.png",
        "color": ORANGE,
        "conditions": [
            "Weekly averages of wind/solar generation and storage state-of-charge",
            "Top: wind and solar generation; Middle: battery SOC; Bottom: hydrogen SOC",
            "Zero CO<sub>2</sub> scenario",
        ],
        "hypotheses": [
            ("H1", "Wind peaks in winter (high generation, high battery cycling) and solar peaks in summer — their complementarity reduces storage requirements."),
            ("H2", "Hydrogen accumulates in spring/summer when renewables exceed demand and discharges in autumn/winter — classic seasonal storage pattern."),
            ("H3", "Battery cycles rapidly week-to-week following wind patterns, while hydrogen cycles slowly on a seasonal timescale — clear division of labour."),
        ],
        "finding": "The storage profiles reveal the two-tier storage system: batteries for short-term (days/weeks) balancing and hydrogen for seasonal (months) balancing. Wind and solar generation drives both storage cycles.",
    },
    {
        "num": "15b",
        "title": "Storage Levels &amp; Generation: Baseline",
        "file": "15_storage_baseline.png",
        "color": HexColor("#252525"),
        "conditions": [
            "Baseline scenario — coal provides baseload",
            "Storage barely used",
        ],
        "hypotheses": [
            ("H1", "Battery activity is minimal and concentrated in winter months when wind occasionally produces surplus."),
            ("H2", "Hydrogen storage is essentially unused — coal makes seasonal storage completely unnecessary."),
            ("H3", "The near-zero storage in Baseline vs the large storage in Zero CO<sub>2</sub> quantifies exactly how much flexibility coal provides."),
        ],
        "finding": "Coal is a near-perfect substitute for storage. Removing coal transfers its entire balancing function to batteries and hydrogen — at significant additional cost.",
    },
    {
        "num": "16",
        "title": "System Cost Overview: All Scenarios",
        "file": "16_cost_summary_descending.png",
        "color": DARK_BLUE,
        "conditions": [
            "All solved scenarios compared in descending cost order",
            "Costs in Billion &#8364;/year (annualised investment + operating costs at 7% discount rate)",
            "Technology costs: 2025 projections",
        ],
        "hypotheses": [
            ("H1", "Autarky is the most expensive real-world scenario — transmission is the most cost-effective flexibility resource available."),
            ("H2", "Wind CAPEX reduction delivers the largest savings of any sensitivity, reflecting wind's dominant role in Denmark's renewable mix."),
            ("H3", "CO<sub>2</sub> pathway scenarios show 60% decarbonisation is affordable; the last 40% costs disproportionately more."),
        ],
        "finding": "Three key policy recommendations: (1) invest in transmission before local storage; (2) prioritise wind cost reduction; (3) consider a phased 80-95% target supplemented by flexible demand or imports.",
    },
    {
        "num": "18",
        "title": "Sensitivity 6: Technology Cost Year Variations",
        "file": "18_sensitivity_tech_years.png",
        "color": MID_BLUE,
        "conditions": [
            "Technology costs from 2020, 2025, 2030, 2040, 2050 projections (PyPSA/technology-data)",
            "Zero CO<sub>2</sub> constraint active",
            "Weather year 2012, 3h resolution throughout",
        ],
        "hypotheses": [
            ("H1", "System costs decrease significantly from 2020 to 2050 as all technologies — wind, solar, batteries — become cheaper over time."),
            ("H2", "Renewable capacity increases in later years as falling costs make it optimal to overbuild rather than invest in storage."),
            ("H3", "Battery storage increases in later years as falling battery costs make it economical to deploy more short-term storage."),
        ],
        "finding": "Technology learning curves substantially reduce the cost of zero-carbon electricity over time. The 2050 system is dramatically cheaper than 2020, highlighting the importance of continued R&amp;D investment.",
    },
    {
        "num": "19",
        "title": "Sensitivity 7: Temporal Resolution",
        "file": "19_sensitivity_time_resolution.png",
        "color": MID_GREY,
        "conditions": [
            "Model solved at 1h, 2h, 3h, 6h temporal resolution",
            "Zero CO<sub>2</sub> constraint active",
            "Same weather year 2012 and technology costs throughout",
        ],
        "hypotheses": [
            ("H1", "System costs are relatively stable across resolutions — the model captures the same fundamental trade-offs at all temporal scales."),
            ("H2", "Storage requirements may decrease at coarser resolutions (6h) as sub-hourly variability is averaged out."),
            ("H3", "The 3h resolution used throughout this study is a reasonable compromise between computational cost and model accuracy."),
        ],
        "finding": "Temporal resolution has limited impact on system costs for this model, validating the choice of 3h resolution. Finer resolution (1h) captures more variability but increases computation time significantly.",
    },
]

# ══════════════════════════════════════════════════════════════════════════════
# BUILD PDF
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ── Cover ──────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 2*cm))
story.append(Paragraph("Modelling a Zero-Carbon Electricity System for Denmark", title_style))
story.append(Paragraph("Scenarios, Sensitivities &amp; Key Findings", ParagraphStyle(
    "ST2", fontSize=15, fontName="Helvetica-Bold", textColor=MID_BLUE,
    alignment=TA_CENTER, spaceAfter=6, leading=20)))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=2, color=MID_BLUE))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Data Science for Energy System Modelling — Summer Term 2026 | Group Assignment 4",
    subtitle_style))
story.append(Spacer(1, 1.5*cm))

cover_key = ParagraphStyle("CK", fontSize=10, fontName="Helvetica-Bold", textColor=DARK_BLUE)
cover_val = ParagraphStyle("CV", fontSize=10, fontName="Helvetica", textColor=HexColor("#333333"))
cover_data = [
    [Paragraph("Country", cover_key),             Paragraph("Denmark (5 GADM-1 regions)", cover_val)],
    [Paragraph("Weather Year", cover_key),         Paragraph("2012 (ERA5 reanalysis)", cover_val)],
    [Paragraph("Temporal Resolution", cover_key),  Paragraph("3-hourly (2,920 timesteps/year)", cover_val)],
    [Paragraph("Solver", cover_key),               Paragraph("Gurobi 13 (academic license)", cover_val)],
    [Paragraph("Technology Data", cover_key),      Paragraph("PyPSA/technology-data 2025 projections", cover_val)],
    [Paragraph("Discount Rate", cover_key),        Paragraph("7% (annualises all capital investment costs)", cover_val)],
    [Paragraph("Renewable Potentials", cover_key), Paragraph("From land eligibility analysis: solar 86,190 MW | onshore wind 11,655 MW | offshore wind 114,975 MW", cover_val)],
    [Paragraph("Total Scenarios", cover_key),      Paragraph("70+ network files across 19 plot categories", cover_val)],
]
ct = Table(cover_data, colWidths=[5*cm, PAGE_W - 5*cm])
ct.setStyle(TableStyle([
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ("RIGHTPADDING",  (0,0), (-1,-1), 10),
    ("ROWBACKGROUNDS",(0,0), (-1,-1), [white, LIGHT_GREY]),
    ("BOX",           (0,0), (-1,-1), 1, MID_BLUE),
    ("LINEBELOW",     (0,0), (-2,-1), 0.3, HexColor("#cccccc")),
]))
story.append(ct)
story.append(PageBreak())

# ── Plot sections ──────────────────────────────────────────────────────────────
for plot in plots:
    # Section header
    story.append(section_header(
        f"Plot {plot['num']} — {plot['title']}", plot["color"]))
    story.append(Spacer(1, 0.2*cm))

    # Plot image
    add_plot(story, plot["file"], width=PAGE_W, height=14*cm)

    # Conditions
    story.append(Paragraph("Modelling Conditions", label_style))
    story.append(conditions_box(plot["conditions"]))
    story.append(Spacer(1, 0.15*cm))

    # Hypotheses
    story.append(Paragraph("Interpretation &amp; Hypotheses", label_style))
    story.append(hypothesis_table(plot["hypotheses"]))
    story.append(Spacer(1, 0.15*cm))

    # Key finding
    story.append(key_finding(plot["finding"]))
    story.append(PageBreak())

# ── Summary ────────────────────────────────────────────────────────────────────
story.append(section_header("Overall Conclusions &amp; Policy Implications"))
story.append(Spacer(1, 0.3*cm))

sh = ParagraphStyle("SH", fontSize=9, fontName="Helvetica-Bold", textColor=white, leading=13, wordWrap="CJK")
sb = ParagraphStyle("SB", fontSize=9, fontName="Helvetica", textColor=HexColor("#111111"), leading=14, wordWrap="CJK")
summary_data = [
    [Paragraph("Key Finding", sh), Paragraph("Policy Implication", sh)],
    [Paragraph("Wind is Denmark's key technology", sb),
     Paragraph("Prioritise offshore wind cost reduction and protect North Sea wind zones", sb)],
    [Paragraph("Storage is the main cost driver", sb),
     Paragraph("Battery R&amp;D investment is critical — halving battery costs halves system costs", sb)],
    [Paragraph("Transmission replaces storage", sb),
     Paragraph("Grid buildout delivers better value than local autarky — regional integration is essential", sb)],
    [Paragraph("Last 5% CO<sub>2</sub> reduction very expensive", sb),
     Paragraph("A 95% target plus imports or demand response may be more cost-effective than 100% local", sb)],
    [Paragraph("Solar is systemically critical", sb),
     Paragraph("Protect solar area — complementarity with wind reduces storage requirements", sb)],
    [Paragraph("Nuclear only competitive below ~5,000 &#8364;/kW", sb),
     Paragraph("Current European projects not economically justified without a CO<sub>2</sub> price", sb)],
    [Paragraph("Technology costs fall significantly by 2050", sb),
     Paragraph("Continued R&amp;D investment accelerates the energy transition — timing matters", sb)],
    [Paragraph("3h resolution is sufficient", sb),
     Paragraph("Model results are robust to temporal resolution — computational efficiency validated", sb)],
]
st = Table(summary_data, colWidths=[6*cm, PAGE_W - 6*cm])
st.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), DARK_BLUE),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [white, LIGHT_BLUE]),
    ("TOPPADDING",    (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ("RIGHTPADDING",  (0,0), (-1,-1), 8),
    ("BOX",           (0,0), (-1,-1), 0.5, MID_BLUE),
    ("LINEBELOW",     (0,0), (-1,-1), 0.3, HexColor("#cccccc")),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ("FONTNAME",      (0,1), (0,-1), "Helvetica-Bold"),
    ("TEXTCOLOR",     (0,1), (0,-1), DARK_BLUE),
]))
story.append(st)
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    "Model: PyPSA | Solver: Gurobi 13 | Weather: ERA5 2012 | "
    "Eligibility: Copernicus Land Cover, WDPA, GEBCO, Marine Regions | "
    "Technology costs: PyPSA/technology-data 2025",
    ParagraphStyle("F", fontSize=7, fontName="Helvetica",
                   textColor=MID_GREY, alignment=TA_CENTER)))

# ── Build ──────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    PDF_PATH,
    pagesize=landscape(A4),
    topMargin=1.5*cm, bottomMargin=1.5*cm,
    leftMargin=2*cm,  rightMargin=2*cm,
    title="Modelling a Zero-Carbon Electricity System for Denmark",
    author="Group Assignment 4 — Data Science for Energy System Modelling SS2026",
)
doc.build(story)
print(f"✓ PDF saved to {PDF_PATH}")
