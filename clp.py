import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

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

def draw_aircraft_visualization(zone_arms, compartment_arms, fuel_arm, oew_arm, view='side', cg=None, cg_min=None, cg_max=None):
    # Create figure with a better aspect ratio
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Set the datum point (at the nose)
    datum_x = 0
    
    # Define a more stylized aircraft shape
    if view == 'side':
        # Simplified but recognizable side profile
        fuselage_length = 100  # Use a standardized length for better visibility
        
        # Define points for a more stylized aircraft
        nose_x = datum_x
        nose_y = 0
        
        fuselage_bottom = [
            (nose_x, nose_y),
            (nose_x + 10, nose_y - 2),
            (nose_x + 20, nose_y - 3),
            (nose_x + fuselage_length - 20, nose_y - 3),
            (nose_x + fuselage_length - 10, nose_y - 1),
            (nose_x + fuselage_length, nose_y)
        ]
        
        fuselage_top = [
            (nose_x, nose_y),
            (nose_x + 10, nose_y + 5),
            (nose_x + 20, nose_y + 8),
            (nose_x + fuselage_length - 50, nose_y + 8),
            (nose_x + fuselage_length - 40, nose_y + 12),  # Tail height
            (nose_x + fuselage_length - 25, nose_y + 12),  # Tail top
            (nose_x + fuselage_length - 10, nose_y + 3),
            (nose_x + fuselage_length, nose_y)
        ]
        
        # Draw the fuselage as a polygon
        fuselage_x_bottom, fuselage_y_bottom = zip(*fuselage_bottom)
        fuselage_x_top, fuselage_y_top = zip(*fuselage_top)
        
        # Complete the fuselage polygon
        fuselage_x = list(fuselage_x_top) + list(fuselage_x_bottom[::-1])
        fuselage_y = list(fuselage_y_top) + list(fuselage_y_bottom[::-1])
        
        # Draw the main fuselage
        ax.fill(fuselage_x, fuselage_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Draw the wing
        wing_front = nose_x + 35
        wing_length = 25
        wing_height = -2
        wing_thickness = 2
        
        wing_x = [wing_front, wing_front + wing_length, wing_front + wing_length, wing_front]
        wing_y = [wing_height, wing_height - 1, wing_height + wing_thickness, wing_height + wing_thickness]
        ax.fill(wing_x, wing_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Set axis limits for side view
        ax.set_ylim(-10, 20)
        
    else:  # top view
        # Simplified but recognizable top view
        fuselage_length = 100  # Use a standardized length
        
        # Define key points
        nose_x = datum_x
        center_y = 0
        
        # Create fuselage shape - smoother curves for the top view
        fuselage_width = 8
        
        # Create a stylized top view with curved fuselage and wings
        fuselage_outline = []
        
        # Top half
        fuselage_outline.append((nose_x, center_y))  # Nose tip
        fuselage_outline.append((nose_x + 10, center_y + 2))  # Nose curve
        fuselage_outline.append((nose_x + 20, center_y + 3.5))  # Forward fuselage
        fuselage_outline.append((nose_x + 40, center_y + fuselage_width/2))  # Mid fuselage
        fuselage_outline.append((nose_x + fuselage_length - 30, center_y + fuselage_width/2))  # Aft fuselage
        fuselage_outline.append((nose_x + fuselage_length - 20, center_y + 3))  # Tail taper
        fuselage_outline.append((nose_x + fuselage_length - 10, center_y + 1.5))  # Tail taper
        fuselage_outline.append((nose_x + fuselage_length, center_y))  # Tail tip
        
        # Bottom half (mirror of top)
        fuselage_outline.append((nose_x + fuselage_length - 10, center_y - 1.5))
        fuselage_outline.append((nose_x + fuselage_length - 20, center_y - 3))
        fuselage_outline.append((nose_x + fuselage_length - 30, center_y - fuselage_width/2))
        fuselage_outline.append((nose_x + 40, center_y - fuselage_width/2))
        fuselage_outline.append((nose_x + 20, center_y - 3.5))
        fuselage_outline.append((nose_x + 10, center_y - 2))
        fuselage_outline.append((nose_x, center_y))  # Back to nose tip
        
        fuselage_x, fuselage_y = zip(*fuselage_outline)
        ax.fill(fuselage_x, fuselage_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Draw the wings
        wing_root_x = nose_x + 40
        wing_span = 45
        wing_chord_root = 15
        wing_chord_tip = 10
        wing_sweep = 15  # Wing sweep angle for a more realistic shape
        
        # Left wing
        left_wing = [
            (wing_root_x, center_y - fuselage_width/2),
            (wing_root_x + wing_sweep, center_y - wing_span),
            (wing_root_x + wing_sweep + wing_chord_tip, center_y - wing_span),
            (wing_root_x + wing_chord_root, center_y - fuselage_width/2)
        ]
        left_wing_x, left_wing_y = zip(*left_wing)
        ax.fill(left_wing_x, left_wing_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Right wing
        right_wing = [
            (wing_root_x, center_y + fuselage_width/2),
            (wing_root_x + wing_sweep, center_y + wing_span),
            (wing_root_x + wing_sweep + wing_chord_tip, center_y + wing_span),
            (wing_root_x + wing_chord_root, center_y + fuselage_width/2)
        ]
        right_wing_x, right_wing_y = zip(*right_wing)
        ax.fill(right_wing_x, right_wing_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Horizontal stabilizer
        h_stab_root_x = nose_x + fuselage_length - 25
        h_stab_span = 20
        h_stab_chord_root = 8
        h_stab_chord_tip = 5
        h_stab_sweep = 10
        
        # Left horizontal stabilizer
        left_h_stab = [
            (h_stab_root_x, center_y - fuselage_width/4),
            (h_stab_root_x + h_stab_sweep, center_y - h_stab_span),
            (h_stab_root_x + h_stab_sweep + h_stab_chord_tip, center_y - h_stab_span),
            (h_stab_root_x + h_stab_chord_root, center_y - fuselage_width/4)
        ]
        left_h_stab_x, left_h_stab_y = zip(*left_h_stab)
        ax.fill(left_h_stab_x, left_h_stab_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Right horizontal stabilizer
        right_h_stab = [
            (h_stab_root_x, center_y + fuselage_width/4),
            (h_stab_root_x + h_stab_sweep, center_y + h_stab_span),
            (h_stab_root_x + h_stab_sweep + h_stab_chord_tip, center_y + h_stab_span),
            (h_stab_root_x + h_stab_chord_root, center_y + fuselage_width/4)
        ]
        right_h_stab_x, right_h_stab_y = zip(*right_h_stab)
        ax.fill(right_h_stab_x, right_h_stab_y, color='lightgray', alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Set axis limits for top view - wider to show the wings
        ax.set_ylim(-wing_span - 5, wing_span + 5)
    
    # Mark datum point
    datum_y = 0 if view == 'top' else 0
    ax.plot(datum_x, datum_y, 'ro', markersize=8, label='Datum Point')
    ax.text(datum_x, datum_y - 3, 'Datum', ha='center', va='top', fontweight='bold')
    
    # Set the x-axis range - use a standardized length with some padding
    ax.set_xlim(-10, fuselage_length + 10)
    
    # Create reference scale for measurement
    scale_positions = range(0, int(fuselage_length) + 20, 20)
    ax.set_xticks(scale_positions)
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Mark and label arm positions
    arms = {
        'OEW': oew_arm,
        'Fuel': fuel_arm,
        'Zone A': zone_arms['A'],
        'Zone B': zone_arms['B'],
        'Zone C': zone_arms['C'],
        'Fwd Cargo': compartment_arms['fwd'],
        'Aft Cargo': compartment_arms['aft']
    }
    
    # Colors for different zones - use a more distinct color palette
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'magenta']
    
    # Calculate adjusted arm positions - map actual arms to our standardized fuselage length
    # This keeps all the important points visible while making the diagram more readable
    max_real_arm = max(arms.values())
    if max_real_arm > 0:
        arm_scale_factor = (fuselage_length * 0.9) / max_real_arm
    else:
        arm_scale_factor = 1
    
    # Plot each arm position with scaled positions to fit our diagram
    for (label, arm), color in zip(arms.items(), colors):
        # Scale the arm position
        scaled_arm = arm * arm_scale_factor
        
        # Draw vertical reference line
        ax.axvline(x=scaled_arm, color=color, linestyle='--', alpha=0.6)
        
        # Plot point on aircraft
        y_pos = 0 if view == 'top' else 2
        ax.plot(scaled_arm, y_pos, 'o', color=color, markersize=8)
        
        # Add label - position differently for side vs top view
        if view == 'side':
            # On side view, stagger the labels to prevent overlap
            vertical_offset = 12 + (list(arms.keys()).index(label) % 3) * 2
            ax.text(scaled_arm, vertical_offset, label, ha='center', va='bottom', color=color, 
                    fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))
            ax.text(scaled_arm, vertical_offset - 1.5, f"({arm} ft)", ha='center', va='top', color=color, 
                    fontsize=8, bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.1'))
        else:
            # On top view, alternate labels above and below
            if list(arms.keys()).index(label) % 2 == 0:
                vertical_offset = wing_span * 0.6
                va_align = 'bottom'
            else:
                vertical_offset = -wing_span * 0.6
                va_align = 'top'
            
            ax.text(scaled_arm, vertical_offset, f"{label}\n({arm} ft)", ha='center', va=va_align, color=color, 
                    fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
    
    # Add CG limits and current CG if provided
    if cg_min is not None and cg_max is not None:
        # Scale CG limits to match our diagram
        scaled_cg_min = cg_min * arm_scale_factor
        scaled_cg_max = cg_max * arm_scale_factor
        
        # Draw CG limit lines
        ax.axvline(x=scaled_cg_min, color='red', linestyle=':', linewidth=2.5)
        ax.axvline(x=scaled_cg_max, color='red', linestyle=':', linewidth=2.5)
        
        # Add labels for CG limits
        min_limit_y = -5 if view == 'top' else -5
        max_limit_y = -5 if view == 'top' else -5
        
        ax.text(scaled_cg_min, min_limit_y, f"Min CG\n{cg_min} ft", ha='center', va='top', color='red', 
                fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
        ax.text(scaled_cg_max, max_limit_y, f"Max CG\n{cg_max} ft", ha='center', va='top', color='red', 
                fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3'))
        
        # Fill the safe CG range
        y_bottom = -wing_span if view == 'top' else -7
        y_top = wing_span if view == 'top' else 15
        ax.fill_between([scaled_cg_min, scaled_cg_max], [y_bottom, y_bottom], [y_top, y_top], 
                       color='green', alpha=0.1)
    
    if cg is not None:
        # Scale the CG position
        scaled_cg = cg * arm_scale_factor
        
        # Draw current CG line
        ax.axvline(x=scaled_cg, color='blue', linewidth=2.5)
        
        # Add a marker at the CG point
        cg_y_pos = 0 if view == 'top' else 5
        ax.plot(scaled_cg, cg_y_pos, 'o', color='blue', markersize=10)
        
        # Add CG label
        cg_label_y = 10 if view == 'top' else 8
        ax.text(scaled_cg, cg_label_y, f"Current CG\n{cg:.2f} ft", ha='center', va='center', color='blue', 
                fontweight='bold', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3'))
    
    # Add a note about scaled representation
    note_text = "Note: Arm positions are shown to scale relative to each other, but aircraft dimensions are stylized for clarity."
    fig.text(0.5, 0.01, note_text, ha='center', fontsize=8, style='italic')
    
    # Add title and labels
    view_title = 'Top' if view == 'top' else 'Side'
    ax.set_title(f'A220-300 {view_title} View with Weight & Balance Points', pad=20, fontsize=14, fontweight='bold')
    ax.set_xlabel('Distance from Datum (ft)', fontsize=12)
    
    if view == 'top':
        ax.set_ylabel('Width (ft)', fontsize=12)
    else:
        ax.set_ylabel('Height (ft)', fontsize=12)
    
    # Remove the legend as we're now adding labels directly to the diagram
    # This makes the visualization cleaner and more readable
    
    return fig

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
        zfw_status = "✓" if result['zfw'] <= zfw_limit else "!"
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
    mtow_status = "✓" if result['total_weight'] <= mtow_limit else "!"
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
        landing_status = "✓" if result['landing_weight'] <= landing_limit else "!"
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
    cg_status = "✓" if s["CG_MIN"] <= result['cg'] <= s["CG_MAX"] else "!"
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
        
        # Calculate bag distribution by type
        # Calculate how many bags to move from forward to aft
        std_bag_weight = s["bag_weights"]["standard"]
        heavy_bag_weight = s["bag_weights"]["heavy"]
        total_std_bags = bags["standard"]
        total_heavy_bags = bags["heavy"]
        
        # Prioritize moving heavy bags first for efficiency (fewer bags to move)
        move_weight_remaining = steps["bag_move"]
        heavy_bags_to_move = min(total_heavy_bags, move_weight_remaining // heavy_bag_weight)
        move_weight_remaining -= heavy_bags_to_move * heavy_bag_weight
        std_bags_to_move = min(total_std_bags, move_weight_remaining // std_bag_weight)
        
        # Calculate remaining bags in forward compartment
        fwd_heavy_bags = total_heavy_bags - heavy_bags_to_move
        fwd_std_bags = total_std_bags - std_bags_to_move
        
        # Calculate weights for display
        fwd_heavy_weight = fwd_heavy_bags * heavy_bag_weight
        fwd_std_weight = fwd_std_bags * std_bag_weight
        aft_heavy_weight = heavy_bags_to_move * heavy_bag_weight
        aft_std_weight = std_bags_to_move * std_bag_weight
        
        # Show bag distribution with counts and weights
        st.markdown("#### Load Instructions for Ground Handlers")
        st.markdown("*Detailed breakdown of bag counts and weights for loading in each compartment:*")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Forward Compartment:**")
            st.markdown(f"- Heavy Bags: {fwd_heavy_bags:.0f} bags ({fwd_heavy_weight:,.0f} lbs)")
            st.markdown(f"- Standard Bags: {fwd_std_bags:.0f} bags ({fwd_std_weight:,.0f} lbs)")
            st.markdown(f"- **Total Forward: {fwd_heavy_bags + fwd_std_bags:.0f} bags ({result['distrib']['fwd']:,.0f} lbs)**")
            
        with col2:
            st.markdown("**Aft Compartment:**")
            st.markdown(f"- Heavy Bags: {heavy_bags_to_move:.0f} bags ({aft_heavy_weight:,.0f} lbs)")
            st.markdown(f"- Standard Bags: {std_bags_to_move:.0f} bags ({aft_std_weight:,.0f} lbs)")
            st.markdown(f"- **Total Aft: {heavy_bags_to_move + std_bags_to_move:.0f} bags ({result['distrib']['aft']:,.0f} lbs)**")
    else:
        # No optimization needed, all bags go in forward compartment
        # Calculate weights for display
        total_std_bags = bags["standard"]
        total_heavy_bags = bags["heavy"]
        fwd_std_weight = total_std_bags * s["bag_weights"]["standard"]
        fwd_heavy_weight = total_heavy_bags * s["bag_weights"]["heavy"]
        
        st.markdown("#### Load Instructions for Ground Handlers")
        st.markdown("*Detailed breakdown of bag counts and weights for loading in each compartment:*")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Forward Compartment:**")
            st.markdown(f"- Heavy Bags: {total_heavy_bags:.0f} bags ({fwd_heavy_weight:,.0f} lbs)")
            st.markdown(f"- Standard Bags: {total_std_bags:.0f} bags ({fwd_std_weight:,.0f} lbs)")
            st.markdown(f"- **Total Forward: {total_heavy_bags + total_std_bags:.0f} bags ({result['distrib']['fwd']:,.0f} lbs)**")
            
        with col2:
            st.markdown("**Aft Compartment:**")
            st.markdown("- Heavy Bags: 0 bags (0 lbs)")
            st.markdown("- Standard Bags: 0 bags (0 lbs)")
            st.markdown("- **Total Aft: 0 bags (0 lbs)**")
    
    # Stabilizer Trim
    st.markdown("#### Stabilizer Trim Setting")
    st.markdown("*The angle setting for the horizontal stabilizer that provides the correct aerodynamic force to balance the aircraft at its current CG position, ensuring level flight.*")
    st.write(f"**Stab Trim**: {result['stab']}° (lookup from {int(result['cg'])})")
    
    # Display the mock stab trim table for reference
    st.markdown("**Stabilizer Trim Lookup Table (MOCK DATA)**")
    st.markdown("*Note: This is mock data for demonstration purposes only. Real A220 stabilizer trim values should be obtained from the Flight Crew Operating Manual (FCOM).*")
    
    # Create a DataFrame for the mock stab trim table
    stab_data = []
    for cg in range(60, 65):  # Covering a range slightly beyond our CG limits
        stab_data.append({"CG Position (ft)": cg, "Stab Trim Setting (°)": float(s["stab_table"].get(cg, 0))})
    
    # Highlight the row corresponding to the current CG position
    current_int_cg = int(result["cg"])
    stab_df = pd.DataFrame(stab_data)
    
    # Function to highlight the row with the current CG
    def highlight_current_cg(row):
        if row["CG Position (ft)"] == current_int_cg:
            return ['background-color: rgba(144, 238, 144, 0.5)'] * len(row)
        return [''] * len(row)
    
    # Apply styling and display table
    styled_df = stab_df.style.apply(highlight_current_cg, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    
    # Overall Safety Check
    st.markdown("#### Overall Safety Check")
    st.markdown("*A comprehensive verification that all aircraft weight and balance parameters (ZFW, Total Weight, Landing Weight, CG) are within operational limits for safe flight.*")
    st.write(f"**Safe to Fly**: {result['safe']}")

    # CG Plot
    st.subheader("CG Visualization")
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Plot CG line
    ax.plot([0, 1], [result["cg"], result["cg"]], label="CG", color="blue", linewidth=2)
    
    # Plot limit lines
    ax.axhline(s["CG_MIN"], color="r", ls="--", label="Min Limit", linewidth=1.5)
    ax.axhline(s["CG_MAX"], color="r", ls="--", label="Max Limit", linewidth=1.5)
    
    # Set y-axis range to ensure CG is visible even if outside limits
    # Add padding above and below to ensure visibility
    cg_value = result["cg"]
    min_limit = s["CG_MIN"]
    max_limit = s["CG_MAX"]
    
    # Calculate appropriate y-axis range with padding
    padding = 0.5  # Half a foot padding
    y_min = min(cg_value, min_limit) - padding
    y_max = max(cg_value, max_limit) + padding
    
    # Set axis limits and labels
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-0.1, 1.1)
    ax.set_xlabel("Position", fontsize=10)
    ax.set_ylabel("Center of Gravity (ft)", fontsize=10)
    ax.set_title(f"CG Position: {cg_value:.2f} ft (Limits: {min_limit}-{max_limit} ft)", fontsize=12)
    
    # Remove x-ticks as they don't represent anything meaningful
    ax.set_xticks([])
    
    # Add a grid for better readability
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Add status indicator
    cg_in_limits = min_limit <= cg_value <= max_limit
    status_color = "green" if cg_in_limits else "red"
    status_text = "✓ Within Limits" if cg_in_limits else "! Outside Limits"
    ax.text(0.5, y_min + 0.2, status_text, ha='center', color=status_color, fontsize=11, 
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
    
    # Improve legend
    ax.legend(loc='upper right', framealpha=0.9)
    
    # Show the plot
    st.pyplot(fig)

    # Add aircraft visualization after the CG plot
    st.subheader("Aircraft Visualization")
    st.markdown("*View of the A220-300 showing the datum point and all arm positions used in calculations.*")
    
    # Add view selector
    view = st.radio("Select View", ["Side View", "Top View"], horizontal=True)
    
    # Create the visualization
    fig = draw_aircraft_visualization(
        s["zone_arms"],
        s["compartment_arms"],
        s["fuel_arm"],
        s["aircraft_data"][tail]["OEW_ARM"],
        view='top' if view == "Top View" else 'side',
        cg=result["cg"],
        cg_min=s["CG_MIN"],
        cg_max=s["CG_MAX"]
    )
    st.pyplot(fig, use_container_width=True)

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
    
    st.subheader("Seat Maps vs. Zone Approach")
    st.write("""
    This PoC uses a simplified three-zone passenger model (A, B, C), but production CLP systems typically use detailed seat maps. Here's how they differ:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Current Zone Approach (PoC):**")
        st.markdown("- Divides the cabin into 3 broad zones (A, B, C)")
        st.markdown("- Each zone has a single arm position (distance from datum)")
        st.markdown("- All passengers in a zone use that zone's arm")
        st.markdown("- Simplifies input and calculations")
        st.markdown("- Less precise CG calculation")
        
    with col2:
        st.markdown("**Seat Map Approach (Production):**")
        st.markdown("- Uses actual seat layout (e.g., 2-3 configuration)")
        st.markdown("- Each seat position has its own arm value")
        st.markdown("- Passenger weight applied at exact seat location")
        st.markdown("- Considers actual passenger seating")
        st.markdown("- More precise CG calculation")
    
    st.write("""
    **A220-300 Seat Configuration:**
    
    The A220-300 typically has 12-13 rows in a 2-3 configuration (2 seats on left, 3 on right) in the forward cabin, 
    and 12-14 rows in the aft cabin, for a total of 135-145 seats. Each seat position would have a specific arm value
    in a production system, allowing for precise CG calculations based on actual passenger seating assignments.
    
    **Implementation in Production:**
    - Integration with reservation system to get actual seat assignments
    - Seat-specific arm values from the aircraft Weight & Balance Manual
    - Ability to optimize passenger seating for better CG positioning
    - Real-time updates as passenger seating changes
    
    For this PoC, the three-zone model provides a reasonable approximation while simplifying the interface and calculations.
    """)
    
    st.subheader("A220-300 Dimensions and Visualization")
    st.write("""
    The aircraft visualization in this PoC is drawn roughly to scale using actual A220-300 dimensions:
    
    **Key Dimensions:**
    - **Length**: 114.7 ft (35.0 m)
    - **Wingspan**: 115.1 ft (35.1 m)
    - **Height**: 35.1 ft (10.7 m)
    
    **Visualization Details:**
    - The side view shows a simplified representation of the aircraft's profile
    - The datum point (reference point) is set at the nose (x=0)
    - All arm distances are measured from this datum point
    - The wing is shown at its approximate position (40 ft from nose)
    - The tail section is simplified but maintains the aircraft's overall proportions
    
    **Weight & Balance Points:**
    - Each colored vertical line represents an arm position used in calculations
    - The legend shows the exact distance of each point from the datum
    - These distances are used to calculate moments and determine the aircraft's center of gravity
    
    Note: While the aircraft shape is drawn to scale, the arm positions shown are currently using mock values. In a production system, these would be replaced with actual A220 arm positions from the aircraft's Weight & Balance Manual.
    """)
    
    st.subheader("Mock vs. Real Data")
    st.write("""
    This proof of concept uses a combination of real and mock data. Here's what's authentic and what still needs to be replaced:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Real Data Currently Used:**")
        st.markdown("- ✓ Operating Empty Weights (OEW) for both A220 aircraft")
        st.markdown("- ✓ Maximum Takeoff Weight (MTOW) limits")
        st.markdown("- ✓ Zero Fuel Weight (ZFW) limits")
        st.markdown("- ✓ Landing Weight limits")
        st.markdown("- ✓ Actual payload figures from flight plans")
    
    with col2:
        st.markdown("**Mock Data Needing Replacement:**")
        st.markdown("- ✗ Aircraft arm positions (OEW arm, fuel arm)")
        st.markdown("- ✗ Passenger zone arm positions")
        st.markdown("- ✗ Baggage compartment arm positions")
        st.markdown("- ✗ CG limits and target CG")
        st.markdown("- ✗ Stabilizer trim lookup values")
    
    st.markdown("**Priority Data Needs:**")
    st.markdown("""
    1. **Arm positions** for the A220 - particularly the OEW arm, zone arms, and cargo compartment arms
    2. **CG envelope limits** (min/max CG) for safe operation
    3. **Stabilizer trim table** that accurately maps CG to trim settings
    4. **Airline-specific standard weights** for passengers and baggage
    5. **Fuel burn profiles** for more accurate landing weight estimation
    """)
    
    st.markdown("**Potential Data Sources:**")
    st.markdown("""
    - A220 Weight & Balance Manual
    - Airbus Flight Crew Operating Manual (FCOM)
    - Airline Operations Manual
    - Existing load sheet system data
    - Airbus technical representatives
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
