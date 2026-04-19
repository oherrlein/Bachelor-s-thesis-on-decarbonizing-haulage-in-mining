import math
from .physics import (
    power_segment,
    drag_constant,
    rolling_gradient_constant_loaded,
    rolling_gradient_constant_empty,
    apply_regen,
    max_speed_from_power,
    idle_energy,
    constancia_speed_loaded_kmh,
    constancia_speed_empty_kmh,
    cerro_corona_speed_loaded_kmh,
    cerro_corona_speed_empty_kmh,
    antamina_cuajone_speed_empty_kmh,
    antamina_cuajone_speed_loaded_kmh,
)

from .loader import MineParam, TruckParam

import yaml
from pathlib import Path

def derive_speeds(mine, truck):
    """
    Bergauf (ec, ed):
      - Wenn im Mine-YAML Design-Geschwindigkeiten angegeben sind,
        werden diese verwendet.
      - Sonst: Mine-spezifische Referenzkurve:
          * Antamina / Cuajone:  Constancia-Kurve –20%
          * Constancia:          Constancia-Kurve (original)
          * Cerro Corona:        Cerro-Corona-Kurve (HD265-class, –25%)
    Bergab (ce, de): mine-spezifisch falls V_CE_DESIGN_KMH gesetzt, sonst 7.7 m/s.
    """
    grad_ec = mine[MineParam.GRAD_DEG_EC]
    L_ec    = mine[MineParam.L_EC]
    L_ed    = mine[MineParam.L_ED]
    g       = mine[MineParam.G]
    rho_air = mine[MineParam.P_AIR]
    f       = mine[MineParam.F]
    C_rr    = mine[MineParam.C_RR]
    C_d     = mine[MineParam.C_D]

    tech    = truck[TruckParam.TECHNOLOGY]
    pay_t   = truck[TruckParam.PAYLOAD_T]
    empty_t = truck[TruckParam.EMPTY_WEIGHT_T]
    gvw_t   = pay_t + empty_t
    A_f     = truck[TruckParam.FRONT_SURFACE_M2]

    mine_name = mine.get(MineParam.NAME, "")

    grad_ec_pct = math.tan(math.radians(grad_ec)) * 100
    print(f"gradient_ec_pct = {grad_ec_pct}")

    # 1) Design-Geschwindigkeiten aus Mine-YAML (optional)
    V_ec_design_kmh         = mine.get(MineParam.V_EC_DESIGN_KMH, None)
    V_flat_design_kmh       = mine.get(MineParam.V_FLAT_DESIGN_KMH, None)
    V_empty_flat_design_kmh = mine.get(MineParam.V_EMPTY_FLAT_DESIGN_KMH, None)

    use_design = (
        V_ec_design_kmh is not None
        and V_flat_design_kmh is not None
        and V_empty_flat_design_kmh is not None
    )

    if use_design:
        V_ec_kmh          = float(V_ec_design_kmh)
        V_flat_loaded_kmh = float(V_flat_design_kmh)
        V_flat_empty_kmh  = float(V_empty_flat_design_kmh)
        print(f"[DEBUG] derive_speeds | mine={mine_name}: using DESIGN speeds "
              f"V_ec={V_ec_kmh:.1f} km/h, V_flat_loaded={V_flat_loaded_kmh:.1f} km/h, "
              f"V_flat_empty={V_flat_empty_kmh:.1f} km/h")

    else:
        # 2) Fallback: Kurvenlogik je nach Mine
        mine_key = mine_name.lower()

        if "antamina" in mine_key or "cuajone" in mine_key:
            V_ec_kmh          = antamina_cuajone_speed_loaded_kmh(grad_ec_pct)
            V_flat_loaded_kmh = antamina_cuajone_speed_loaded_kmh(0.0)
            V_flat_empty_kmh  = antamina_cuajone_speed_empty_kmh(0.0)
            curve_label = "ANTAMINA/CUAJONE (Constancia –20%)"

        elif pay_t < 100:
            # Cerro Corona: kleine Truck-Klasse (HD265-class)
            V_ec_kmh          = cerro_corona_speed_loaded_kmh(grad_ec_pct)
            V_flat_loaded_kmh = cerro_corona_speed_loaded_kmh(0.0)
            V_flat_empty_kmh  = cerro_corona_speed_empty_kmh(0.0)
            curve_label = "CERRO CORONA (HD265 –25%)"

        else:
            # Constancia: große Truck-Klasse (T264, 930E, 980E)
            V_ec_kmh          = constancia_speed_loaded_kmh(grad_ec_pct)
            V_flat_loaded_kmh = constancia_speed_loaded_kmh(0.0)
            V_flat_empty_kmh  = constancia_speed_empty_kmh(0.0)
            curve_label = "CONSTANCIA (original)"

        print(f"[DEBUG] derive_speeds | mine={mine_name}: using CURVE speeds [{curve_label}] "
              f"V_ec={V_ec_kmh:.1f} km/h, V_flat_loaded={V_flat_loaded_kmh:.1f} km/h, "
              f"V_flat_empty={V_flat_empty_kmh:.1f} km/h")

    # Umrechnung in m/s
    V_ec          = V_ec_kmh / 3.6
    V_flat_loaded = V_flat_loaded_kmh / 3.6
    V_flat_empty  = V_flat_empty_kmh / 3.6

    # Debug: Leistung bei V_ec
    if tech == "diesel":
        P_kw = truck[TruckParam.ENGINE_POWER_KW]
    else:
        P_kw = (truck.get(TruckParam.TOTAL_DRIVE_POWER_KW)
                or truck.get(TruckParam.MOTOR_POWER_KW))

    W_loaded = gvw_t * 1000 * g
    a        = drag_constant(C_d, rho_air, A_f)
    rc_ec    = rolling_gradient_constant_loaded(grad_ec, f, C_rr, direction="up")

    def power_at_speed(V, W, L, a_drag, rc):
        return V * (a_drag * V**2 + rc * W) + 0.5 * W * V**3 / L

    P_needed_ec = power_at_speed(V_ec, W_loaded, L_ec, a, rc_ec)
    print(f"[DEBUG] derive_speeds | mine={mine_name}, tech={tech}: "
          f"V_ec={V_ec*3.6:.1f} km/h, P_needed_ec={P_needed_ec/1e6:.2f} MW, "
          f"P_max={P_kw/1000:.2f} MW")

    # Bergab: mine-spezifisch falls V_CE_DESIGN_KMH gesetzt, sonst brake-limited
    V_ce_design_kmh = mine.get(MineParam.V_CE_DESIGN_KMH, None)
    if V_ce_design_kmh is not None:
        V_ce = float(V_ce_design_kmh) / 3.6
    else:
        V_ce = 7.7  # brake-limited fallback (Constancia reference)

    return {
        "V_ec": V_ec,
        "V_ce": V_ce,
        "V_flat_loaded": V_flat_loaded,
        "V_flat_empty": V_flat_empty,
    }


