import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import pytz

# ==================== CONFIG ====================
st.set_page_config(
    page_title="Inspecciones Vehiculares",
    layout="wide",
    page_icon="🔍",
    initial_sidebar_state="collapsed"
)

BOGOTA_TZ = pytz.timezone("America/Bogota")

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
.kpi-card.verde  { border-left-color: #27ae60; }
.kpi-card.rojo   { border-left-color: #e74c3c; }
.kpi-card.ambar  { border-left-color: #f39c12; }
.kpi-card.azul   { border-left-color: #2980b9; }
.kpi-val { font-size: 2rem; font-weight: 700; color: #0f2027; }
.kpi-lbl { font-size: 0.78rem; color: #666; text-transform: uppercase; letter-spacing: 1px; }

.badge-ok    { background:#d5f5e3; color:#1e8449; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-falla { background:#fadbd8; color:#922b21; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }
.badge-na    { background:#eaecee; color:#566573; padding:2px 10px; border-radius:12px; font-size:0.82rem; font-weight:600; }

.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.15rem; font-weight: 700; color: #203a43;
    border-bottom: 2px solid #2c5364; padding-bottom: 4px; margin: 1.2rem 0 0.6rem 0;
}
.config-box {
    background: #eaf4fb; border: 1px solid #aed6f1; border-radius: 8px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
}
.config-box code { background: #d6eaf8; padding: 2px 6px; border-radius: 4px; font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)

# ==================== MAPEO DE COLUMNAS ====================
# Mapea nombre corto → nombre exacto en Google Sheets
COLS = {
    "marca_temporal":       "Marca temporal",
    "fecha":                "FECHA: ",
    "dia_semana":           "DIA DE LA SEMANA",
    "placa":                "PLACA DEL VEHICULO:",
    "conductor":            "NOMBRE Y APELLIDOS DEL CONDUCTOR:",
    "documento":            "DOCUMENTO IDENTIDAD:",
    "kilometraje":          "KILOMETRAJE:",
    "salud_conductor":      "1. ESTADO DE LA SALUD DEL CONDUCTOR (¿Está en condiciones de salud y descanso para usar el vehículo (sin malestar, mareos, fiebre, sueño u otros síntomas)?)",
    "luces":                "2. ESTADO DE LAS LUCES (Luces Medias, altas, bajas, direccionales, de parqueo, de frenos, reversa, interiores, y de tablero).",
    "liquidos":             "3. NIVELES Y PÉRDIDAS DE LÍQUIDOS (Nivel de Aceite de motor, hidráulico, de transmisión, de agua del radiador y del limpiabrisas, A.C.P.M.)  ",
    "frenos":               "4. ESTADO DE FRENOS, FUGAS Y FILTROS (Estado de frenos, frenos de emergencia y frenos del tráiler).",
    "baterias":             "5. FUNCIONAMIENTO DE LAS BATERIAS (Estado de las baterías).",
    "tablero":              "6. TABLERO DE CONTROL - Estado del (Medidor del nivel de combustible, odómetro, pito, tacómetro, velocímetro, indicador de aceite y temperatura).",
    "cabina_seguridad":     "7.1 Cinturones de Seguridad, estado y anclaje de la silla/cojinería, chasis, carrocería, pito y puertas. ",
    "cabina_interior":      "7.2. ESTADO DE LA CABINA (interior pisos y techos, sección de pasajeros)",
    "parachoques":          "7.3 ESTADO DEL PARACHOQUES O DEFENSA",
    "tanque":               "7.4 ESTADO DEL TANQUE DEL COMBUSTIBLE Y DEL AGUA",
    "espejos":              "8. ESPEJOS RETROVISORES (Limpieza y posición de los espejos laterales). ",
    "direccion":            "9.1 Estado de la Dirección (rótulas, terminales, ballestas).",
    "suspension":           "9.2. Estado de la Suspensión (hojas de muelles, amortiguadores, resortes, bombonas,  delantera - trasera)",
    "vidrios":              "10. ESTADO DE LOS VIDRIOS (Panorámico y trasero)",
    "limpiaparabrisas":     "11. LIMPIAPARABRISAS - Estado del limpiaparabrisas (derecho e izquierdo)",
    "llantas_cabezote":     "12.1 Llantas del cabezote",
    "llantas_trailer":      "12.2 Llantas del Tráiler",
    "llanta_repuesto":      "12.3 Llanta de Repuesto",
    "electrico":            "13.1 Instalaciones eléctricas (cabezote y/o Tráiler, encendido del vehículo)",
    "embrague":             "13.2 Estado de Embrague / Clutch",
    "transmision":          "13.3 Estado de la transmisión de velocidades",
    "acelerador":           "13.4 Estado del acelerador",
    "exosto":               "13.5 Exosto",
    "pitos_reversa":        "13.6 Pitos de Reversa (cabezote y tráiler)",
    "placas":               "13.7 Placas (tráiler y cabezote)",
    "pisos_falsos":         "13.8 Existen pisos y/o techos falsos ",
    "pata_mecanica":        "13.9 Pata mecánica del tráiler",
    "quinta_rueda":         "13.10 Estado del área de la quinta rueda",
    "kingpin":              "13.11 Kingpin ",
    "documentos":           "13.12 Documentos (soat, tecnomecánica y Tarjeta de Propiedad) ",
    "equipo_carretera":     "14.1. Verifique el contenido y estado del equipo de carretera (gato  con capacidad para elevar el vehículo, llave de tacón, tacos, conos, extintor, linterna, chaleco reflectivo, botiquín)",
    "caja_herramientas":    "14.2 Caja de herramientas (alicates, destornilladores de pala y estrella, llave de expansión y fijas)",
    "equipos_carga":        "15.1 Equipos para asegurar la carga (Cadenas, monas, Malacates, Cinchas, Pines, Madera, Trompos / Twist lock).",
    "carpa":                "15.2 Estado de la carpa (si aplica)",
    "generador":            "15.3 Estado del generador para carga refrigerada (Si aplica)",
    "observaciones":        "OBSERVACIONES GENERALES:",
    "firma_supervisor":     "FIRMA DEL SUPERVISOR",
    "placa_tercero":        "SI USTED ES UN TERCERO, ESCRIBA SU PLACA A CONTINUACIÓN",
    "contaminacion":        "13.13. ¿Durante la inspección ha identificado sustancias o productos no autorizados, o alguna situación inusual o condición que pueda resultar sospechosa de contaminación?",
    "foto_evidencia":       "Foto de evidencia",
    "hallazgos":            "HALLAZGOS (Si evidencia daños importantes adjuntar foto) Maximo 5 fotos",
    "en_taller":            "Antes de contestar las siguientes preguntas confirme si el vehículo se encuentra en el taller:",
}

# Columnas que son ítems de inspección (para análisis de fallas)
ITEMS_INSPECCION = {
    "Salud Conductor":    "salud_conductor",
    "Luces":              "luces",
    "Líquidos":           "liquidos",
    "Frenos":             "frenos",
    "Baterías":           "baterias",
    "Tablero Control":    "tablero",
    "Cabina Seguridad":   "cabina_seguridad",
    "Cabina Interior":    "cabina_interior",
    "Parachoques":        "parachoques",
    "Tanque":             "tanque",
    "Espejos":            "espejos",
    "Dirección":          "direccion",
    "Suspensión":         "suspension",
    "Vidrios":            "vidrios",
    "Limpiaparabrisas":   "limpiaparabrisas",
    "Llantas Cabezote":   "llantas_cabezote",
    "Llantas Tráiler":    "llantas_trailer",
    "Llanta Repuesto":    "llanta_repuesto",
    "Eléctrico":          "electrico",
    "Embrague":           "embrague",
    "Transmisión":        "transmision",
    "Acelerador":         "acelerador",
    "Exosto":             "exosto",
    "Pitos Reversa":      "pitos_reversa",
    "Placas":             "placas",
    "Pata Mecánica":      "pata_mecanica",
    "Quinta Rueda":       "quinta_rueda",
    "Kingpin":            "kingpin",
    "Documentos":         "documentos",
    "Equipo Carretera":   "equipo_carretera",
    "Caja Herramientas":  "caja_herramientas",
    "Equipos Carga":      "equipos_carga",
}

GRUPOS_INSPECCION = {
    "🧑 Conductor":         ["salud_conductor"],
    "💡 Luces y Tablero":   ["luces", "tablero"],
    "🔧 Mecánica":          ["liquidos", "frenos", "baterias", "embrague", "transmision", "acelerador", "exosto", "electrico"],
    "🚗 Cabina y Carrocería": ["cabina_seguridad", "cabina_interior", "parachoques", "tanque", "espejos", "vidrios", "limpiaparabrisas"],
    "⚙️ Chasis y Tren":     ["direccion", "suspension", "llantas_cabezote", "llantas_trailer", "llanta_repuesto", "pata_mecanica", "quinta_rueda", "kingpin"],
    "📋 Documentos y Equipo": ["placas", "documentos", "equipo_carretera", "caja_herramientas", "equipos_carga"],
}

# ==================== CARGA DE DATOS ====================
def es_falla(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return False
    v = str(valor).strip().upper()
    keywords_falla = ["MAL", "FALLA", "DEFICIENTE", "DAÑA", "ROTO", "NO FUNCIONA",
                      "REGULAR", "DETERIORA", "REQUIERE", "URGENTE", "NO TIENE",
                      "INCOMPLETO", "VENCIDO", "NO", "MALO"]
    keywords_ok = ["BIEN", "OK", "BUENO", "EXCELENTE", "NORMAL", "COMPLETO",
                   "VIGENTE", "FUNCIONA", "SÍ", "SI", "CORRECTO", "BUEN"]
    for k in keywords_falla:
        if k in v:
            return True
    for k in keywords_ok:
        if k in v:
            return False
    return False

@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos_sheets(sheet_id: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        # Renombrar columnas usando el mapeo
        rename_map = {}
        for short, full in COLS.items():
            # Búsqueda flexible (strip + lower)
            for col in df.columns:
                if col.strip().lower() == full.strip().lower():
                    rename_map[col] = short
                    break
                # fallback: buscar si el nombre corto aparece en el nombre largo
            if short not in rename_map.values():
                for col in df.columns:
                    if full.strip()[:30].lower() in col.strip().lower():
                        rename_map[col] = short
                        break
        df = df.rename(columns=rename_map)

        # Parsear fechas
        for col_fecha in ["marca_temporal", "fecha"]:
            if col_fecha in df.columns:
                df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce", dayfirst=True)

        # Columna auxiliar de estado general
        item_cols = [k for k in ITEMS_INSPECCION.values() if k in df.columns]
        if item_cols:
            df["_fallas_count"] = df[item_cols].apply(
                lambda row: sum(es_falla(v) for v in row), axis=1
            )
            df["_estado"] = df["_fallas_count"].apply(
                lambda n: "✅ Sin Fallas" if n == 0 else ("⚠️ Fallas Menores" if n <= 3 else "❌ Fallas Críticas")
            )
        return df
    except Exception as e:
        st.error(f"Error al cargar Google Sheets: {e}")
        return pd.DataFrame()


def get_col(df, col_short):
    """Obtiene columna si existe, si no retorna Serie vacía."""
    if col_short in df.columns:
        return df[col_short]
    return pd.Series([""] * len(df))


# ==================== EXCEL ====================
def generar_excel_inspeccion(df: pd.DataFrame) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Inspecciones"

    ft_tit  = Font(name="Calibri", bold=True, size=13, color="FFFFFF")
    ft_hdr  = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
    ft_norm = Font(name="Calibri", size=9)
    ft_falla = Font(name="Calibri", size=9, color="C0392B", bold=True)
    ft_ok   = Font(name="Calibri", size=9, color="1E8449")

    fill_tit  = PatternFill("solid", start_color="0F2027")
    fill_hdr  = PatternFill("solid", start_color="203A43")
    fill_alt  = PatternFill("solid", start_color="EBF5FB")
    fill_falla = PatternFill("solid", start_color="FADBD8")
    fill_ok   = PatternFill("solid", start_color="D5F5E3")
    fill_warn = PatternFill("solid", start_color="FDEBD0")

    borde  = Border(left=Side(style="thin"), right=Side(style="thin"),
                    top=Side(style="thin"),  bottom=Side(style="thin"))
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    izq    = Alignment(horizontal="left",   vertical="center", wrap_text=True)

    now_col = datetime.now(BOGOTA_TZ)

    # ---- Hoja 1: Detalle completo ----
    cols_export = [
        ("marca_temporal", "FECHA REGISTRO", 18),
        ("fecha",          "FECHA",          12),
        ("dia_semana",     "DÍA",             10),
        ("placa",          "PLACA",           12),
        ("conductor",      "CONDUCTOR",       28),
        ("documento",      "DOCUMENTO",       14),
        ("kilometraje",    "KM",              10),
        ("_estado",        "ESTADO",          18),
        ("_fallas_count",  "# FALLAS",        10),
        ("observaciones",  "OBSERVACIONES",   35),
        ("hallazgos",      "HALLAZGOS",       35),
        ("contaminacion",  "CONTAMINACIÓN",   22),
        ("en_taller",      "EN TALLER",       12),
        ("firma_supervisor","SUPERVISOR",      22),
    ]
    # Agregar ítems de inspección
    for label, short in ITEMS_INSPECCION.items():
        cols_export.append((short, label.upper(), 20))

    n_cols = len(cols_export)
    ws.merge_cells(f"A1:{get_column_letter(n_cols)}1")
    ws["A1"] = f"🔍 REPORTE DE INSPECCIONES VEHICULARES  |  {now_col.strftime('%d/%m/%Y %H:%M')} COL  |  {len(df)} registros"
    ws["A1"].font = ft_tit; ws["A1"].fill = fill_tit; ws["A1"].alignment = centro
    ws.row_dimensions[1].height = 28

    for ci, (_, nombre, ancho) in enumerate(cols_export, 1):
        c = ws.cell(2, ci, nombre)
        c.font = ft_hdr; c.fill = fill_hdr; c.alignment = centro; c.border = borde
        ws.column_dimensions[get_column_letter(ci)].width = ancho
    ws.row_dimensions[2].height = 28

    for ri, (_, row) in enumerate(df.iterrows(), 3):
        estado = str(row.get("_estado", ""))
        es_crit = "Críticas" in estado
        es_warn = "Menores" in estado

        for ci, (short, _, _) in enumerate(cols_export, 1):
            val = row.get(short, "")
            if pd.isna(val): val = ""
            if hasattr(val, "strftime"): val = val.strftime("%d/%m/%Y %H:%M")
            c = ws.cell(ri, ci, str(val) if val != "" else "")
            c.border = borde
            c.alignment = centro if ci in (1,2,3,4,8,9,13) else izq

            if short in ITEMS_INSPECCION.values() and es_falla(val):
                c.font = ft_falla; c.fill = fill_falla
            elif es_crit:
                c.font = ft_falla if ci == 8 else ft_norm
                if ci == 8: c.fill = fill_falla
                elif ri % 2 == 0: c.fill = fill_alt
            elif es_warn:
                c.font = ft_norm
                if ci == 8: c.fill = fill_warn
                elif ri % 2 == 0: c.fill = fill_alt
            else:
                c.font = ft_ok if ci == 8 else ft_norm
                if ci == 8: c.fill = fill_ok
                elif ri % 2 == 0: c.fill = fill_alt

        ws.row_dimensions[ri].height = 16

    ws.freeze_panes = "A3"

    # ---- Hoja 2: Resumen por placa ----
    ws2 = wb.create_sheet("Resumen Placas")
    ws2["A1"] = "Resumen por Placa"
    ws2["A1"].font = ft_tit; ws2["A1"].fill = fill_tit; ws2["A1"].alignment = centro
    ws2.row_dimensions[1].height = 26

    hdrs2 = ["PLACA", "TOTAL", "SIN FALLAS", "FALLAS MENORES", "FALLAS CRÍTICAS", "% APROBADO", "PROM. KM"]
    for ci, h in enumerate(hdrs2, 1):
        c = ws2.cell(2, ci, h); c.font = ft_hdr; c.fill = fill_hdr
        c.alignment = centro; c.border = borde
    ws2.row_dimensions[2].height = 22

    if "placa" in df.columns and "_estado" in df.columns:
        gr = df.groupby("placa")
        resumen_rows = []
        for placa_v, g in gr:
            tot = len(g)
            sin = (g["_estado"] == "✅ Sin Fallas").sum()
            men = g["_estado"].str.contains("Menores", na=False).sum()
            cri = g["_estado"].str.contains("Críticas", na=False).sum()
            pct = f"{round((sin+men)/tot*100,1)}%" if tot > 0 else "0%"
            km_vals = pd.to_numeric(g.get("kilometraje", pd.Series()), errors="coerce").dropna()
            prom_km = f"{int(km_vals.mean()):,}" if len(km_vals) > 0 else "—"
            resumen_rows.append((placa_v, tot, sin, men, cri, pct, prom_km))
        resumen_rows.sort(key=lambda x: x[1], reverse=True)
        for ri, vals in enumerate(resumen_rows, 3):
            fill_r = PatternFill("solid", start_color="EBF5FB") if ri % 2 == 0 else None
            for ci, v in enumerate(vals, 1):
                c = ws2.cell(ri, ci, v); c.font = ft_norm; c.border = borde
                c.alignment = izq if ci == 1 else centro
                if fill_r: c.fill = fill_r

    for col_l, w in zip(["A","B","C","D","E","F","G"], [14,8,12,14,14,12,12]):
        ws2.column_dimensions[col_l].width = w

    # ---- Hoja 3: Fallas por ítem ----
    ws3 = wb.create_sheet("Fallas por Ítem")
    ws3["A1"] = "Ranking de Fallas por Ítem de Inspección"
    ws3["A1"].font = ft_tit; ws3["A1"].fill = fill_tit; ws3["A1"].alignment = centro
    ws3.row_dimensions[1].height = 26

    hdrs3 = ["ÍTEM DE INSPECCIÓN", "TOTAL FALLAS", "% DEL TOTAL"]
    for ci, h in enumerate(hdrs3, 1):
        c = ws3.cell(2, ci, h); c.font = ft_hdr; c.fill = fill_hdr
        c.alignment = centro; c.border = borde
    ws3.row_dimensions[2].height = 22

    fallas_items = []
    for label, short in ITEMS_INSPECCION.items():
        if short in df.columns:
            cnt = df[short].apply(es_falla).sum()
            fallas_items.append((label, int(cnt)))
    fallas_items.sort(key=lambda x: x[1], reverse=True)
    total_fallas_all = sum(x[1] for x in fallas_items) or 1

    for ri, (label, cnt) in enumerate(fallas_items, 3):
        pct_str = f"{round(cnt/total_fallas_all*100,1)}%"
        fill_r = fill_falla if cnt > 0 else (fill_alt if ri % 2 == 0 else None)
        for ci, v in enumerate([label, cnt, pct_str], 1):
            c = ws3.cell(ri, ci, v); c.border = borde
            c.font = ft_falla if cnt > 0 else ft_norm
            c.alignment = izq if ci == 1 else centro
            if fill_r: c.fill = fill_r

    for col_l, w in zip(["A","B","C"], [40, 14, 12]):
        ws3.column_dimensions[col_l].width = w

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

    # ==================== CONFIGURACIÓN SHEETS ====================
    with st.sidebar:
        st.markdown("### ⚙️ Configuración")
        st.markdown("**Google Sheets**")
        sheet_id   = st.text_input("ID de la hoja",   placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
                                   help="El ID está en la URL: docs.google.com/spreadsheets/d/**ID**/edit")
        sheet_name = st.text_input("Nombre de la pestaña", value="respuestas de formulario 1",
                                   help="Nombre exacto de la hoja dentro del archivo")
        if st.button("🔄 Recargar datos", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption("💡 La hoja debe estar compartida como **'Cualquier persona con el enlace puede ver'**")

    # ==================== DEMO MODE ====================
    if not sheet_id:
        st.markdown("""
        <div class="config-box">
            <b>🔧 Cómo conectar tu Google Sheets:</b><br><br>
            1. Abre tu Google Sheets con las inspecciones<br>
            2. Click en <b>Compartir</b> → <b>Cualquier persona con el enlace</b> → <b>Lector</b><br>
            3. Copia el ID de la URL: <code>docs.google.com/spreadsheets/d/<b>ESTE-ES-EL-ID</b>/edit</code><br>
            4. Pégalo en el campo <b>ID de la hoja</b> en el panel izquierdo (⚙️)<br>
            5. Escribe el nombre exacto de tu pestaña (ej: <code>respuestas de formulario 1</code>)
        </div>
        """, unsafe_allow_html=True)

        st.info("👈 Configura tu Google Sheets en el panel izquierdo para comenzar.")
        st.stop()

    # ==================== CARGAR DATOS ====================
    with st.spinner("📡 Conectando con Google Sheets..."):
        df_raw = cargar_datos_sheets(sheet_id, sheet_name)

    if df_raw.empty:
        st.error("No se pudieron cargar datos. Verifica el ID de la hoja y que esté compartida públicamente.")
        st.stop()

    # ==================== TABS ====================
    tab1, tab2, tab3 = st.tabs(["📋 Historial", "📊 Dashboard", "🔎 Detalle"])

    # ===================== TAB 1: HISTORIAL =====================
    with tab1:
        st.markdown("### 📋 Historial de Inspecciones")

        with st.expander("🛠️ Filtros", expanded=True):
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            with fc1:
                fecha_col = df_raw.get("fecha", df_raw.get("marca_temporal", pd.Series()))
                fechas_validas = fecha_col.dropna()
                if len(fechas_validas) > 0:
                    f_min = fechas_validas.min().date()
                    f_max = fechas_validas.max().date()
                else:
                    f_min = datetime.now().date() - timedelta(days=30)
                    f_max = datetime.now().date()
                fi = st.date_input("Desde", f_min, key="h_fi")
            with fc2:
                ff = st.date_input("Hasta", f_max, key="h_ff")
            with fc3:
                placas_disp = ["Todas"] + sorted(df_raw["placa"].dropna().unique().tolist()) if "placa" in df_raw.columns else ["Todas"]
                fp = st.selectbox("Placa", placas_disp)
            with fc4:
                conductores_disp = ["Todos"] + sorted(df_raw["conductor"].dropna().unique().tolist()) if "conductor" in df_raw.columns else ["Todos"]
                fc_sel = st.selectbox("Conductor", conductores_disp)
            with fc5:
                if "_estado" in df_raw.columns:
                    estados_disp = ["Todos", "✅ Sin Fallas", "⚠️ Fallas Menores", "❌ Fallas Críticas"]
                else:
                    estados_disp = ["Todos"]
                fe = st.selectbox("Estado", estados_disp)

        # Aplicar filtros
        df = df_raw.copy()
        fecha_ref = df.get("fecha", df.get("marca_temporal"))
        if fecha_ref is not None and fecha_ref.notna().any():
            df = df[fecha_ref.dt.date.between(fi, ff)]
        if fp != "Todas" and "placa" in df.columns:
            df = df[df["placa"] == fp]
        if fc_sel != "Todos" and "conductor" in df.columns:
            df = df[df["conductor"] == fc_sel]
        if fe != "Todos" and "_estado" in df.columns:
            df = df[df["_estado"] == fe]

        # KPIs
        total = len(df)
        sin_f  = (df["_estado"] == "✅ Sin Fallas").sum()    if "_estado" in df.columns else 0
        men_f  = df["_estado"].str.contains("Menores",  na=False).sum() if "_estado" in df.columns else 0
        crit_f = df["_estado"].str.contains("Críticas", na=False).sum() if "_estado" in df.columns else 0
        pct_ok = round(sin_f / total * 100) if total > 0 else 0

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("🔍 Total Inspecciones", total)
        k2.metric("✅ Sin Fallas",        sin_f,  f"{pct_ok}%")
        k3.metric("⚠️ Fallas Menores",    men_f)
        k4.metric("❌ Fallas Críticas",   crit_f)
        k5.metric("🚗 Vehículos únicos",  df["placa"].nunique() if "placa" in df.columns else 0)

        st.divider()

        # Botón descarga
        col_rep, col_btn = st.columns([2, 3])
        with col_rep:
            nombre_rep = st.text_input("Nombre del reporte", value="Inspecciones_Vehiculares")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if total > 0:
                excel_data = generar_excel_inspeccion(df)
                st.download_button(
                    "⬇️ Descargar Excel completo",
                    data=excel_data,
                    file_name=f"{nombre_rep}_{datetime.now(BOGOTA_TZ).strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

        st.divider()

        # Tabla
        cols_tabla = [c for c in ["marca_temporal","fecha","placa","conductor","kilometraje","_estado","_fallas_count","observaciones","hallazgos"] if c in df.columns]
        rename_tabla = {
            "marca_temporal": "Registro", "fecha": "Fecha", "placa": "Placa",
            "conductor": "Conductor", "kilometraje": "KM",
            "_estado": "Estado", "_fallas_count": "# Fallas",
            "observaciones": "Observaciones", "hallazgos": "Hallazgos"
        }
        if not df.empty:
            df_show = df[cols_tabla].rename(columns=rename_tabla).copy()
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay registros con los filtros seleccionados.")

    # ===================== TAB 2: DASHBOARD =====================
    with tab2:
        st.markdown("### 📊 Dashboard de Inspecciones")

        try:
            import plotly.express as px
            import plotly.graph_objects as go

            df_dash = df_raw.copy()

            g1, g2 = st.columns(2)

            with g1:
                st.markdown("#### Distribución por Estado")
                if "_estado" in df_dash.columns:
                    est_c = df_dash["_estado"].value_counts().reset_index()
                    est_c.columns = ["estado", "cantidad"]
                    colores = {
                        "✅ Sin Fallas": "#27ae60",
                        "⚠️ Fallas Menores": "#f39c12",
                        "❌ Fallas Críticas": "#e74c3c"
                    }
                    fig1 = px.pie(est_c, values="cantidad", names="estado", hole=0.45,
                                  color="estado", color_discrete_map=colores)
                    fig1.update_layout(margin=dict(t=20, b=10), height=300)
                    st.plotly_chart(fig1, use_container_width=True)

            with g2:
                st.markdown("#### Inspecciones por Día")
                fecha_col_name = "fecha" if "fecha" in df_dash.columns else "marca_temporal"
                if fecha_col_name in df_dash.columns:
                    df_dia = df_dash.groupby(df_dash[fecha_col_name].dt.date).size().reset_index(name="inspecciones")
                    df_dia.columns = ["fecha", "inspecciones"]
                    fig2 = px.bar(df_dia, x="fecha", y="inspecciones",
                                  color_discrete_sequence=["#2c5364"], text="inspecciones")
                    fig2.update_traces(textposition="outside")
                    fig2.update_layout(margin=dict(t=20, b=10), height=300,
                                       xaxis_title="", yaxis_title="Inspecciones")
                    st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            g3, g4 = st.columns(2)

            with g3:
                st.markdown("#### 🔴 Top Fallas por Ítem")
                fallas_data = []
                for label, short in ITEMS_INSPECCION.items():
                    if short in df_dash.columns:
                        cnt = df_dash[short].apply(es_falla).sum()
                        if cnt > 0:
                            fallas_data.append({"Ítem": label, "Fallas": int(cnt)})
                if fallas_data:
                    df_fallas = pd.DataFrame(fallas_data).sort_values("Fallas", ascending=True).tail(15)
                    fig3 = px.bar(df_fallas, x="Fallas", y="Ítem", orientation="h",
                                  color="Fallas", color_continuous_scale="Reds", text="Fallas")
                    fig3.update_traces(textposition="outside")
                    fig3.update_layout(margin=dict(t=20, b=10), height=max(300, len(df_fallas)*30),
                                       coloraxis_showscale=False, yaxis_title="", xaxis_title="N° Fallas")
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.success("✅ Sin fallas registradas en el período.")

            with g4:
                st.markdown("#### Inspecciones por Placa")
                if "placa" in df_dash.columns:
                    df_placa = df_dash.groupby("placa").agg(
                        total=("placa","count"),
                        fallas=("_fallas_count","sum") if "_fallas_count" in df_dash.columns else ("placa","count")
                    ).reset_index().sort_values("total", ascending=True)
                    fig4 = px.bar(df_placa, x="total", y="placa", orientation="h",
                                  color="total", color_continuous_scale="Blues", text="total")
                    fig4.update_traces(textposition="outside")
                    fig4.update_layout(margin=dict(t=20, b=10), height=max(280, len(df_placa)*35),
                                       coloraxis_showscale=False, yaxis_title="", xaxis_title="Inspecciones")
                    st.plotly_chart(fig4, use_container_width=True)

            st.divider()
            g5, g6 = st.columns(2)

            with g5:
                st.markdown("#### 📅 Inspecciones por Día de Semana")
                fecha_col_name2 = "fecha" if "fecha" in df_dash.columns else "marca_temporal"
                if fecha_col_name2 in df_dash.columns:
                    orden = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
                    nombres_es = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                                  "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
                    df_dash["_dia"] = df_dash[fecha_col_name2].dt.day_name()
                    df_sem = df_dash.groupby("_dia").size().reset_index(name="inspecciones")
                    df_sem["orden"] = df_sem["_dia"].map({d: i for i, d in enumerate(orden)})
                    df_sem = df_sem.sort_values("orden")
                    df_sem["dia_es"] = df_sem["_dia"].map(nombres_es)
                    fig5 = px.bar(df_sem, x="dia_es", y="inspecciones",
                                  color="inspecciones", color_continuous_scale="Teal", text="inspecciones")
                    fig5.update_traces(textposition="outside")
                    fig5.update_layout(margin=dict(t=20, b=10), height=300,
                                       coloraxis_showscale=False, xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig5, use_container_width=True)

            with g6:
                st.markdown("#### 🏆 Ranking Conductores")
                if "conductor" in df_dash.columns and "_estado" in df_dash.columns:
                    df_cond = df_dash[df_dash["conductor"].notna()].groupby("conductor").agg(
                        total=("conductor","count"),
                        sin_fallas=("_estado", lambda x: (x=="✅ Sin Fallas").sum()),
                        fallas_crit=("_estado", lambda x: x.str.contains("Críticas",na=False).sum()),
                    ).reset_index()
                    df_cond["% OK"] = (df_cond["sin_fallas"] / df_cond["total"] * 100).round(1)
                    df_cond = df_cond.sort_values("total", ascending=False)
                    df_cond.columns = ["Conductor","Total","Sin Fallas","Críticas","% OK"]
                    st.dataframe(df_cond, use_container_width=True, hide_index=True)

        except ImportError:
            st.warning("Instala plotly: `pip install plotly`")
        except Exception as e:
            st.error(f"Error en dashboard: {e}")
            import traceback; st.code(traceback.format_exc())

    # ===================== TAB 3: DETALLE =====================
    with tab3:
        st.markdown("### 🔎 Detalle de Inspección")

        if df_raw.empty:
            st.warning("No hay datos cargados.")
            st.stop()

        # Selector
        if "placa" in df_raw.columns and "marca_temporal" in df_raw.columns:
            df_raw["_label_sel"] = df_raw.apply(
                lambda r: f"{str(r.get('marca_temporal',''))[:16]} | {r.get('placa','')} | {r.get('conductor','')} | {r.get('_estado','')}",
                axis=1
            )
        elif "placa" in df_raw.columns:
            df_raw["_label_sel"] = df_raw.apply(
                lambda r: f"{r.get('placa','')} | {r.get('conductor','')} | {r.get('_estado','')}",
                axis=1
            )
        else:
            df_raw["_label_sel"] = df_raw.index.astype(str)

        sel = st.selectbox("Seleccionar inspección:", df_raw["_label_sel"].tolist())
        if sel:
            row = df_raw[df_raw["_label_sel"] == sel].iloc[0]

            # Info general
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🚛 Placa",      row.get("placa","—"))
            c2.metric("👤 Conductor",  str(row.get("conductor","—"))[:25])
            c3.metric("📏 Kilometraje", str(row.get("kilometraje","—")))
            c4.metric("🚦 Estado",     row.get("_estado","—"))

            fallas_count = int(row.get("_fallas_count", 0))
            if fallas_count > 0:
                st.error(f"⚠️ Se encontraron **{fallas_count} ítems con fallas** en esta inspección.")
            else:
                st.success("✅ Inspección aprobada — sin fallas detectadas.")

            # Ítems por grupo
            for grupo, items in GRUPOS_INSPECCION.items():
                st.markdown(f'<div class="section-title">{grupo}</div>', unsafe_allow_html=True)
                cols_g = st.columns(3)
                for i, short in enumerate(items):
                    label = [k for k,v in ITEMS_INSPECCION.items() if v == short]
                    label = label[0] if label else short
                    val = row.get(short, "")
                    if pd.isna(val) or str(val).strip() == "":
                        badge = f'<span class="badge-na">N/A</span>'
                    elif es_falla(val):
                        badge = f'<span class="badge-falla">⚠️ {str(val)[:40]}</span>'
                    else:
                        badge = f'<span class="badge-ok">✅ {str(val)[:40]}</span>'
                    with cols_g[i % 3]:
                        st.markdown(f"**{label}**<br>{badge}", unsafe_allow_html=True)
                        st.write("")

            # Obs y hallazgos
            st.markdown('<div class="section-title">📝 Observaciones y Hallazgos</div>', unsafe_allow_html=True)
            obs_val = str(row.get("observaciones","")).strip()
            hall_val = str(row.get("hallazgos","")).strip()
            cont_val = str(row.get("contaminacion","")).strip()

            if obs_val and obs_val != "nan":
                st.info(f"**Observaciones generales:** {obs_val}")
            if hall_val and hall_val != "nan":
                st.warning(f"**Hallazgos:** {hall_val}")
            if cont_val and cont_val.lower() not in ["nan","no","no."]:
                st.error(f"🚨 **Contaminación/Situación inusual:** {cont_val}")


if __name__ == "__main__":
    main()
