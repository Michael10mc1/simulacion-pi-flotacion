import numpy as np
import pandas as pd

# Parámetros físicos y experimentales extraídos de Quintanilla et al. (2023), MethodsX 10, 102081
CELL_LENGTH_CM = 30.0
CELL_WIDTH_CM = 30.0
CELL_HEIGHT_CM = 45.0
CELL_AREA_CM2 = CELL_LENGTH_CM * CELL_WIDTH_CM  # 900 cm²

# Constante integradora experimental (Tabla 2): k' = -0.001018 cm * s^-1 * lpm^-1
K_PRIME_ABS = 0.001018

# Parámetros por celda (Tabla 2 y texto sección SIMC / Feedforward)
CELL_PARAMS = {
    1: {
        "nombre": "Celda 1 (FT-101 / Rougher 1)",
        "k_prime": -0.001018,
        "theta": 7,          # Tiempo muerto [s]
        "tau_c": 7,          # Parámetro de sintonización SIMC [s]
        "kc_init": -70.2,    # Kc inicial SIMC [lpm/cm]
        "kc_final": -62.0,   # Kc final experimental [lpm/cm]
        "ti_init": 56.0,     # tau_i inicial SIMC [s]
        "ti_final": 56.0,    # tau_i final experimental [s]
        "kff": 0.8,          # Ganancia Feedforward [-]
        "sp_init": 30.0,     # Nivel inicial de operación [cm]
        "pump_slope": 0.0029,      # Calibración bomba relave P-1: Q = 0.0029 * bits [lpm] (Fig. 9)
        "level_slope": -0.0018,    # Calibración sensor nivel LI-1 (Fig. 11)
        "level_intercept": 40.1363
    },
    2: {
        "nombre": "Celda 2 (FT-102 / Rougher 2)",
        "k_prime": -0.001018,
        "theta": 6,
        "tau_c": 6,
        "kc_init": -81.8,
        "kc_final": -76.0,
        "ti_init": 48.0,
        "ti_final": 30.0,
        "kff": 0.8,
        "sp_init": 33.5,
        "pump_slope": 0.0033,      # Calibración bomba relave P-2: Q = 0.0033 * bits [lpm] (Fig. 9)
        "level_slope": -0.0019,    # Calibración sensor nivel LI-2 (Fig. 11)
        "level_intercept": 43.8823
    },
    3: {
        "nombre": "Celda 3 (FT-103 / Rougher 3)",
        "k_prime": -0.001018,
        "theta": 3,
        "tau_c": 8,
        "kc_init": -78.1,
        "kc_final": -85.0,
        "ti_init": 52.0,
        "ti_final": 44.0,
        "kff": 1.0,
        "sp_init": 33.5,
        "pump_slope": 0.0033,      # Calibración bomba relave P-3: Q = 0.0033 * bits [lpm] (Fig. 9)
        "level_slope": -0.0020,    # Calibración sensor nivel LI-3 (Fig. 11)
        "level_intercept": 41.2930
    }
}

FEED_PUMP_SLOPE = 0.0035  # Calibración bomba alimentación P-4: Q_feed = 0.0035 * bits [lpm] (Fig. 9)


def calcular_sintonizacion_simc(k_prime: float, theta: float, tau_c: float):
    """
    Calcula los parámetros iniciales PI mediante las reglas SIMC de Skogestad
    para procesos integradores (Ecuaciones 2, 3 y 6 del artículo):
        Kc = (1 / k') * (1 / (tau_c + theta))
        tau_i = 4 * (tau_c + theta)
    """
    kc_simc = (1.0 / k_prime) * (1.0 / (tau_c + theta))
    ti_simc = 4.0 * (tau_c + theta)
    return kc_simc, ti_simc


def bits_a_nivel_cm(bits: np.ndarray, cell_id: int) -> np.ndarray:
    """Convierte registros enteros de 16 bits (0 - 32767) a nivel de pulpa en cm (Fig. 11)."""
    p = CELL_PARAMS[cell_id]
    return p["level_slope"] * bits + p["level_intercept"]


def bits_a_caudal_lpm(bits: np.ndarray, pump_type: str = "feed", cell_id: int = 1) -> np.ndarray:
    """Convierte registros enteros de 16 bits (0 - 32767) a caudal en lpm (Fig. 9)."""
    if pump_type == "feed":
        return FEED_PUMP_SLOPE * bits
    return CELL_PARAMS[cell_id]["pump_slope"] * bits