def _base_params_ec(mine, truck):
    # Params for Excavator ↔ Crusher."""
    C_d = mine[MineParam.C_D]
    rho_air = mine[MineParam.P_AIR]
    g = mine[MineParam.G]
    grad = mine[MineParam.GRAD_DEG_EC]
    f = mine[MineParam.F]
    C_rr = mine[MineParam.C_RR]

    speeds = derive_speeds(mine, truck)
    V_ec = speeds["V_ec"]
    V_ce = speeds["V_ce"]

    # ---Truck ---

    A_f = truck[TruckParam.FRONT_SURFACE_M2]
    payload_t = truck[TruckParam.PAYLOAD_T]  #t
    empty_t = truck[TruckParam.EMPTY_WEIGHT_T]    #t
    eta_regen = truck.get(TruckParam.REGEN_EFFICIENCY, 0.0)

    # Umrechnung: Masse [t] → Gewichtskraft [N]
    # g kommt aus der Mine-YAML (ggf. höhenkorrigiert)
    W_loaded = (empty_t + payload_t) * 1000 * g   # [N] beladen
    W_empty  = empty_t * 1000 * g                  # [N] leer

    a = drag_constant(C_d, rho_air, A_f)

    return a, g, grad, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen

def _base_params_ed(mine, truck):
    # Params for Excavator ↔ Dump."""
    C_d = mine[MineParam.C_D]
    rho_air = mine[MineParam.P_AIR]
    g = mine[MineParam.G]
    grad = mine[MineParam.GRAD_DEG_EC]
    f = mine[MineParam.F]
    C_rr = mine[MineParam.C_RR]

    speeds = derive_speeds(mine, truck)
    V_ec = speeds["V_ec"]
    V_ce = speeds["V_ce"]
    #V = mine[MineParam.V_ED]

    # ---Truck ---

    A_f = truck[TruckParam.FRONT_SURFACE_M2]
    payload_t = truck[TruckParam.PAYLOAD_T]  #t
    empty_t = truck[TruckParam.EMPTY_WEIGHT_T]    #t
    eta_regen = truck.get(TruckParam.REGEN_EFFICIENCY, 0.0)

    # Umrechnung: Masse [t] → Gewichtskraft [N]
    # g kommt aus der Mine-YAML (ggf. höhenkorrigiert)
    W_loaded = (empty_t + payload_t) * 1000 * g   # [N] beladen
    W_empty  = empty_t * 1000 * g                  # [N] leer

    a = drag_constant(C_d, rho_air, A_f)

    return a, g, grad, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen

