import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import io

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(
    page_title="INTEL - FORENSIC SYSTEM",
    layout="wide",
    page_icon="🛰️"
)

# =========================
# UI HACKER / POLICIAL
# =========================
st.markdown("""
<style>
.stApp {
    background-color: #05070a;
    color: #00ff88;
    font-family: "Courier New", monospace;
}
h1 {
    color: #00ff88 !important;
    text-align: center;
    letter-spacing: 3px;
    text-transform: uppercase;
    text-shadow: 0 0 10px #00ff88;
}
.stButton>button {
    background: transparent;
    border: 1px solid #00ff88;
    color: #00ff88;
    width: 100%;
    font-weight: bold;
}
.stButton>button:hover {
    background: #00ff88;
    color: #000;
}
.stDataFrame {
    border: 1px solid #00ff88;
}
.credito-firma {
    color: #00ff88;
    font-weight: bold;
    text-shadow: 0 0 5px #00ff88;
    letter-spacing: 2px;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCIONES
# =========================
def formatear_valor(valor):
    str_valor = str(valor)
    if '.0' in str_valor and len(str_valor) > 5:
        return str_valor.split('.')[0]
    return str_valor

def estandarizar_df(df_temp):
    df_temp.columns = [str(c).strip().lower() for c in df_temp.columns]

    mapping = {
        'linea a': ['linea_a', 'linea a', 'origen', 'numero_llamante', 'msisdn_a', 'abonado'],
        'linea b': ['linea_b', 'linea b', 'destino', 'numero_marcado', 'msisdn_b', 'interlocutor'],
        'latitud': ['latitud', 'lat', 'latitude'],
        'longitud': ['longitud', 'lon', 'longitude'],
        'hora': ['hora', 'time'],
        'fecha': ['fecha', 'date']
    }

    for col_estandar, variantes in mapping.items():
        for var in variantes:
            if var in df_temp.columns:
                df_temp.rename(columns={var: col_estandar}, inplace=True)
                break

    for col in df_temp.columns:
        if 'linea' in col or 'imei' in col or 'imsi' in col:
            df_temp[col] = df_temp[col].apply(formatear_valor).replace('nan', 'DESCONOCIDO')

    if 'latitud' in df_temp.columns and 'longitud' in df_temp.columns:
        df_temp['latitud'] = pd.to_numeric(df_temp['latitud'], errors='coerce')
        df_temp['longitud'] = pd.to_numeric(df_temp['longitud'], errors='coerce')

    if 'fecha' in df_temp.columns:
        try:
            df_temp['fecha'] = pd.to_datetime(df_temp['fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
        except:
            df_temp['fecha'] = df_temp['fecha'].astype(str)

    return df_temp

def generar_html_popup_comparativo(reg_base, reg_espejo, tipo_alerta, titulo_alerta):
    color_banner = "#28a745" 
    if tipo_alerta == "CRUCIAL":
        color_banner = "#dc3545" 
    elif tipo_alerta == "ALERTA":
        color_banner = "#ffc107" 

    text_color = '#fff' if tipo_alerta != 'ALERTA' else '#000'

    html = f"""
    <div style="font-family: monospace; min-width: 410px; color: #000; font-size: 11px;">
        <div style="background-color: {color_banner}; color: {text_color}; padding: 6px; text-align: center; font-weight: bold; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
            {titulo_alerta}
        </div>
    """

    if reg_espejo is not None:
        html += f"""
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1; background: #f8f9fa; padding: 6px; border-radius: 4px; border-left: 3px solid #00ff88;">
                <b style="color: #111;">📄 ALFA (S1)</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                <b>F:</b> {reg_base.get('fecha', 'N/A')}<br>
                <b>H:</b> {reg_base.get('hora', 'N/A')}<br>
                <b>A:</b> {reg_base.get('linea a', 'N/A')}<br>
                <b>B:</b> {reg_base.get('linea b', 'N/A')}<br>
                <b>GEO:</b> {reg_base.get('latitud', 'N/A')}, {reg_base.get('longitud', 'N/A')}<br>
            </div>
            <div style="flex: 1; background: #fdf3f3; padding: 6px; border-radius: 4px; border-left: 3px solid {color_banner};">
                <b style="color: #111;">📑 BRAVO (S2)</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                <b>F:</b> {reg_espejo.get('fecha', 'N/A')}<br>
                <b>H:</b> {reg_espejo.get('hora', 'N/A')}<br>
                <b>A:</b> {reg_espejo.get('linea a', 'N/A')}<br>
                <b>B:</b> {reg_espejo.get('linea b', 'N/A')}<br>
                <b>GEO:</b> {reg_espejo.get('latitud', 'N/A')}, {reg_espejo.get('longitud', 'N/A')}<br>
            </div>
        </div>
        """
    else:
        html += f"""
        <div style="background: #f8f9fa; padding: 8px; border-radius: 4px;">
            <b>Fecha:</b> {reg_base.get('fecha', 'N/A')}<br>
            <b>Hora:</b> {reg_base.get('hora', 'N/A')}<br>
            <b>Línea A:</b> {reg_base.get('linea a', 'N/A')}<br>
            <b>Línea B:</b> {reg_base.get('linea b', 'N/A')}<br>
            <b>Coordenadas:</b> {reg_base.get('latitud', 'N/A')}, {reg_base.get('longitud', 'N/A')}
        </div>
        """
        
    html += "</div>"
    return html

# =========================
# CONTROL DE ESTADO
# =========================
if "opcion_activa" not in st.session_state:
    st.session_state.opcion_activa = "Vista General"

# =========================
# PANEL DE CONTROL
# =========================
st.markdown("### ⚙️ PANEL DE CONTROL")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("📡 GENERAL"): st.session_state.opcion_activa = "Vista General"
with c2:
    if st.button("🌙 PERNOCTA"): st.session_state.opcion_activa = "Pernocta (Personalizada)"
with c3:
    if st.button("🔎 NÚMERO"): st.session_state.opcion_activa = "Búsqueda por Número"
with c4:
    if st.button("📡 ANTENAS"): st.session_state.opcion_activa = "Top Antenas"
with c5:
    if st.button("🧩 CRUCE"): st.session_state.opcion_activa = "Cruce de Sábanas"

st.info(f"MODO ACTIVO: {st.session_state.opcion_activa}")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXPEDIENTE TELEFÓNICO PRINCIPAL", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df_base = estandarizar_df(pd.read_excel(uploaded_file))
        df_filtrado = df_base.copy()
        
        es_cruce_inteligente = False
        df_cruce_referencia = None

        if st.session_state.opcion_activa == "Pernocta (Personalizada)":
            st.markdown("### 🌙 FILTRO HORARIO PERNOCTA")
            col1, col2 = st.columns(2)
            with col1:
                h_inicio = st.slider("Hora Inicio", 0, 23, 22, key="pern_inicio")
            with col2:
                h_fin = st.slider("Hora Fin", 0, 23, 7, key="pern_fin")

            df_filtrado['hora_num'] = pd.to_datetime(df_filtrado['hora'].astype(str), errors='coerce').dt.hour
            if h_inicio > h_fin:
                df_filtrado = df_filtrado[(df_filtrado['hora_num'] >= h_inicio) | (df_filtrado['hora_num'] <= h_fin)]
            else:
                df_filtrado = df_filtrado[(df_filtrado['hora_num'] >= h_inicio) & (df_filtrado['hora_num'] <= h_fin)]

        elif st.session_state.opcion_activa == "Búsqueda por Número":
            num = st.text_input("🔎 NÚMERO OBJETIVO")
            if num:
                df_filtrado = df_base[
                    df_base['linea a'].astype(str).str.contains(num) |
                    df_base['linea b'].astype(str).str.contains(num)
                ]

        elif st.session_state.opcion_activa == "Top Antenas":
            if 'latitud' in df_base.columns and 'longitud' in df_base.columns:
                df_antenas_clean = df_base.dropna(subset=['latitud', 'longitud'])
                df_antenas_clean = df_antenas_clean[(df_antenas_clean['latitud'] != 0) & (df_antenas_clean['longitud'] != 0)]
            else:
                df_antenas_clean = df_base
            df_filtrado = df_antenas_clean.groupby(['latitud', 'longitud']).size().reset_index(name='hits').sort_values('hits', ascending=False).head(15)

        elif st.session_state.opcion_activa == "Cruce de Sábanas":
            st.markdown("### 🧩 INTEL CROSS ANALYSIS")
            tipo = st.selectbox("Modo", ["Números", "Ubicación Inteligente"])
            file2 = st.file_uploader("📂 SEGUNDA SÁBANA", type=["xlsx", "xls"])

            if file2:
                df2 = estandarizar_df(pd.read_excel(file2))
                if tipo == "Números":
                    n1 = set(df_base['linea a']) | set(df_base['linea b'])
                    n2 = set(df2['linea a']) | set(df2['linea b'])
                    comunes = n1.intersection(n2)
                    df_filtrado = df_base[df_base['linea a'].isin(comunes) | df_base['linea b'].isin(comunes)]
                elif tipo == "Ubicación Inteligente":
                    es_cruce_inteligente = True
                    df_cruce_referencia = df2
                    df_filtrado = df_base.copy()

        if not df_filtrado.empty:
            st.subheader("📊 RESULTADOS")
            st.dataframe(df_filtrado, use_container_width=True)

            st.subheader("🗺️ MAPA TÁCTICO")

            df_m = df_filtrado.dropna(subset=['latitud', 'longitud']).copy()
            if not df_m.empty:
                df_m = df_m[(df_m['latitud'] != 0) & (df_m['longitud'] != 0)]

            if not df_m.empty:
                st.success(f"🌐 Procesando cartografía completa: Mapeando {len(df_m)} coordenadas válidas detectadas (registros vacíos o en 0 omitidos).")

                if es_cruce_inteligente and df_cruce_referencia is not None:
                    st.markdown("""
                    <div style="background-color: #0b1119; padding: 12px; border: 1px solid #00ff88; border-radius: 4px; margin-bottom: 15px;">
                        <span style="color:#00ff88; font-weight:bold; font-size:14px;">📋 LEYENDA ANALÍTICA DE CRUCE (SÁBANA 1 vs SÁBANA 2):</span><br>
                        <span style="color:#ff4d4d; font-weight:bold;">● ROJO:</span> Coincidencia espacio-temporal crítica. <b>Mismo lugar el mismo día</b> (Ficha Alfa/Bravo lado a lado).<br>
                        <span style="color:#ffaa00; font-weight:bold;">● AMARILLO:</span> Coincidencia de interés recurrentes. <b>Mismo lugar pero diferente día</b>.<br>
                        <span style="color:#00ff88; font-weight:bold;">● VERDE:</span> Registro estándar de la Sábana Principal (Sin concurrencia detectada en S2).
                    </div>
                    """, unsafe_allow_html=True)

                m = folium.Map(
                    location=[df_m['latitud'].mean(), df_m['longitud'].mean()],
                    zoom_start=11,
                    tiles="OpenStreetMap"
                )

                cluster = MarkerCluster(
                    disableClusteringAtZoom=17, 
                    maxClusterRadius=50
                ).add_to(m)

                for _, r in df_m.iterrows():
                    color_punto = "#00ff88"  
                    tipo_alerta = "BASE"
                    titulo_alerta = "REGISTRO TELEFÓNICO"
                    reg_espejo_dict = None

                    if es_cruce_inteligente and df_cruce_referencia is not None:
                        coincidencias_geo = df_cruce_referencia[
                            (df_cruce_referencia['latitud'] == r['latitud']) & 
                            (df_cruce_referencia['longitud'] == r['longitud'])
                        ]
                        if not coincidencias_geo.empty:
                            mismo_dia = coincidencias_geo[coincidencias_geo['fecha'] == r['fecha']]
                            if not mismo_dia.empty:
                                color_punto = "red"
                                tipo_alerta = "CRUCIAL"
                                titulo_alerta = "💥 CRUCE: MISMO LUGAR/DÍA"
                                reg_espejo_dict = mismo_dia.iloc[0].to_dict()
                            else:
                                color_punto = "orange"
                                tipo_alerta = "ALERTA"
                                titulo_alerta = "⏳ CRUCE: MISMO LUGAR/DIF. DÍA"
                                reg_espejo_dict = coincidencias_geo.iloc[0].to_dict()

                    popup_html = generar_html_popup_comparativo(r.to_dict(), reg_espejo_dict, tipo_alerta, titulo_alerta)
                    
                    # Ajustado ligeramente el alto para dar espacio a la fila de coordenadas (GEO)
                    iframe = folium.IFrame(popup_html, width=420, height=175)
                    popup_obj = folium.Popup(iframe, parse_html=True)

                    folium.CircleMarker(
                        location=[r['latitud'], r['longitud']],
                        radius=5,
                        color=color_punto,
                        fill=True,
                        fill_opacity=0.7,
                        popup=popup_obj
                    ).add_to(cluster)

                st_folium(
                    m, 
                    width="100%", 
                    height=650, 
                    key=f"mapa_completo_{st.session_state.opcion_activa}_{len(df_m)}",
                    returned_objects=[] 
                )

                col_down, col_firma = st.columns([1, 1])
                with col_down:
                    st.download_button(
                        label="📥 DESCARGAR MAPA HTML COMPLETO",
                        data=m._repr_html_(),
                        file_name=f"MAPA_COMPLETO_{st.session_state.opcion_activa.upper()}.html",
                        mime="text/html"
                    )
                with col_firma:
                    st.markdown("<p class='credito-firma' style='text-align: right;'>CREADO POR: J-I-A-M</p>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ No quedan coordenadas válidas tras limpiar campos en cero o vacíos.")
        else:
            st.warning("Sin datos disponibles para este análisis.")

    except Exception as e:
        st.error(f"ERROR DE SISTEMA: {e}")

st.markdown("---")
st.caption("CREADO POR: J - I - A - M")
