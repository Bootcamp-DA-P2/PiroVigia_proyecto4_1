import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import requests
from io import StringIO
import datetime
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

st.set_page_config(
    page_title="PiroVigía Pro v4.5 | Real-Time Live Intelligence",
    page_icon="🛰️",
    layout="wide"
)

# --- CARGA DEL NÚCLEO IA ---
@st.cache_resource
def cargar_sistema_ia():
    try:
        modelo = joblib.load("clasificador_tipos_smote.pkl")
        scaler = joblib.load("escalador_features.pkl")
        return modelo, scaler
    except Exception as e:
        return None, None

modelo_cls, scaler_cls = cargar_sistema_ia()
MAPEO_INVERSO = {0: '🔥 Incendio forestal / Vegetación', 1: '🏭 Industria / Foco estático', 2: '❓ Otros', 3: '🌋 Actividad Volcánica'}
colores_sistema = {'Incendio Forestal': '#E63946', 'Zona Industrial': '#1D3557', 'Volcán': '#F4A261', 'Otros': '#E9C46A'}

# --- FUNCIÓN DE DESCARGA EN TIEMPO REAL (NASA FIRMS) ---
@st.cache_data(ttl=3600)  # Guarda en caché un máximo de 1 hora para refrescar datos vivos
def descargar_datos_tiempo_real_espana(api_key=""):
    """
    Descarga los focos activos de las últimas 24h a nivel global y filtra por España.
    Si tienes un token de la NASA FIRMS lo puedes poner, si no, usa la zona abierta de la URL.
    """
    # Usamos la URL de datos de texto libre de FIRMS para el satélite MODIS (últimas 24 horas)
    # Nota: Si dispones de un MAPS_KEY propio de la NASA FIRMS, puedes cambiar la URL a su endpoint oficial por países.
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"
    
    try:
        respuesta = requests.get(url, timeout=10)
        if respuesta.status_code == 200:
            df_rt = pd.read_csv(StringIO(respuesta.text))
            
            # Bounding Box aproximado de España (incluyendo Península, Baleares y Canarias)
            lat_min, lat_max = 27.5, 44.0
            lon_min, lon_max = -18.5, 4.5
            
            df_espana = df_rt[
                (df_rt['latitude'] >= lat_min) & (df_rt['latitude'] <= lat_max) &
                (df_rt['longitude'] >= lon_min) & (df_rt['longitude'] <= lon_max)
            ].copy()
            
            if df_espana.empty:
                return pd.DataFrame() # Devuelve vacío si no hay alertas hoy en España
                
            # Homologación de columnas para que coincida con tu pipeline y modelo de IA
            df_espana['acq_date'] = pd.to_datetime(df_espana['acq_date'])
            df_espana['Mes'] = df_espana['acq_date'].dt.strftime('%B')
            df_espana['Mes_Num'] = df_espana['acq_date'].dt.month
            df_espana['Horario'] = df_espana['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
            
            # Si el modelo de IA está cargado, clasificamos dinámicamente el tiempo real
            if modelo_cls is not None and scaler_cls is not None:
                dn_num = np.where(df_espana['daynight'].astype(str).str.strip().str.upper() == 'N', 1, 0)
                X_pred = pd.DataFrame({
                    'latitude': df_espana['latitude'].astype(float),
                    'longitude': df_espana['longitude'].astype(float),
                    'brightness': df_espana['brightness'].astype(float),
                    'bright_t31': df_espana['bright_t31'].astype(float),
                    'frp': df_espana['frp'].astype(float),
                    'confidence': df_espana['confidence'].astype(float),
                    'daynight_num': dn_num
                }).fillna(0.0)
                
                X_scaled = scaler_cls.transform(X_pred)
                df_espana['clase_predicha_num'] = modelo_cls.predict(X_scaled)
                
                mapeo_nombres = {0: 'Incendio Forestal', 1: 'Zona Industrial', 2: 'Otros', 3: 'Volcán'}
                df_espana['Origen'] = df_espana['clase_predicha_num'].map(mapeo_nombres)
            else:
                # Fallback si no hay modelo entrenado a mano
                df_espana['Origen'] = 'Incendio Forestal'
                
            return df_espana
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- CARGA DEL DATASET HISTÓRICO LOCAL ---
@st.cache_data
def cargar_dataset_maestro():
    try:
        df = pd.read_csv("data/modis_2024_unificado_limpio.csv")
        df['acq_date'] = pd.to_datetime(df['acq_date'])
        df['Mes'] = df['acq_date'].dt.strftime('%B')
        df['Mes_Num'] = df['acq_date'].dt.month
        mapeo_limpieza = {
            'Incendio forestal/vegetación': 'Incendio Forestal', 'Incendio Forestal': 'Incendio Forestal',
            'Industria/Foco estático': 'Zona Industrial', 'Zona Industrial': 'Zona Industrial',
            'Volcán': 'Volcán', 'Otros/Fuera de rango': 'Otros', 'Otros / Fuera de rango': 'Otros'
        }
        df['Origen'] = df['type'].map(mapeo_limpieza).fillna('Otros')
        df['Horario'] = df['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
        return df
    except:
        # Dataframe vacío de emergencia si no encuentra el archivo local
        return pd.DataFrame(columns=['acq_date', 'latitude', 'longitude', 'brightness', 'bright_t31', 'frp', 'confidence', 'Origen', 'Horario', 'Mes', 'Mes_Num'])

# --- BARRA LATERAL: CONTROL DE ORIGEN DE DATOS ---
st.sidebar.title("🛰️ PiroVigía Live v4.5")
st.sidebar.markdown("*Consola Avanzada con Conexión Satelital NASA*")
st.sidebar.markdown("---")

modo_datos = st.sidebar.radio(
    "🚨 Selecciona el Modo de Datos:",
    ["📊 Archivo Histórico Local", "🔴 Vigilancia en Tiempo Real (España Live)"]
)

if modo_datos == "🔴 Vigilancia en Tiempo Real (España Live)":
    st.sidebar.info("Conectando con servidores satelitales de la NASA FIRMS... Buscando anomalías en España en las últimas 24 horas.")
    df_completo = descargar_datos_tiempo_real_espana()
    
    if df_completo.empty:
        st.sidebar.warning("No se detectaron anomalías térmicas críticas en España en las últimas 24h o los servidores externos están saturados. Cargando histórico por seguridad.")
        df_completo = cargar_dataset_maestro()
        modo_datos = "📊 Archivo Histórico Local"
else:
    df_completo = cargar_dataset_maestro()

# --- FILTROS COMUNES EN SIDEBAR ---
if not df_completo.empty:
    fecha_min, fecha_max = df_completo['acq_date'].min().to_pydatetime(), df_completo['acq_date'].max().to_pydatetime()
    
    # Solo mostramos rango de fechas completo si es histórico
    if modo_datos == "📊 Archivo Histórico Local":
        rango_fechas = st.sidebar.date_input("Periodo de Observación", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
    else:
        st.sidebar.caption(f"📅 Monitorizando ventana activa: {fecha_min.strftime('%d/%m/%Y')} al {fecha_max.strftime('%d/%m/%Y')}")
        rango_fechas = (fecha_min, fecha_max)
        
    confianza_min = st.sidebar.slider("Filtro de Confianza MODIS (%)", 0, 100, 30)
    frp_max_entero = int(np.ceil(df_completo['frp'].max())) if len(df_completo) > 0 else 100
    rango_frp = st.sidebar.slider("Potencia Radiativa (FRP - MW)", 0, max(frp_max_entero, 10), (0, max(frp_max_entero // 2, 5)))

    # Aplicación de filtros
    if len(rango_fechas) == 2:
        f_in, f_fi = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
        mask = (df_completo['acq_date'] >= f_in) & (df_completo['acq_date'] <= f_fi) & \
               (df_completo['confidence'] >= confianza_min) & (df_completo['frp'] >= rango_frp[0]) & (df_completo['frp'] <= rango_frp[1])
        df_filtrado = df_completo[mask]
    else:
        df_filtrado = df_completo[(df_completo['confidence'] >= confianza_min) & (df_completo['frp'] >= rango_frp[0]) & (df_completo['frp'] <= rango_frp[1])]
else:
    df_filtrado = pd.DataFrame()

# --- AUDITORÍA MANUAL UNITARIA ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔮 Auditoría Unitaria Inteligente")
with st.sidebar.form("formulario_ia"):
    lat_in = st.number_input("Latitud Objetivo", value=40.41, format="%.5f") # Por defecto Madrid
    lon_in = st.number_input("Longitud Objetivo", value=-3.70, format="%.5f")
    bright_in = st.number_input("Canal Térmico 21 (K)", value=318.0)
    t31_in = st.number_input("Canal Térmico 31 (K)", value=298.0)
    frp_in = st.number_input("Energía FRP Estimada (MW)", value=35.0)
    conf_in = st.slider("Confianza de Entrada", 0, 100, 85)
    dn_in = st.selectbox("Momento del Día", ["Día", "Noche"])
    boton_prediccion = st.form_submit_button("Consultar Núcleo IA")

# --- CONSOLA PRINCIPAL ---
st.title("🛰️ Ecosistema Analítico PiroVigía Pro v4.5")
if modo_datos == "🔴 Vigilancia en Tiempo Real (España Live)":
    st.subheader("🔴 CONEXIÓN EN DIRECTO: Vigilancia Activa del Territorio Español")
else:
    st.subheader("📊 MODO ANÁLISIS: Consulta de Base de Datos Histórica")

# Métricas Kpi
k1, k2, k3, k4 = st.columns(4)
alertas_activas = len(df_filtrado)
frp_promedio = df_filtrado['frp'].mean() if alertas_activas > 0 else 0.0
max_termico = df_filtrado['brightness'].max() if alertas_activas > 0 else 0.0
focos_forestales = len(df_filtrado[df_filtrado['Origen'] == 'Incendio Forestal']) if alertas_activas > 0 else 0
ratio_riesgo = (focos_forestales / max(alertas_activas, 1) * 100) if alertas_activas > 0 else 0.0

with k1: st.metric("Anomalías Activas", f"{alertas_activas:,}")
with k2: st.metric("Potencia FRP Promedio", f"{frp_promedio:.1f} MW")
with k3: st.metric("Máximo Térmico Detectado", f"{max_termico:.1f} K")
with k4: st.metric("Índice de Riesgo Forestal", f"{ratio_riesgo:.1f}%")

st.markdown("---")

if alertas_activas > 0:
    # Pestañas operativas
    tab_mapa, tab_temporal, tab_fisica, tab_datos = st.tabs([
        "🗺️ Centro de Despliegue Geográfico", 
        "📅 Evolución y Tendencias Temporales", 
        "🔬 Correlaciones y Física de Datos", 
        "📋 Registro Crítico y Control IA"
    ])

    with tab_mapa:
        st.subheader("Despliegue Geoespacial de Focos Detectados")
        df_mapa = df_filtrado.copy()
        df_mapa['color_mapa'] = df_mapa['Origen'].map(colores_sistema).fillna('#E63946')
        # El mapa centrará automáticamente la vista según las detecciones encontradas en España
        st.map(df_mapa, latitude='latitude', longitude='longitude', size='frp', color='color_mapa')

    with tab_temporal:
        st.subheader("Análisis de Tendencias Chrono-Satelitales")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            if modo_datos == "📊 Archivo Histórico Local":
                df_mes = df_filtrado.groupby(['Mes_Num', 'Mes', 'Origen']).size().reset_index(name='Detecciones').sort_values('Mes_Num')
                fig_mes = px.line(df_mes, x='Mes', y='Detecciones', color='Origen', title="Historial Estacional de Alertas", color_discrete_map=colores_sistema, markers=True)
                st.plotly_chart(fig_mes, use_container_width=True)
            else:
                df_horas = df_filtrado.copy()
                df_horas['Hora'] = df_horas['acq_date'].dt.hour
                fig_horas = px.histogram(df_horas, x='Hora', color='Origen', title="Detecciones hoy por tramo horario", barmode='stack', color_discrete_map=colores_sistema)
                st.plotly_chart(fig_horas, use_container_width=True)
        with t_col2:
            fig_dn = px.histogram(df_filtrado, x='Origen', color='Horario', title="Distribución por Ciclo Solar", barmode='group', color_discrete_sequence=['#E9C46A', '#457B9D'])
            st.plotly_chart(fig_dn, use_container_width=True)

    with tab_fisica:
        st.subheader("Física Cuantitativa y Firmas Térmicas")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            fig_box = px.box(df_filtrado, x='Origen', y='brightness', color='Origen', title="Rangos de Temperatura de Brillo (K)", color_discrete_map=colores_sistema)
            st.plotly_chart(fig_box, use_container_width=True)
        with f_col2:
            fig_disp = px.scatter(df_filtrado, x='brightness', y='frp', color='Origen', size='confidence', title="Temperatura vs Potencia FRP", color_discrete_map=colores_sistema, opacity=0.7)
            st.plotly_chart(fig_disp, use_container_width=True)

    with tab_datos:
        st.subheader("Consola de Extracción y Logs Críticos")
        top_criticos = df_filtrado.sort_values(by='frp', ascending=False).head(15)[['acq_date', 'latitude', 'longitude', 'brightness', 'frp', 'confidence', 'Origen', 'Horario']]
        top_criticos.columns = ['Fecha / Registro', 'Latitud', 'Longitud', 'Brillo (K)', 'FRP (MW)', 'Confianza (%)', 'Clasificación IA', 'Horario']
        st.dataframe(top_criticos, use_container_width=True, hide_index=True)
else:
    st.warning("Ningún punto caliente cumple con las condiciones actuales de los filtros aplicados.")

# Ejecución del predictor manual aislado
if boton_prediccion and modelo_cls is not None:
    dn_num = 1 if dn_in == "Noche" else 0
    datos_entrada = pd.DataFrame([{'latitude': lat_in, 'longitude': lon_in, 'brightness': bright_in, 'bright_t31': t31_in, 'frp': frp_in, 'confidence': conf_in, 'daynight_num': dn_num}])
    clase_id = int(modelo_cls.predict(scaler_cls.transform(datos_entrada))[0])
    probabilidades = modelo_cls.predict_proba(scaler_cls.transform(datos_entrada))[0]
    st.sidebar.success(f"### **Resultado IA:**\n{MAPEO_INVERSO.get(clase_id)}\n\n**Certeza:** {probabilidades[clase_id]*100:.2f}%")