def calculate_power_excavator_to_crusher(mine, truck): #(direction=up hängt davon ab, ob es ce, es, usw ist!)
    """
    P_ec: Excavator → Crusher, uphill, fully loaded.
    """
    a, g, grad, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen = _base_params_ec(mine, truck)

    L = mine[MineParam.L_EC]
    resistance = rolling_gradient_constant_loaded(grad, f, C_rr, direction="up")
    P_ec = power_segment(V_ec, W_loaded, L, a, resistance)

    # --- DEBUG ---
    mine_name   = mine.get(MineParam.NAME, "unknown")
    tech        = truck[TruckParam.TECHNOLOGY]
    scenario    = truck[TruckParam.SCENARIO]
    print(f"[DEBUG] P_ec  | mine={mine_name}, tech={tech}, scen={scenario}: "
          f"grad={grad:.2f}°, V_ec={V_ec*3.6:.1f} km/h, "
          f"P_ec={P_ec/1e6:.3f} MW")
    
    #Cap on max motor power
    tech = truck[TruckParam.TECHNOLOGY]
    P_kw = truck[TruckParam.ENGINE_POWER_KW] if tech == "diesel" else (
        truck.get(TruckParam.TOTAL_DRIVE_POWER_KW) or truck.get(TruckParam.MOTOR_POWER_KW))
    return min(P_ec, P_kw * 1000)

    
    
def calculate_power_crusher_to_excavator(mine, truck):
    """
    P_ce: Crusher → Excavator, downhill, empty.
    recuperation is automatically applied through eta_regen from YAML
    """
    a, g, grad, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen = _base_params_ec(mine, truck)
    L = mine[MineParam.L_EC]
    
    resistance = rolling_gradient_constant_empty(grad, f, C_rr, direction="down")
    P_raw = power_segment(V_ce, W_empty, L, a, resistance)
    
    return apply_regen(P_raw, eta_regen)


def calculate_power_excavator_to_dump(mine, truck):
    a, g, grad_ec, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen = _base_params_ed(mine, truck)
    """
    P_ed: Excavator → Dump, bergauf + flach.
    Strecke L_ed setzt sich zusammen aus:
      - Teilstrecke 1: L_ec mit mine_gradient_degree_crusher (Steigung)
      - Teilstrecke 2: (L_ed - L_ec) mit 0° (flach)
    Mittlere Leistung: zeitgewichtet über beide Teilabschnitte.
    """
    L_ec   = mine[MineParam.L_EC]
    L_ed   = mine[MineParam.L_ED]
    L_flat = L_ed - L_ec

    speeds        = derive_speeds(mine, truck)
    V_ec          = speeds["V_ec"]
    V_flat_loaded = speeds["V_flat_loaded"]

    rc_uphill = rolling_gradient_constant_loaded(grad_ec, f, C_rr, direction="up")
    rc_flat   = rolling_gradient_constant_loaded(0.0,     f, C_rr, direction="up")

    # Nur Traktionskraft (ohne Beschleunigungsterm) für jeden Abschnitt
    def traction_power(V, W, a_drag, rc):
        return V * (a_drag * V**2 + rc * W)

    P_uphill_traction = traction_power(V_ec,          W_loaded, a, rc_uphill)
    P_flat_traction   = traction_power(V_flat_loaded, W_loaded, a, rc_flat)

    # Zeitgewichtete mittlere Traktionsleistung
    t_uphill = L_ec   / V_ec
    t_flat   = L_flat / V_flat_loaded
    P_traction_avg = (P_uphill_traction * t_uphill + P_flat_traction * t_flat) / (t_uphill + t_flat)

    # Beschleunigungsterm einmal, mit repräsentativer Geschwindigkeit und L_ed
    # V_ec ist die "Anfahrgeschwindigkeit" des dominanten (steilsten) Abschnitts
    P_accel = (W_loaded * V_ec**3) / (2 * L_ed)

    P_ed = P_traction_avg + P_accel

    # --- DEBUG ---
    mine_name   = mine.get(MineParam.NAME, "unknown")
    tech        = truck[TruckParam.TECHNOLOGY]
    scenario    = truck[TruckParam.SCENARIO]
    print(f"[DEBUG] P_ed  | mine={mine_name}, tech={tech}, scen={scenario}: "
          f"grad_ec={grad_ec:.2f}°, L_ec={L_ec:.0f} m, L_flat={L_flat:.0f} m, "
          f"V_ec={V_ec*3.6:.1f} km/h, V_flat={V_flat_loaded*3.6:.1f} km/h, "
          f"P_uphill_trac={P_uphill_traction/1e6:.3f} MW, "
          f"P_flat_trac={P_flat_traction/1e6:.3f} MW, "
          f"P_trac_avg={P_traction_avg/1e6:.3f} MW, "
          f"P_accel={P_accel/1e6:.3f} MW, "
          f"P_ed={P_ed/1e6:.3f} MW")

    tech = truck[TruckParam.TECHNOLOGY]
    P_kw = truck[TruckParam.ENGINE_POWER_KW] if tech == "diesel" else (
        truck.get(TruckParam.TOTAL_DRIVE_POWER_KW) or truck.get(TruckParam.MOTOR_POWER_KW))
    return min(P_ed, P_kw * 1000)

