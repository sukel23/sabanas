import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="ANONYMOUS ANALYZER", layout="wide")

# Inicializar estados para que el mapa no desaparezca
if 'mostrar_mapa' not in st.session_state:
    st.session_state.mostrar_mapa = False
if 'datos_mapa' not in st.session_state:
    st.session_state.datos_mapa = None
if 'titulo_mapa' not in st.session_state:
    st.session_state.titulo_mapa = ""

# Estilo CSS Personalizado
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; }
    .stButton>button:hover { background-color: #0f0; color: black; box-shadow: 0 0 15px #0f0; }
    .stDataFrame { border: 1px solid #0f0; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; text-transform: uppercase; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("👤 SABANAS ANALYZER v1.4")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXCEL", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Mapeo de columnas
        mapping = {
            'linea b': ['linea_b', 'linea b', 'destino', 'numero_b', 'telefono_b'],
            'latitud': ['latitud', 'lat', 'latitude'],
            'longitud': ['longitud', 'lon', 'long', 'longitude'],
            'hora': ['hora', 'time'],
            'fecha': ['fecha', 'date']
        }

        for col_estandar, variantes in mapping.items():
            for var in variantes:
                if var in df.columns:
                    df.rename(columns={var: col_estandar}, inplace=True)
                    break

        df['linea b'] = df['linea b'].astype(str).str.replace('.0', '', regex=False)

        # --- MENÚ LATERAL ---
        st.sidebar.header("OPERACIONES")
        opcion = st.sidebar.radio("Selecciona Análisis:", 
            ["Vista General", "Pernocta (23:00-06:00)", "Top Antenas", "Top Números Frecuentes", "Búsqueda Específica"])

        # Resetear mapa si cambia la opción del menú
        if st.sidebar.button("Limpiar Pantalla"):
            st.session_state.mostrar_mapa = False

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
                df_filtrado = antenas.sort_values(by='repeticiones', ascending=False).head(10)
        elif opcion == "Top Números Frecuentes":
            top_contactos = df['linea b'].value_counts().head(10)
            df_filtrado = df[df['linea b'].isin(top_contactos.index.tolist())].copy()
        elif opcion == "Búsqueda Específica":
            num_buscado = st.text_input("🔍 Buscar número:")
            if num_buscado:
                df_filtrado = df[df['linea b'].str.contains(num_buscado, na=False)].copy()

        st.subheader(f"📊 {opcion}")
        st.dataframe(df_filtrado, use_container_width=True)

        # --- BOTONES DE MAPA ---
        st.write("---")
        c1, c2 = st.columns(2)
        
        if c1.button("🗺️ MAPA VISTA ACTUAL"):
            st.session_state.datos_mapa = df_filtrado.copy()
            st.session_state.titulo_mapa = f"Mapa: {opcion}"
            st.session_state.mostrar_mapa = True

        if c2.button("🌎 MAPA COMPLETO"):
            st.session_state.datos_mapa = df.copy()
            st.session_state.titulo_mapa = "Mapa: Registros Totales"
            st.session_state.mostrar_mapa = True

        # --- RENDERIZADO PERSISTENTE DEL MAPA ---
        if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
            df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
            if not df_m.empty:
                st.subheader(st.session_state.titulo_mapa)
                centro = [float(df_m['latitud'].iloc[0]), float(df_m['longitud'].iloc[0])]
                m = folium.Map(location=centro, zoom_start=12, tiles="CartoDB dark_matter")
                cluster = MarkerCluster().add_to(m)

                for _, fila in df_m.iterrows():
                    popup_info = f"<b>Lat:</b> {fila['latitud']}<br><b>Lon:</b> {fila['longitud']}"
                    if 'repeticiones' in fila:
                        popup_info += f"<br><b>Frecuencia:</b> {fila['repeticiones']}"
                    else:
                        popup_info += f"<br><b>Número:</b> {fila['linea b']}"

                    folium.Marker(
                        location=[float(fila['latitud']), float(fila['longitud'])],
                        popup=folium.Popup(popup_info, max_width=300),
                        icon=folium.Icon(color='green', icon='crosshairs', prefix='fa')
                    ).add_to(cluster)

                st_folium(m, width="100%", height=600, key=f"mapa_{st.session_state.titulo_mapa}")
            else:
                st.error("No hay coordenadas para mostrar.")

    except Exception as e:
        st.error(f"Error: {e}")