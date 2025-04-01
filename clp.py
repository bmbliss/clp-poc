import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Initialize session state for settings if not already done
if 'settings' not in st.session_state:
    st.session_state.settings = {
        # A220 Data from real flight plan weight headers
        "aircraft_data": {
            "A220-1": {
                "OEW": 87202.0,  # Dry Operating Weight
                "OEW_ARM": 64.8,  # Using mock arm since real arm unknown
                "ZFW_LIMIT": 123000.0,  # Zero Fuel Weight Structural Limit
                "MTOW_LIMIT": 149000.0,  # Takeoff Weight Structural Limit
                "LANDING_LIMIT": 129500.0,  # Landing Weight Structural Limit
                "TAKEOFF_WEIGHT": 122484.0,  # From example - for reference
                "LOAD": 20582.0  # Payload weight from header
            },
            "A220-2": {
                "OEW": 87517.0,  # Dry Operating Weight
                "OEW_ARM": 64.9,  # Using mock arm since real arm unknown
                "ZFW_LIMIT": 123000.0,  # Zero Fuel Weight Structural Limit
                "MTOW_LIMIT": 149000.0,  # Takeoff Weight Structural Limit 
                "LANDING_LIMIT": 129500.0,  # Landing Weight Structural Limit
                "TAKEOFF_WEIGHT": 139112.0,  # From example - for reference
                "LOAD": 24395.0  # Payload weight from header
            }
        },
        "zone_arms": {"A": 60.0, "B": 70.0, "C": 80.0},
        "bag_weights": {"standard": 50.0, "heavy": 70.0},
        "compartment_arms": {"fwd": 50.0, "aft": 80.0},
        "MTOW": 149000.0,
        "CG_MIN": 61.0, 
        "CG_MAX": 63.0,
        "stab_table": {61: 2.0, 62: 0.0, 63: -2.0},
        "fuel_arm": 70.0,
        "target_cg": 62.5,
        
        # Passenger weights
        "PAX_WEIGHT_ADULT": 200.0,    # lbs
        "PAX_WEIGHT_CHILD": 80.0,     # lbs
        "PAX_WEIGHT_INFANT": 22.0     # lbs
    }

# Access settings from session state
s = st.session_state.settings

