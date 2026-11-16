# Simulación y Sinóptico SCADA — Control PI Feedback–Feedforward en Banco de Flotación

Proyecto completo en Python (Streamlit + HTML5 Canvas + Plotly) basado en:
> **Quintanilla, P., Navia, D., Moreno, F., Neethling, S. J., & Brito-Parada, P. R. (2023).** *A methodology to implement a closed-loop feedback-feedforward level control in a laboratory-scale flotation bank using peristaltic pumps.* MethodsX, 10, 102081.

## Contenido del Paquete
- `app.py`: Aplicación principal en Streamlit con 3 pestañas (Sinóptico SCADA Animado, Simulación Comparativa Fig. 14 y Modelo Matemático SIMC).
- `scada_sinoptico.html`: Sinóptico P&ID/SCADA animado de las 3 celdas en serie (`FT-101/102/103`), bombas peristálticas (`P-1/2/3/4`) y telemetría en vivo `P + I + Feedforward`.
- `modelo_matematico.py`: Modelo integrador con retardo, reglas SIMC, curvas de calibración de 16 bits e índice IAE (`cm·s`).
- `requirements.txt`: Librerías requeridas.

## Ejecución Local en Visual Studio Code
1. Abrir la carpeta `Simulacion_PI_Flotacion_Quintanilla2023_Final` en VS Code.
2. En la terminal integrada ejecutar:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

## Despliegue Público en Render
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