def calculate_power_dump_to_excavator(mine, truck):
    a, g, grad_ec, f, C_rr, V_ec, V_ce, W_loaded, W_empty, eta_regen = _base_params_ed(mine, truck)
    """
    P_de: Dump → Excavator, leer.
    Teilstrecke 1: (L_ed - L_ec) flach, leer
    Teilstrecke 2: L_ec bergab, leer → Rekuperation möglich
    Zeitgewichtete mittlere Leistung (nach apply_regen).
    """
    L_ec   = mine[MineParam.L_EC]
    L_ed   = mine[MineParam.L_ED]
    L_flat = L_ed - L_ec

    speeds       = derive_speeds(mine, truck)
    V_ce = speeds["V_ce"]
    V_flat_empty = speeds["V_flat_empty"]

    rc_downhill = rolling_gradient_constant_empty(grad_ec, f, C_rr, direction="down")
    rc_flat     = rolling_gradient_constant_empty(0.0,     f, C_rr, direction="down")

#Für die Strecke L_ed (egal welche Richtung) packen wir die funktion power_segment aus physics.py quasi hier rein. Das machen wir, damit die beschleunigung auf beiden teilstrecken jeweils nicht neu berechnet wird.
    def traction_power(V, W, a_drag, rc):
        return V * (a_drag * V**2 + rc * W)

    P_flat_traction = traction_power(V_flat_empty, W_empty, a, rc_flat)
    P_down_traction = traction_power(V_ce,         W_empty, a, rc_downhill)

    # Rekuperation auf Traktionsleistung anwenden
    P_flat = apply_regen(P_flat_traction, 0.0)
    P_down = apply_regen(P_down_traction, eta_regen)

    t_flat = L_flat / V_flat_empty
    t_down = L_ec   / V_ce
    P_traction_avg = (P_flat * t_flat + P_down * t_down) / (t_flat + t_down)

    # Beschleunigungsterm einmal, leer, mit V_flat_empty als Anfahrgeschwindigkeit
    P_accel = (W_empty * V_flat_empty**3) / (2 * L_ed)

    P_de = P_traction_avg + P_accel

    return P_de

def _apply_eta(P, eta):
    """eta nur auf positive Leistung (Antrieb) anwenden, nicht auf Rekuperation."""
    return (P / eta) if P >= 0 else P

def calculate_total_power(mine, truck):
    """
    P_ges: Sum of the powers of all four routes.
    the fact if its calculated by the conservative or progressive way is defined in main.
    """
    P_ec = calculate_power_excavator_to_crusher(mine, truck)
    P_ce = calculate_power_crusher_to_excavator(mine, truck)
    P_ed = calculate_power_excavator_to_dump(mine, truck)
    P_de = calculate_power_dump_to_excavator(mine, truck)
    return P_ec + P_ce + P_ed + P_de

def calculate_cycle_energy(mine, truck):
    """
    Total Energy by full cycle
    (ec + ce + ed + de + idle during load / deloading).
    as from equation (21) of Paper (Sahoo et al. 2014),
    but: here we calculate [J] instead of fuel mass [kg].

    Returns: dict with part-energies and total energy [J]
    """
    eta = truck[TruckParam.DRIVETRAIN_EFFICIENCY]
    L_ec   = mine[MineParam.L_EC]
    L_ed   = mine[MineParam.L_ED]
    L_flat = L_ed - L_ec   # flacher Restabschnitt
    # trajectory times [s]
    speeds = derive_speeds(mine, truck)
    t_ec = mine[MineParam.L_EC] / speeds["V_ec"]
    t_ce = mine[MineParam.L_EC] / speeds["V_ce"]

    t_ed = (mine[MineParam.L_EC] / speeds["V_ec"]) + (L_flat / speeds["V_flat_loaded"])
    t_de = (mine[MineParam.L_EC] / speeds["V_ce"]) + (L_flat / speeds["V_flat_empty"])

    # power on wheel [W] (Recuperation already included for ce, de)
    P_ec = calculate_power_excavator_to_crusher(mine, truck)
    P_ce = calculate_power_crusher_to_excavator(mine, truck)
    P_ed = calculate_power_excavator_to_dump(mine, truck)
    P_de = calculate_power_dump_to_excavator(mine, truck)

    # driving energies from energy source [J]
    E_ec = _apply_eta(P_ec, eta) * t_ec
    E_ce = _apply_eta(P_ce, eta) * t_ce
    E_ed = _apply_eta(P_ed, eta) * t_ed
    E_de = _apply_eta(P_de, eta) * t_de

    # idle energy [J] – equation (21) from Sahoo et. al, last term
    E_idle = idle_energy(
        truck[TruckParam.IDLE_POWER_KW],
        truck[TruckParam.T_LOAD_S],
        truck[TruckParam.T_UNLOAD_S],
    )

    E_ges = E_ec + E_ce + E_ed + E_de + E_idle

    return {
        "E_ec": E_ec,
        "E_ce": E_ce,
        "E_ed": E_ed,
        "E_de": E_de,
        "E_idle": E_idle,
        "E_ges": E_ges,
    }