# W&B and Optimization Logic
def calculate_wab(tail, pax_zones, bags, fuel):
    # Initialize values to store calculation steps for display
    calculation_steps = {}
    
    # Aircraft base weights
    weights = [s["aircraft_data"][tail]["OEW"], fuel]
    arms = [s["aircraft_data"][tail]["OEW_ARM"], s["fuel_arm"]]
    
    # Calculate passenger weights by zone
    pax_weights_by_zone = {}
    for zone, counts in pax_zones.items():
        adults = counts.get("adults", 0)
        children = counts.get("children", 0)
        infants = counts.get("infants", 0)
        
        # Store steps for display
        pax_weights_by_zone[zone] = {
            "adults": adults * s["PAX_WEIGHT_ADULT"],
            "children": children * s["PAX_WEIGHT_CHILD"],
            "infants": infants * s["PAX_WEIGHT_INFANT"]
        }
        
        pax_weight = pax_weights_by_zone[zone]["adults"] + pax_weights_by_zone[zone]["children"] + pax_weights_by_zone[zone]["infants"]
        weights.append(pax_weight)
        arms.append(s["zone_arms"][zone])
    
    # Calculate bag weights
    std_bag_weight = bags["standard"] * s["bag_weights"]["standard"]
    heavy_bag_weight = bags["heavy"] * s["bag_weights"]["heavy"]
    bag_weight = std_bag_weight + heavy_bag_weight
    
    # Calculate ZFW
    zfw = sum(weights[:-1]) + bag_weight
    
    # Initial bag distribution (all forward)
    distrib = {"fwd": bag_weight, "aft": 0}
    weights.extend([distrib["fwd"], distrib["aft"]])
    arms.extend([s["compartment_arms"]["fwd"], s["compartment_arms"]["aft"]])
    
    # Calculate total weight and initial CG
    total_weight = sum(weights)
    
    # Calculate moments and store for display
    moments = [w * a for w, a in zip(weights, arms)]
    total_moment = sum(moments)
    
    # Calculate initial CG
    initial_cg = total_moment / total_weight
    
    # CG optimization
    cg = initial_cg
    move = 0
    if cg < s["target_cg"]:  # Optimize for target CG (fuel savings)
        fwd_arm = s["compartment_arms"]["fwd"]
        aft_arm = s["compartment_arms"]["aft"]
        move = min(bag_weight, ((s["target_cg"] - cg) * total_weight) / (aft_arm - fwd_arm))
        distrib["fwd"] -= move
        distrib["aft"] += move
        weights[-2:] = [distrib["fwd"], distrib["aft"]]
        total_weight = sum(weights)
        moments = [w * a for w, a in zip(weights, arms)]
        total_moment = sum(moments)
        cg = total_moment / total_weight
    
    # Lookup stab trim
    stab = s["stab_table"].get(int(cg), 0)
    
    # Initialize additional checks
    mtow_limit = s["MTOW"]
    zfw_limit = None
    landing_limit = None
    
    # If using real data aircraft, use its specific limits
    if tail in s["aircraft_data"] and "ZFW_LIMIT" in s["aircraft_data"][tail]:
        mtow_limit = s["aircraft_data"][tail]["MTOW_LIMIT"]
        zfw_limit = s["aircraft_data"][tail]["ZFW_LIMIT"]
        landing_limit = s["aircraft_data"][tail]["LANDING_LIMIT"]
    
    # Check if ZFW and Landing Weight are within limits for real data
    zfw_ok = True
    if zfw_limit and zfw > zfw_limit:
        zfw_ok = False
    
    # Estimate landing weight as total weight minus 75% of fuel
    landing_weight = total_weight - (fuel * 0.75)
    landing_ok = True
    if landing_limit and landing_weight > landing_limit:
        landing_ok = False
    
    # Store calculation steps for display
    calculation_steps = {
        "pax_weights": pax_weights_by_zone,
        "std_bag_weight": std_bag_weight,
        "heavy_bag_weight": heavy_bag_weight,
        "oew": s["aircraft_data"][tail]["OEW"],
        "fuel": fuel,
        "initial_cg": initial_cg,
        "bag_move": move,
        "moments": moments,
        "total_moment": total_moment
    }
    
    return {
        "zfw": zfw, 
        "total_weight": total_weight, 
        "cg": cg, 
        "stab": stab,
        "distrib": distrib,
        "landing_weight": landing_weight if landing_limit else None,
        "safe": (total_weight <= mtow_limit and 
                s["CG_MIN"] <= cg <= s["CG_MAX"] and 
                zfw_ok and landing_ok),
        "steps": calculation_steps  # Add calculation steps to result
    }

# App title
st.title("A220 Central Load Planning PoC")

# Create tabs
tab1, tab2, tab3 = st.tabs(["Calculations", "Explanatory Notes", "Settings"])

