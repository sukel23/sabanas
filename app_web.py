import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, Search
import plotly.express as px
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="ANALISIS FORENSE INTELIGENCIA", layout="wide")

# Estilo CSS Personalizado (Hacker Style)
st.markdown("""
    <style>
    .main { background-color: #000000; color: #0f0; font-family: 'Courier New'; }
    .stButton>button { width: 100%; border: 1px solid #0f0; background-color: black; color: #0f0; font-weight: bold; }
    h1, h2, h3 { color: #0f0 !important; text-shadow: 0 0 8px #0f0; text-transform: uppercase; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #0f0; }
    .stDataFrame { border: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

# Función para formatear valores, eliminando decimales innecesarios de IMEI/IMSI
def formatear_valor(valor):
    str_valor = str(valor)
    if '.0' in str_valor and len(str_valor) > 5: # Limpieza de números largos
        return str_valor.split('.')[0]
    return str_valor

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
    
    # Limpieza de datos en columnas clave
    for col in df_temp.columns:
        if 'linea' in col or 'imei' in col or 'imsi' in col:
             df_temp[col] = df_temp[col].apply(formatear_valor).replace('nan', 'DESCONOCIDO')
    
    if 'latitud' in df_temp.columns and 'longitud' in df_temp.columns:
        df_temp['latitud'] = pd.to_numeric(df_temp['latitud'], errors='coerce')
        df_temp['longitud'] = pd.to_numeric(df_temp['longitud'], errors='coerce')
    return df_temp

st.title("👤 ANALIZADOR DE SABANAS DE INTELIGENCIA")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXCEL DE TELEFONÍA", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Carga inicial y estandarización
        df_base = estandarizar_df(pd.read_excel(uploaded_file))
        
        st.sidebar.header("OPERACIONES")
        opcion = st.sidebar.radio("Selecciona Análisis:", 
            ["Vista General", "Pernocta (Personalizada)", "Búsqueda por Número", "Top Antenas", "Cruce de Sábanas"])

        df_filtrado = df_base.copy()

        # --- LÓGICA DE FILTRADO ---
        if opcion == "Pernocta (Personalizada)":
            st.sidebar.subheader("⚙️ RANGO HORARIO")
            h_inicio = st.sidebar.slider("Hora de Inicio:", 0, 23, 22, key="s_ini")
            h_fin = st.sidebar.slider("Hora de Fin:", 0, 23, 7, key="s_fin")
            
            df_filtrado['hora_num'] = pd.to_datetime(df_filtrado['hora'].astype(str), format='%H:%M:%S', errors='coerce').dt.hour
            
            if h_inicio > h_fin:
                df_filtrado = df_filtrado[(df_filtrado['hora_num'] >= h_inicio) | (df_filtrado['hora_num'] <= h_fin)]
            else:
                df_filtrado = df_filtrado[(df_filtrado['hora_num'] >= h_inicio) & (df_filtrado['hora_num'] <= h_fin)]
            
            st.sidebar.write(f"📊 Registros en rango: **{len(df_filtrado)}**")

        elif opcion == "Búsqueda por Número":
            num = st.sidebar.text_input("Ingresa número:")
            if num: 
                df_filtrado = df_base[(df_base['linea a'].str.contains(num)) | (df_base['linea b'].str.contains(num))]

        elif opcion == "Top Antenas":
            df_filtrado = df_base.groupby(['latitud', 'longitud']).size().reset_index(name='repeticiones').sort_values('repeticiones', ascending=False).head(15)

        elif opcion == "Cruce de Sábanas":
            tipo_cruce = st.sidebar.selectbox("Criterio:", ["Números", "Ubicación"])
            second_file = st.sidebar.file_uploader("📂 SEGUNDA SÁBANA", type=["xlsx", "xls"])
            if second_file:
                df2 = estandarizar_df(pd.read_excel(second_file))
                if tipo_cruce == "Números":
                    nums1 = set(df_base['linea a']) | set(df_base['linea b'])
                    nums2 = set(df2['linea a']) | set(df2['linea b'])
                    comunes = nums1.intersection(nums2)
                    comunes.discard('DESCONOCIDO')
                    df_filtrado = df_base[df_base['linea a'].isin(comunes) | df_base['linea b'].isin(comunes)]
                else:
                    df_base['lat_r'], df_base['lon_r'] = df_base['latitud'].round(4), df_base['longitud'].round(4)
                    df2['lat_r'], df2['lon_r'] = df2['latitud'].round(4), df2['longitud'].round(4)
                    coord_comunes = set(zip(df_base.dropna(subset=['lat_r'])['lat_r'], df_base.dropna(subset=['lon_r'])['lon_r'])).intersection(
                                    set(zip(df2.dropna(subset=['lat_r'])['lat_r'], df2.dropna(subset=['lon_r'])['lon_r'])))
                    df_filtrado = df_base[df_base.set_index(['lat_r', 'lon_r']).index.isin(coord_comunes)]

        # --- VISUALIZACIÓN ---
        if not df_filtrado.empty:
            if opcion != "Top Antenas":
                st.subheader("🔝 TOP CONTACTOS")
                resumen = df_filtrado.groupby(['linea a', 'linea b']).size().reset_index(name='Total').sort_values('Total', ascending=False).head(5)
                c1, c2 = st.columns([1, 2])
                with c1: st.table(resumen)
                with c2:
                    fig = px.bar(resumen, x='linea b', y='Total', template="plotly_dark", color_discrete_sequence=['#0f0'])
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"📑 REGISTROS ({len(df_filtrado)})")
            st.dataframe(df_filtrado, use_container_width=True)

            # --- MAPA AUTOMÁTICO DETALLADO ---
            st.subheader("🗺️ MAPA GEORREFERENCIAL DETALLADO")
            df_m = df_filtrado.dropna(subset=['latitud', 'longitud'])
            df_m = df_m[(df_m['latitud'] != 0) & (df_m['longitud'] != 0)]

            if not df_m.empty:
                m = folium.Map(location=[df_m['latitud'].mean(), df_m['longitud'].mean()], zoom_start=12)
                cluster = MarkerCluster().add_to(m)
                
                for _, fila in df_m.iterrows():
                    # Definimos val_a para que no de error
                    val_a = formatear_valor(fila.get('linea a', 'N/A'))
                    
                    # Generar tabla HTML idéntica al ejemplo del usuario
                    html_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px;'>"
                    html_table += "<tr style='background-color: #333; color: white;'><th>CAMPO</th><th>VALOR</th></tr>"
                    
                    for col in df_m.columns:
                        if col not in ['hora_num', 'lat_r', 'lon_r']:
                            val_celda = formatear_valor(fila[col])
                            html_table += f"<tr style='border-bottom: 1px solid #ddd;'><td style='padding: 3px; font-weight: bold;'>{col.upper()}</td><td style='padding: 3px;'>{val_celda}</td></tr>"
                    html_table += "</table>"
                    
                    folium.CircleMarker(
                        location=[fila['latitud'], fila['longitud']],
                        radius=8,
                        color='black',
                        fill=True,
                        fill_color='#ff0000',
                        fill_opacity=0.8,
                        popup=folium.Popup(html_table, max_width=300),
                        name=f"Línea A: {val_a}"
                    ).add_to(cluster)
                
                Search(layer=cluster, geom_type="Point", placeholder="Buscar en el mapa...", collapsed=False, search_label="name").add_to(m)
                st_folium(m, width="100%", height=600, key="mapa_final")
                st.download_button("📥 DESCARGAR MAPA HTML", data=m._repr_html_(), file_name="mapa_analisis.html", mime="text/html")
            else:
                st.warning("Sin datos geográficos válidos.")
        else:
            st.info("Sin registros para este filtro.")

    except Exception as e:
        st.error(f"Error crítico detectado: {e}")

st.sidebar.caption("MENU DE ANALISIS")
