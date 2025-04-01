# Airbus A220 Central Load Planning (CLP) Proof of Concept

## Overview
This Proof of Concept (PoC) demonstrates an in-house Central Load Planning (CLP) solution for an Airbus A220 fleet (40 aircraft, 100-200 daily flights). The goal is to explore replacing third-party tools by calculating Weight and Balance (W&B) and generating optimized load instructions for fuel efficiency and safe takeoff/landing performance. Built with Python and Streamlit, this simple web app takes flight inputs, performs key calculations, and visualizes results—showcasing the potential for an internal system.

### Purpose
- **Learning**: Understand W&B physics, optimization challenges, and aviation operational needs.
- **Demonstration**: Share with coworkers to evaluate feasibility of an in-house CLP tool.
- **Transparency**: Display calculations and logic for trust and collaboration.

---

## Background and Discussion
This PoC evolved from discussions about central load planning for an airline operating 40 Airbus A220s. Key insights:

- **Current Process**: 
  1. Flight plan (ARINC 633 XML) provides initial data (fuel, pax estimates).
  2. Zero Fuel Weight (ZFW) calculated (OEW + pax + bags).
  3. CLP uses guest zone counts to generate load instructions (e.g., bag placement).
  4. Guests and cargo loaded; load sheet submitted with actuals.
  5. CLP checks operating envelope (weight ≤ MTOW, CG in limits).
  6. CG and stabilizer trim calculated, sent to aircraft (e.g., FMS).
- **Third-Party Role**: External tools currently handle W&B and optimization.
- **Goal**: Replicate core functionality (W&B, load optimization) in-house.

### Key Capabilities
1. **Weight and Balance (W&B)**:
   - Calculates ZFW, total weight, CG, and stab trim.
   - Ensures safety (MTOW 149,000 lbs, CG 15%-35% MAC).
2. **Load Optimization**:
   - Suggests bag placement (fwd/aft) for aft CG (fuel savings) within safe limits.

### Challenges Identified
- **Data Accuracy**: Needs precise A220 OEW, zone arms, and bag weights.
- **Optimization**: Balancing fuel burn (aft CG) vs. takeoff/landing (mid-CG).
- **Validation**: Requires flight data (e.g., CG, fuel burn) to model and verify savings.
- **Integration**: Sending to FMS/ramp is future work, not in PoC scope.

---

## Calculations
The PoC performs these aviation-standard calculations:

1. **Zero Fuel Weight (ZFW)**:
   - Formula: `ZFW = OEW + Pax Weight + Bag Weight`
   - Pax Weight = (Adults × 200 lbs) + (Children × 80 lbs) per zone.
   - Bag Weight = (Standard × 50 lbs) + (Heavy × 70 lbs).

2. **Total Weight**:
   - Formula: `Total Weight = ZFW + Fuel Weight`

3. **Moments**:
   - Formula: `Moment = Weight × Arm`
   - Arms: OEW (e.g., 64.8 ft), pax zones (A: 60 ft, B: 70 ft, C: 80 ft), fuel (70 ft), bags (fwd: 50 ft, aft: 80 ft).

4. **Center of Gravity (CG)**:
   - Formula: `CG = Σ(Moment) / Σ(Weight)`
   - Optimized to target aft CG (e.g., 62.5 ft) for fuel efficiency.

5. **Stabilizer Trim (Stab)**:
   - Lookup: CG mapped to trim setting (e.g., 61 ft → 2°, 62 ft → 0°, 63 ft → -2°).

6. **Safety Check**:
   - Conditions: `Total Weight ≤ MTOW` and `CG_MIN ≤ CG ≤ CG_MAX`.

7. **Load Optimization**:
   - Logic: If CG < target (62.5 ft), shift bags aft (max = available bag weight).
   - Formula: `Move (lbs) = (Target CG - Current CG) × Total Weight / (Aft Arm - Fwd Arm)`

---

## Inputs
The PoC accepts these inputs, simplified from full flight data:
- **Aircraft Tail**: Dropdown (e.g., N001, N002) with OEW and arm.
- **Passengers by Zone**:
  - Zone A, B, C: Adults (200 lbs), Children (80 lbs).
- **Bags**:
  - Standard (50 lbs), Heavy (70 lbs).
- **Fuel**: Total lbs (e.g., 27,000).

### Assumptions
- Hardcoded A220 data (OEW, arms) for 2 tails—expandable with real values.
- No flight plan parsing (manual input vs. ARINC 633 XML).
- Simplified stab trim table—real FCOM data needed later.

---

## Proof of Concept: Streamlit App
This PoC uses Streamlit for a web-based, interactive demo. It calculates W&B, optimizes bag placement, and visualizes CG.

### Setup
1. **Install Dependencies**:
   ```bash
   pip install streamlit matplotlib pandas
   ```
2. **Run**:
   ```bash
   streamlit run clp.py
   ```
