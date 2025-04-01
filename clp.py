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
        pax_weight = counts.get("adults", 0) * 200 + counts.get("kids", 0) * 80
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
    a_kids = st.number_input("Zone A Kids", min_value=0, value=5)
with col2:
    b_adults = st.number_input("Zone B Adults", min_value=0, value=40)
    b_kids = st.number_input("Zone B Kids", min_value=0, value=0)
with col3:
    c_adults = st.number_input("Zone C Adults", min_value=0, value=20)
    c_kids = st.number_input("Zone C Kids", min_value=0, value=0)
pax_zones = {
    "A": {"adults": a_adults, "kids": a_kids},
    "B": {"adults": b_adults, "kids": b_kids},
    "C": {"adults": c_adults, "kids": c_kids}
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
