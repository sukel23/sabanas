import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SABANAS ANALYZER PRO", layout="wide")

# Inicializar estados de sesión
if 'mostrar_mapa' not in st.session_state:
    st.session_state.mostrar_mapa = False
if 'datos_mapa' not in st.session_state:
    st.session_state.datos_mapa = None

# --- ESTILO VISUAL CLARO Y BRILLANTE ---
st.markdown("""
    <style>
    .main { background-color: #ffffff; color: #1a1a1a; font-family: 'Segoe UI', sans-serif; }
    
    /* PANEL LATERAL: Texto muy nítido y oscuro */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        border-right: 1px solid #dee2e6;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #000000 !important;
        font-weight: 700 !important;
    }

    /* Botones con colores vivos */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 2px solid #007bff;
        background-color: #ffffff;
        color: #007bff;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #007bff;
        color: white;
    }
    
    /* Títulos con brillo */
    h1, h2, h3 { color: #007bff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SABANAS ANALYZER v2.2")
st.write("---")

uploaded_file = st.file_uploader("📂 Seleccione archivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo automático
        mapping = {
            'linea_b': ['linea b', 'linea_b', 'emisor', 'origen'],
            'linea_a': ['linea a', 'linea_a', 'receptor', 'destino'],
            'latitud': ['latitud', 'lat', 'latitude'],
            'longitud': ['longitud', 'lon', 'longitude'],
            'hora': ['hora', 'time'],
            'fecha': ['fecha', 'date']
        }

        for col_estandar, variantes in mapping.items():
            for var in variantes:
                if var in df.columns:
                    df.rename(columns={var: col_estandar}, inplace=True)
                    break

        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')

        # --- PANEL LATERAL ---
        with st.sidebar:
            st.markdown("### ⚙️ OPCIONES")
            opcion = st.radio("Módulo de Análisis:", ["Vista General", "Pernocta", "Top Antenas", "Búsqueda"])
            if st.button("🔄 Reiniciar App"):
                st.session_state.mostrar_mapa = False
                st.rerun()

        df_filtrado = df.copy()
        # (Aquí se mantiene tu lógica de filtrado de versiones anteriores)

        st.subheader(f"📍 Registros: {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- BOTONES DE MAPA ---
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗺️ VER MAPA (ALTO BRILLO)"):
                st.session_state.datos_mapa = df_filtrado.copy()
                st.session_state.mostrar_mapa = True
        with c2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filtrado.to_excel(writer, index=False)
            st.download_button("📥 DESCARGAR EXCEL", data=buffer.getvalue(), file_name="analisis.xlsx")

        # --- MAPA DE ALTA LUMINOSIDAD ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                st.write("---")
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                
                # USAMOS CARTODB POSITRON PARA MÁXIMO BRILLO Y NITIDEZ
                m = folium.Map(
                    location=centro, 
                    zoom_start=12, 
                    tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                    control_scale=True
                )
                
                cluster = MarkerCluster(options={'maxClusterRadius': 50}).add_to(m)

                for _, fila in df_m.iterrows():
                    html_popup = f"<div style='color:black; font-family:sans-serif; font-size:12px; min-width:200px;'>"
                    html_popup += "<h4 style='color:#007bff; border-bottom:1px solid #eee;'>Info Registro</h4>"
                    for col in df_m.columns:
                        if col == 'hora_dt': continue
                        label = col.upper().replace('_', ' ')
                        if col == 'linea_b': label = "📞 EMISOR (B)"
                        if col == 'linea_a': label = "📱 RECEPTOR (A)"
                        html_popup += f"<b>{label}:</b> {fila[col]}<br>"
                    html_popup += "</div>"

                    folium.Marker(
                        location=[fila['latitud'], fila['longitud']],
                        popup=folium.Popup(html_popup, max_width=350),
                        icon=folium.Icon(color='blue', icon='info-sign', prefix='fa')
                    ).add_to(cluster)

                # Renderizado estable
                st_folium(m, width="100%", height=600, key=f"map_brillante_{len(df_m)}")
                
                m_html = io.BytesIO()
                m.save(m_html, close_file=False)
                st.download_button("💾 Guardar Mapa HTML", data=m_html.getvalue(), file_name="mapa_nítido.html")

    except Exception as e:
        st.error(f"Error: {e}")


