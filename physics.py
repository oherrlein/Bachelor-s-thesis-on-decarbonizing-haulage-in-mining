import math
import numpy as np  # neu hinzufügen am Anfang der Datei
from .loader import MineParam, TruckParam 

# -------------------------
# DRAG CONSTANT
# -------------------------

def drag_constant(C_d, rho_air, A_f):
    #C_d drag coefficient: depends on mine
    #p_air density of air: depends on mine
    #A_f surface truck: depends on truck technology
    return 0.5 * C_d * rho_air * A_f

# -------------------------
# ROLLING + GRADIENT
# -------------------------

def constancia_speed_loaded_kmh(grad_percent):
    """
    Approximation of red speed curve (loaded) from Constancia - technical report.
    Input: Gradient [%] (negative = downhill, positive = uphill)
    Output: velocity [km/h] for 240 - payload - class (similar to Liebherr T264).
    """
    g = grad_percent
    # Values are taken from graph manually:
    # -12%:19, -10%:20, -8%:21, -6%:22, -4%:24, -2%:27, 0%:30,
    #  2%:30,  4%:26,  6%:15,  8%:11, 10%:9
    points = [
        (-12, 19), (-10, 20), (-8, 21), (-6, 22), (-4, 24),
        (-2, 27), (0, 30), (2, 30), (4, 26), (6, 15), (8, 11), (10, 9),
    ]
    grads, speeds = zip(*points)
    return float(np.interp(g, grads, speeds))  # km/h

def constancia_speed_empty_kmh(grad_percent):
    """
    Approximation of blue speed curve (empty) from Constancia - technical report.
    Same as above, just for empty trucks of 240 t - payload class
    """
    g = grad_percent
    # Abgelesen:
    # -12%:28, -10%:29, -8%:30, -6%:32, -4%:36,
    #  -2%:36,  0%:36,  2%:36,  4%:34,  6%:30,  8%:25, 10%:19
    points = [
        (-12, 28), (-10, 29), (-8, 30), (-6, 32), (-4, 36),
        (-2, 36), (0, 36), (2, 36), (4, 34), (6, 30), (8, 25), (10, 19),
    ]
    grads, speeds = zip(*points)
    return float(np.interp(g, grads, speeds))  # km/h

def cerro_corona_speed_loaded_kmh(grad_percent): 
    """
    Information does not come from sahoo anymore, but from technical report of Komatsu 
    HD265, which is a comparable truck. The values from the technical report are reduced by 25%.
    This is done bc the data in the report is theoretical data under laboratory conditions.
    """
    points = [
        (-12, 21), (-10, 22), (-8, 23.1), (-6, 24.2), (-4, 26.4),
        (-2, 29.7), (0, 33), (2, 33), (4, 28.6), (6, 16.5), (8, 12.1), (10, 9.9),
    ]
    grads, speeds = zip(*points)
    return float(np.interp(grad_percent, grads, speeds))

def cerro_corona_speed_empty_kmh(grad_percent):
    """
    Information does not come from sahoo anymore, but from technical report of Komatsu 
    HD265, which is a comparable truck. The values from the technical report are reduced by 25%.
    This is done bc the data in the report is theoretical data under laboratory conditions.
    """
    points = [
        (-12, 30.8), (-10, 31.9), (-8, 33), (-6, 35.2), (-4, 39.6),
        (-2, 39.6), (0, 39.6), (2, 39.6), (4, 37.4), (6, 33), (8, 27.5), (10, 20.9),
    ]
    grads, speeds = zip(*points)
    return float(np.interp(grad_percent, grads, speeds))

def antamina_cuajone_speed_loaded_kmh(grad_percent):
    """
    Speed curve for Antamina and Cuajone – loaded trucks.
    Based on Constancia speed curve (large truck class), reduced by 20%
    to reflect site-specific conditions.
    """
    base = constancia_speed_loaded_kmh(grad_percent)
    return base * 0.80

def antamina_cuajone_speed_empty_kmh(grad_percent):
    """
    Speed curve for Antamina and Cuajone – empty trucks.
    Based on Constancia speed curve (large truck class), reduced by 20%
    to reflect site-specific conditions.
    """
    base = constancia_speed_empty_kmh(grad_percent)
    return base * 0.80

    
