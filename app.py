import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

st.set_page_config(
    page_title="PiroVigía Pro v3.0 | Enterprise Thermal Intelligence",
    page_icon="🛰️",
    layout="wide"
)

@st.cache_resource
def cargar_sistema_ia():
    try:
        modelo = joblib.load("clasificador_tipos_smote.pkl")
        scaler = joblib.load("escalador_features.pkl")
        return modelo, scaler
    except:
        return None, None

@st.cache_data
def cargar_dataset_maestro():
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

df_completo = cargar_dataset_maestro()
modelo_cls, scaler_cls = cargar_sistema_ia()
MAPEO_INVERSO = {0: '🔥 Incendio forestal / Vegetación', 1: '🏭 Industria / Foco estático', 2: '❓ Otros', 3: '🌋 Actividad Volcánica'}
colores_sistema = {'Incendio Forestal': '#E63946', 'Zona Industrial': '#1D3557', 'Volcán': '#F4A261', 'Otros': '#E9C46A'}

st.sidebar.title("🛰️ PiroVigía Ecosistema v3.0")
st.sidebar.markdown("*Consola Definitiva de Inteligencia Térmica Satelital*")
st.sidebar.markdown("---")

fecha_min, fecha_max = df_completo['acq_date'].min().to_pydatetime(), df_completo['acq_date'].max().to_pydatetime()
rango_fechas = st.sidebar.date_input("Periodo de Observación", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
confianza_min = st.sidebar.slider("Filtro de Confianza MODIS (%)", 0, 100, 30)
frp_max_entero = int(np.ceil(df_completo['frp'].max()))
rango_frp = st.sidebar.slider("Potencia Radiativa Comercial (FRP - MW)", 0, frp_max_entero, (0, frp_max_entero // 3))

if len(rango_fechas) == 2:
    f_in, f_fi = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
    mask = (df_completo['acq_date'] >= f_in) & (df_completo['acq_date'] <= f_fi) & \
           (df_completo['confidence'] >= confianza_min) & (df_completo['frp'] >= rango_frp[0]) & (df_completo['frp'] <= rango_frp[1])
    df_filtrado = df_completo[mask]
else:
    df_filtrado = df_completo[(df_completo['confidence'] >= confianza_min) & (df_completo['frp'] >= rango_frp[0]) & (df_completo['frp'] <= rango_frp[1])]

st.sidebar.markdown("---")
st.sidebar.subheader("🔮 Auditoría Unitaria Inteligente")
with st.sidebar.form("formulario_ia"):
    lat_in = st.number_input("Latitud Objetivo", value=-33.45, format="%.5f")
    lon_in = st.number_input("Longitud Objetivo", value=-70.66, format="%.5f")
    bright_in = st.number_input("Canal Térmico 21 (K)", value=315.0)
    t31_in = st.number_input("Canal Térmico 31 (K)", value=295.0)
    frp_in = st.number_input("Energía FRP Estimada (MW)", value=20.0)
    conf_in = st.slider("Confianza de Entrada", 0, 100, 80)
    dn_in = st.selectbox("Momento del Día", ["Día", "Noche"])
    boton_prediccion = st.form_submit_button("Consultar Núcleo IA")

st.title("🛰️ Ecosistema Analítico PiroVigía Pro")
k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("Anomalías Térmicas Activas", f"{len(df_filtrado):,}")
with k2: st.metric("Potencia FRP Promedio", f"{df_filtrado['frp'].mean():.1f} MW")
with k3: st.metric("Máximo Térmico Detectado", f"{df_filtrado['brightness'].max():.1f} K")
with k4: st.metric("Índice de Riesgo Forestal", f"{(len(df_filtrado[df_filtrado['Origen'] == 'Incendio Forestal']) / max(len(df_filtrado), 1) * 100):.1f}%")

st.markdown("---")

# 🏛️ PESTAÑAS NAVEGABLES NATIVAS (Secreto de la interfaz Pro)
tab_mapa, tab_temporal, tab_fisica, tab_datos = st.tabs([
    "🗺️ Centro de Despliegue Geográfico", 
    "📅 Evolución y Tendencias Temporales", 
    "🔬 Correlaciones y Física de Datos", 
    "📋 Registro Crítico y Control IA"
])

with tab_mapa:
    st.subheader("Despliegue Geoespacial de Focos Detectados")
    df_mapa = df_filtrado.sample(min(len(df_filtrado), 6000), random_state=42)
    df_mapa['color_mapa'] = df_mapa['Origen'].map(colores_sistema).fillna('#E63946')
    st.map(df_mapa, latitude='latitude', longitude='longitude', size='frp', color='color_mapa')

with tab_temporal:
    st.subheader("Análisis de Tendencias Chrono-Satelitales")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        df_mes = df_filtrado.groupby(['Mes_Num', 'Mes', 'Origen']).size().reset_index(name='Detecciones').sort_values('Mes_Num')
        fig_mes = px.line(df_mes, x='Mes', y='Detecciones', color='Origen', title="Historial Estacional de Alertas", color_discrete_map=colores_sistema, markers=True)
        st.plotly_chart(fig_mes, use_container_width=True)
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
        # Gráfico dinámico bidimensional que sustituyó con éxito al gráfico plano de certezas
        fig_disp = px.scatter(df_filtrado.head(3000), x='brightness', y='frp', color='Origen', size='confidence', title="Temperatura vs Potencia FRP (Muestra)", color_discrete_map=colores_sistema, opacity=0.7)
        st.plotly_chart(fig_disp, use_container_width=True)

with tab_datos:
    st.subheader("Consola de Extracción y Logs Críticos")
    top_criticos = df_filtrado.sort_values(by='frp', ascending=False).head(15)[['acq_date', 'latitude', 'longitude', 'brightness', 'frp', 'confidence', 'Origen', 'Horario']]
    top_criticos.columns = ['Fecha', 'Latitud', 'Longitud', 'Brillo (K)', 'FRP (MW)', 'Confianza (%)', 'Clasificación', 'Horario']
    st.dataframe(top_criticos, use_container_width=True, hide_index=True)

if boton_prediccion and modelo_cls is not None:
    dn_num = 1 if dn_in == "Noche" else 0
    datos_entrada = pd.DataFrame([{'latitude': lat_in, 'longitude': lon_in, 'brightness': bright_in, 'bright_t31': t31_in, 'frp': frp_in, 'confidence': conf_in, 'daynight_num': dn_num}])
    clase_id = int(modelo_cls.predict(scaler_cls.transform(datos_entrada))[0])
    probabilidades = modelo_cls.predict_proba(scaler_cls.transform(datos_entrada))[0]
    st.sidebar.success(f"### **Resultado IA:**\n{MAPEO_INVERSO.get(clase_id)}\n\n**Certeza:** {probabilidades[clase_id]*100:.2f}%")