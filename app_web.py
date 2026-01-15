import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Search
import plotly.express as px
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SABANAS ANALYZER PRO v2.8", layout="wide")

if 'mostrar_mapa' not in st.session_state:
    st.session_state.mostrar_mapa = False
if 'datos_mapa' not in st.session_state:
    st.session_state.datos_mapa = None

# Estilo CSS Personalizado
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; }
    .stButton>button:hover { background-color: #0f0; color: black; box-shadow: 0 0 15px #0f0; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; text-transform: uppercase; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Analisis_Forense')
    return output.getvalue()

def estandarizar_df(df_temp):
    df_temp.columns = [str(c).strip().lower() for c in df_temp.columns]
    mapping = {
        'linea a': ['linea_a', 'linea a', 'origen', 'numero_llamante', 'msisdn_a', 'abonado'],
        'linea b': ['linea_b', 'linea b', 'destino', 'numero_marcado', 'msisdn_b', 'interlocutor', 'llamado'],
        'latitud': ['latitud', 'lat', 'latitude', 'lat_antena'],
        'longitud': ['longitud', 'lon', 'long', 'longitude', 'lon_antena'],
        'hora': ['hora', 'time', 'inicio_llamada'],
        'fecha': ['fecha', 'date', 'fecha_inicio']
    }
    for col_estandar, variantes in mapping.items():
        for var in variantes:
            if var in df_temp.columns:
                df_temp.rename(columns={var: col_estandar}, inplace=True)
                break
    for col in ['linea a', 'linea b']:
        if col in df_temp.columns:
            df_temp[col] = df_temp[col].astype(str).str.replace('.0', '', regex=False).replace('nan', 'DESCONOCIDO')
    
    if 'latitud' in df_temp.columns and 'longitud' in df_temp.columns:
        df_temp['latitud'] = pd.to_numeric(df_temp['latitud'], errors='coerce')
        df_temp['longitud'] = pd.to_numeric(df_temp['longitud'], errors='coerce')
        
    return df_temp

st.title("👤 SABANAS ANALYZER v2.8 PRO")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXCEL DE TELEFONÍA", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df = estandarizar_df(df)
        
        st.sidebar.header("OPERACIONES")
        opcion = st.sidebar.radio("Selecciona Análisis:", 
            ["Vista General", "Pernocta (23:00-06:00)", "Búsqueda por Número", "Top Antenas", "Cruce de Sábanas"])

        df_filtrado = df.copy()

        # Lógica de filtrado (Mantenida igual)
        if opcion == "Cruce de Sábanas":
            st.sidebar.write("---")
            tipo_cruce = st.sidebar.selectbox("Criterio:", ["Números", "Ubicación"])
            second_file = st.sidebar.file_uploader("📂 SEGUNDA SÁBANA", type=["xlsx", "xls"])
            if second_file:
                df2 = estandarizar_df(pd.read_excel(second_file))
                if tipo_cruce == "Números":
                    nums1 = set(df['linea a']) | set(df['linea b'])
                    nums2 = set(df2['linea a']) | set(df2['linea b'])
                    coincidencias = nums1.intersection(nums2)
                    coincidencias.discard('DESCONOCIDO')
                    df_filtrado = df[df['linea a'].isin(coincidencias) | df['linea b'].isin(coincidencias)]
                else:
                    df['lat_r'], df['lon_r'] = df['latitud'].round(4), df['longitud'].round(4)
                    df2['lat_r'], df2['lon_r'] = df2['latitud'].round(4), df2['longitud'].round(4)
                    coord1 = set(zip(df.dropna(subset=['lat_r'])['lat_r'], df.dropna(subset=['lon_r'])['lon_r']))
                    coord2 = set(zip(df2.dropna(subset=['lat_r'])['lat_r'], df2.dropna(subset=['lon_r'])['lon_r']))
                    comunes = coord1.intersection(coord2)
                    df_filtrado = df[df.set_index(['lat_r', 'lon_r']).index.isin(comunes)]

        elif opcion == "Búsqueda por Número":
            num = st.sidebar.text_input("Número:")
            if num: df_filtrado = df[(df['linea a'].str.contains(num)) | (df['linea b'].str.contains(num))]

        elif opcion == "Pernocta (23:00-06:00)":
            df['hora_dt'] = pd.to_datetime(df['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.time
            inicio, fin = pd.to_datetime("23:00:00").time(), pd.to_datetime("06:00:00").time()
            df_filtrado = df[(df['hora_dt'] >= inicio) | (df['hora_dt'] <= fin)]

        elif opcion == "Top Antenas":
            df_filtrado = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones').sort_values('repeticiones', ascending=False).head(15)

        st.subheader(f"📑 REGISTROS ({len(df_filtrado)})")
        st.dataframe(df_filtrado, use_container_width=True)
        
        if not df_filtrado.empty:
            col_m1, col_m2 = st.columns([1, 1])
            with col_m1:
                if st.button("🗺️ GENERAR MAPA PROFESIONAL"):
                    st.session_state.datos_mapa = df_filtrado.copy()
                    st.session_state.mostrar_mapa = True

            if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
                df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
                df_m = df_m[(df_m['latitud'] != 0) & (df_m['longitud'] != 0)]
                
                if not df_m.empty:
                    # MAPA FONDO BLANCO Y BUSCADOR
                    m = folium.Map(location=[df_m['latitud'].mean(), df_m['longitud'].mean()], zoom_start=12, tiles="OpenStreetMap")
                    cluster = MarkerCluster().add_to(m)
                    
                    # Capa para el buscador
                    fg = folium.FeatureGroup(name="Registros")
                    
                    for _, fila in df_m.iterrows():
                        # TABLA HTML PARA EL POPUP (Más organizada)
                        html_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px;'>"
                        html_table += "<tr style='background-color: #f2f2f2;'><th>CAMPO</th><th>VALOR</th></tr>"
                        for col in df_m.columns:
                            if col not in ['lat_r', 'lon_r', 'hora_dt']:
                                html_table += f"<tr><td style='border:1px solid #ddd; padding:4px; font-weight:bold;'>{col.upper()}</td><td style='border:1px solid #ddd; padding:4px;'>{fila[col]}</td></tr>"
                        html_table += "</table>"
                        
                        # SOLUCIÓN: CircleMarker en lugar de Marker (No usa imágenes externas)
                        folium.CircleMarker(
                            location=[fila['latitud'], fila['longitud']],
                            radius=8,
                            popup=folium.Popup(html_table, max_width=350),
                            color='black', # Borde del punto
                            weight=1,
                            fill=True,
                            fill_color='red', # Color del punto
                            fill_opacity=0.7,
                            name=f"A: {fila.get('linea a', '')} | B: {fila.get('linea b', '')}"
                        ).add_to(fg)
                    
                    fg.add_to(m)
                    cluster.add_to(m)
                    
                    # BUSCADOR SOBRE EL MAPA
                    Search(layer=fg, geom_type="Point", placeholder="Buscar número...", collapsed=False, search_label="name").add_to(m)

                    st_folium(m, width="100%", height=600)
                    with col_m2:
                        st.download_button("📥 DESCARGAR MAPA HTML", data=m._repr_html_(), file_name="mapa_forense.html", mime="text/html")
                else:
                    st.warning("⚠️ Sin coordenadas válidas.")

    except Exception as e:
        st.error(f"Error: {e}")

st.sidebar.caption("SABANAS ANALYZER v2.8 PRO")