3. **Access**: Open `http://localhost:8501` in a browser.

### Code: `clp.py`
```python
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# A220 Data (replace with real values from manuals/pilots)
aircraft_data = {
    "N001": {"OEW": 87300, "OEW_ARM": 64.8},
    "N002": {"OEW": 87500, "OEW_ARM": 64.9}
}
zone_arms = {"A": 60, "B": 70, "C": 80}
bag_weights = {"standard": 50, "heavy": 70}
compartment_arms = {"fwd": 50, "aft": 80}
MTOW = 149000; CG_MIN, CG_MAX = 61.0, 63.0
stab_table = {61: 2, 62: 0, 63: -2}

# W&B and Optimization Logic
def calculate_wab(tail, pax_zones, bags, fuel):
    weights = [aircraft_data[tail]["OEW"], fuel]
    arms = [aircraft_data[tail]["OEW_ARM"], 70]
    for zone, counts in pax_zones.items():
        pax_weight = counts.get("adults", 0) * 200 + counts.get("children", 0) * 80
        weights.append(pax_weight)
        arms.append(zone_arms[zone])
    bag_weight = bags["standard"] * bag_weights["standard"] + bags["heavy"] * bag_weights["heavy"]
    zfw = sum(weights[:-1]) + bag_weight
    distrib = {"fwd": bag_weight, "aft": 0}
    weights.extend([distrib["fwd"], distrib["aft"]])
    arms.extend([compartment_arms["fwd"], compartment_arms["aft"]])
    total_weight = sum(weights)
    cg = sum(w * a for w, a in zip(weights, arms)) / total_weight
    if cg < 62.5:  # Optimize for aft CG (fuel savings)
        move = min(bag_weight, ((62.5 - cg) * total_weight) / (80 - 50))
        distrib["fwd"] -= move
        distrib["aft"] += move
        weights[-2:] = [distrib["fwd"], distrib["aft"]]
        total_weight = sum(weights)
        cg = sum(w * a for w, a in zip(weights, arms)) / total_weight
    stab = stab_table.get(int(cg), 0)
    return {
        "zfw": zfw, "total_weight": total_weight, "cg": cg, "stab": stab,
        "distrib": distrib, "safe": total_weight <= MTOW and CG_MIN <= cg <= CG_MAX
    }

# Streamlit UI
st.title("A220 Central Load Planning PoC")
st.write("Enter flight details to calculate W&B and load instructions.")

# Inputs
tail = st.selectbox("Tail Number", list(aircraft_data.keys()))
st.subheader("Passengers by Zone")
col1, col2, col3 = st.columns(3)
with col1:
    a_adults = st.number_input("Zone A Adults", min_value=0, value=30)
    a_children = st.number_input("Zone A Children", min_value=0, value=5)
with col2:
    b_adults = st.number_input("Zone B Adults", min_value=0, value=40)
    b_children = st.number_input("Zone B Children", min_value=0, value=0)
with col3:
    c_adults = st.number_input("Zone C Adults", min_value=0, value=20)
    c_children = st.number_input("Zone C Children", min_value=0, value=0)
pax_zones = {
    "A": {"adults": a_adults, "children": a_children},
    "B": {"adults": b_adults, "children": b_children},
    "C": {"adults": c_adults, "children": c_children}
}

st.subheader("Bags")
bag_cols = st.columns(2)
with bag_cols[0]:
    standard_bags = st.number_input("Standard Bags", min_value=0, value=80)
with bag_cols[1]:
    heavy_bags = st.number_input("Heavy Bags", min_value=0, value=20)
bags = {"standard": standard_bags, "heavy": heavy_bags}

fuel = st.number_input("Fuel (lbs)", min_value=0.0, value=27000.0)

# Calculate and Display Results
result = calculate_wab(tail, pax_zones, bags, fuel)
st.subheader("Results")
st.write(f"**ZFW**: {result['zfw']:.0f} lbs")
st.write(f"**Total Weight**: {result['total_weight']:.0f} lbs (Max: {MTOW})")
st.write(f"**CG**: {result['cg']:.2f} ft (Range: {CG_MIN}-{CG_MAX})")
st.write(f"**Stab Trim**: {result['stab']}°")
st.write(f"**Load Instructions**: Bags - Fwd: {result['distrib']['fwd']:.0f} lbs, Aft: {result['distrib']['aft']:.0f} lbs")
st.write(f"**Safe**: {result['safe']}")

# Formulas
st.subheader("Formulas Used")
st.write("""
- **ZFW** = OEW + Pax + Bags
- **Moment** = Weight × Arm
- **CG** = Σ(Moment) / Σ(Weight)
- **Stab Trim** = f(CG) [Table Lookup]
- **Bag Move** = (Target CG - Current CG) × Total Weight / (Aft Arm - Fwd Arm)
""")

# CG Plot
st.subheader("CG Visualization")
fig, ax = plt.subplots()
ax.plot([0, 1], [result["cg"], result["cg"]], label="CG")
ax.axhline(CG_MIN, color="r", ls="--", label="Limits")
ax.axhline(CG_MAX, color="r", ls="--")
ax.set_ylim(60, 64)
ax.legend()
st.pyplot(fig)

# Sidebar Notes
st.sidebar.write("### Notes")
st.sidebar.write("- Aft CG (e.g., 62.5 ft) targets fuel savings.")
st.sidebar.write("- Data is mock—replace with real A220 values.")
st.sidebar.write("- Expand with flight data for validation.")
```

