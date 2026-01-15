import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import plotly.express as px
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SABANAS ANALYZER PRO v2.2", layout="wide")

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

st.title("👤 SABANAS ANALYZER v2.2 PRO")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXCEL DE TELEFONÍA (PRINCIPAL)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df = estandarizar_df(df)
        
        st.sidebar.header("OPERACIONES")
        opcion = st.sidebar.radio("Selecciona Análisis:", 
            ["Vista General", "Pernocta (23:00-06:00)", "Búsqueda por Número", "Top Antenas", "Cruce de Sábanas"])

        df_filtrado = df.copy()

        # --- LÓGICA DE FILTRADO ---
        if opcion == "Búsqueda por Número":
            num_buscado = st.sidebar.text_input("Introduce el número a buscar:")
            if num_buscado:
                df_filtrado = df[(df['linea a'].str.contains(num_buscado)) | (df['linea b'].str.contains(num_buscado))]
            else:
                st.info("Ingresa un número en la barra lateral.")

        elif opcion == "Pernocta (23:00-06:00)":
            df['hora_dt'] = pd.to_datetime(df['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.time
            inicio, fin = pd.to_datetime("23:00:00").time(), pd.to_datetime("06:00:00").time()
            df_filtrado = df[(df['hora_dt'] >= inicio) | (df['hora_dt'] <= fin)].copy()

        elif opcion == "Top Antenas":
            df_filtrado = df.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones').sort_values('repeticiones', ascending=False).head(15)

        elif opcion == "Cruce de Sábanas":
            st.sidebar.write("---")
            tipo_cruce = st.sidebar.selectbox("Criterio de Cruce:", ["Números Telefónicos", "Ubicación Geográfica (Lat/Lon)"])
            second_file = st.sidebar.file_uploader("📂 CARGAR SEGUNDA SÁBANA", type=["xlsx", "xls"])
            
            if second_file:
                df2 = pd.read_excel(second_file)
                df2 = estandarizar_df(df2)
                
                if tipo_cruce == "Números Telefónicos":
                    nums_f1 = set(df['linea a'].unique()) | set(df['linea b'].unique())
                    nums_f2 = set(df2['linea a'].unique()) | set(df2['linea b'].unique())
                    coincidencias = nums_f1.intersection(nums_f2)
                    coincidencias.discard('DESCONOCIDO')
                    
                    if coincidencias:
                        st.success(f"🎯 COINCIDENCIA DE NÚMEROS: {len(coincidencias)}")
                        df_filtrado = df[df['linea a'].isin(coincidencias) | df['linea b'].isin(coincidencias)]
                    else:
                        st.warning("No se encontraron números comunes.")
                        df_filtrado = pd.DataFrame()
                
                else: # CRUCE GEOGRÁFICO
                    df1_geo = df.dropna(subset=['latitud', 'longitud'])
                    df1_geo = df1_geo[(df1_geo['latitud'] != 0) & (df1_geo['longitud'] != 0)]
                    df2_geo = df2.dropna(subset=['latitud', 'longitud'])
                    df2_geo = df2_geo[(df2_geo['latitud'] != 0) & (df2_geo['longitud'] != 0)]
                    
                    df1_geo['lat_r'] = df1_geo['latitud'].round(4)
                    df1_geo['lon_r'] = df1_geo['longitud'].round(4)
                    df2_geo['lat_r'] = df2_geo['latitud'].round(4)
                    df2_geo['lon_r'] = df2_geo['longitud'].round(4)
                    
                    coord_f1 = set(zip(df1_geo['lat_r'], df1_geo['lon_r']))
                    coord_f2 = set(zip(df2_geo['lat_r'], df2_geo['lon_r']))
                    coincidencias_geo = coord_f1.intersection(coord_f2)
                    
                    if coincidencias_geo:
                        st.success(f"📍 COINCIDENCIA GEOGRÁFICA: {len(coincidencias_geo)} PUNTOS")
                        df_filtrado = df1_geo[df1_geo.set_index(['lat_r', 'lon_r']).index.isin(coincidencias_geo)]
                    else:
                        st.warning("No se encontraron ubicaciones comunes.")
                        df_filtrado = pd.DataFrame()
            else:
                st.info("Cargue el segundo archivo para realizar el cruce.")

        # --- 📊 ESTADÍSTICAS ---
        if not df_filtrado.empty and opcion != "Top Antenas":
            st.subheader("🔝 TOP 5 CONTACTOS MÁS FRECUENTES")
            resumen = df_filtrado.groupby(['linea a', 'linea b']).size().reset_index(name='Total')
            resumen = resumen.sort_values(by='Total', ascending=False).head(5)
            c1, c2 = st.columns([1, 2])
            with c1: st.table(resumen)
            with c2:
                fig = px.bar(resumen, x='linea b', y='Total', color='Total', template="plotly_dark", color_continuous_scale='Greens')
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

        # --- 📑 REGISTROS ---
        st.subheader(f"📑 REGISTROS ({len(df_filtrado)})")
        st.dataframe(df_filtrado, use_container_width=True)
        
        if not df_filtrado.empty:
            st.download_button("💾 DESCARGAR EXCEL", data=to_excel(df_filtrado), file_name="analisis.xlsx")

            st.write("---")
            col_map1, col_map2 = st.columns([1, 1])
            
            with col_map1:
                if st.button("🗺️ GENERAR MAPA INTERACTIVO"):
                    st.session_state.datos_mapa = df_filtrado.copy()
                    st.session_state.mostrar_mapa = True

            if st.session_state.mostrar_mapa and st.session_state.datos_mapa is not None:
                df_m = st.session_state.datos_mapa.dropna(subset=['latitud', 'longitud'])
                df_m = df_m[(df_m['latitud'] != 0) & (df_m['longitud'] != 0)]
                
                if not df_m.empty:
                    m = folium.Map(location=[df_m['latitud'].mean(), df_m['longitud'].mean()], zoom_start=12, tiles="CartoDB dark_matter")
                    cluster = MarkerCluster().add_to(m)
                    for _, fila in df_m.iterrows():
                        html = f"<b>A:</b> {fila['linea a']}<br><b>B:</b> {fila['linea b']}<br><b>FECHA:</b> {fila['fecha']}"
                        folium.Marker([fila['latitud'], fila['longitud']], popup=folium.Popup(html, max_width=200)).add_to(cluster)
                    
                    st_folium(m, width="100%", height=600)
                    
                    # --- BOTÓN DE DESCARGA DE MAPA ---
                    mapa_html = m._repr_html_()
                    with col_map2:
                        st.download_button(
                            label="📥 DESCARGAR MAPA (HTML)",
                            data=mapa_html,
                            file_name="mapa_analisis_forense.html",
                            mime="text/html"
                        )
                else:
                    st.warning("Sin coordenadas válidas para el mapa.")

    except Exception as e:
        st.error(f"Error técnico: {e}")

st.sidebar.caption("SABANAS ANALYZER v2.2 PRO")
