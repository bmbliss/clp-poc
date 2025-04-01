import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Initialize session state for settings if not already done
if 'settings' not in st.session_state:
    st.session_state.settings = {
        # A220 Data (replace with real values from manuals/pilots)
        "aircraft_data": {
            "N001": {"OEW": 87300, "OEW_ARM": 64.8},
            "N002": {"OEW": 87500, "OEW_ARM": 64.9}
        },
        "zone_arms": {"A": 60, "B": 70, "C": 80},
        "bag_weights": {"standard": 50, "heavy": 70},
        "compartment_arms": {"fwd": 50, "aft": 80},
        "MTOW": 149000,
        "CG_MIN": 61.0, 
        "CG_MAX": 63.0,
        "stab_table": {61: 2, 62: 0, 63: -2},
        "fuel_arm": 70,
        "target_cg": 62.5,
        
        # Passenger weights
        "PAX_WEIGHT_ADULT": 200,    # lbs
        "PAX_WEIGHT_CHILD": 80,     # lbs
        "PAX_WEIGHT_INFANT": 22     # lbs
    }

# Access settings from session state
s = st.session_state.settings

# W&B and Optimization Logic
def calculate_wab(tail, pax_zones, bags, fuel):
    weights = [s["aircraft_data"][tail]["OEW"], fuel]
    arms = [s["aircraft_data"][tail]["OEW_ARM"], s["fuel_arm"]]
    for zone, counts in pax_zones.items():
        pax_weight = counts.get("adults", 0) * s["PAX_WEIGHT_ADULT"] + counts.get("children", 0) * s["PAX_WEIGHT_CHILD"] + counts.get("infants", 0) * s["PAX_WEIGHT_INFANT"]
        weights.append(pax_weight)
        arms.append(s["zone_arms"][zone])
    bag_weight = bags["standard"] * s["bag_weights"]["standard"] + bags["heavy"] * s["bag_weights"]["heavy"]
    zfw = sum(weights[:-1]) + bag_weight
    distrib = {"fwd": bag_weight, "aft": 0}
    weights.extend([distrib["fwd"], distrib["aft"]])
    arms.extend([s["compartment_arms"]["fwd"], s["compartment_arms"]["aft"]])
    total_weight = sum(weights)
    cg = sum(w * a for w, a in zip(weights, arms)) / total_weight
    
    # CG optimization
    if cg < s["target_cg"]:  # Optimize for target CG (fuel savings)
        fwd_arm = s["compartment_arms"]["fwd"]
        aft_arm = s["compartment_arms"]["aft"]
        move = min(bag_weight, ((s["target_cg"] - cg) * total_weight) / (aft_arm - fwd_arm))
        distrib["fwd"] -= move
        distrib["aft"] += move
        weights[-2:] = [distrib["fwd"], distrib["aft"]]
        total_weight = sum(weights)
        cg = sum(w * a for w, a in zip(weights, arms)) / total_weight
    
    stab = s["stab_table"].get(int(cg), 0)
    return {
        "zfw": zfw, 
        "total_weight": total_weight, 
        "cg": cg, 
        "stab": stab,
        "distrib": distrib, 
        "safe": total_weight <= s["MTOW"] and s["CG_MIN"] <= cg <= s["CG_MAX"]
    }

# App title
st.title("A220 Central Load Planning PoC")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Main", "Explanatory Notes", "Settings"])