def calculate_annual_cycles(mine, truck):
    """
    calculates number of trajectories per year, for each route.
    - n_crusher: number of necessary ore-cycles (Excavator → Crusher → Excavator)
    - n_dump:    number of necessary waste-cycles (Excavator → Dump → Excavator)
    Strip Ratio = waste / ore → waste = ore * strip_ratio
    """
    ore_t      = mine[MineParam.ORE_THROUGHPUT]   # [t/a] – nur Erz
    strip      = mine[MineParam.STRIP_RATIO]
    payload    = truck[TruckParam.PAYLOAD_T]       # [t]

    waste_t    = ore_t * strip                     # [t/a]

    n_crusher  = ore_t   / payload
    n_dump     = waste_t / payload

    return {
        "n_crusher":    n_crusher,
        "n_dump":       n_dump,
        "n_total":      n_crusher + n_dump,
        "ore_t_per_a":  ore_t,
        "waste_t_per_a": waste_t,
    }


def calculate_annual_energy(mine, truck):
    """
    yearly energy [J] from energy source.
    For every cycle (crusher or dump), theres one E_idle (for loading or unloading the truck).
    E_specific: specific consumption for mass of transported material [kWh/t].
    E_specific_tkm: specific consumption per tonne-kilometre [kWh/(t·km)],
                    calculated as total annual energy divided by total transport work.
                    Transport work accounts separately for crusher cycles (n_crusher × 2×L_EC)
                    and dump cycles (n_dump × 2×L_ED), weighted by payload.
    """
    cycles  = calculate_annual_cycles(mine, truck)
    e_cycle = calculate_cycle_energy(mine, truck)

    # Energy per Crusher-cycle (ec + ce + own idle)
    E_crusher_cycle = e_cycle["E_ec"] + e_cycle["E_ce"] + e_cycle["E_idle"]

    # Energy per Dump-cycle (ed + de + own idle)
    E_dump_cycle    = e_cycle["E_ed"] + e_cycle["E_de"] + e_cycle["E_idle"]

    E_annual_J = (
        cycles["n_crusher"] * E_crusher_cycle +
        cycles["n_dump"]    * E_dump_cycle
    )

    E_annual_kWh = E_annual_J / 3.6e6
    E_specific   = E_annual_kWh / cycles["ore_t_per_a"]   # [kWh/t ore]

    # Strecken je Zyklustyp [km] (Hin + Zurück)
    L_crusher_km = 2 * mine[MineParam.L_EC] / 1000
    L_dump_km    = 2 * mine[MineParam.L_ED] / 1000

    # Gesamte Transportleistung [t·km/a]:
    # Crusher-Zyklen transportieren Erz auf L_EC-Strecke,
    # Dump-Zyklen transportieren Abraum auf L_ED-Strecke.
    payload_t  = truck[TruckParam.PAYLOAD_T]
    tkm_crusher = cycles["n_crusher"] * payload_t * L_crusher_km
    tkm_dump    = cycles["n_dump"]    * payload_t * L_dump_km
    tkm_total   = tkm_crusher + tkm_dump

    E_specific_tkm = E_annual_kWh / tkm_total   # [kWh/(t·km)]

    return {
        "E_annual_J":          E_annual_J,
        "E_annual_kWh":        E_annual_kWh,
        "E_annual_MWh":        E_annual_kWh / 1000,
        "E_annual_GWh":        E_annual_kWh / 1e6,
        "E_specific_kWh_t":    E_specific,
        "E_specific_kWh_tkm":  E_specific_tkm,
        "E_crusher_total_kWh": cycles["n_crusher"] * E_crusher_cycle / 3.6e6,
        "E_dump_total_kWh":    cycles["n_dump"]    * E_dump_cycle    / 3.6e6,
    }

