# A220 CLP Mock Data Inventory

This document catalogs all the mock or estimated data used in the Central Load Planning (CLP) Proof of Concept. These are parameters that should be replaced with real operational values when moving from the PoC to a production system.

## Aircraft Balance Data (Mock)

The following arm positions (balance points) are mock values that need to be replaced with real A220 data:

```python
# Aircraft OEW arm positions (mock)
"OEW_ARM": 64.8  # for A220-1
"OEW_ARM": 64.9  # for A220-2

# Zone arm positions (mock)
"zone_arms": {"A": 60.0, "B": 70.0, "C": 80.0}

# Baggage compartment arm positions (mock)
"compartment_arms": {"fwd": 50.0, "aft": 80.0}

# Fuel arm position (mock)
"fuel_arm": 70.0
```

## CG Envelope (Mock)

The CG limits used are placeholders and should be replaced with the real A220 CG envelope values:

```python
"CG_MIN": 61.0  # Minimum allowable CG position (ft)
"CG_MAX": 63.0  # Maximum allowable CG position (ft)
"target_cg": 62.5  # Target CG for optimization (ft)
```

## Stabilizer Trim Table (Mock)

The stabilizer trim lookup table is simplified and needs the real A220 values:

```python
"stab_table": {61: 2.0, 62: 0.0, 63: -2.0}  # Maps integer CG to trim angle
```

## Standard Weights (Placeholder)

The following standard weights should be updated according to airline policies:

```python
# Passenger standard weights
"PAX_WEIGHT_ADULT": 200.0  # lbs
"PAX_WEIGHT_CHILD": 80.0   # lbs
"PAX_WEIGHT_INFANT": 22.0  # lbs

# Baggage standard weights
"bag_weights": {"standard": 50.0, "heavy": 70.0}  # lbs
```

## Calculations (Estimated)

Some calculations use estimated values that should be validated:

1. **Landing Weight Estimation**: Currently uses a simple formula:
   ```python
   landing_weight = total_weight - (fuel * 0.75)  # Assuming 75% fuel burn
   ```
   This should be replaced with actual fuel burn profiles for the routes.

2. **Bag Movement Optimization**: The optimization algorithm is basic and assumes:
   - Bags can be moved freely between forward and aft compartments 
   - The priority is fuel efficiency (aft CG)
   - No other constraints (e.g., structural load distribution)

## Real Data Already Incorporated

For reference, the following values are already using real data from flight plans:

1. **A220-1**:
   - Operating Empty Weight: 87,202 lbs
   - Zero Fuel Weight Limit: 123,000 lbs
   - Maximum Takeoff Weight: 149,000 lbs
   - Maximum Landing Weight: 129,500 lbs

2. **A220-2**:
   - Operating Empty Weight: 87,517 lbs
   - Zero Fuel Weight Limit: 123,000 lbs
   - Maximum Takeoff Weight: 149,000 lbs
   - Maximum Landing Weight: 129,500 lbs

## Priority Data Needs

In order of importance, these are the key real data points needed:

1. **Arm positions** for the A220 - particularly the OEW arm, zone arms, and cargo compartment arms
2. **CG envelope limits** (min/max CG) for safe operation
3. **Stabilizer trim table** that accurately maps CG to trim settings
4. **Airline-specific standard weights** for passengers and baggage
5. **Fuel burn profiles** for more accurate landing weight estimation

## Data Sources

Potential sources for the required data:

1. A220 Weight & Balance Manual
2. Airbus Flight Crew Operating Manual (FCOM)
3. Airline Operations Manual
4. Existing load sheet system data
5. Airbus technical representatives 