with tab1:
    # Main Tab - Inputs and Calculations
    st.write("Enter flight details to calculate W&B and load instructions.")

    st.subheader("Aircraft")

    # Inputs
    tail = st.selectbox("Tail Number", list(s["aircraft_data"].keys()))
    
    # Show real data notice if using real data
    if tail in ["A220-1", "A220-2"]:
        st.success("Using actual A220 aircraft weight data. Note that arm positions still use mock values.")
    
    # Display selected aircraft data in a clean format
    aircraft_data = s["aircraft_data"][tail]
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Aircraft Data Summary**")
        st.write(f"**OEW**: {aircraft_data['OEW']:,.0f} lbs")
        if "ZFW_LIMIT" in aircraft_data:
            st.write(f"**ZFW Limit**: {aircraft_data['ZFW_LIMIT']:,.0f} lbs")
        st.write(f"**MTOW**: {aircraft_data.get('MTOW_LIMIT', s['MTOW']):,.0f} lbs")
    with col2:
        st.write("**⠀**")  # Invisible character for alignment
        if "LANDING_LIMIT" in aircraft_data:
            st.write(f"**Landing Limit**: {aircraft_data['LANDING_LIMIT']:,.0f} lbs")
        st.write(f"**CG Limits**: {s['CG_MIN']} - {s['CG_MAX']} ft")
        st.write(f"**Target CG**: {s['target_cg']} ft")
    
    st.markdown("---")
    
    st.subheader("Passengers by Zone")
    col1, col2, col3 = st.columns(3)
    with col1:
        a_adults = st.number_input("Zone A Adults", min_value=0, value=30, step=1)
        a_children = st.number_input("Zone A Children", min_value=0, value=5, step=1)
        a_infants = st.number_input("Zone A Infants", min_value=0, value=0, step=1)
    with col2:
        b_adults = st.number_input("Zone B Adults", min_value=0, value=40, step=1)
        b_children = st.number_input("Zone B Children", min_value=0, value=0, step=1)
        b_infants = st.number_input("Zone B Infants", min_value=0, value=0, step=1)
    with col3:
        c_adults = st.number_input("Zone C Adults", min_value=0, value=20, step=1)
        c_children = st.number_input("Zone C Children", min_value=0, value=0, step=1)
        c_infants = st.number_input("Zone C Infants", min_value=0, value=0, step=1)
    pax_zones = {
        "A": {"adults": a_adults, "children": a_children, "infants": a_infants},
        "B": {"adults": b_adults, "children": b_children, "infants": b_infants},
        "C": {"adults": c_adults, "children": c_children, "infants": c_infants}
    }

    st.subheader("Bags")
    bag_cols = st.columns(2)
    with bag_cols[0]:
        standard_bags = st.number_input("Standard Bags", min_value=0, value=80, step=1)
    with bag_cols[1]:
        heavy_bags = st.number_input("Heavy Bags", min_value=0, value=20, step=1)
    bags = {"standard": standard_bags, "heavy": heavy_bags}

    # Set default fuel based on selected aircraft
    default_fuel = 27000.0
    if tail in ["A220-1", "A220-2"] and "TAKEOFF_WEIGHT" in s["aircraft_data"][tail] and "LOAD" in s["aircraft_data"][tail]:
        # Calculate fuel consistently for both aircraft: TOW - (OEW + Load)
        default_fuel = s["aircraft_data"][tail]["TAKEOFF_WEIGHT"] - (s["aircraft_data"][tail]["OEW"] + s["aircraft_data"][tail]["LOAD"])
        
    fuel = st.number_input("Fuel (lbs)", min_value=0.0, value=default_fuel, step=100.0)

    st.markdown("---")

    # Calculate and Display Results
    result = calculate_wab(tail, pax_zones, bags, fuel)
    
    # Determine MTOW limit based on aircraft selected
    mtow_limit = s["aircraft_data"][tail].get("MTOW_LIMIT", s["MTOW"])
    
    # Extract calculation steps for display
    steps = result["steps"]
    
    st.subheader("Calculations and Results")
    
    # Zero Fuel Weight Calculation
    st.markdown("#### Zero Fuel Weight (ZFW)")
    st.markdown("*The weight of the aircraft with all payload but without fuel, used to ensure structural limits are not exceeded.*")
    zfw_formula = "ZFW = OEW + Pax Weights + Bag Weight"
    
    # Calculate total passenger weight by summing all zone weights
    total_pax_weight = sum(sum(zone_weights.values()) for zone_weights in steps["pax_weights"].values())
    
    # Display the formula with actual values
    zfw_calc = f"""
    ZFW = {steps['oew']:,.0f} + {total_pax_weight:,.0f} + {(steps['std_bag_weight'] + steps['heavy_bag_weight']):,.0f}
    ZFW = {result['zfw']:,.0f} lbs
    """
    st.code(zfw_formula + "\n" + zfw_calc)
    
    # Show ZFW limit check if available
    if "ZFW_LIMIT" in s["aircraft_data"][tail]:
        zfw_limit = s["aircraft_data"][tail]["ZFW_LIMIT"]
        zfw_status = "✓" if result['zfw'] <= zfw_limit else "❌"
        st.write(f"**ZFW Limit Check**: {result['zfw']:,.0f} ≤ {zfw_limit:,.0f} lbs {zfw_status}")
    
    # Total Weight Calculation
    st.markdown("#### Total Weight")
    st.markdown("*The total aircraft weight including passengers, cargo, and fuel that must remain below Maximum Takeoff Weight (MTOW) for safe operation.*")
    total_weight_formula = "Total Weight = ZFW + Fuel"
    total_weight_calc = f"""
    Total Weight = {result['zfw']:,.0f} + {steps['fuel']:,.0f}
    Total Weight = {result['total_weight']:,.0f} lbs
    """
    st.code(total_weight_formula + "\n" + total_weight_calc)
    
    # Show MTOW limit check
    mtow_status = "✓" if result['total_weight'] <= mtow_limit else "❌"
    st.write(f"**MTOW Limit Check**: {result['total_weight']:,.0f} ≤ {mtow_limit:,.0f} lbs {mtow_status}")
    
    # Landing Weight Estimation
    if result['landing_weight']:
        st.markdown("#### Estimated Landing Weight")
        st.markdown("*The projected weight of the aircraft at landing, calculated by subtracting estimated fuel burn from takeoff weight, must remain below maximum landing weight limits to prevent structural damage.*")
        landing_formula = "Landing Weight = Total Weight - (Fuel × 0.75)"
        landing_calc = f"""
        Landing Weight = {result['total_weight']:,.0f} - ({steps['fuel']:,.0f} × 0.75)
        Landing Weight = {result['landing_weight']:,.0f} lbs
        """
        st.code(landing_formula + "\n" + landing_calc)
        
        # Show Landing Weight limit check
        landing_limit = s["aircraft_data"][tail]["LANDING_LIMIT"]
        landing_status = "✓" if result['landing_weight'] <= landing_limit else "❌"
        st.write(f"**Landing Weight Limit Check**: {result['landing_weight']:,.0f} ≤ {landing_limit:,.0f} lbs {landing_status}")
    
    # Center of Gravity Calculation
    st.markdown("#### Center of Gravity (CG)")
    st.markdown("*The point where the aircraft would balance if suspended, calculated as total moment divided by total weight, must stay within prescribed limits for safe handling and stability.*")
    cg_formula = "CG = Total Moment / Total Weight"
    cg_calc = f"""
    CG = {steps['total_moment']:,.0f} / {result['total_weight']:,.0f}
    CG = {result['cg']:.2f} ft
    """
    st.code(cg_formula + "\n" + cg_calc)
    
    # Show CG limit check
    cg_status = "✓" if s["CG_MIN"] <= result['cg'] <= s["CG_MAX"] else "❌"
    st.write(f"**CG Limit Check**: {s['CG_MIN']} ≤ {result['cg']:.2f} ≤ {s['CG_MAX']} ft {cg_status}")
    
    # Bag Movement Optimization (if any)
    if steps["bag_move"] > 0:
        st.markdown("#### Bag Movement Optimization")
        st.markdown("*The process of shifting bags between forward and aft compartments to adjust the aircraft's CG toward a target value, typically an aft position for improved fuel efficiency.*")
        bag_move_formula = "Move = (Target CG - Initial CG) × Total Weight / (Aft Arm - Fwd Arm)"
        bag_move_calc = f"""
        Move = ({s['target_cg']} - {steps['initial_cg']:.2f}) × {result['total_weight']:,.0f} / ({s['compartment_arms']['aft']} - {s['compartment_arms']['fwd']})
        Move = {steps['bag_move']:,.0f} lbs
        """
        st.code(bag_move_formula + "\n" + bag_move_calc)
        
        # Show bag distribution
        st.write(f"**Load Instructions**: Bags - Fwd: {result['distrib']['fwd']:,.0f} lbs, Aft: {result['distrib']['aft']:,.0f} lbs")
    else:
        st.write(f"**Load Instructions**: Bags - Fwd: {result['distrib']['fwd']:,.0f} lbs, Aft: {result['distrib']['aft']:,.0f} lbs")
    
    # Stabilizer Trim
    st.markdown("#### Stabilizer Trim Setting")
    st.markdown("*The angle setting for the horizontal stabilizer that provides the correct aerodynamic force to balance the aircraft at its current CG position, ensuring level flight.*")
    st.write(f"**Stab Trim**: {result['stab']}° (lookup from {int(result['cg'])})")
    
    # Overall Safety Check
    st.markdown("#### Overall Safety Check")
    st.markdown("*A comprehensive verification that all aircraft weight and balance parameters (ZFW, Total Weight, Landing Weight, CG) are within operational limits for safe flight.*")
    st.write(f"**Safe to Fly**: {result['safe']}")

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
    
    st.subheader("Acronyms and Terminology")
    
    # Create two columns for acronym list
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Aircraft Weight Terms:**")
        st.markdown("- **CLP**: Central Load Planning - System for managing aircraft weight distribution and calculating balance.")
        st.markdown("- **W&B**: Weight and Balance - Calculations ensuring aircraft is within safe operating weight and balance limitations.")
        st.markdown("- **ZFW**: Zero Fuel Weight - Weight of aircraft including payload but without fuel.")
        st.markdown("- **OEW**: Operating Empty Weight - Base weight of aircraft with crew and equipment but no payload or fuel.")
        st.markdown("- **MTOW**: Maximum Takeoff Weight - Maximum allowable weight for safe takeoff operations.")
        st.markdown("- **MAC**: Mean Aerodynamic Chord - Reference length used for aerodynamic calculations and CG positioning.")
        st.markdown("- **DOW**: Dry Operating Weight - Another term for OEW or basic weight of aircraft without payload or fuel.")
    
    with col2:
        st.markdown("**Balance and Control Terms:**")
        st.markdown("- **CG**: Center of Gravity - Point where aircraft weight balances in all axes.")
        st.markdown("- **Arm**: Distance from reference datum to the center of an item's weight.")
        st.markdown("- **Moment**: Product of weight and arm, used to calculate CG position.")
        st.markdown("- **Stab**: Stabilizer Trim - Horizontal stabilizer setting required for level flight at the calculated CG.")
        st.markdown("- **PAX**: Passengers - Abbreviated term for people aboard the aircraft.")
        st.markdown("- **FMS**: Flight Management System - Onboard computer that uses W&B data for flight performance calculations.")
    
    st.subheader("Real Flight Data")
    st.write("""
    This application uses actual weight data from real flight plans:
    
    **A220-1:**
    - **Dry Operating Weight**: 87,202 lbs
    - **Payload**: 20,582 lbs
    - **Zero Fuel Weight Limit**: 123,000 lbs
    - **Maximum Takeoff Weight**: 149,000 lbs
    - **Maximum Landing Weight**: 129,500 lbs
    
    **A220-2:**
    - **Dry Operating Weight**: 87,517 lbs
    - **Payload**: 24,395 lbs
    - **Zero Fuel Weight Limit**: 123,000 lbs
    - **Maximum Takeoff Weight**: 149,000 lbs
    - **Maximum Landing Weight**: 129,500 lbs
    
    Note that while these weights are real, the arm positions (balance points) still use mock values as they weren't provided in the source data.
    """)
    
    st.write("**Note**: This PoC uses a mix of real weight data and mock arm positions for demonstration purposes.")

