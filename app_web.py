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

# Estilo visual "Hacker"
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; }
    .stButton>button:hover { background-color: #0f0; color: black; box-shadow: 0 0 15px #0f0; }
    .stDataFrame { border: 1px solid #0f0; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("👤 SABANAS ANALYZER v1.8 - FINAL")
st.write("---")

# --- CARGA DE DATOS ---
uploaded_file = st.file_uploader("📂 SUBIR ARCHIVO EXCEL DE SABANAS", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        # Guardar nombres originales para los títulos del popup antes de normalizar
        columnas_originales = df.columns.tolist()
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo de columnas automático (Emisor B, Receptor A)
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

        # Limpieza de datos
        if 'linea_b' in df.columns:
            df['linea_b'] = df['linea_b'].astype(str).str.replace('.0', '', regex=False)
        if 'linea_a' in df.columns:
            df['linea_a'] = df['linea_a'].astype(str).str.replace('.0', '', regex=False)
            
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')

        # --- PANEL LATERAL ---
        st.sidebar.header("MENÚ DE ANÁLISIS")
        opcion = st.sidebar.radio("Módulos:", 
            ["Vista General", "Pernocta (23:00-06:00)", "Top Antenas", "Top Números Frecuentes", "Búsqueda Específica"])

        if st.sidebar.button("🗑️ RESETEAR VISTA"):
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
            if 'latitud' in df.columns and 'longitud' in df.columns:
                antenas = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones')
                df_filtrado = antenas.sort_values(by='repeticiones', ascending=False).head(15)
        elif opcion == "Top Números Frecuentes":
            if 'linea_b' in df.columns:
                top_nums = df['linea_b'].value_counts().head(10)
                df_filtrado = df[df['linea_b'].isin(top_nums.index.tolist())].copy()
        elif opcion == "Búsqueda Específica":
            busqueda = st.text_input("🔍 Buscar número:")
            if busqueda:
                df_filtrado = df[df['linea_b'].str.contains(busqueda, na=False)].copy()

        st.subheader(f"📊 RESULTADOS: {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- EXPORTACIÓN ---
        st.write("---")
        st.subheader("💾 EXPORTE INTELIGENCIA")
        exp_col1, exp_col2, exp_col3 = st.columns(3)

        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Resultados')
        
        exp_col1.download_button("📥 DESCARGAR EXCEL FILTRADO", data=buffer_excel.getvalue(), 
                                 file_name="reporte_sabana.xlsx", mime="application/vnd.ms-excel")

        if exp_col2.button("🗺️ MAPEER VISTA ACTUAL"):
            st.session_state.datos_mapa = df_filtrado.copy()
            st.session_state.titulo_mapa = f"MAPA: {opcion}"
            st.session_state.mostrar_mapa = True

        if exp_col3.button("🌎 MAPA TODO"):
            st.session_state.datos_mapa = df.copy()
            st.session_state.titulo_mapa = "MAPA: REGISTROS TOTALES"
            st.session_state.mostrar_mapa = True

        # --- RENDERIZADO DEL MAPA CON TODOS LOS TÍTULOS ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                st.write("---")
                st.subheader(st.session_state.titulo_mapa)
                
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
                cluster = MarkerCluster().add_to(m)

                for _, fila in df_m.iterrows():
                    # Generar popup con TODAS las columnas
                    html_popup = "<div style='color:black; font-family:Arial; font-size:12px; min-width:200px;'>"
                    html_popup += "<h4 style='color:#007bff; margin-top:0;'>Detalle del Registro</h4>"
                    
                    for col in df_m.columns:
                        if col in ['hora_dt']: continue # Omitir columnas auxiliares
                        
                        valor = fila[col]
                        label = col.upper().replace('_', ' ')
                        
                        # Resaltar Emisor y Receptor
                        if col == 'linea_b': label = "🔴 EMISOR (B)"
                        if col == 'linea_a': label = "🔵 RECEPTOR (A)"
                        
                        html_popup += f"<b>{label}:</b> {valor}<br>"
                    
                    html_popup += "</div>"

                    folium.Marker(
                        location=[fila['latitud'], fila['longitud']],
                        popup=folium.Popup(html_popup, max_width=350),
                        icon=folium.Icon(color='green', icon='crosshairs', prefix='fa')
                    ).add_to(cluster)

                # Descarga de Mapa
                mapa_html = io.BytesIO()
                m.save(mapa_html, close_file=False)
                st.download_button("🔥 DESCARGAR MAPA (HTML)", data=mapa_html.getvalue(), 
                                   file_name="mapa_inteligencia.html", mime="text/html")

                st_folium(m, width="100%", height=600, key=f"map_{len(df_m)}")
            else:
                st.error("❌ No hay coordenadas para mostrar.")

    except Exception as e:
        st.error(f"❌ ERROR SISTEMA: {e}")
else:
    st.info("💻 Cargue un archivo Excel para iniciar el análisis de celdas.")

