from enum import Enum
from pathlib import Path
import yaml


class MineParam(Enum): 
    NAME = "name"
    COUNTRY = "country"

    ORE_THROUGHPUT = "ore_throughput_t_per_year"
    STRIP_RATIO = "strip_ratio"

    # environment
    ELEVATION_MASL = "elevation_masl"
    P_AIR = "p_air"
    G = "acc_gravity"
    GRAD_DEG_EC = "mine_gradient_degree_crusher"
    GRAD_DEG_ED = "mine_gradient_degree_dump"
    C_D = "drag_coefficient"
    F = "coefficient_friction_tire_soil"
    C_RR = "coefficient_rolling_resistance"

    # distances
    L_EC = "distance_crusher_excavator"
    L_ED = "distance_dump_excavator"
    MAX_MINE_DEPTH = "max_mine_depth"   # [m]

    V_EC_DESIGN_KMH = "V_EC_DESIGN_KMH"
    V_CE_DESIGN_KMH = "V_CE_DESIGN_KMH"
    V_FLAT_DESIGN_KMH = "V_FLAT_DESIGN_KMH"
    V_EMPTY_FLAT_DESIGN_KMH = "V_EMPTY_FLAT_DESIGN_KMH"



class TruckParam(Enum):
    # identification
    NAME = "name"
    MODEL = "model"
    TECHNOLOGY = "technology"          # "diesel", "battery", "hydrogen"
    SCENARIO = "scenario"              # "conservative", "progressive"

    # mass & geometry
    PAYLOAD_T = "payload_t"
    EMPTY_WEIGHT_T = "empty_weight_t"
    GVW_T = "gross_vehicle_weight_t"
    FRONT_SURFACE_M2 = "front_surface_m2"

    # powertrain
    ENGINE_POWER_KW = "engine_power_kw"        # diesel
    MOTOR_POWER_KW = "motor_power_kw"          # BEV
    FUEL_CELL_POWER_KW = "fuel_cell_power_kw"  # H2  
    DRIVETRAIN_EFFICIENCY = "drivetrain_efficiency"
    REGEN_EFFICIENCY = "regen_efficiency"
    FC_SHARE = "fc_share"                      #[0-1]
    TOTAL_DRIVE_POWER_KW = "total_drive_power_kw"
    ELECTROLYSIS_EFFICIENCY = "electrolysis_efficiency" 

    # energy storage
    BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
    HYDROGEN_MASS_KG = "hydrogen_mass_kg"

    # energy & costs
    FUEL_TYPE = "fuel_type"                    # "diesel"
    ENERGY_TYPE = "energy_type"                # "electricity", "hydrogen"
    HYDROGEN_COST_MODE = "hydrogen_cost_mode"
    FUEL_ENERGY_DENSITY_MJ_PER_L = "fuel_energy_density_MJ_per_l"
    FUEL_ENERGY_DENSITY_MJ_PER_KWH = "fuel_energy_density_MJ_per_kwh"
    HYDROGEN_LHV_MJ_PER_KG = "hydrogen_LHV_MJ_per_kg"
    FUEL_COST_PER_L = "fuel_cost_per_l"
    ELECTRICITY_COST_PER_KWH = "electricity_cost_per_kwh"
    HYDROGEN_COST_PER_KG = "hydrogen_cost_per_kg"

    # idle / cycle timing
    IDLE_POWER_KW = "idle_power_kw" 
    T_LOAD_S = "t_load_s"
    T_UNLOAD_S = "t_unload_s"

    TROLLEY_SHARE = "trolley_share" #represents that not the whole trajectories can be used with trolley. still a battery is needed

    
    

# -------------------------
# CONSTANTS
# -------------------------

TECHNOLOGIES = ["diesel", "battery", "hydrogen", "trolley"]
SCENARIOS = ["conservative", "progressive"]
    
# -------------------------
# GENERIC LOADER 
# -------------------------

def get_data(object_name, param_enum, *params): 
    file_name = object_name + ".yml"
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    param_file = DATA_DIR / file_name

    if not param_file.exists():
        raise FileNotFoundError(f"YAML-file not found: {param_file}")
    
    with open(param_file) as f:
        data = yaml.safe_load(f)

    #Collect data from all sub-categories:
    combined_data = {}
    for section in data.values():
        if isinstance(section, dict):
            combined_data.update(section)

    #Change String-Keys to Enum-Keys
    valid_values = {e.value for e in param_enum}
    enum_data = {
        param_enum(key): value
        for key, value in combined_data.items()
        if key in valid_values
    }

    #Mode 1: give all parameters back
    if not params: 
        return enum_data

    #Mode 2: get specific parameters
    return {param: enum_data[param] for param in params}

def get_config():
    BASE_DIR = Path(__file__).resolve().parent.parent
    config_file = BASE_DIR / "data" / "config.yml"
    with open(config_file) as f:
        return yaml.safe_load(f)

def truck_file_name(truck_set, technology, scenario):
    return f"reference_truck_{truck_set}_{technology}_{scenario}"
# -------------------------
# WRAPPER FUNCTIONS
# -------------------------

def get_data_mine(name, *params): #to facilitate use of get_data - Function, those sub-functions are created.
    return get_data(name, MineParam, *params)

def get_data_truck(name, *params):
    return get_data(name, TruckParam, *params)

# ← NEU HINZUFÜGEN:
def load_capex():
    """Lädt CAPEX-Daten aus data/capex.yml."""
    BASEDIR = Path(__file__).resolve().parent.parent
    capex_file = BASEDIR / "data" / "capex.yml"
    
    if not capex_file.exists():
        raise FileNotFoundError(f"CAPEX-File nicht gefunden: {capex_file}")
    
    with open(capex_file, 'r') as f:
        capex_data = yaml.safe_load(f)
    
    return capex_data
