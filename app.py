import os
import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modelo_matematico import (
    CELL_PARAMS,
    CELL_AREA_CM2,
    CELL_HEIGHT_CM,
    K_PRIME_ABS,
    calcular_sintonizacion_simc,
    bits_a_nivel_cm,
    bits_a_caudal_lpm,
    simular_banco_flotacion,
)

st.set_page_config(
    page_title="Control PI Feedback–Feedforward | Banco de Flotación",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("Control de Nivel Feedback–Feedforward (PI) en Banco de 3 Celdas de Flotación")
st.caption(
    "Simulación Física, Sinóptico SCADA Interactivo y Modelo Matemático basados en "
    "Quintanilla, Navia, Moreno, Neethling & Brito-Parada (2023) — MethodsX 10, 102081."
)

tab_scada, tab_sim, tab_math = st.tabs([
    "1. Sinóptico SCADA Animado (3 Tanques en Serie)",
    "2. Simulación Comparativa (PI vs. PI + Feedforward — Fig. 14)",
    "3. Modelo Matemático, Calibración 16-bit y Sintonización SIMC"
])

with tab_scada:
    html_path = os.path.join(os.path.dirname(__file__), "scada_sinoptico.html")
    with open(html_path, "r", encoding="utf-8") as f:
        scada_html = f.read()
    components.html(scada_html, height=920, scrolling=True)

with tab_sim:
    st.subheader("Evaluación Cuantitativa de Desempeño — Índice IAE (Ecuación 9)")
    col_ctrl, col_plot = st.columns([1, 2.8])

    with col_ctrl:
        st.markdown("#### Parámetros de Ensayo")
        modo_vista = st.radio(
            "Estrategia a graficar:",
            ["Comparación Directa (PI vs. PI + FF)", "Solo Feedback (PI Clásico)", "Feedback + Feedforward (PI + FF)"],
            index=0
        )
        t_total = st.slider("Duración simulación [s]", 200, 900, 600, step=50)
        q_feed_base = st.slider("Caudal base Q_feed [lpm]", 25.0, 65.0, 45.0, step=1.0)
        t_sp_change = st.slider("Instante cambio SP (-1 cm) [s]", 50, 400, 175, step=25)
        t_dist = st.slider("Instante perturbación Q_feed [s]", 100, 500, 250, step=25)
        step_dist = st.slider("Escalón perturbación ΔQ_feed [lpm]", -20.0, 30.0, 15.0, step=1.0)

        with st.expander("Sintonización SIMC (Tabla 2)", expanded=False):
            kc1 = st.number_input("Kc Celda 1 [lpm/cm]", value=-62.0, step=1.0)
            ti1 = st.number_input("τi Celda 1 [s]", value=56.0, step=1.0)
            kff1 = st.number_input("Kff Celda 1 [-]", value=0.8, step=0.1)

            kc2 = st.number_input("Kc Celda 2 [lpm/cm]", value=-76.0, step=1.0)
            ti2 = st.number_input("τi Celda 2 [s]", value=30.0, step=1.0)
            kff2 = st.number_input("Kff Celda 2 [-]", value=0.8, step=0.1)

            kc3 = st.number_input("Kc Celda 3 [lpm/cm]", value=-85.0, step=1.0)
            ti3 = st.number_input("τi Celda 3 [s]", value=44.0, step=1.0)
            kff3 = st.number_input("Kff Celda 3 [-]", value=1.0, step=0.1)

        with st.expander("Prueba: Ruido y Derivada (τd)", expanded=False):
            noise_std = st.slider("Ruido sensor por burbujeo (σ) [cm]", 0.0, 0.4, 0.05, step=0.01)
            td_val = st.slider("Tiempo derivativo τd [s] (0 = PI puro)", 0.0, 5.0, 0.0, step=0.5)

    res_fb = simular_banco_flotacion(
        t_total=t_total, q_feed_base=q_feed_base, step_dist=step_dist,
        t_dist=t_dist, t_sp_change=t_sp_change,
        kc_list=[kc1, kc2, kc3], ti_list=[ti1, ti2, ti3], kff_list=[kff1, kff2, kff3],
        td_list=[td_val, td_val, td_val], noise_std=noise_std, use_ff=False
    )
    res_ff = simular_banco_flotacion(
        t_total=t_total, q_feed_base=q_feed_base, step_dist=step_dist,
        t_dist=t_dist, t_sp_change=t_sp_change,
        kc_list=[kc1, kc2, kc3], ti_list=[ti1, ti2, ti3], kff_list=[kff1, kff2, kff3],
        td_list=[td_val, td_val, td_val], noise_std=noise_std, use_ff=True
    )

    with col_plot:
        m1, m2, m3 = st.columns(3)
        for idx, col in enumerate([m1, m2, m3]):
            iae_pi = res_fb["iae"][idx]
            iae_ff = res_ff["iae"][idx]
            diff = iae_ff - iae_pi
            pct = ((iae_pi - iae_ff) / iae_pi * 100.0) if iae_pi > 0 else 0.0
            col.metric(
                label=f"Celda {idx+1} — IAE (PI + FF)",
                value=f"{iae_ff:.1f} cm·s",
                delta=f"{diff:.1f} cm·s ({pct:.1f}% menor error vs Solo PI)",
                delta_color="inverse"
            )

        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "Celda 1 (FT-101) — Nivel hp [cm]", "Celda 1 — Bomba P-1 vs Perturbación [lpm]",
                "Celda 2 (FT-102) — Nivel hp [cm]", "Celda 2 — Bomba P-2 vs Perturbación [lpm]",
                "Celda 3 (FT-103) — Nivel hp [cm]", "Celda 3 — Bomba P-3 vs Perturbación [lpm]"
            ),
            vertical_spacing=0.09, horizontal_spacing=0.07
        )
        time = res_ff["time"]
        for i in range(3):
            row = i + 1
            fig.add_trace(go.Scatter(x=time, y=res_ff["sp"][i], name="Setpoint (SP)", line=dict(color="red", dash="dash", width=1.8), showlegend=(i == 0)), row=row, col=1)
            if modo_vista in ["Comparación Directa (PI vs. PI + FF)", "Solo Feedback (PI Clásico)"]:
                fig.add_trace(go.Scatter(x=time, y=res_fb["h_true"][i], name="Nivel Solo PI", line=dict(color="#ff7f0e", width=2.0), showlegend=(i == 0)), row=row, col=1)
                fig.add_trace(go.Scatter(x=time, y=res_fb["u"][i], name="Bomba (Solo PI)", line=dict(color="#ff7f0e", dash="dot", width=1.6), showlegend=(i == 0)), row=row, col=2)
            if modo_vista in ["Comparación Directa (PI vs. PI + FF)", "Feedback + Feedforward (PI + FF)"]:
                fig.add_trace(go.Scatter(x=time, y=res_ff["h_true"][i], name="Nivel PI + FF", line=dict(color="#1f77b4", width=2.4), showlegend=(i == 0)), row=row, col=1)
                fig.add_trace(go.Scatter(x=time, y=res_ff["u"][i], name="Bomba (PI + FF)", line=dict(color="black", width=1.8), showlegend=(i == 0)), row=row, col=2)
            fig.add_trace(go.Scatter(x=time, y=res_ff["q_in"][i], name="Perturbación Q_in", line=dict(color="#00bcd4", width=1.6), showlegend=(i == 0)), row=row, col=2)
            fig.update_yaxes(title_text="hp [cm]", range=[25, 38], row=row, col=1)
            fig.update_yaxes(title_text="Q [lpm]", range=[0, 100], row=row, col=2)

        fig.update_xaxes(title_text="Tiempo [s]", row=3, col=1)
        fig.update_xaxes(title_text="Tiempo [s]", row=3, col=2)
        fig.update_layout(height=820, template="plotly_white", legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True)

        df_out = pd.DataFrame({
            "Tiempo_s": time,
            "SP_C1_cm": res_ff["sp"][0], "Nivel_PI_C1_cm": res_fb["h_true"][0], "Nivel_PI_FF_C1_cm": res_ff["h_true"][0], "Bomba_P1_FF_lpm": res_ff["u"][0],
            "SP_C2_cm": res_ff["sp"][1], "Nivel_PI_C2_cm": res_fb["h_true"][1], "Nivel_PI_FF_C2_cm": res_ff["h_true"][1], "Bomba_P2_FF_lpm": res_ff["u"][1],
            "SP_C3_cm": res_ff["sp"][2], "Nivel_PI_C3_cm": res_fb["h_true"][2], "Nivel_PI_FF_C3_cm": res_ff["h_true"][2], "Bomba_P3_FF_lpm": res_ff["u"][2],
        })
        st.download_button(
            label="Descargar resultados completos en CSV",
            data=df_out.to_csv(index=False).encode("utf-8"),
            file_name="resultados_flotacion_PI_Feedforward.csv",
            mime="text/csv"
        )