def calculate_h2_energy_breakdown(mine, truck, energy_result):
    """
    helps with Estimation of yearly H2-energy. 

    fc_share = 1.0  → 100% Fuel Cell (not going to happen. Always need some batteries for recuperation etc.)
    fc_share < 1.0  → (in our case: around 1/4) Hybrid: FC + direct battery drive (progressive, based upon Liebherr T264 H2)

    returns:
    - E_h2_drive_kWh:    energy that goes into fuel cell as Hydrogen [kWh/a] (needed for estimation of hydrogen)
    - E_elec_direct_kWh: electrical energy that comes directly out of battery to the electrical engines [kWh/a]
    - E_elec_for_h2_kWh: electricity needed for production of green H2 [kWh/a]
    - E_elec_total_kWh:  total electricity (direct + Elektrolysis) [kWh/a]
    - h2_mass_t_per_a:   needed H2 - mass per year [t/a]
    """
    fc_share  = truck[TruckParam.FC_SHARE]
    bat_share = 1.0 - fc_share

    E_annual_kWh  = energy_result["E_annual_kWh"]
    E_h2_drive    = E_annual_kWh * fc_share
    E_elec_direct = E_annual_kWh * bat_share

    # H2-Masse: LHV in MJ/kg → umrechnen in kWh/kg
    H2_LHV_kWh_per_kg = truck[TruckParam.HYDROGEN_LHV_MJ_PER_KG] / 3.6
    h2_mass_kg = E_h2_drive / H2_LHV_kWh_per_kg

    # Strom für Elektrolyse: E_h2_drive / eta_electrolysis
    eta_el = truck[TruckParam.ELECTROLYSIS_EFFICIENCY]
    E_elec_for_h2 = E_h2_drive / eta_el

    E_elec_total = E_elec_direct + E_elec_for_h2

    return {
        "fc_share":            fc_share,
        "bat_share":           bat_share,
        "E_h2_drive_kWh":      E_h2_drive,
        "E_h2_drive_GWh":      E_h2_drive      / 1e6,
        "E_elec_direct_kWh":   E_elec_direct,
        "E_elec_direct_GWh":   E_elec_direct   / 1e6,
        "E_elec_for_h2_kWh":   E_elec_for_h2,
        "E_elec_for_h2_GWh":   E_elec_for_h2   / 1e6,
        "E_elec_total_kWh":    E_elec_total,
        "E_elec_total_GWh":    E_elec_total     / 1e6,
        "h2_mass_t_per_a":     h2_mass_kg / 1000,
    }

