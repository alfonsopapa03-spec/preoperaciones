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
    initial_sidebar_state="collapsed"
)

BOGOTA_TZ = pytz.timezone("America/Bogota")

# ==================== HARDCODED SHEET CONFIG ====================
SHEET_ID = "1Y9L1NGfUpb79k672ZV8eq9M0MrZABzWdE_SfnFiBOi4"
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
.kpi-card {
    background: white; border-radius: 10px; padding: 1rem 1.2rem;
    border-left: 5px solid #2c5364; box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    margin-bottom: 0.5rem;
}
.kpi-card.verde { border-left-color: #27ae60; }
.kpi-card.rojo { border-left-color: #e74c3c; }
.kpi-card.ambar { border-left-color: #f39c12; }
.kpi-card.azul { border-left-color: #2980b9; }
.kpi-val { font-size: 2rem; font-weight: 700; color: #0f2027; }
.kpi-lbl { font-size: 0.78rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }
.badge-ok { background:#d5f5e3; color:#1e8449; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-falla { background:#fadbd8; color:#922b21; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-na { background:#eaecee; color:#566573; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.15rem; font-weight: 700; color: #203a43;
    border-bottom: 2px solid #2c5364; padding-bottom: 4px; margin: 1.2rem 0 0.6rem 0;
}
.conductor-card {
    background: white; border-radius: 10px; padding: 0.9rem 1.1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 0.5rem;
    border-left: 5px solid #27ae60;
}
.conductor-card.no-insp { border-left-color: #e74c3c; background: #fff9f9; }
.conductor-card.parcial { border-left-color: #f39c12; }
</style>
""", unsafe_allow_html=True)

# ==================== MAPEO DE COLUMNAS ====================
COLS = {
    "marca_temporal": "Marca temporal",
    "fecha": "FECHA: ",
    "dia_semana": "DIA DE LA SEMANA",
    "placa": "PLACA DEL VEHICULO:",
    "conductor": "NOMBRE Y APELLIDOS DEL CONDUCTOR:",
    "documento": "DOCUMENTO IDENTIDAD:",
    "kilometraje": "KILOMETRAJE:",
    "salud_conductor": "1. ESTADO DE LA SALUD DEL CONDUCTOR...",
    "luces": "2. ESTADO DE LAS LUCES...",
    "liquidos": "3. NIVELES Y PÉRDIDAS DE LÍQUIDOS...",
    "frenos": "4. ESTADO DE FRENOS...",
    "baterias": "5. FUNCIONAMIENTO DE LAS BATERIAS...",
    "tablero": "6. TABLERO DE CONTROL...",
    "cabina_seguridad": "7.1 Cinturones de Seguridad...",
    "cabina_interior": "7.2. ESTADO DE LA CABINA...",
    "parachoques": "7.3 ESTADO DEL PARACHOQUES...",
    "tanque": "7.4 ESTADO DEL TANQUE...",
    "espejos": "8. ESPEJOS RETROVISORES...",
    "direccion": "9.1 Estado de la Dirección...",
    "suspension": "9.2. Estado de la Suspensión...",
    "vidrios": "10. ESTADO DE LOS VIDRIOS...",
    "limpiaparabrisas": "11. LIMPIAPARABRISAS...",
    "llantas_cabezote": "12.1 Llantas del cabezote",
    "llantas_trailer": "12.2 Llantas del Tráiler",
    "llanta_repuesto": "12.3 Llanta de Repuesto",
    "electrico": "13.1 Instalaciones eléctricas...",
    "embrague": "13.2 Estado de Embrague...",
    "transmision": "13.3 Estado de la transmisión...",
    "acelerador": "13.4 Estado del acelerador",
    "exosto": "13.5 Exosto",
    "pitos_reversa": "13.6 Pitos de Reversa...",
    "placas": "13.7 Placas...",
    "pisos_falsos": "13.8 Existen pisos y/o techos falsos",
    "pata_mecanica": "13.9 Pata mecánica del tráiler",
    "quinta_rueda": "13.10 Estado del área de la quinta rueda",
    "kingpin": "13.11 Kingpin",
    "documentos": "13.12 Documentos...",
    "equipo_carretera": "14.1. Verifique el contenido...",
    "caja_herramientas": "14.2 Caja de herramientas...",
    "equipos_carga": "15.1 Equipos para asegurar la carga...",
    "carpa": "15.2 Estado de la carpa...",
    "generador": "15.3 Estado del generador...",
    "observaciones": "OBSERVACIONES GENERALES:",
    "firma_supervisor": "FIRMA DEL SUPERVISOR",
    "placa_tercero": "SI USTED ES UN TERCERO...",
    "contaminacion": "13.13. ¿Durante la inspección ha identificado...",
    "foto_evidencia": "Foto de evidencia",
    "hallazgos": "HALLAZGOS...",
    "en_taller": "Antes de contestar las siguientes preguntas confirme si el vehículo se encuentra en el taller:",
}

ITEMS_INSPECCION = {
    "Salud Conductor": "salud_conductor", "Luces": "luces", "Líquidos": "liquidos",
    "Frenos": "frenos", "Baterías": "baterias", "Tablero Control": "tablero",
    "Cabina Seguridad": "cabina_seguridad", "Cabina Interior": "cabina_interior",
    "Parachoques": "parachoques", "Tanque": "tanque", "Espejos": "espejos",
    "Dirección": "direccion", "Suspensión": "suspension", "Vidrios": "vidrios",
    "Limpiaparabrisas": "limpiaparabrisas", "Llantas Cabezote": "llantas_cabezote",
    "Llantas Tráiler": "llantas_trailer", "Llanta Repuesto": "llanta_repuesto",
    "Eléctrico": "electrico", "Embrague": "embrague", "Transmisión": "transmision",
    "Acelerador": "acelerador", "Exosto": "exosto", "Pitos Reversa": "pitos_reversa",
    "Placas": "placas", "Pata Mecánica": "pata_mecanica", "Quinta Rueda": "quinta_rueda",
    "Kingpin": "kingpin", "Documentos": "documentos", "Equipo Carretera": "equipo_carretera",
    "Caja Herramientas": "caja_herramientas", "Equipos Carga": "equipos_carga",
}

GRUPOS_INSPECCION = {
    "🧑 Conductor": ["salud_conductor"],
    "💡 Luces y Tablero": ["luces", "tablero"],
    "🔧 Mecánica": ["liquidos", "frenos", "baterias", "embrague", "transmision", "acelerador", "exosto", "electrico"],
    "🚗 Cabina y Carrocería": ["cabina_seguridad", "cabina_interior", "parachoques", "tanque", "espejos", "vidrios", "limpiaparabrisas"],
    "⚙️ Chasis y Tren": ["direccion", "suspension", "llantas_cabezote", "llantas_trailer", "llanta_repuesto", "pata_mecanica", "quinta_rueda", "kingpin"],
    "📋 Documentos y Equipo": ["placas", "documentos", "equipo_carretera", "caja_herramientas", "equipos_carga"],
}

DIAS_ES = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
           "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}

MESES_ES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",
            9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

# ==================== HELPERS ====================
def es_falla(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return False
    v = str(valor).strip().upper()
    keywords_falla = ["MAL", "FALLA", "DEFICIENTE", "DAÑA", "ROTO", "NO FUNCIONA", "REGULAR", "DETERIORA", "REQUIERE", "URGENTE", "NO TIENE", "INCOMPLETO", "VENCIDO", "NO", "MALO"]
    keywords_ok = ["BIEN", "OK", "BUENO", "EXCELENTE", "NORMAL", "COMPLETO", "VIGENTE", "FUNCIONA", "SÍ", "SI", "CORRECTO", "BUEN"]
    for k in keywords_falla:
        if k in v: return True
    for k in keywords_ok:
        if k in v: return False
    return False

def normalizar_nombre(nombre):
    if pd.isna(nombre) or str(nombre).strip() == "": return ""
    n = str(nombre).strip()
    n = re.sub(r'\s+', ' ', n)
    return n.title()

def nombre_clave(nombre):
    if not nombre: return ""
    n = nombre.lower()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        n = n.replace(a, b)
    n = re.sub(r'[^a-z\s]', '', n)
    partes = n.split()
    return ' '.join(partes[:2]) if len(partes) >= 2 else ' '.join(partes)

def parsear_fecha(serie):
    serie = serie.astype(str).str.strip().replace(['nan', '', 'NaT'], pd.NaT)
    return pd.to_datetime(serie, errors='coerce', dayfirst=True, format='mixed')

# ==================== CARGA DE DATOS ====================
@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos_sheets(sheet_id: str, sheet_name: str) -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        
        # Renombrar columnas
        rename_map = {}
        for short, full in COLS.items():
            for col in df.columns:
                if col.strip().lower() == full.strip().lower() or full.strip()[:30].lower() in col.strip().lower():
                    rename_map[col] = short
                    break
        df = df.rename(columns=rename_map)

        # Parseo de fechas
        for col_fecha in ["marca_temporal", "fecha"]:
            if col_fecha in df.columns:
                df[col_fecha] = parsear_fecha(df[col_fecha])

        # Normalizar
        if "conductor" in df.columns:
            df["conductor_raw"] = df["conductor"].copy()
            df["conductor"] = df["conductor"].apply(normalizar_nombre)
            df["conductor_clave"] = df["conductor"].apply(nombre_clave)
        
        if "placa" in df.columns:
            df["placa"] = df["placa"].astype(str).str.strip().str.upper()

        # Conteo de fallas
        item_cols = [k for k in ITEMS_INSPECCION.values() if k in df.columns]
        if item_cols:
            df["_fallas_count"] = df[item_cols].apply(lambda row: sum(es_falla(v) for v in row), axis=1)
            df["_estado"] = df["_fallas_count"].apply(
                lambda n: "✅ Sin Fallas" if n == 0 else ("⚠️ Fallas Menores" if n <= 3 else "❌ Fallas Críticas")
            )
        return df
    except Exception as e:
        st.error(f"Error al cargar Google Sheets: {e}")
        return pd.DataFrame()

# ==================== EXCEL ORIGINAL (mantengo tu función) ====================
def generar_excel_inspeccion(df: pd.DataFrame) -> bytes:
    # ... (tu función original completa - la mantengo igual para no alargar demasiado)
    # Si quieres la versión completa de esta función dime y te la pego también
    # Por ahora uso un placeholder para que el código corra
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Inspecciones", index=False)
    return output.getvalue()

# ==================== NUEVO: REPORTE DE CUMPLIMIENTO ====================
def generar_reporte_cumplimiento(df: pd.DataFrame) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "RESUMEN"

    # Estilos
    ft_titulo = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ft_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    ft_normal = Font(name="Calibri", size=11)
    fill_header = PatternFill("solid", start_color="203A43")
    fill_bueno = PatternFill("solid", start_color="D5F5E3")
    fill_regular = PatternFill("solid", start_color="FDEBD0")
    fill_critico = PatternFill("solid", start_color="FADBD8")
    borde = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    center = Alignment(horizontal="center", vertical="center")

    now = datetime.now(BOGOTA_TZ)
    ws1.merge_cells("A1:G1")
    ws1["A1"] = f"REPORTE DE INSPECCIONES - {now.strftime('%B %Y').upper()}"
    ws1["A1"].font = ft_titulo
    ws1["A1"].fill = PatternFill("solid", start_color="0F2027")
    ws1["A1"].alignment = center

    total_placas = df["placa"].nunique() if "placa" in df.columns else 0
    fechas_unicas = df["fecha"].dt.date.nunique() if "fecha" in df.columns and df["fecha"].notna().any() else 0
    total_registros = len(df)

    ws1["A2"] = f"{total_placas} placas | {fechas_unicas} fechas registradas | {total_registros} registros totales"
    ws1["A2"].font = Font(size=12, bold=True)

    headers = ["PLACA", "DÍAS EVALUADOS", "SI HIZO ✓", "NO HIZO ✗", "EN TALLER 🔧", "% CUMPLIMIENTO", "ESTADO"]
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(4, col, header)
        cell.font = ft_header
        cell.fill = fill_header
        cell.alignment = center
        cell.border = borde
        ws1.column_dimensions[get_column_letter(col)].width = [12, 14, 12, 12, 14, 16, 18][col-1]

    if "fecha" not in df.columns or "placa" not in df.columns or df.empty:
        ws1["A6"] = "No hay datos suficientes para generar el reporte"
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    df["fecha_date"] = df["fecha"].dt.date
    all_dates = sorted(df["fecha_date"].unique())
    dias_evaluados = len(all_dates)

    resumen = []
    for placa, group in df.groupby("placa"):
        en_taller = group.get("en_taller", pd.Series()).notna().sum() if "en_taller" in group.columns else 0
        hizo = len(group)
        no_hizo = max(0, dias_evaluados - hizo - en_taller)
        pct = round(hizo / dias_evaluados, 3) if dias_evaluados > 0 else 0

        if pct >= 0.70:
            estado = "✅ BUENO"
            fill_row = fill_bueno
        elif pct >= 0.40:
            estado = "⚠️ REGULAR"
            fill_row = fill_regular
        else:
            estado = "❌ CRÍTICO"
            fill_row = fill_critico

        resumen.append({
            "PLACA": placa,
            "DÍAS EVALUADOS": dias_evaluados,
            "SI HIZO ✓": hizo,
            "NO HIZO ✗": no_hizo,
            "EN TALLER 🔧": en_taller,
            "% CUMPLIMIENTO": pct,
            "ESTADO": estado,
            "fill": fill_row
        })

    resumen.sort(key=lambda x: x["% CUMPLIMIENTO"], reverse=True)

    for r_idx, row_data in enumerate(resumen, 5):
        for c_idx, key in enumerate(["PLACA","DÍAS EVALUADOS","SI HIZO ✓","NO HIZO ✗","EN TALLER 🔧","% CUMPLIMIENTO","ESTADO"], 1):
            val = row_data[key]
            cell = ws1.cell(r_idx, c_idx, val)
            cell.border = borde
            cell.alignment = center if c_idx != 1 else Alignment(horizontal="left")
            if key == "% CUMPLIMIENTO":
                cell.number_format = '0.0%'
            if key == "ESTADO":
                cell.font = Font(bold=True)
        for c in range(1, 8):
            ws1.cell(r_idx, c).fill = row_data["fill"]

    # ===================== HOJA 2: DETALLE POR FECHA =====================
    ws2 = wb.create_sheet("DETALLE POR FECHA")
    ws2["A1"] = "DETALLE DE INSPECCIONES POR FECHA"
    ws2["A1"].font = ft_titulo
    ws2["A1"].fill = PatternFill("solid", start_color="0F2027")
    ws2["A1"].alignment = center

    headers2 = ["FECHA", "SI HIZO ✓", "NO HIZO ✗", "EN TALLER 🔧", "TOTAL PLACAS", "% CUMPLIMIENTO"]
    for col, h in enumerate(headers2, 1):
        cell = ws2.cell(3, col, h)
        cell.font = ft_header
        cell.fill = fill_header
        cell.alignment = center
        cell.border = borde

    fecha_group = df.groupby("fecha_date")
    for i, (fecha, g) in enumerate(fecha_group, 4):
        total_placas_dia = df["placa"].nunique()  # total general de placas
        en_taller_dia = g.get("en_taller", pd.Series()).notna().sum() if "en_taller" in g.columns else 0
        hizo_dia = len(g)
        no_hizo_dia = total_placas_dia - hizo_dia - en_taller_dia

        pct = round(hizo_dia / total_placas_dia, 4) if total_placas_dia > 0 else 0

        ws2.cell(i, 1, fecha.strftime("%d/%m/%Y"))
        ws2.cell(i, 2, hizo_dia)
        ws2.cell(i, 3, max(0, no_hizo_dia))
        ws2.cell(i, 4, en_taller_dia)
        ws2.cell(i, 5, total_placas_dia)
        ws2.cell(i, 6, pct)

        for c in range(1, 7):
            ws2.cell(i, c).border = borde
            ws2.cell(i, c).alignment = center
        ws2.cell(i, 6).number_format = '0.00%'

    # ===================== HOJA 3: MAPA DE INSPECCIONES =====================
    ws3 = wb.create_sheet("MAPA DE INSPECCIONES")
    ws3["A1"] = "MAPA DE INSPECCIONES POR PLACA Y FECHA"
    ws3["A1"].font = ft_titulo
    ws3["A1"].fill = PatternFill("solid", start_color="0F2027")
    ws3["A1"].alignment = center

    ws3.cell(2, 1, "PLACA")
    for idx, fecha in enumerate(all_dates, 2):
        ws3.cell(2, idx, fecha.strftime("%d/%m"))
        ws3.cell(2, idx).font = ft_header
        ws3.cell(2, idx).fill = fill_header
        ws3.cell(2, idx).alignment = center
        ws3.cell(2, idx).border = borde

    placas_orden = sorted(df["placa"].unique())
    for r_idx, placa in enumerate(placas_orden, 3):
        ws3.cell(r_idx, 1, placa)
        ws3.cell(r_idx, 1).border = borde

        for c_idx, fecha in enumerate(all_dates, 2):
            inspecciones = df[(df["placa"] == placa) & (df["fecha_date"] == fecha)]
            en_taller = inspecciones.get("en_taller", pd.Series()).notna().any() if "en_taller" in df.columns else False

            simbolo = "🔧" if en_taller else ("✓" if len(inspecciones) > 0 else "✗")
            cell = ws3.cell(r_idx, c_idx, simbolo)
            cell.alignment = center
            cell.border = borde

            if simbolo == "✓":
                cell.font = Font(color="006400", bold=True)
            elif simbolo == "🔧":
                cell.font = Font(color="FF8C00", bold=True)
            else:
                cell.font = Font(color="B22222")

    # Leyenda
    last_row = len(placas_orden) + 5
    ws3.cell(last_row, 1, "LEYENDA:")
    ws3.cell(last_row, 2, "✓ SI HIZO")
    ws3.cell(last_row+1, 2, "✗ NO HIZO")
    ws3.cell(last_row+2, 2, "🔧 TALLER")

    ws3.column_dimensions["A"].width = 12
    for c in range(2, len(all_dates)+2):
        ws3.column_dimensions[get_column_letter(c)].width = 10

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

# ==================== MAIN ====================
def main():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 INSPECCIONES VEHICULARES</h1>
        <p>Reporte y análisis de inspecciones pre-operacionales · Google Sheets</p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### ⚙️ Opciones")
        if st.button("🔄 Recargar datos", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption("📊 Fuente: Google Sheets")
        st.caption("🕐 Caché: 5 minutos")

    with st.spinner("📡 Conectando con Google Sheets..."):
        df_raw = cargar_datos_sheets(SHEET_ID, SHEET_NAME)

    if df_raw.empty:
        st.error("No se pudieron cargar datos. Verifica que la hoja esté compartida públicamente.")
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Historial", "📊 Dashboard", "🔎 Detalle", "📅 Cumplimiento Mensual"])

    # TAB 1: Historial (mantengo tu código original aquí - solo muestro estructura)
    with tab1:
        st.markdown("### 📋 Historial de Inspecciones")
        st.info("Aquí va tu código original del Tab Historial (filtros, KPIs, tabla y descarga Excel)")
        # ... (pega aquí tu código original del tab1 si quieres que quede completo)

    # TAB 2: Dashboard
    with tab2:
        st.markdown("### 📊 Dashboard de Inspecciones")
        st.info("Aquí va tu código original del Dashboard con Plotly")

    # TAB 3: Detalle
    with tab3:
        st.markdown("### 🔎 Detalle de Inspección")
        st.info("Aquí va tu código original del Tab Detalle")

    # ===================== NUEVO TAB 4: CUMPLIMIENTO =====================
    with tab4:
        st.markdown("### 📅 Reporte de Cumplimiento Mensual")
        st.caption("Muestra claramente quién **sí hizo**, **no hizo** o está **en taller** la inspección diaria")

        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown("**Este reporte genera exactamente el formato que me mostraste:**")
            st.markdown("- Hoja **RESUMEN** por placa")
            st.markdown("- Hoja **DETALLE POR FECHA**")
            st.markdown("- Hoja **MAPA DE INSPECCIONES** (calendario)")

        with col2:
            if st.button("🚀 Generar Reporte de Cumplimiento", type="primary", use_container_width=True):
                with st.spinner("Generando Excel con resumen, detalle y mapa..."):
                    excel_bytes = generar_reporte_cumplimiento(df_raw)
                    fecha_str = datetime.now(BOGOTA_TZ).strftime("%Y%m%d_%H%M")
                    st.download_button(
                        label="⬇️ Descargar REPORTE_INSPECCIONES.xlsx",
                        data=excel_bytes,
                        file_name=f"REPORTE_INSPECCIONES_{fecha_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                st.success("✅ Reporte generado correctamente!")

if __name__ == "__main__":
    main()
