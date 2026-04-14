import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import re
import pytz
from urllib.parse import quote

# ==================== CONFIG ====================
st.set_page_config(
    page_title="Inspecciones Vehiculares",
    layout="wide",
    page_icon="🔍",
    initial_sidebar_state="expanded"
)

BOGOTA_TZ = pytz.timezone("America/Bogota")

# ==================== HARDCODED SHEET CONFIG ====================
SHEET_ID   = "1Y9L1NGfUpb79k672ZV8eq9M0MrZABzWdE_SfnFiBOi4"
SHEET_NAME = "Respuestas de formulario 1"

# ==================== CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }
.main-header {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
}
.main-header h1 {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem; font-weight: 700; color: white; margin: 0; letter-spacing: 1px;
}
.main-header p { color: #a0c4d8; margin: 0.3rem 0 0 0; font-size: 0.9rem; }

.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.15rem; font-weight: 700; color: #203a43;
    border-bottom: 2px solid #2c5364; padding-bottom: 4px; margin: 1.2rem 0 0.6rem 0;
}
.badge-ok    { background:#d5f5e3; color:#1e8449; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-falla { background:#fadbd8; color:#922b21; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-na    { background:#eaecee; color:#566573; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ==================== MAPEO DE COLUMNAS ====================
COLS = {
    "marca_temporal":       "Marca temporal",
    "fecha":                "FECHA: ",
    "placa":                "PLACA DEL VEHICULO:",
    "conductor":            "NOMBRE Y APELLIDOS DEL CONDUCTOR:",
    "documento":            "DOCUMENTO IDENTIDAD:",
    "kilometraje":          "KILOMETRAJE:",
    "salud_conductor":      "1. ESTADO DE LA SALUD DEL CONDUCTOR",
    "luces":                "2. ESTADO DE LAS LUCES",
    "liquidos":             "3. NIVELES Y PÉRDIDAS DE LÍQUIDOS",
    "frenos":               "4. ESTADO DE FRENOS",
    "baterias":             "5. FUNCIONAMIENTO DE LAS BATERIAS",
    "tablero":              "6. TABLERO DE CONTROL",
    "observaciones":        "OBSERVACIONES GENERALES:",
    "hallazgos":            "HALLAZGOS",
}

ITEMS_INSPECCION = {
    "Salud Conductor":    "salud_conductor",
    "Luces":              "luces",
    "Líquidos":           "liquidos",
    "Frenos":             "frenos",
    "Baterías":           "baterias",
    "Tablero Control":    "tablero",
}

GRUPOS_INSPECCION = {
    "🧑 Conductor":           ["salud_conductor"],
    "💡 Luces y Tablero":     ["luces", "tablero"],
    "🔧 Mecánica":            ["liquidos", "frenos", "baterias"],
}

DIAS_ES = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
MESES_ES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

# ==================== HELPERS ====================
def es_falla(valor):
    if pd.isna(valor) or str(valor).strip() == "": return False
    v = str(valor).strip().upper()
    keywords_falla = ["MAL", "FALLA", "DEFICIENTE", "ROTO", "NO FUNCIONA", "REGULAR", "NO", "MALO"]
    for k in keywords_falla:
        if k in v: return True
    return False

def normalizar_nombre(nombre):
    if pd.isna(nombre) or str(nombre).strip() == "": return ""
    return re.sub(r'\s+', ' ', str(nombre).strip()).title()

def parsear_fecha(serie):
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)