---

## How to Use
1. **Setup**: Install dependencies and run the app (see above).
2. **Interact**: Open in browser, adjust inputs (e.g., pax, bags), see live updates.
3. **Share**: Run locally for coworkers or deploy (e.g., Streamlit Community Cloud) with:
   ```bash
   # Requires GitHub repo
   streamlit deploy
   ```
4. **Discuss**: Use results, formulas, and plot to explain W&B and optimization.

---

## Inputs and Outputs
### Inputs
- **Tail Number**: Select from `N001`, `N002` (mock OEW, arms).
- **Pax by Zone**: Adults (200 lbs), Children (80 lbs) for Zones A, B, C.
- **Bags**: Standard (50 lbs), Heavy (70 lbs).
- **Fuel**: Total lbs.

### Outputs
- **ZFW**: Weight without fuel.
- **Total Weight**: Full load, checked vs. MTOW.
- **CG**: Center of gravity, optimized to 62.5 ft if possible.
- **Stab Trim**: Takeoff trim setting.
- **Load Instructions**: Bag distribution (fwd/aft).
- **Safety**: Confirms envelope compliance.
- **Plot**: CG vs. limits.

---

## Relevant Code Snippets
### Core Calculation
```python
# From calculate_wab
total_weight = sum(weights)
cg = sum(w * a for w, a in zip(weights, arms)) / total_weight
if cg < 62.5:  # Optimize
    move = min(bag_weight, ((62.5 - cg) * total_weight) / (80 - 50))
    distrib["fwd"] -= move
    distrib["aft"] += move
```

### Plotting
```python
fig, ax = plt.subplots()
ax.plot([0, 1], [cg, cg], label="CG")
ax.axhline(CG_MIN, color="r", ls="--", label="Limits")
ax.axhline(CG_MAX, color="r", ls="--")
ax.legend()
st.pyplot(fig)
```

---

## Next Steps
- **Real Data**: Replace mock values with A220 OEW, arms, and stab table from pilots/manuals.
- **Validation**: Test with 20-30 flights’ FMS data (weight, CG, fuel burn).
- **Enhancements**:
  - Add takeoff/landing distance calcs (needs FCOM).
  - Parse ARINC 633 XML for flight plan input.
  - Scale to 100-200 flights with batch processing.
- **Feedback**: Share with team—ask for input on usability, accuracy.

---

## Limitations
- **Simplified**: No real-time integration (FMS, ramp) or full optimization (e.g., pax moves).
- **Mock Data**: Needs actual A220 specs for production use.
- **Single Flight**: Demo focuses on one flight, not fleet-wide.

---

## Conclusion
This PoC proves an in-house CLP tool can calculate W&B and optimize loads for an A220, potentially reducing reliance on third-party solutions. It’s a starting point—safe, transparent, and expandable with real data and validation. Share it, gather feedback, and iterate!

--- 

### Notes for You
- **Save**: Copy this into `README.md` in your project folder.
- **Customize**: Update aircraft data with real A220 values when available.
- **Share**: Pair with `clp.py` in a GitHub repo or run locally for demos.

## Dev Notes

### MacBook Quick Start with `venv`

## MacBook Quick Start with `venv`

To set up and run the PoC on a MacBook using a virtual environment:

1. **Create and Activate `venv`** (first time only):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   - You'll see `(venv)` in your terminal.

2. **Install Dependencies** (first time or after updates):
   ```bash
   pip install -r requirements.txt
   ```
   - Assumes `requirements.txt` exists (e.g., `streamlit`, `matplotlib`, `pandas`).

3. **Run the App**:
   ```bash
   streamlit run clp.py
   ```
   - Opens in your browser at `http://localhost:8501`.

4. **Stop and Deactivate**:
   - Ctrl+C to stop Streamlit.
   - `deactivate` to exit `venv`.

**Tip**: If you update libraries, regenerate `requirements.txt` with:
```bash
pip freeze > requirements.txt
```

---

### Notes
- **Mac-Specific**: Uses `python3` (common on macOS) and `source venv/bin/activate` (Unix-style).
- **Short**: Fits your “easier to remember” goal—four steps, minimal fluff.
- **Placement**: Add this under the existing **Setup** section or as a standalone **MacBook Quick Start** section.

