
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import io
import os
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(
    page_title="INTEL - FORENSIC SYSTEM",
    layout="wide",
    page_icon="🛰️"
)

# =========================
# UI HACKER / POLICIAL
# =========================
st.markdown("""
<style>
.stApp {
    background-color: #05070a;
    color: #00ff88;
    font-family: "Courier New", monospace;
}
h1 {
    color: #00ff88 !important;
    text-align: left;
    letter-spacing: 3px;
    text-transform: uppercase;
    text-shadow: 0 0 10px #00ff88;
    margin-top: 10px;
}
.stButton>button {
    background: transparent;
    border: 1px solid #00ff88;
    color: #00ff88;
    width: 100%;
    font-weight: bold;
}
.stButton>button:hover {
    background: #00ff88;
    color: #000;
}
.stDataFrame {
    border: 1px solid #00ff88;
}
.credito-firma {
    color: #00ff88;
    font-weight: bold;
    text-shadow: 0 0 5px #00ff88;
    letter-spacing: 2px;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCIONES
# =========================
def formatear_valor(valor):
    str_valor = str(valor)
    if '.0' in str_valor and len(str_valor) > 5:
        return str_valor.split('.')[0]
    return str_valor

def estandarizar_df(df_temp):
    df_temp.columns = [str(c).strip().lower() for c in df_temp.columns]

    mapping = {
        'linea a': ['linea_a', 'linea a', 'origen', 'numero_llamante', 'msisdn_a', 'abonado'],
        'linea b': ['linea_b', 'linea b', 'destino', 'numero_marcado', 'msisdn_b', 'interlocutor'],
        'latitud': ['latitud', 'lat', 'latitude'],
        'longitud': ['longitud', 'lon', 'longitude'],
        'hora': ['hora', 'time'],
        'fecha': ['fecha', 'date'],
        'tipo': ['tipo', 'type', 'evento', 'tipo_evento', 'tipo_comunicacion']
    }

    for col_estandar, variantes in mapping.items():
        for var in variantes:
            if var in df_temp.columns:
                df_temp.rename(columns={var: col_estandar}, inplace=True)
                break

    for col in df_temp.columns:
        if 'linea' in col or 'imei' in col or 'imsi' in col:
            df_temp[col] = df_temp[col].apply(formatear_valor).replace('nan', 'DESCONOCIDO')

    if 'latitud' in df_temp.columns and 'longitud' in df_temp.columns:
        df_temp['latitud'] = pd.to_numeric(df_temp['latitud'], errors='coerce')
        df_temp['longitud'] = pd.to_numeric(df_temp['longitud'], errors='coerce')

    if 'fecha' in df_temp.columns:
        df_temp['fecha_dt'] = pd.to_datetime(df_temp['fecha'], errors='coerce')
        df_temp['fecha'] = df_temp['fecha_dt'].dt.strftime('%Y-%m-%d')

    return df_temp

def ordenar_por_frecuencia_interacciones(df_target):
    if 'linea a' not in df_target.columns or 'linea b' not in df_target.columns:
        return df_target

    columnas_limpias = [c for c in df_target.columns if c != 'fecha_dt']
    df_trabajo = df_target[columnas_limpias].copy()

    todo_junto = pd.concat([df_trabajo['linea a'], df_trabajo['linea b']])
    numero_sabana = todo_junto.value_counts().idxmax()

    df_trabajo['interlocutor_externo'] = df_trabajo.apply(
        lambda r: r['linea b'] if str(r['linea a']) == str(numero_sabana) else r['linea a'], axis=1
    )

    df_agrupado = df_trabajo.groupby('interlocutor_externo').agg(
        total_interacciones=('interlocutor_externo', 'count'),
        ultima_fecha=('fecha', 'max'),
        ultima_hora=('hora', 'max'),
        ultima_latitud=('latitud', 'last'),
        ultima_longitud=('longitud', 'last')
    ).reset_index()

    df_resumen = df_agrupado.sort_values(by='total_interacciones', ascending=False).copy()
    df_resumen.rename(columns={'interlocutor_externo': 'telefono_objetivo'}, inplace=True)
    
    columnas_finales = ['total_interacciones', 'telefono_objetivo', 'ultima_fecha', 'ultima_hora', 'ultima_latitud', 'ultima_longitud']
    return df_resumen[columnas_finales]

def generar_html_popup_comparativo(reg_base, reg_espejo, tipo_alerta, titulo_alerta):
    color_banner = "#28a745" 
    if tipo_alerta == "CRUCIAL":
        color_banner = "#dc3545" 
    elif tipo_alerta == "ALERTA":
        color_banner = "#ffc107" 

    text_color = '#fff' if tipo_alerta != 'ALERTA' else '#000'

    html = f"""
    <div style="font-family: monospace; min-width: 410px; color: #000; font-size: 11px;">
        <div style="background-color: {color_banner}; color: {text_color}; padding: 6px; text-align: center; font-weight: bold; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
            {titulo_alerta}
        </div>
    """

    if reg_espejo is not None:
        html += f"""
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1; background: #f8f9fa; padding: 6px; border-radius: 4px; border-left: 3px solid #00ff88;">
                <b style="color: #111;">📄 ALFA (S1)</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                <b>F:</b> {reg_base.get('fecha', 'N/A')}<br>
                <b>H:</b> {reg_base.get('hora', 'N/A')}<br>
                <b>TIPO:</b> {reg_base.get('tipo', 'N/A')}<br>
                <b>A:</b> {reg_base.get('linea a', 'N/A')}<br>
                <b>B:</b> {reg_base.get('linea b', 'N/A')}<br>
                <b>GEO:</b> {reg_base.get('latitud', 'N/A')}, {reg_base.get('longitud', 'N/A')}<br>
            </div>
            <div style="flex: 1; background: #fdf3f3; padding: 6px; border-radius: 4px; border-left: 3px solid {color_banner};">
                <b style="color: #111;">📑 BRAVO (S2)</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                <b>F:</b> {reg_espejo.get('fecha', 'N/A')}<br>
                <b>H:</b> {reg_espejo.get('hora', 'N/A')}<br>
                <b>TIPO:</b> {reg_espejo.get('tipo', 'N/A')}<br>
                <b>A:</b> {reg_espejo.get('linea a', 'N/A')}<br>
                <b>B:</b> {reg_espejo.get('linea b', 'N/A')}<br>
                <b>GEO:</b> {reg_espejo.get('latitud', 'N/A')}, {reg_espejo.get('longitud', 'N/A')}<br>
            </div>
        </div>
        """
    else:
        html += f"""
        <div style="background: #f8f9fa; padding: 8px; border-radius: 4px;">
            <b>Fecha:</b> {reg_base.get('fecha', 'N/A')}<br>
            <b>Hora:</b> {reg_base.get('hora', 'N/A')}<br>
            <b>Tipo:</b> {reg_base.get('tipo', 'N/A')}<br>
            <b>Línea A:</b> {reg_base.get('linea a', 'N/A')}<br>
            <b>Línea B:</b> {reg_base.get('linea b', 'N/A')}<br>
            <b>Coordenadas:</b> {reg_base.get('latitud', 'N/A')}, {reg_base.get('longitud', 'N/A')}
        </div>
        """
        
    html += "</div>"
    return html

def aplicar_marca_agua_mapa(objeto_mapa, texto_firma):
    codigo_marca_agua = f"""
    <div style="
        position: fixed; 
        bottom: 50px; 
        left: 20px; 
        width: auto; 
        height: auto; 
        z-index: 9999; 
        font-family: 'Courier New', monospace;
        color: rgba(0, 0, 0, 0.25); 
        font-weight: bold; 
        font-size: 26px; 
        letter-spacing: 3px;
        white-space: nowrap;
        pointer-events: none;
        user-select: none;
        transform: rotate(-15deg);
        background: rgba(255, 255, 255, 0.5);
        padding: 5px 15px;
        border: 2px dashed rgba(0, 0, 0, 0.15);
        border-radius: 5px;
    ">
        {texto_firma}
    </div>
    """
    objeto_mapa.get_root().html.add_child(folium.Element(codigo_marca_agua))

# =========================
# CONTROL DE ESTADO
# =========================
if "opcion_activa" not in st.session_state:
    st.session_state.opcion_activa = "Vista General"

# =========================
# CABECERA SUPERIOR CON LOGO
# =========================
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    # Esta es la línea crucial que debes actualizar:
    ruta_imagen = os.path.join(dir_actual, "logotipo.png") 
    
    if os.path.exists(ruta_imagen):
        st.image(ruta_imagen, use_container_width=True)
    else:
        st.error("⚠️ Falta el archivo 'logotipo.png' en la carpeta sabana1")

with col_titulo:
    st.title("🛰️ INTEL FORENSIC ANALYSIS SYSTEM")
    st.caption("CENTRO DE ANÁLISIS GEO-TELEFÓNICO | NIVEL CLASIFICADO")
# =========================
# PANEL DE CONTROL
# =========================
st.markdown("### ⚙️ PANEL DE CONTROL")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("📡 GENERAL"): st.session_state.opcion_activa = "Vista General"
with c2:
    if st.button("🌙 PERNOCTA"): st.session_state.opcion_activa = "Pernocta (Personalizada)"
with c3:
    if st.button("🔎 NÚMERO"): st.session_state.opcion_activa = "Búsqueda por Número"
with c4:
    if st.button("📡 ANTENAS"): st.session_state.opcion_activa = "Top Antenas"
with c5:
    if st.button("🧩 CRUCE"): st.session_state.opcion_activa = "Cruce de Sábanas"

st.info(f"MODO ACTIVO: {st.session_state.opcion_activa}")
st.write("---")

uploaded_file = st.file_uploader("📂 CARGAR EXPEDIENTE TELEFÓNICO PRINCIPAL", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df_base = estandarizar_df(pd.read_excel(uploaded_file))
        
        if "df_ejecutado" not in st.session_state:
            st.session_state.df_ejecutado = df_base.copy()
            st.session_state.ejecutar_cruce_inteligente = False
            st.session_state.df_cruce_ref = None

        # Contenedor visual del Buscador Temporal
        if 'fecha_dt' in df_base.columns and not df_base['fecha_dt'].isna().all():
            st.markdown("### 📅 BUSCADOR POR RANGO TEMPORAL")
            
            min_fecha = df_base['fecha_dt'].min().date()
            max_fecha = df_base['fecha_dt'].max().date()
            
            c_cal, c_btn1, c_btn2 = st.columns([2, 1, 1])
            
            with c_cal:
                rango_seleccionado = st.date_input(
                    "Seleccione el periodo objetivo a graficar en el mapa:",
                    value=(min_fecha, max_fecha),
                    min_value=min_fecha,
                    max_value=max_fecha,
                    key="buscador_fechas_global"
                )
            
            with c_btn1:
                st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                btn_buscar = st.button("⚡ FILTRAR EXPEDIENTE")
                
            with c_btn2:
                st.markdown("<div style='padding-top:28px;'></div>", unsafe_allow_html=True)
                btn_limpiar = st.button("🔄 LIMPIAR FILTRO")

            # ACCIÓN DEL BOTÓN FILTRAR
            if btn_buscar:
                df_trabajo = df_base.copy()
                if isinstance(rango_seleccionado, tuple) and len(rango_seleccionado) == 2:
                    f_inicio, f_fin = rango_seleccionado
                    df_trabajo = df_trabajo[
                        (df_trabajo['fecha_dt'].dt.date >= f_inicio) & 
                        (df_trabajo['fecha_dt'].dt.date <= f_fin)
                    ]
                
                if st.session_state.opcion_activa == "Pernocta (Personalizada)":
                    df_trabajo['hora_num'] = pd.to_datetime(df_trabajo['hora'].astype(str), errors='coerce').dt.hour
                    df_trabajo = df_trabajo[(df_trabajo['hora_num'] >= 22) | (df_trabajo['hora_num'] <= 7)]

                st.session_state.df_ejecutado = df_trabajo

            # ACCIÓN DEL BOTÓN LIMPIAR (RESTAURAR)
            if btn_limpiar:
                st.session_state.df_ejecutado = df_base.copy()
                st.session_state.ejecutar_cruce_inteligente = False
                st.session_state.df_cruce_ref = None
                st.rerun()

        if st.session_state.opcion_activa == "Búsqueda por Número":
            num = st.text_input("🔎 NÚMERO OBJETIVO (Escriba y presione Enter)")
            if num:
                st.session_state.df_ejecutado = st.session_state.df_ejecutado[
                    st.session_state.df_ejecutado['linea a'].astype(str).str.contains(num) |
                    st.session_state.df_ejecutado['linea b'].astype(str).str.contains(num)
                ]

        elif st.session_state.opcion_activa == "Cruce de Sábanas":
            st.markdown("### 🧩 INTEL CROSS ANALYSIS")
            tipo = st.selectbox("Modo", ["Números", "Ubicación Inteligente"])
            file2 = st.file_uploader("📂 SEGUNDA SÁBANA", type=["xlsx", "xls"])

            if file2:
                df2 = estandarizar_df(pd.read_excel(file2))
                if tipo == "Números":
                    n1 = set(st.session_state.df_ejecutado['linea a']) | set(st.session_state.df_ejecutado['linea b'])
                    n2 = set(df2['linea a']) | set(df2['linea b'])
                    comunes = n1.intersection(n2)
                    st.session_state.df_ejecutado = st.session_state.df_ejecutado[
                        st.session_state.df_ejecutado['linea a'].isin(comunes) | 
                        st.session_state.df_ejecutado['linea b'].isin(comunes)
                    ]
                elif tipo == "Ubicación Inteligente":
                    st.session_state.ejecutar_cruce_inteligente = True
                    st.session_state.df_cruce_ref = df2

        # =========================
        # DESPLIEGUE DE RESULTADOS
        # =========================
        df_render = st.session_state.df_ejecutado

        if not df_render.empty:
            st.subheader("📊 RESULTADOS DETECTADOS EN EL RANGO")
            st.caption("🔒 PROPIEDAD INTELECTUAL CLASIFICADA | PROPÓSITO FORENSE EXCLUSIVO - AUTOR: J-I-A-M")
            
            df_tabla_final = df_render.copy()
            if 'fecha_dt' in df_tabla_final.columns:
                df_tabla_final.drop(columns=['fecha_dt'], inplace=True)

            if st.session_state.opcion_activa != "Top Antenas":
                df_resultados_vista = ordenar_por_frecuencia_interacciones(df_tabla_final)
            else:
                df_antenas_clean = df_tabla_final.dropna(subset=['latitud', 'longitud'])
                df_antenas_clean = df_antenas_clean[(df_antenas_clean['latitud'] != 0) & (df_antenas_clean['longitud'] != 0)]
                df_resultados_vista = df_antenas_clean.groupby(['latitud', 'longitud']).size().reset_index(name='hits').sort_values('hits', ascending=False).head(15)

            st.dataframe(df_resultados_vista, use_container_width=True)

            st.subheader("🗺️ MAPA TÁCTICO DEL PERIODO FILTRADO")

            df_m = df_render.dropna(subset=['latitud', 'longitud']).copy()
            if not df_m.empty:
                df_m = df_m[(df_m['latitud'] != 0) & (df_m['longitud'] != 0)]

            if not df_m.empty:
                st.success(f"🌐 Rango Acotado Sincronizado: Mapeando {len(df_m)} coordenadas correspondientes al filtro ejecutado.")

                if st.session_state.ejecutar_cruce_inteligente and st.session_state.df_cruce_ref is not None:
                    st.markdown("""
                    <div style="background-color: #0b1119; padding: 12px; border: 1px solid #00ff88; border-radius: 4px; margin-bottom: 15px;">
                        <span style="color:#00ff88; font-weight:bold; font-size:14px;">📋 LEYENDA ANALÍTICA DE CRUCE (SÁBANA 1 vs SÁBANA 2):</span><br>
                        <span style="color:#ff4d4d; font-weight:bold;">● ROJO:</span> Coincidencia espacio-temporal crítica. <b>Mismo lugar el mismo día</b>.<br>
                        <span style="color:#ffaa00; font-weight:bold;">● AMARILLO:</span> Coincidencia de interés de recurrencia. <b>Mismo lugar pero diferente día</b>.<br>
                        <span style="color:#00ff88; font-weight:bold;">● VERDE:</span> Registro estándar de la Sábana Principal.
                    </div>
                    """, unsafe_allow_html=True)

                m = folium.Map(
                    location=[df_m['latitud'].mean(), df_m['longitud'].mean()],
                    zoom_start=11,
                    tiles="OpenStreetMap"
                )

                cluster = MarkerCluster(disableClusteringAtZoom=17, maxClusterRadius=50).add_to(m)

                for _, r in df_m.iterrows():
                    color_punto = "#00ff88"  
                    tipo_alerta = "BASE"
                    titulo_alerta = "REGISTRO TELEFÓNICO"
                    reg_espejo_dict = None

                    if st.session_state.ejecutar_cruce_inteligente and st.session_state.df_cruce_ref is not None:
                        coincidencias_geo = st.session_state.df_cruce_ref[
                            (st.session_state.df_cruce_ref['latitud'] == r['latitud']) & 
                            (st.session_state.df_cruce_ref['longitud'] == r['longitud'])
                        ]
                        if not coincidencias_geo.empty:
                            mismo_dia = coincidencias_geo[coincidencias_geo['fecha'] == r['fecha']]
                            if not mismo_dia.empty:
                                color_punto = "red"
                                tipo_alerta = "CRUCIAL"
                                titulo_alerta = "💥 CRUCE: MISMO LUGAR/DÍA"
                                reg_espejo_dict = mismo_dia.iloc[0].to_dict()
                            else:
                                color_punto = "orange"
                                tipo_alerta = "ALERTA"
                                titulo_alerta = "⏳ CRUCE: MISMO LUGAR/DIF. DÍA"
                                reg_espejo_dict = coincidencias_geo.iloc[0].to_dict()

                    popup_html = generar_html_popup_comparativo(r.to_dict(), reg_espejo_dict, tipo_alerta, titulo_alerta)
                    
                    iframe = folium.IFrame(popup_html, width=420, height=175)
                    popup_obj = folium.Popup(iframe, parse_html=True)

                    folium.CircleMarker(
                        location=[r['latitud'], r['longitud']],
                        radius=5,
                        color=color_punto,
                        fill=True,
                        fill_opacity=0.7,
                        popup=popup_obj
                    ).add_to(cluster)

                aplicar_marca_agua_mapa(m, "PROP. J-I-A-M / FORENSIC SYSTEM")

                st_folium(
                    m, 
                    width="100%", 
                    height=650, 
                    key=f"mapa_completo_{st.session_state.opcion_activa}_{len(df_m)}",
                    returned_objects=[] 
                )

                col_down, col_firma = st.columns([1, 1])
                with col_down:
                    st.download_button(
                        label="📥 DESCARGAR MAPA HTML EN PERIODO SELECCIONADO",
                        data=m._repr_html_(),
                        file_name=f"MAPA_FILTRADO_{st.session_state.opcion_activa.upper()}.html",
                        mime="text/html"
                    )
                with col_firma:
                    st.markdown("<p class='credito-firma' style='text-align: right;'>CREADO POR: J-I-A-M</p>", unsafe_allow_html=True)
            else:
                st.warning("⚠️ No quedan coordenadas válidas en este periodo tras la limpieza.")
        else:
            st.warning("Sin registros disponibles. Seleccione un rango válido y presione '⚡ FILTRAR EXPEDIENTE'.")

    except Exception as e:
        st.error(f"ERROR DE SISTEMA: {e}")

st.markdown("---")
st.caption("INTEL FORENSIC SYSTEM • UI MODE: COMMAND CENTER")