# ==================== CARGA DE DATOS ====================
@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos_sheets(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
    try:
        df = pd.read_csv(url)
        rename_map = {}
        for short, full in COLS.items():
            for col in df.columns:
                if full.lower() in col.lower():
                    rename_map[col] = short
                    break
        df = df.rename(columns=rename_map)
        
        for col in ["marca_temporal", "fecha"]:
            if col in df.columns: df[col] = parsear_fecha(df[col])
        
        if "conductor" in df.columns:
            df["conductor"] = df["conductor"].apply(normalizar_nombre)
        
        if "placa" in df.columns:
            df["placa"] = df["placa"].astype(str).str.strip().str.upper()

        # Cálculo de estado
        item_cols = [c for c in df.columns if c in ITEMS_INSPECCION.values()]
        if item_cols:
            df["_fallas_count"] = df[item_cols].apply(lambda r: sum(es_falla(v) for v in r), axis=1)
            df["_estado"] = df["_fallas_count"].apply(lambda n: "✅ Sin Fallas" if n == 0 else ("⚠️ Fallas Menores" if n <= 3 else "❌ Fallas Críticas"))
        
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

def generar_excel_inspeccion(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inspecciones')
    return output.getvalue()

# ==================== MAIN ====================
def main():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 INSPECCIONES VEHICULARES</h1>
        <p>Reporte de Cumplimiento y Análisis de Seguridad</p>
    </div>
    """, unsafe_allow_html=True)

    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.header("⚙️ Configuración")
        if st.button("🔄 Recargar Datos", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.subheader("👥 Nómina Oficial")
        st.caption("Pega la lista de conductores (uno por línea) para verificar quién NO está cumpliendo.")
        nomina_input = st.text_area("Nombres de conductores:", 
                                    placeholder="JUAN PEREZ\nMARIA LOPEZ...",
                                    height=250)
        # Limpiar y normalizar lista maestra
        lista_maestra = [normalizar_nombre(n) for n in nomina_input.split('\n') if n.strip()]

    df_raw = cargar_datos_sheets(SHEET_ID, SHEET_NAME)
    if df_raw.empty:
        st.warning("No hay datos disponibles.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📋 Historial", "📊 Dashboard de Cumplimiento", "🔎 Detalle"])

    # ===================== TAB 1: HISTORIAL =====================
    with tab1:
        st.dataframe(df_raw, use_container_width=True)

    # ===================== TAB 2: DASHBOARD =====================
    with tab2:
        import plotly.express as px
        
        # --- SECCIÓN 1: CUMPLIMIENTO ---
        st.markdown("## 📈 Control de Cumplimiento")
        
        if "conductor" in df_raw.columns:
            # Conductores que han registrado al menos una vez
            conductores_activos = df_raw["conductor"].unique()
            conteo_por_conductor = df_raw["conductor"].value_counts().reset_index()
            conteo_por_conductor.columns = ["Conductor", "Inspecciones"]

            # Si hay lista maestra, comparamos
            if lista_maestra:
                maestros_set = set(lista_maestra)
                activos_set = set(conductores_activos)
                
                faltan = sorted(list(maestros_set - activos_set))
                cumplen = sorted(list(maestros_set & activos_set))
                
                c1, c2, c3 = st.columns(3)
                c1.metric("👥 Nómina Total", len(maestros_set))
                c2.metric("✅ Han Reportado", len(cumplen))
                c3.metric("❌ No han Reportado", len(faltan))
                
                col_cumple, col_falta = st.columns(2)
                with col_cumple:
                    st.success("#### ✅ Conductores al día")
                    resumen_ok = conteo_por_conductor[conteo_por_conductor["Conductor"].isin(cumplen)]
                    st.dataframe(resumen_ok, use_container_width=True, hide_index=True)
                
                with col_falta:
                    st.error("#### ❌ Conductores sin ningún registro")
                    if faltan:
                        for f in faltan: st.write(f"- {f}")
                    else:
                        st.write("¡Todos han reportado!")
            else:
                st.info("💡 Ingresa la lista de conductores en la barra lateral para ver quién falta.")

            st.divider()

            # --- SECCIÓN 2: RANKINGS ---
            st.markdown("## 🏆 Rankings de Actividad")
            k1, k2 = st.columns(2)
            
            with k1:
                st.markdown("#### 🔥 Los que más reportan")
                top_conductores = conteo_por_conductor.head(5)
                fig_top = px.bar(top_conductores, x="Inspecciones", y="Conductor", orientation='h',
                                 color="Inspecciones", color_continuous_scale="Viridis")
                st.plotly_chart(fig_top, use_container_width=True)
                
            with k2:
                st.markdown("#### 🧊 Los que menos reportan")
                # Solo tomamos a los que han reportado al menos una vez
                bottom_conductores = conteo_por_conductor.tail(5).sort_values("Inspecciones")
                fig_bot = px.bar(bottom_conductores, x="Inspecciones", y="Conductor", orientation='h',
                                 color="Inspecciones", color_continuous_scale="Reds")
                st.plotly_chart(fig_bot, use_container_width=True)

        st.divider()
        
        # --- SECCIÓN 3: ESTADOS ---
        st.markdown("## 🚦 Estado de la Flota")
        g1, g2 = st.columns(2)
        with g1:
            if "_estado" in df_raw.columns:
                fig_pie = px.pie(df_raw, names="_estado", hole=0.4, 
                                 color="_estado", color_discrete_map={
                                     "✅ Sin Fallas": "#27ae60",
                                     "⚠️ Fallas Menores": "#f39c12",
                                     "❌ Fallas Críticas": "#e74c3c"
                                 })
                st.plotly_chart(fig_pie, use_container_width=True)
        with g2:
            if "placa" in df_raw.columns:
                conteo_placa = df_raw["placa"].value_counts().head(10).reset_index()
                st.markdown("#### 🚛 Vehículos con más inspecciones")
                st.dataframe(conteo_placa, use_container_width=True, hide_index=True)

    # ===================== TAB 3: DETALLE =====================
    with tab3:
        st.markdown("### 🔎 Buscador de Inspección")
        opciones = df_raw.apply(lambda r: f"{r.get('fecha','')} | {r.get('placa','')} | {r.get('conductor','')}", axis=1).tolist()
        seleccion = st.selectbox("Seleccione una inspección:", opciones)
        
        if seleccion:
            idx = opciones.index(seleccion)
            row = df_raw.iloc[idx]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Conductor", row.get("conductor"))
            c2.metric("Placa", row.get("placa"))
            c3.metric("Estado", row.get("_estado"))
            
            st.write("---")
            for grupo, items in GRUPOS_INSPECCION.items():
                st.subheader(grupo)
                cols = st.columns(len(items))
                for i, item in enumerate(items):
                    val = row.get(item, "N/A")
                    color = "badge-falla" if es_falla(val) else "badge-ok"
                    cols[i].markdown(f"**{item.replace('_',' ').title()}**")
                    cols[i].markdown(f'<span class="{color}">{val}</span>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