def simular_banco_flotacion(
    t_total: int = 600,
    q_feed_base: float = 45.0,
    step_dist: float = 15.0,
    t_dist: int = 250,
    t_sp_change: int = 175,
    sp_targets: tuple = (30.0, 33.5, 33.5),
    sp_step_delta: float = -1.0,
    kc_list: list = None,
    ti_list: list = None,
    kff_list: list = None,
    td_list: list = None,
    noise_std: float = 0.0,
    use_ff: bool = True,
    seed: int = 42
):
    """
    Simula el banco de 3 celdas de flotación en serie (Quintanilla et al., 2023):
      - Modelo de planta integradora con tiempo muerto: dh_i/dt = |k'| * (Q_in_i - Q_out_i)
      - Acoplamiento en serie: Q_in_2(t) = Q_out_1(t-1), Q_in_3(t) = Q_out_2(t-1)
      - Controlador Feedback PI (tau_d = 0 en el paper) + Feedforward:
            u_i(t) = u_bias + Kc_i * (e_i(t) + (1/tau_i)*int(e_i) + tau_d*de_i/dt) + Kff_i * dQ_in_i
      - Índice de desempeño IAE_i = integral(|e_i(t)| dt) [cm·s] (Ec. 9)
    """
    rng = np.random.default_rng(seed)
    dt = 1.0  # Tiempo de muestreo Ts = 1 s (sección Method validation)
    steps = int(t_total / dt)
    time = np.arange(0, steps) * dt

    if kc_list is None:
        kc_list = [CELL_PARAMS[i]["kc_final"] for i in (1, 2, 3)]
    if ti_list is None:
        ti_list = [CELL_PARAMS[i]["ti_final"] for i in (1, 2, 3)]
    if kff_list is None:
        kff_list = [CELL_PARAMS[i]["kff"] if use_ff else 0.0 for i in (1, 2, 3)]
    else:
        kff_list = [val if use_ff else 0.0 for val in kff_list]
    if td_list is None:
        td_list = [0.0, 0.0, 0.0]

    thetas = [CELL_PARAMS[i]["theta"] for i in (1, 2, 3)]

    h_true = np.zeros((3, steps))
    h_meas = np.zeros((3, steps))
    sp = np.zeros((3, steps))
    u = np.zeros((3, steps))
    q_in = np.zeros((3, steps))
    integral = np.zeros(3)
    prev_err = np.zeros(3)

    for i in range(3):
        h_true[i, 0] = sp_targets[i]
        h_meas[i, 0] = sp_targets[i]
        u[i, 0] = q_feed_base

    for k in range(steps):
        for i in range(3):
            sp[i, k] = sp_targets[i] if time[k] < t_sp_change else (sp_targets[i] + sp_step_delta)
        q_in[0, k] = q_feed_base if time[k] < t_dist else (q_feed_base + step_dist)

    for k in range(1, steps):
        # Acoplamiento en serie (Fig. 15)
        q_in[1, k] = u[0, k - 1]
        q_in[2, k] = u[1, k - 1]

        for i in range(3):
            idx_delay = max(0, k - thetas[i])
            noise = rng.normal(0.0, noise_std) if noise_std > 0 else 0.0
            y_sensor = h_true[i, idx_delay] + noise
            h_meas[i, k] = y_sensor

            err = sp[i, k] - y_sensor
            integral[i] = np.clip(integral[i] + err * dt, -60.0, 60.0)
            deriv = (err - prev_err[i]) / dt
            prev_err[i] = err

            # Acción Feedforward: Kff_i * (Qd_i(t) - Qd_i(t-1)) (Ec. 7 y 8)
            dq_dist = q_in[i, k] - q_in[i, k - 1]
            u_ff = kff_list[i] * dq_dist

            # Ley de control completa (Ec. 1 y 7)
            u_fb = kc_list[i] * (err + (1.0 / ti_list[i]) * integral[i] + td_list[i] * deriv)
            u_cmd = q_feed_base + u_fb + u_ff

            # Restricciones físicas bombas peristálticas Masterflex L/S (0 - 95 lpm)
            u[i, k] = np.clip(u_cmd, 0.0, 95.0)

            # Balance de masa integrador (Ec. 4 y 10): dh/dt = |k'| * (Q_in - Q_out)
            dh = K_PRIME_ABS * (q_in[i, k] - u[i, k]) * dt
            h_true[i, k] = np.clip(h_true[i, k - 1] + dh, 0.0, CELL_HEIGHT_CM)

    iae = [float(np.sum(np.abs(sp[i] - h_true[i])) * dt) for i in range(3)]

    return {
        "time": time,
        "h_true": h_true,
        "h_meas": h_meas,
        "sp": sp,
        "u": u,
        "q_in": q_in,
        "iae": iae
    }