with tab1:
    # Main Tab - Inputs and Calculations
    st.write("Enter flight details to calculate W&B and load instructions.")

    # Inputs
    tail = st.selectbox("Tail Number", list(s["aircraft_data"].keys()))
    st.subheader("Passengers by Zone")
    col1, col2, col3 = st.columns(3)
    with col1:
        a_adults = st.number_input("Zone A Adults", min_value=0, value=30)
        a_children = st.number_input("Zone A Children", min_value=0, value=5)
        a_infants = st.number_input("Zone A Infants", min_value=0, value=0)
    with col2:
        b_adults = st.number_input("Zone B Adults", min_value=0, value=40)
        b_children = st.number_input("Zone B Children", min_value=0, value=0)
        b_infants = st.number_input("Zone B Infants", min_value=0, value=0)
    with col3:
        c_adults = st.number_input("Zone C Adults", min_value=0, value=20)
        c_children = st.number_input("Zone C Children", min_value=0, value=0)
        c_infants = st.number_input("Zone C Infants", min_value=0, value=0)
    pax_zones = {
        "A": {"adults": a_adults, "children": a_children, "infants": a_infants},
        "B": {"adults": b_adults, "children": b_children, "infants": b_infants},
        "C": {"adults": c_adults, "children": c_children, "infants": c_infants}
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
    st.write(f"**Total Weight**: {result['total_weight']:.0f} lbs (Max: {s['MTOW']})")
    st.write(f"**CG**: {result['cg']:.2f} ft (Range: {s['CG_MIN']}-{s['CG_MAX']})")
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
    ax.axhline(s["CG_MIN"], color="r", ls="--", label="Limits")
    ax.axhline(s["CG_MAX"], color="r", ls="--")
    ax.set_ylim(60, 64)
    ax.legend()
    st.pyplot(fig)

with tab2:
    # Explanatory Notes Tab
    st.header("Central Load Planning: Background")
    
    st.subheader("What is Central Load Planning?")
    st.write("""
    Central Load Planning (CLP) ensures an aircraft's weight and balance are within safe limits for all flight phases. 
    It calculates key parameters like Zero Fuel Weight (ZFW), Center of Gravity (CG), and stabilizer trim settings.
    """)
    
    st.subheader("Why it Matters")
    st.write("""
    - **Safety**: Proper weight and balance keeps the aircraft within manufacturer limits
    - **Efficiency**: An optimized CG position (typically aft) reduces fuel consumption
    - **Performance**: Weight affects takeoff distance, climb performance, and landing characteristics
    """)
    
    st.subheader("Weight & Balance Principles")
    st.write("""
    - **Weight**: Total mass must not exceed structural or performance limits
    - **Balance**: CG must stay within the manufacturer's envelope for stability and control
    - **Optimization**: Moving bags between compartments can adjust CG position while keeping total weight constant
    """)
    
    st.subheader("Key Values")
    st.write(f"""
    - **Aft CG** (e.g., {s["target_cg"]} ft) targets fuel savings
    - **CG Limits**: {s["CG_MIN"]}-{s["CG_MAX"]} ft ensures proper aircraft handling
    - **MTOW**: {s["MTOW"]} lbs is the maximum allowed takeoff weight
    - **Passenger weights**: Adults: {s["PAX_WEIGHT_ADULT"]} lbs, Children: {s["PAX_WEIGHT_CHILD"]} lbs, Infants: {s["PAX_WEIGHT_INFANT"]} lbs
    """)
    
    st.write("**Note**: This PoC uses mock data—replace with real A220 values for production use.")

with tab3:
    # Settings Tab
    st.header("Settings")
    st.write("Adjust parameters used in the calculations.")
    
    st.subheader("Passenger Weights")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_adult_weight = st.number_input("Adult Weight (lbs)", min_value=1, value=s["PAX_WEIGHT_ADULT"])
    with col2:
        new_child_weight = st.number_input("Child Weight (lbs)", min_value=1, value=s["PAX_WEIGHT_CHILD"])
    with col3:
        new_infant_weight = st.number_input("Infant Weight (lbs)", min_value=1, value=s["PAX_WEIGHT_INFANT"])
    
    # Update session state if values changed
    if (new_adult_weight != s["PAX_WEIGHT_ADULT"] or 
        new_child_weight != s["PAX_WEIGHT_CHILD"] or 
        new_infant_weight != s["PAX_WEIGHT_INFANT"]):
        s["PAX_WEIGHT_ADULT"] = new_adult_weight
        s["PAX_WEIGHT_CHILD"] = new_child_weight
        s["PAX_WEIGHT_INFANT"] = new_infant_weight
        st.success("Passenger weights updated!")
    
    st.subheader("Aircraft Parameters")
    col1, col2 = st.columns(2)
    with col1:
        new_target_cg = st.number_input("Target CG (ft)", min_value=float(s["CG_MIN"]), max_value=float(s["CG_MAX"]), value=float(s["target_cg"]))
    with col2:
        new_fuel_arm = st.number_input("Fuel Arm (ft)", min_value=0.0, value=float(s["fuel_arm"]))
    
    # Update session state if values changed
    if new_target_cg != s["target_cg"] or new_fuel_arm != s["fuel_arm"]:
        s["target_cg"] = new_target_cg
        s["fuel_arm"] = new_fuel_arm
        st.success("Aircraft parameters updated!")
    
    st.subheader("Weight Limits")
    new_mtow = st.number_input("Maximum Takeoff Weight (lbs)", min_value=1, value=s["MTOW"])
    if new_mtow != s["MTOW"]:
        s["MTOW"] = new_mtow
        st.success("MTOW updated!")
    
    col1, col2 = st.columns(2)
    with col1:
        new_cg_min = st.number_input("CG Minimum (ft)", min_value=0.0, value=s["CG_MIN"])
    with col2:
        new_cg_max = st.number_input("CG Maximum (ft)", min_value=new_cg_min, value=s["CG_MAX"])
    
    # Update session state if values changed
    if new_cg_min != s["CG_MIN"] or new_cg_max != s["CG_MAX"]:
        s["CG_MIN"] = new_cg_min
        s["CG_MAX"] = new_cg_max
        st.success("CG limits updated!")
