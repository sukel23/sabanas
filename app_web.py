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
if 'titulo_mapa' not in st.session_state:
    st.session_state.titulo_mapa = ""

# --- ESTILO VISUAL MEJORADO (Interfaz Clara y Panel Lateral Legible) ---
st.markdown("""
    <style>
    /* Estilo General */
    .main { background-color: #f8f9fa; color: #212529; font-family: 'Segoe UI', sans-serif; }
    
    /* PANEL LATERAL (SIDEBAR) */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #dee2e6;
        padding-top: 20px;
    }
    
    /* Forzar visibilidad de textos en el Sidebar */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stRadio > label {
        color: #31333F !important; /* Gris oscuro para lectura perfecta */
        font-weight: 600 !important;
        font-size: 16px !important;
    }

    /* Estilo de los Radio Buttons del menú */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        background-color: #fbfcfd;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #edf0f2;
    }

    /* Estilo de los Botones Generales */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #007bff;
        background-color: #ffffff;
        color: #007bff;
        font-weight: 600;
        transition: 0.3s all;
    }
    .stButton>button:hover {
        background-color: #007bff;
        color: white;
        box-shadow: 0 4px 8px rgba(0,123,255,0.2);
    }

    /* Títulos */
    h1, h2, h3 { color: #004085 !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 SABANAS ANALYZER v2.1")
st.write("Análisis geoespacial avanzado con interfaz profesional.")
st.write("---")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 Cargar Archivo Excel", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo de columnas automático
        mapping = {
            'linea_b': ['linea b', 'linea_b', 'emisor', 'origen', 'numero_b', 'telefono_b', 'llamado'],
            'linea_a': ['linea a', 'linea_a', 'receptor', 'destino', 'numero_a', 'telefono_a', 'destinatario'],
            'latitud': ['latitud', 'lat', 'latitude', 'lat_dec'],
            'longitud': ['longitud', 'lon', 'long', 'longitude', 'lon_dec'],
            'hora': ['hora', 'time', 'h_inicio'],
            'fecha': ['fecha', 'date', 'f_inicio']
        }

        for col_estandar, variantes in mapping.items():
            for var in variantes:
                if var in df.columns:
                    df.rename(columns={var: col_estandar}, inplace=True)
                    break

        # Limpieza y conversión
        if 'linea_b' in df.columns:
            df['linea_b'] = df['linea_b'].astype(str).str.replace('.0', '', regex=False)
        if 'linea_a' in df.columns:
            df['linea_a'] = df['linea_a'].astype(str).str.replace('.0', '', regex=False)
            
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')

        # --- PANEL LATERAL MEJORADO ---
        with st.sidebar:
            st.markdown("### ⚙️ CONFIGURACIÓN")
            opcion = st.radio(
                "Módulos de Análisis:", 
                ["Vista General", "Pernocta (23:00-06:00)", "Top Antenas", "Top Números Frecuentes", "Búsqueda Específica"]
            )
            
            st.markdown("---")
            if st.sidebar.button("🔄 Reiniciar App"):
                st.session_state.mostrar_mapa = False
                st.rerun()

        df_filtrado = df.copy()

        # --- LÓGICA DE FILTRADO ---
        if opcion == "Pernocta (23:00-06:00)":
            if 'hora' in df.columns:
                df['hora_dt'] = pd.to_datetime(df['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.time
                inicio, fin = pd.to_datetime("23:00:00").time(), pd.to_datetime("06:00:00").time()
                df_filtrado = df[(df['hora_dt'] >= inicio) | (df['hora_dt'] <= fin)].copy()
        elif opcion == "Top Antenas":
            if 'latitud' in df.columns:
                antenas = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones')
                df_filtrado = antenas.sort_values(by='repeticiones', ascending=False).head(15)
        elif opcion == "Búsqueda Específica":
            busqueda = st.text_input("🔍 Buscar número:")
            if busqueda:
                df_filtrado = df[df['linea_b'].str.contains(busqueda, na=False)].copy()

        st.subheader(f"📊 Tabla de Datos: {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- EXPORTACIÓN ---
        st.write("---")
        st.subheader("📦 Exportar Resultados")
        exp_col1, exp_col2, exp_col3 = st.columns(3)

        # Excel
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Resultados')
        
        exp_col1.download_button("📥 Descargar Excel", data=buffer_excel.getvalue(), 
                                 file_name="reporte.xlsx", mime="application/vnd.ms-excel")

        if exp_col2.button("🗺️ Ver Mapa Filtrado"):
            st.session_state.datos_mapa = df_filtrado.copy()
            st.session_state.titulo_mapa = f"Mapa de {opcion}"
            st.session_state.mostrar_mapa = True

        if exp_col3.button("🌎 Ver Mapa Completo"):
            st.session_state.datos_mapa = df.copy()
            st.session_state.titulo_mapa = "Mapa General"
            st.session_state.mostrar_mapa = True

        # --- RENDERIZADO DEL MAPA ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                st.write("---")
                st.subheader(st.session_state.titulo_mapa)
                
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                m = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")
                cluster = MarkerCluster().add_to(m)

                for _, fila in df_m.iterrows():
                    html_popup = "<div style='color:black; font-family:sans-serif; font-size:12px; min-width:200px;'>"
                    html_popup += "<h4 style='color:#007bff; border-bottom:1px solid #ddd; padding-bottom:5px;'>Detalles</h4>"
                    
                    for col in df_m.columns:
                        if col in ['hora_dt']: continue
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

                # Descarga de Mapa
                mapa_html = io.BytesIO()
                m.save(mapa_html, close_file=False)
                st.download_button("💾 Guardar Mapa (HTML)", data=mapa_html.getvalue(), 
                                   file_name="mapa.html", mime="text/html")

                st_folium(m, width="100%", height=600, key=f"map_{len(df_m)}")
            else:
                st.error("No hay coordenadas disponibles.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Esperando archivo Excel...")