def rolling_gradient_constant_loaded(grad_deg, f, C_rr, direction="up"):
    grad_rad = math.radians(grad_deg)
    cos_o = math.cos(grad_rad)
    sin_o = math.sin(grad_rad)

    # beladen: analogue to c in equation (10) for negative/positive gradients
    # but mapped to my scenario, where trucks go up fully loaded and down empty
    if direction == "up":
        # uphill loaded: resistance sums up with gradient and rolling resistance (P_ec)
        return cos_o * (f + C_rr) + sin_o
    else:
        # downhill loaded: (will never happen using uphill mines, as in my case but wanted to represent it bc its in the used paper)
        return cos_o * (f + C_rr) - sin_o

def rolling_gradient_constant_empty(grad_deg, f, C_rr, direction="up"):
    grad_rad = math.radians(grad_deg)
    cos_o = math.cos(grad_rad)
    sin_o = math.sin(grad_rad)

    # leer: analogue to c in equation (10), for negative/positive gradients
    # mapped to my scenario, 
    if direction == "up":
        # uphill empty (should never happen using uphill mines, as in my case, but wanted to represent it bc its in the used paper)
        return cos_o * (f + C_rr) + sin_o
    else:
        # downhill empty (P_ce)
        return cos_o * (f + C_rr) - sin_o

def apply_regen(P_wheel, eta_regen):
    """
    P_wheel: Leistung am Rad (+ = Vortrieb, - = Bremsen).
    Rückgabe: Leistung am Energiespeicher/Antrieb:
      >0  -> Speicher liefert Energie
      <0  -> Speicher wird geladen (Rekuperation)
    """
    if P_wheel >= 0:
        # Vortrieb: Quelle muss mehr liefern als am Rad ankommt (wegen eta),
        # das berücksichtigst du aber später über eta in calculate_cycle_energy.
        return P_wheel
    else:
        # Bremsen: Betrag der Radleistung
        P_brake = -P_wheel
        # Anteil, der als Ladung im Speicher ankommt
        P_recup = eta_regen * P_brake
        # Am Speicher: negative Leistung (Ladung)
        return -P_recup



def max_speed_from_power(P_max_W, W, L, a, resistance_const):
    """
    Calculates maximum physically achievable truck speed from engine power.
    Solves the cubic power equation (Sahoo et al. 2014, Eq. 4) for V:
    
        P_max = V * (a*V² + resistance_const*W) + W*V³ / (2L)
        → (a + W/(2L)) * V³ + resistance_const*W * V - P_max = 0
    
    Args:
        P_max_W          : maximum drive power [W]
        W                : weight force (mass * g) [N]
        L                : segment length [m]
        a                : drag constant (0.5 * C_d * rho_air * A_f)
        resistance_const : rolling + gradient constant (b or c from paper)
    Returns:
        speed [m/s] — smallest positive real root
    """
    A = a + W / (2 * L)
    C = resistance_const * W
    D = -P_max_W
    # cubic equation: A*V³ + 0*V² + C*V + D = 0
    roots = np.roots([A, 0, C, D])
    real_positive = [r.real for r in roots if abs(r.imag) < 1e-6 and r.real > 0]
    if not real_positive:
        raise ValueError(
            f"No valid speed solution found: P_max={P_max_W/1000:.0f} kW, "
            f"W={W/1000:.0f} kN, L={L:.0f} m, a={a:.4f}, c={resistance_const:.4f}"
        )
    return min(real_positive)


# -------------------------
# POWER EQUATION
# -------------------------

def power_segment(V, W, L, a, resistance_const): #resistance const is either a or b
    """
    Power required by dump truck on a segment.
    Eq. (4), Sahoo et al. (2014).
    
    V               : truck speed [m/s]
    W               : weight force (mass * g) [N]  ← das ist W_G aus dem Paper
    L               : segment distance [m]
    a               : drag constant (= 0.5 * C_d * rho_air * A_f)
    resistance_const: rolling + gradient constant (b or c from paper)
    """
    term_drive = V * (a * V**2 + resistance_const *W)
    term_accel = 0.5 * W * V**3 / L
    
    #equation 4 in paper
    #Assumption: V_rec = V
    print(f"term_drive={term_drive/1e6:.2f}MW, term_accel={term_accel/1e6:.2f}MW")
    print(f"  c*W={resistance_const * W / 1e6:.3f} MN, "
      f"a*V²={a * V**2:.1f} N, "
      f"V={V:.2f} m/s")

    return term_drive + term_accel

def idle_energy(idle_power_kw, t_load_s, t_unload_s):
    """
    Energy that truck consumes in during idle (loading and unloading)
    equals mf_idle * (t_load_UL), from equation (21) of Paper
    Returns: Idle-Energy [J]
    """
    t_idle = t_load_s + t_unload_s   # [s]
    return idle_power_kw * 1000 * t_idle  # [W * s = J]




