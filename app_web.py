import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SABANAS ANALYZER", layout="wide")

# Inicializar estados para persistencia de datos
if 'mostrar_mapa' not in st.session_state:
    st.session_state.mostrar_mapa = False
if 'datos_mapa' not in st.session_state:
    st.session_state.datos_mapa = None
if 'titulo_mapa' not in st.session_state:
    st.session_state.titulo_mapa = ""

# Estilo CSS Personalizado (Tema Matrix/Hacker)
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; height: 3em; }
    .stButton>button:hover { background-color: #0f0; color: black; box-shadow: 0 0 15px #0f0; }
    .stDataFrame { border: 1px solid #0f0; background-color: black; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; text-transform: uppercase; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    .stTextInput>div>div>input { background-color: black; color: #0f0; border: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("👤 SABANAS ANALYZER v1.5")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR ARCHIVO EXCEL", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Carga de datos
        df = pd.read_excel(uploaded_file)
        # Limpieza básica de nombres de columnas
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo inteligente de columnas
        mapping = {
            'linea b': ['linea_b', 'linea b', 'destino', 'numero_b', 'telefono_b', 'llamado'],
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

        # Asegurar que linea b sea texto y lat/lon sean números
        if 'linea b' in df.columns:
            df['linea b'] = df['linea b'].astype(str).str.replace('.0', '', regex=False)
        
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')

        # --- MENÚ LATERAL ---
        st.sidebar.header("SISTEMA DE ANÁLISIS")
        opcion = st.sidebar.radio("Seleccione Módulo:", 
            ["Vista General", "Pernocta (23:00-06:00)", "Top Antenas", "Top Números Frecuentes", "Búsqueda Específica"])

        if st.sidebar.button("LIMPIAR PANTALLA"):
            st.session_state.mostrar_mapa = False
            st.rerun()

        df_filtrado = df.copy()

        # --- LÓGICA DE FILTRADO ---
        if opcion == "Pernocta (23:00-06:00)":
            if 'hora' in df.columns:
                # Convertir a formato tiempo para comparar
                df['hora_dt'] = pd.to_datetime(df['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.time
                inicio, fin = pd.to_datetime("23:00:00").time(), pd.to_datetime("06:00:00").time()
                df_filtrado = df[(df['hora_dt'] >= inicio) | (df['hora_dt'] <= fin)].copy()

        elif opcion == "Top Antenas":
            if 'latitud' in df.columns and 'longitud' in df.columns:
                antenas = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones')
                df_filtrado = antenas.sort_values(by='repeticiones', ascending=False).head(15)

        elif opcion == "Top Números Frecuentes":
            if 'linea b' in df.columns:
                top_contactos = df['linea b'].value_counts().head(10)
                df_filtrado = df[df['linea b'].isin(top_contactos.index.tolist())].copy()

        elif opcion == "Búsqueda Específica":
            num_buscado = st.text_input("🔍 Ingrese número o patrón:")
            if num_buscado:
                df_filtrado = df[df['linea b'].str.contains(num_buscado, na=False)].copy()

        # Mostrar Tabla de Resultados
        st.subheader(f"📊 RESULTADOS: {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- SECCIÓN DE MAPAS ---
        st.write("---")
        col_btn1, col_btn2 = st.columns(2)
        
        if col_btn1.button("🗺️ GENERAR MAPA FILTRADO"):
            st.session_state.datos_mapa = df_filtrado.copy()
            st.session_state.titulo_mapa = f"MAPA: {opcion}"
            st.session_state.mostrar_mapa = True

        if col_btn2.button("🌎 GENERAR MAPA COMPLETO"):
            st.session_state.datos_mapa = df.copy()
            st.session_state.titulo_mapa = "MAPA: TOTAL DE REGISTROS"
            st.session_state.mostrar_mapa = True

        # --- RENDERIZADO DEL MAPA ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            # Limpiar nulos de coordenadas antes de graficar
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            
            if not df_m.empty:
                st.subheader(st.session_state.titulo_mapa)
                
                # Centro del mapa basado en el promedio de los datos
                centro = [df_m['latitud'].mean(), df_m['longitud'].mean()]
                
                # Crear mapa con tema oscuro
                m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
                cluster = MarkerCluster().add_to(m)

                # Dibujar marcadores
                for _, fila in df_m.iterrows():
                    popup_txt = f"""
                    <div style='color: black; font-family: sans-serif;'>
                        <b>Número:</b> {fila.get('linea b', 'N/A')}<br>
                        <b>Fecha:</b> {fila.get('fecha', 'N/A')}<br>
                        <b>Hora:</b> {fila.get('hora', 'N/A')}<br>
                        <b>Coord:</b> {round(fila['latitud'], 5)}, {round(fila['longitud'], 5)}
                    </div>
                    """
                    
                    folium.Marker(
                        location=[fila['latitud'], fila['longitud']],
                        popup=folium.Popup(popup_txt, max_width=250),
                        icon=folium.Icon(color='green', icon='crosshairs', prefix='fa')
                    ).add_to(cluster)

                # Renderizar en Streamlit (con una key única para forzar actualización)
                st_folium(m, width="100%", height=600, key=f"mapa_act_{len(df_m)}")
            else:
                st.error("❌ ERROR: Los datos seleccionados no tienen coordenadas (Latitud/Longitud) válidas.")

    except Exception as e:
        st.error(f"❌ ERROR CRÍTICO: {e}")

else:
    st.info("💻 Esperando carga de archivo Excel para iniciar análisis...")