def calculate_annual_cost(mine, truck, energy_result):
    """
    Jährliche Energieträgerkosten [$/a] und spezifische Kosten [$/t Erz].

    Diesel:    E_annual [J] → Volumen [l] → Kosten [$/a]
    BEV:       E_annual [kWh] → Kosten [$/a]
    Hydrogen:  E_annual [kWh] → H2-Masse [kg] → Kosten [$/a]
               (bezogen auf die Energie, die als H2 durch den FC geht)
    """
    technology   = truck[TruckParam.TECHNOLOGY]
    E_annual_kWh = energy_result["E_annual_kWh"]
    ore_t        = mine[MineParam.ORE_THROUGHPUT]


    cycles       = calculate_annual_cycles(mine, truck)
    L_crusher_km = 2 * mine[MineParam.L_EC] / 1000
    L_dump_km    = 2 * mine[MineParam.L_ED] / 1000
    payload_t    = truck[TruckParam.PAYLOAD_T]
    tkm_crusher  = cycles["n_crusher"] * payload_t * L_crusher_km
    tkm_dump     = cycles["n_dump"]    * payload_t * L_dump_km
    tkm_total    = tkm_crusher + tkm_dump

    if technology == "diesel":
        energy_density_MJ_per_l = truck[TruckParam.FUEL_ENERGY_DENSITY_MJ_PER_L]
        E_annual_MJ  = E_annual_kWh * 3.6
        volume_l     = E_annual_MJ / energy_density_MJ_per_l
        cost_per_l   = truck[TruckParam.FUEL_COST_PER_L]
        cost_annual  = volume_l * cost_per_l
        cost_specific = cost_annual / ore_t
        cost_specific_tkm = cost_annual / tkm_total

        return {
            "cost_annual_USD":      cost_annual,
            "cost_specific_USD_t":  cost_specific,
            "cost_specific_USD_tkm": cost_specific_tkm,
            "volume_or_mass":       volume_l,
            "unit":                 "l",
        }

    elif technology == "battery":
        cost_per_kwh  = truck[TruckParam.ELECTRICITY_COST_PER_KWH]
        cost_annual   = E_annual_kWh * cost_per_kwh
        cost_specific = cost_annual / ore_t
        cost_specific_tkm = cost_annual / tkm_total

        return {
            "cost_annual_USD":      cost_annual,
            "cost_specific_USD_t":  cost_specific,
            "cost_specific_USD_tkm": cost_specific_tkm,
            "volume_or_mass":       E_annual_kWh,
            "unit":                 "kWh",
        }

    elif technology == "hydrogen":
        cost_mode = truck.get(TruckParam.HYDROGEN_COST_MODE, "market")

        # Energieaufteilung des H2-Hybrids
        fc_share          = truck[TruckParam.FC_SHARE]
        E_h2_kWh          = E_annual_kWh * fc_share
        E_elec_direct_kWh = E_annual_kWh * (1 - fc_share)

        # Gemeinsame Größen
        cost_per_kwh      = truck.get(TruckParam.ELECTRICITY_COST_PER_KWH, 0.0) or 0.0
        H2_LHV_kWh_per_kg = truck[TruckParam.HYDROGEN_LHV_MJ_PER_KG] / 3.6
        h2_mass_kg        = E_h2_kWh / H2_LHV_kWh_per_kg

        if cost_mode == "onsite_electrolysis":
            # H2 wird on-site via Elektrolyse erzeugt:
            # Kosten basieren auf dem dafür nötigen Strombedarf
            eta_el            = truck[TruckParam.ELECTROLYSIS_EFFICIENCY]
            E_elec_for_h2_kWh = E_h2_kWh / eta_el
            cost_h2           = E_elec_for_h2_kWh * cost_per_kwh
            unit_label        = "kWh electricity"

        else:
            # Standardfall: H2 wird als Energieträger zu einem Marktpreis [$/kg] bezogen
            cost_per_kg = truck[TruckParam.HYDROGEN_COST_PER_KG]
            cost_h2     = h2_mass_kg * cost_per_kg
            unit_label  = "kg H2 + kWh"

        # Stromkosten für den direkten Batterie-Anteil
        cost_elec_direct = E_elec_direct_kWh * cost_per_kwh

        # Gesamtkosten
        cost_annual      = cost_h2 + cost_elec_direct
        cost_specific    = cost_annual / ore_t
        cost_specific_tkm = cost_annual / tkm_total

        return {
            "cost_annual_USD":        cost_annual,
            "cost_specific_USD_t":    cost_specific,
            "cost_specific_USD_tkm":  cost_specific_tkm,
            "cost_h2_USD":            cost_h2,
            "cost_elec_direct_USD":   cost_elec_direct,
            "h2_mass_kg_per_a":       h2_mass_kg,
            "unit":                   unit_label,
        }

    elif technology == "trolley":
        cost_per_kwh  = truck[TruckParam.ELECTRICITY_COST_PER_KWH]
        cost_annual   = E_annual_kWh * cost_per_kwh
        cost_specific = cost_annual / ore_t
        cost_specific_tkm = cost_annual / tkm_total

        return {
            "cost_annual_USD":       cost_annual,
            "cost_specific_USD_t":   cost_specific,
            "cost_specific_USD_tkm": cost_specific_tkm,
            "volume_or_mass":        E_annual_kWh,
            "unit":                  "kWh",
        }


# CAPEX loader
def load_capex():
    capex_file = Path(__file__).parent.parent / "data/capex.yml"
    return yaml.safe_load(capex_file.open())

def calculate_crf(rate, years):
    """Capital Recovery Factor."""
    return rate / (1 - (1 + rate) ** -years)

def calculate_fleet_size(mine, truck):
    """Anzahl Trucks aus Erzdurchsatz."""
    payload_t = truck[TruckParam.PAYLOAD_T]
    ore_t_a   = mine[MineParam.ORE_THROUGHPUT]
    return ore_t_a / (payload_t * 20 * 350 * 0.9)

