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

# --- ESTILO VISUAL PROFESIONAL MEJORADO ---
st.markdown("""
    <style>
    /* Fondo general */
    .main { background-color: #f0f2f6; }
    
    /* Panel lateral: Forzar colores de texto */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e6e9ef;
    }
    
    /* Color de los textos en el sidebar */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #1f2937 !important;
        font-weight: 500 !important;
    }

    /* Estilo de los Botones */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #0052cc;
        background-color: #ffffff;
        color: #0052cc;
        padding: 10px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0052cc;
        color: white;
    }

    /* Títulos */
    h1, h2, h3 {
        color: #111827 !important;
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SABANAS ANALYZER v2.0")
st.write("Cargue sus datos para iniciar el análisis geoespacial.")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Seleccione archivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo automático
        mapping = {
            'linea_b': ['linea b', 'linea_b', 'emisor', 'origen', 'numero_b', 'telefono_b'],
            'linea_a': ['linea a', 'linea_a', 'receptor', 'destino', 'numero_a'],
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

        # --- PANEL LATERAL CON TEXTO VISIBLE ---
        with st.sidebar:
            st.header("⚙️ CONFIGURACIÓN")
            opcion = st.radio(
                "Módulos de Análisis:",
                ["Vista General", "Pernocta (23:00-06:00)", "Top Antenas", "Top Números Frecuentes", "Búsqueda Específica"]
            )
            
            st.write("---")
            if st.button("🔄 Reiniciar App"):
                st.session_state.mostrar_mapa = False
                st.rerun()

        # --- LÓGICA DE FILTRADO ---
        df_filtrado = df.copy()
        if opcion == "Pernocta (23:00-06:00)":
            if 'hora' in df.columns:
                df['hora_dt'] = pd.to_datetime(df['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.time
                inicio, fin = pd.to_datetime("23:00:00").time(), pd.to_datetime("06:00:00").time()
                df_filtrado = df[(df['hora_dt'] >= inicio) | (df['hora_dt'] <= fin)].copy()
        elif opcion == "Top Antenas":
            if 'latitud' in df.columns:
                antenas = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones')
                df_filtrado = antenas.sort_values(by='repeticiones', ascending=False).head(15)

        # --- MOSTRAR DATOS ---
        st.subheader(f"📍 Datos Filtrados: {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- BOTONES DE ACCIÓN ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_filtrado.to_excel(writer, index=False)
            st.download_button("📥 Descargar Tabla", data=buffer.getvalue(), file_name="analisis.xlsx")

        with c2:
            if st.button("🗺️ Ver Mapa Filtrado"):
                st.session_state.datos_mapa = df_filtrado.copy()
                st.session_state.mostrar_mapa = True

        with c3:
            if st.button("🌎 Ver Mapa Completo"):
                st.session_state.datos_mapa = df.copy()
                st.session_state.mostrar_mapa = True

        # --- MAPA ESTILO GOOGLE MAPS ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                st.write("---")
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                m = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")
                cluster = MarkerCluster().add_to(m)

                for _, fila in df_m.iterrows():
                    html_popup = "<div style='font-family:sans-serif; font-size:12px; min-width:200px;'>"
                    html_popup += "<h4 style='color:#0052cc; border-bottom:1px solid #eee;'>Info Registro</h4>"
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
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(cluster)

                st_folium(m, width="100%", height=600, key=f"map_{len(df_m)}")
                
                # Botón para descargar el mapa
                m_html = io.BytesIO()
                m.save(m_html, close_file=False)
                st.download_button("💾 Guardar Mapa (HTML)", data=m_html.getvalue(), file_name="mapa.html")

    except Exception as e:
        st.error(f"Error: {e}")