with tab_math:
    st.header("Modelo Matemático del Artículo (Quintanilla et al., 2023)")
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        st.subheader("1. Planta Integradora con Tiempo Muerto (Ec. 4)")
        st.markdown(
            f"Cada celda tiene área transversal de **30 × 30 cm** ($A = {CELL_AREA_CM2:.0f}\text{{ cm}}^2$) "
            f"y altura de **{CELL_HEIGHT_CM:.0f} cm**. Al extraer relaves mediante **bombas peristálticas** "
            "(*Masterflex L/S*), el nivel responde como un **integrador puro con retardo**:"
        )
        st.latex(r"G_p(s) = \frac{Y(s)}{U(s)} = \frac{k'}{s} e^{-\theta s} = \frac{-0.001018}{s} e^{-\theta s}")
        st.markdown(
            "Con $k' = -0.001018\text{ cm}\cdot\text{s}^{-1}\cdot\text{lpm}^{-1}$ y tiempos muertos "
            "$\theta_1 = 7\text{ s}$, $\theta_2 = 6\text{ s}$ y $\theta_3 = 3\text{ s}$."
        )

    with col_eq2:
        st.subheader("2. Controlador PI (τd = 0) + Feedforward (Ec. 7 y 8)")
        st.markdown(
            "Los autores fijan **$\tau_d = 0$ (PI puro)** por el ruido del aire ($47\text{ lpm}$) y añaden el "
            "adelanto **Feedforward** proporcional al cambio del caudal de entrada:"
        )
        st.latex(r"u_i(t) = K_{c_i}\left(e_i(t) + \frac{1}{\tau_{i_i}}\int_0^t e_i(\tau)\,d\tau\right) + K_{ff_i}\Delta Q_{d_i}")
        st.latex(r"\Delta Q_{d_i} = Q_{d_i}(t) - Q_{d_i}(t-1), \quad i = 1, 2, 3")

    st.divider()
    st.subheader("3. Reglas de Sintonización SIMC (Tabla 2)")
    st.latex(r"K_c = \frac{1}{k'}\frac{1}{\tau_c + \theta}, \qquad \tau_i = 4(\tau_c + \theta)")

    rows_tabla = []
    for i in (1, 2, 3):
        p = CELL_PARAMS[i]
        kc_calc, ti_calc = calcular_sintonizacion_simc(p["k_prime"], p["theta"], p["tau_c"])
        rows_tabla.append({
            "Celda": p["nombre"],
            "k' [cm·s⁻¹·lpm⁻¹]": p["k_prime"],
            "θ [s]": p["theta"],
            "τc [s]": p["tau_c"],
            "Kc SIMC Inicial [lpm/cm]": round(kc_calc, 1),
            "Kc Final Paper [lpm/cm]": p["kc_final"],
            "τi SIMC Inicial [s]": round(ti_calc, 1),
            "τi Final Paper [s]": p["ti_final"],
            "Kff Óptimo [-]": p["kff"],
        })
    st.dataframe(pd.DataFrame(rows_tabla), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("4. Calibración de Instrumentación PLC (Registros 16-bit: 0 – 32,767)")
    bits_nivel = np.linspace(500, 8500, 100)
    bits_bomba = np.linspace(0, 30000, 100)

    col_cal1, col_cal2 = st.columns(2)
    with col_cal1:
        fig_cal_lvl = go.Figure()
        for i in (1, 2, 3):
            fig_cal_lvl.add_trace(go.Scatter(x=bits_nivel, y=bits_a_nivel_cm(bits_nivel, i), name=f"Sensor Nivel LI-{i}"))
        fig_cal_lvl.update_layout(title="Calibración Sensores de Nivel (Fig. 11)", xaxis_title="Bits 16-bit", yaxis_title="Nivel hp [cm]", template="plotly_white", height=360)
        st.plotly_chart(fig_cal_lvl, use_container_width=True)

    with col_cal2:
        fig_cal_pmp = go.Figure()
        fig_cal_pmp.add_trace(go.Scatter(x=bits_bomba, y=bits_a_caudal_lpm(bits_bomba, "feed"), name="Bomba Alimentación P-4 (0.0035x)"))
        fig_cal_pmp.add_trace(go.Scatter(x=bits_bomba, y=bits_a_caudal_lpm(bits_bomba, "tailings", 1), name="Bomba Relave P-1 (0.0029x)"))
        fig_cal_pmp.add_trace(go.Scatter(x=bits_bomba, y=bits_a_caudal_lpm(bits_bomba, "tailings", 2), name="Bombas Relave P-2 y P-3 (0.0033x)"))
        fig_cal_pmp.update_layout(title="Calibración Bombas Peristálticas (Fig. 9)", xaxis_title="Bits 16-bit", yaxis_title="Caudal Q [lpm]", template="plotly_white", height=360)
        st.plotly_chart(fig_cal_pmp, use_container_width=True)