def calculate_lcoe(mine, truck, energy_result, capex, technology, scenario):
    """
    Voll-LCOE [USD/t Erz] inkl. annualisiertem CAPEX.
    Diesel = CAPEX-freie Baseline (Status Quo).
    """
    # OPEX aus bestehendem Modell
    cost        = calculate_annual_cost(mine, truck, energy_result)
    opex_annual = cost['cost_annual_USD']           # ← Key aus deinem return-Dict

    # Flottengröße
    n_trucks = calculate_fleet_size(mine, truck)

    # Diskontrate je Szenario
    rate     = capex['DISCOUNT_PROG'] if scenario == 'progressive' else capex['DISCOUNT_CONS']
    crf_val  = calculate_crf(rate, capex['LIFETIME_YEARS'])
    salvage  = capex['SALVAGE_FACTOR']

    # CAPEX annualisiert (Diesel = 0 = Baseline)
    if technology == 'diesel':
        ann_capex   = 0
        total_capex = 0
    else:
        capex_truck = capex['CAPEX_TRUCK'][technology]
        capex_infra = capex['CAPEX_INFRA'][technology]
        total_capex = n_trucks * capex_truck + capex_infra
        ann_capex   = total_capex * crf_val * (1 - salvage)

    total_annual = opex_annual + ann_capex
    ore_mt_a     = mine[MineParam.ORE_THROUGHPUT]
    print(f"n_trucks", n_trucks)
    print(f"  SERVUS; TEST!!!")
    print(f"  total_capex:    {total_capex/1e6:.2f} Mio USD")
    print(f"  ann_capex:      {ann_capex/1e6:.2f} Mio USD/a")
    print(f"  opex_annual:    {opex_annual/1e6:.2f} Mio USD/a")
    print(f"  ore_throughput: {mine[MineParam.ORE_THROUGHPUT]/1e6:.1f} Mt/a")
    print(f"  lcoe_usd_per_t: {total_annual / mine[MineParam.ORE_THROUGHPUT]:.4f} USD/t")
    return {
        'n_trucks':          round(n_trucks),
        'total_capex_mio':   total_capex / 1e6,
        'ann_capex_mio':     ann_capex / 1e6,
        'opex_annual_mio':   opex_annual / 1e6,
        'total_annual_mio':  total_annual / 1e6,
        'lcoe_usd_per_t':    total_annual / ore_mt_a,  # ← Key den main.py erwartet!
    }

"""
def calculate_h2_lcoe(mine, truck):
    H2-spezifisch: LCOH + FC.
    h2_breakdown = calculate_h2energybreakdown(mine, truck)
    opex_h2 = h2_breakdown['h2_mass_t_per_a'] * 1000 * CAPEX['H2_LCOH']['prog']
    
    n_trucks = ...  # Wie oben
    fc_capex = 400 * truck[FUELCELL_POWER_KW] * n_trucks
    ann_fc = fc_capex * crf(0.12, 15)
    
    total_opex = opex_h2 + ann_fc  # Rest in calculate_annual_cost
    return total_opex / (mine[ORE_THROUGHPUT]/1e6)
    """

def calculate_phased_lcoe(mine, truck_new, energy_new,
                          truck_diesel, energy_diesel,
                          capex, technology_new, scenario):
    """Phased Transition: Diesel-Anteil (1-phase) + Neue Tech (phase)."""
    LIFETIME = capex['LIFETIME_YEARS']
    rate     = capex['DISCOUNT_PROG'] if scenario == 'progressive' else capex['DISCOUNT_CONS']
    crf_val  = calculate_crf(rate, LIFETIME)

    new_lcoe     = calculate_lcoe(mine, truck_new, energy_new, capex, technology_new, scenario)
    diesel_cost  = calculate_annual_cost(mine, truck_diesel, energy_diesel)
    diesel_opex  = diesel_cost['cost_annual_USD']
    ore_mt_a     = mine[MineParam.ORE_THROUGHPUT]

    results = []
    for phase in capex['PHASE_CURVE']:
        phased_opex  = diesel_opex * (1 - phase) + new_lcoe['opex_annual_mio'] * 1e6 * phase
        phased_capex = new_lcoe['ann_capex_mio'] * 1e6 * phase
        total        = phased_opex + phased_capex
        results.append({
            'phase_pct':         phase * 100,
            'phased_lcoe_usd_t': total / ore_mt_a,
            'diesel_share_pct':  (1 - phase) * 100,
        })
    return results

def convert_h2_energy_to_electricity(energy_result: dict, truck: dict) -> dict:
    """
    Gibt ein modifiziertes energy_result zurück, in dem die H2-Energie
    durch die äquivalente Strommenge (inkl. Elektrolyse-Verluste) ersetzt ist.
    Alle anderen Technologien bleiben unverändert.

    Verwendung NUR für Plots/Vergleiche – NICHT für Kostenberechnung.
    """
    from .loader import TruckParam
    tech = truck[TruckParam.TECHNOLOGY]
    if tech != "hydrogen":
        return energy_result  # keine Änderung für Diesel, BEV, Trolley

    fc_share  = truck[TruckParam.FC_SHARE]
    eta_el    = truck[TruckParam.ELECTROLYSIS_EFFICIENCY]

    E_kWh = energy_result["E_annual_kWh"]

    # H2-Anteil: Energie wird durch Elektrolyse-Wirkungsgrad dividiert
    E_h2_as_elec   = (E_kWh * fc_share) / eta_el
    E_direct_elec  = E_kWh * (1.0 - fc_share)
    E_total_elec   = E_h2_as_elec + E_direct_elec

    # Skalierungsfaktor gegenüber Original
    scale = E_total_elec / E_kWh if E_kWh > 0 else 1.0

    # Alle Energiewerte skalieren (E_specific etc. proportional)
    result = {k: v * scale if isinstance(v, float) else v
              for k, v in energy_result.items()}
    return result