with tab3:
    # Settings Tab
    st.header("Settings")
    st.write("Adjust parameters used in the calculations.")
    
    st.subheader("Passenger Weights")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_adult_weight = st.number_input("Adult Weight (lbs)", min_value=1.0, value=s["PAX_WEIGHT_ADULT"], step=1.0)
    with col2:
        new_child_weight = st.number_input("Child Weight (lbs)", min_value=1.0, value=s["PAX_WEIGHT_CHILD"], step=1.0)
    with col3:
        new_infant_weight = st.number_input("Infant Weight (lbs)", min_value=1.0, value=s["PAX_WEIGHT_INFANT"], step=1.0)
    
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
        new_target_cg = st.number_input("Target CG (ft)", min_value=float(s["CG_MIN"]), max_value=float(s["CG_MAX"]), value=float(s["target_cg"]), step=0.1)
    with col2:
        new_fuel_arm = st.number_input("Fuel Arm (ft)", min_value=0.0, value=float(s["fuel_arm"]), step=0.1)
    
    # Update session state if values changed
    if new_target_cg != s["target_cg"] or new_fuel_arm != s["fuel_arm"]:
        s["target_cg"] = new_target_cg
        s["fuel_arm"] = new_fuel_arm
        st.success("Aircraft parameters updated!")
    
    st.subheader("Weight Limits")
    new_mtow = st.number_input("Maximum Takeoff Weight (lbs)", min_value=1.0, value=float(s["MTOW"]), step=100.0)
    if new_mtow != s["MTOW"]:
        s["MTOW"] = new_mtow
        st.success("MTOW updated!")
    
    col1, col2 = st.columns(2)
    with col1:
        new_cg_min = st.number_input("CG Minimum (ft)", min_value=0.0, value=float(s["CG_MIN"]), step=0.1)
    with col2:
        new_cg_max = st.number_input("CG Maximum (ft)", min_value=new_cg_min, value=float(s["CG_MAX"]), step=0.1)
    
    # Update session state if values changed
    if new_cg_min != s["CG_MIN"] or new_cg_max != s["CG_MAX"]:
        s["CG_MIN"] = new_cg_min
        s["CG_MAX"] = new_cg_max
        st.success("CG limits updated!")
