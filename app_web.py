import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SABANAS ANALYZER PRO", layout="wide")

if 'mostrar_mapa' not in st.session_state:
    st.session_state.mostrar_mapa = False
if 'datos_mapa' not in st.session_state:
    st.session_state.datos_mapa = None

# Estilo Hacker
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("👤 SABANAS ANALYZER v1.7")

uploaded_file = st.file_uploader("📂 SUBIR ARCHIVO EXCEL", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        # Limpiar nombres de columnas (quitar espacios y poner minúsculas para procesar)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # --- NORMALIZACIÓN DE EMISOR Y RECEPTOR ---
        # Buscamos variantes para asegurar que Línea B sea Emisor y Línea A sea Receptor
        mapping = {
            'linea_b': ['linea b', 'linea_b', 'emisor', 'origen', 'numero b'],
            'linea_a': ['linea a', 'linea_a', 'receptor', 'destino', 'numero a'],
            'latitud': ['latitud', 'lat', 'latitude'],
            'longitud': ['longitud', 'lon', 'longitude']
        }

        for col_estandar, variantes in mapping.items():
            for var in variantes:
                if var in df.columns:
                    df.rename(columns={var: col_estandar}, inplace=True)
                    break

        # Convertir coordenadas a números
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')

        # --- MENÚ Y FILTROS ---
        st.sidebar.header("ANÁLISIS")
        opcion = st.sidebar.radio("Módulo:", ["Vista General", "Pernocta", "Top Antenas"])
        
        df_filtrado = df.copy() # Aquí iría tu lógica de filtrado previa...

        st.dataframe(df_filtrado)

        # --- BOTONES DE MAPA ---
        if st.button("🗺️ GENERAR MAPA CON TODA LA INFORMACIÓN"):
            st.session_state.datos_mapa = df_filtrado.copy()
            st.session_state.mostrar_mapa = True

        # --- RENDERIZADO DEL MAPA ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
                cluster = MarkerCluster().add_to(m)

                for _, fila in df_m.iterrows():
                    # --- GENERAR CONTENIDO DINÁMICO DEL POPUP ---
                    # Esto recorre TODAS las columnas del Excel original
                    contenido_html = "<div style='font-family: sans-serif; font-size: 12px; color: black; min-width: 200px;'>"
                    contenido_html += "<h4 style='margin-bottom:5px; color:blue;'>Datos del Registro</h4>"
                    
                    for col in df_m.columns:
                        valor = fila[col]
                        # Personalizar etiquetas específicas si existen
                        label = col.upper()
                        if col == 'linea_b': label = "🔴 EMISOR (Línea B)"
                        if col == 'linea_a': label = "🔵 RECEPTOR (Línea A)"
                        
                        contenido_html += f"<b>{label}:</b> {valor}<br>"
                    
                    contenido_html += "</div>"

                    folium.Marker(
                        location=[fila['latitud'], fila['longitud']],
                        popup=folium.Popup(contenido_html, max_width=350),
                        icon=folium.Icon(color='green', icon='info-sign')
                    ).add_to(cluster)

                # Botón de Descarga
                mapa_html = io.BytesIO()
                m.save(mapa_html, close_file=False)
                st.download_button("💾 Descargar este Mapa (HTML)", data=mapa_html.getvalue(), file_name="mapa_detallado.html", mime="text/html")

                st_folium(m, width="100%", height=600, key=f"map_{len(df_m)}")
            else:
                st.error("No hay coordenadas válidas.")

    except Exception as e:
        st.error(f"Error: {e}")


