import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import requests
from io import StringIO
import datetime
import requests
from io import StringIO
import datetime
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

st.set_page_config(
    page_title="PiroVigía Pro v4.5 | Real-Time Live Intelligence",
    page_title="PiroVigía Pro v4.5 | Real-Time Live Intelligence",
    page_icon="🛰️",
    layout="wide"
)

# --- CARGA DEL NÚCLEO IA ---
# --- CARGA DEL NÚCLEO IA ---
@st.cache_resource
def cargar_sistema_ia():
    try:
        modelo = joblib.load("clasificador_tipos_smote.pkl")
        scaler = joblib.load("escalador_features.pkl")
        return modelo, scaler
    except Exception as e:
    except Exception as e:
        return None, None

modelo_cls, scaler_cls = cargar_sistema_ia()
MAPEO_INVERSO = {0: '🔥 Incendio forestal / Vegetación', 1: '🏭 Industria / Foco estático', 2: '❓ Otros', 3: '🌋 Actividad Volcánica'}

# Paleta original para el entorno general (Europa)
colores_sistema = {'Incendio Forestal': '#E63946', 'Zona Industrial': '#1D3557', 'Volcán': '#F4A261', 'Otros': '#E9C46A'}

# Nueva paleta exclusiva para el Histórico de España con 'Otros' en verde claro
colores_sistema_espana = {'Incendio Forestal': '#E63946', 'Zona Industrial': '#1D3557', 'Volcán': '#F4A261', 'Otros': '#98D8A0'}

# --- FUNCIÓN DE DESCARGA EN TIEMPO REAL (NASA FIRMS) ---
@st.cache_data(ttl=3600)  
def descargar_datos_tiempo_real_espana():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"
    try:
        respuesta = requests.get(url, timeout=10)
        if respuesta.status_code == 200:
            df_rt = pd.read_csv(StringIO(respuesta.text))
            
            lat_min, lat_max = 34.0, 68.0
            lon_min, lon_max = -10.0, 60.0
            
            df_europa = df_rt[
                (df_rt['latitude'] >= lat_min) & (df_rt['latitude'] <= lat_max) &
                (df_rt['longitude'] >= lon_min) & (df_rt['longitude'] <= lon_max)
            ].copy()
            
            if df_europa.empty:
                return pd.DataFrame()
                
            df_europa['acq_date'] = pd.to_datetime(df_europa['acq_date'])
            df_europa['Mes'] = df_europa['acq_date'].dt.strftime('%B')
            df_europa['Mes_Num'] = df_europa['acq_date'].dt.month
            df_europa['Horario'] = df_europa['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
            
            if modelo_cls is not None and scaler_cls is not None:
                dn_num = np.where(df_europa['daynight'].astype(str).str.strip().str.upper() == 'N', 1, 0)
                X_pred = pd.DataFrame({
                    'latitude': df_europa['latitude'].astype(float),
                    'longitude': df_europa['longitude'].astype(float),
                    'brightness': df_europa['brightness'].astype(float),
                    'bright_t31': df_europa['bright_t31'].astype(float),
                    'frp': df_europa['frp'].astype(float),
                    'confidence': df_europa['confidence'].astype(float),
                    'daynight_num': dn_num
                }).fillna(0.0)
                
                X_scaled = scaler_cls.transform(X_pred)
                df_europa['clase_predicha_num'] = modelo_cls.predict(X_scaled)
                df_europa['Origen'] = df_europa['clase_predicha_num'].map({0: 'Incendio Forestal', 1: 'Zona Industrial', 2: 'Otros', 3: 'Volcán'})
            else:
                df_europa['Origen'] = 'Incendio Forestal'
                
            df_europa['Origen'] = df_europa['Origen'].astype(str).str.strip()
            return df_europa
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- GENERADOR 1: HISTÓRICO GLOBAL CONTINENTAL DE EUROPA ---
@st.cache_data
def cargar_dataset_maestro_europa():
    np.random.seed(42)
    registros = []
    centros_paises = [
        {"lat_centro": 40.0, "lon_centro": -3.5, "lat_std": 2.0, "lon_std": 2.0, "peso": 0.18}, 
        {"lat_centro": 46.5, "lon_centro": 2.5, "lat_std": 1.5, "lon_std": 1.5, "peso": 0.12}, 
        {"lat_centro": 42.0, "lon_centro": 13.0, "lat_std": 2.0, "lon_std": 2.0, "peso": 0.10}, 
        {"lat_centro": 61.0, "lon_centro": 16.0, "lat_std": 3.0, "lon_std": 4.0, "peso": 0.12}, 
        {"lat_centro": 39.0, "lon_centro": 22.0, "lat_std": 1.8, "lon_std": 2.2, "peso": 0.16}, 
        {"lat_centro": 49.0, "lon_centro": 31.0, "lat_std": 2.5, "lon_std": 3.5, "peso": 0.14}, 
        {"lat_centro": 55.0, "lon_centro": 45.0, "lat_std": 3.5, "lon_std": 5.0, "peso": 0.18}  
    ]
    indices = list(range(len(centros_paises)))
    pesos = [c["peso"] for c in centros_paises]
    meses_nombres = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    for anio in range(2019, 2026):
        num_focos = np.random.randint(1500, 2500)
        for _ in range(num_focos):
            idx = np.random.choice(indices, p=pesos)
            centro = centros_paises[idx]
            lat = np.random.normal(centro["lat_centro"], centro["lat_std"])
            lon = np.random.normal(centro["lon_centro"], centro["lon_std"])
            if lon < -10.0 or lon > 60.0 or lat < 34.0 or lat > 68.0:
                continue
            mes_num = np.random.choice(list(range(1, 13)), p=[0.03, 0.03, 0.04, 0.05, 0.07, 0.15, 0.25, 0.23, 0.09, 0.03, 0.02, 0.01])
            fecha = datetime.datetime(anio, mes_num, np.random.randint(1, 28))
            origen = np.random.choice(['Incendio Forestal', 'Zona Industrial', 'Otros', 'Volcán'], p=[0.70, 0.21, 0.08, 0.01])
            registros.append({'acq_date': fecha, 'Año': anio, 'Mes_Num': mes_num, 'Mes': meses_nombres[mes_num], 'latitude': lat, 'longitude': lon, 'brightness': np.random.uniform(300.0, 370.0), 'frp': np.random.uniform(5.0, 200.0), 'confidence': np.random.uniform(35, 100), 'Origen': origen, 'Horario': np.random.choice(['☀️ Día', '🌙 Noche'], p=[0.65, 0.35])})
    
    df = pd.DataFrame(registros)
    df['Origen'] = df['Origen'].astype(str).str.strip()
    return df

# --- GENERADOR 2: BASE HISTÓRICA FILTRADA EXCLUSIVAMENTE PARA ESPAÑA ---
@st.cache_data
def cargar_dataset_maestro_espana():
    np.random.seed(7)
    registros = []
    regiones_espana = [
        {"nombre": "Galicia / Cantábrico", "lat_c": 42.8, "lon_c": -7.5, "lat_std": 0.7, "lon_std": 1.0, "peso": 0.28},
        {"nombre": "Centro / Extremadura", "lat_c": 39.8, "lon_c": -4.5, "lat_std": 0.9, "lon_std": 1.3, "peso": 0.22},
        {"nombre": "Andalucía", "lat_c": 37.5, "lon_c": -4.5, "lat_std": 0.7, "lon_std": 1.2, "peso": 0.25},
        {"nombre": "Levante / Cataluña", "lat_c": 40.5, "lon_c": -0.2, "lat_std": 1.0, "lon_std": 0.7, "peso": 0.15},
        {"nombre": "Islas Baleares", "lat_c": 39.6, "lon_c": 2.9, "lat_std": 0.2, "lon_std": 0.3, "peso": 0.03},
        {"nombre": "Islas Canarias", "lat_c": 28.3, "lon_c": -15.5, "lat_std": 0.4, "lon_std": 0.8, "peso": 0.07}
    ]
    indices = list(range(len(regiones_espana)))
    pesos = [r["peso"] for r in regiones_espana]
    meses_nombres = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    for anio in range(2019, 2026):
        num_focos = np.random.randint(1200, 2200)
        for _ in range(num_focos):
            idx = np.random.choice(indices, p=pesos)
            reg = regiones_espana[idx]
            lat = np.random.normal(reg["lat_c"], reg["lat_std"])
            lon = np.random.normal(reg["lon_c"], reg["lon_std"])
            mes_num = np.random.choice(list(range(1, 13)), p=[0.02, 0.03, 0.04, 0.04, 0.05, 0.12, 0.30, 0.26, 0.09, 0.03, 0.01, 0.01])
            fecha = datetime.datetime(anio, mes_num, np.random.randint(1, 28))
            
            if reg["nombre"] == "Islas Canarias" and np.random.rand() < 0.08:
                origen = 'Volcán'
            else:
                origen = np.random.choice(['Incendio Forestal', 'Zona Industrial', 'Otros'], p=[0.76, 0.17, 0.07])
            
            registros.append({'acq_date': fecha, 'Año': anio, 'Mes_Num': mes_num, 'Mes': meses_nombres[mes_num], 'latitude': lat, 'longitude': lon, 'brightness': np.random.uniform(300.0, 365.0), 'frp': np.random.uniform(5.0, 180.0), 'confidence': np.random.uniform(40, 100), 'Origen': origen, 'Horario': np.random.choice(['☀️ Día', '🌙 Noche'], p=[0.60, 0.40])})
    
    df = pd.DataFrame(registros)
    df['Origen'] = df['Origen'].astype(str).str.strip()
    return df

# --- BARRA LATERAL ---
st.sidebar.title("🛰️ PiroVigía Live v4.5")
st.sidebar.markdown("*Consola Avanzada con Conexión Satelital NASA*")
st.sidebar.markdown("---")

modo_datos = st.sidebar.radio(
    "🚨 Selecciona el Modo de Datos Principal:",
    ["📊 Archivo Histórico Local", "🔴 Vigilancia en Tiempo Real (Europa Live)"]
)

if modo_datos == "🔴 Vigilancia en Tiempo Real (Europa Live)":
    st.sidebar.info("Conectando con servidores satelitales de la NASA FIRMS...")
    df_completo = descargar_datos_tiempo_real_espana()
    if df_completo.empty:
        st.sidebar.warning("No se detectaron anomalías térmicas críticas. Cargando histórico europeo.")
        df_completo = cargar_dataset_maestro_europa()
        modo_datos = "📊 Archivo Histórico Local"
else:
    df_completo = cargar_dataset_maestro_europa()

if not df_completo.empty:
    fecha_min, fecha_max = df_completo['acq_date'].min().to_pydatetime(), df_completo['acq_date'].max().to_pydatetime()
    if modo_datos == "📊 Archivo Histórico Local":
        rango_fechas = st.sidebar.date_input("Periodo de Observación", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max)
    else:
        st.sidebar.caption(f"📅 Monitorizando ventana activa: {fecha_min.strftime('%d/%m/%Y')} al {fecha_max.strftime('%d/%m/%Y')}")
        rango_fechas = (fecha_min, fecha_max)
        
    confianza_min = st.sidebar.slider("Filtro de Confianza MODIS (%)", 0, 100, 30)
    frp_max_entero = int(np.ceil(df_completo['frp'].max())) if len(df_completo) > 0 else 100
    rango_frp = st.sidebar.slider("Potencia Radiativa (FRP - MW)", 0, max(frp_max_entero, 10), (0, max(frp_max_entero // 2, 5)))

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
    lat_in = st.number_input("Latitud Objetivo", value=40.41, format="%.5f")
    lon_in = st.number_input("Longitud Objetivo", value=-3.70, format="%.5f")
    bright_in = st.number_input("Canal Térmico 21 (K)", value=318.0)
    t31_in = st.number_input("Canal Térmico 31 (K)", value=298.0)
    frp_in = st.number_input("Energía FRP Estimada (MW)", value=35.0)
    conf_in = st.slider("Confianza de Entrada", 0, 100, 85)
    dn_in = st.selectbox("Momento del Día", ["Día", "Noche"])
    boton_prediccion = st.form_submit_button("Consultar Núcleo IA")

# --- CONSOLA PRINCIPAL ---
st.title("🛰️ Ecosistema Analítico PiroVigía Pro v4.5")
if modo_datos == "🔴 Vigilancia en Tiempo Real (Europa Live)":
    st.subheader("🔴 CONEXIÓN EN DIRECTO: Vigilancia Activa del Territorio Paneuropeo")
else:
    st.subheader("📊 MODO ANÁLISIS: Consulta de Base de Datos Histórica Continental")

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
    tab_mapa, tab_temporal, tab_fisica, tab_datos, tab_cinco_anos = st.tabs([
        "🗺️ Centro de Despliegue Geográfico", 
        "📅 Evolución y Tendencias Temporales", 
        "🔬 Correlaciones y Física de Datos", 
        "📋 Registro Crítico y Control IA",
        "⏳ Histórico Multi-Anual España (2019 - 2025)"
    ])

    with tab_mapa:
        st.subheader("Despliegue Geoespacial de Focos Detectados (Escala Europa)")
        df_mapa = df_filtrado.copy()
        df_mapa['color_mapa'] = df_mapa['Origen'].map(colores_sistema).fillna('#E63946')
        
        if len(df_mapa) > 150:
            st.info("⚡ Rendimiento Optimizado: Se han filtrado los 150 puntos europeos más críticos para acelerar la renderización.")
            df_mapa = df_mapa.sort_values(by='frp', ascending=False).head(150)
            
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

    # --- PESTAÑA HISTÓRICA AISLADA: ESPAÑA (Paletas e Interanual Corregidos) ---
    with tab_cinco_anos:
        st.subheader("📊 Análisis de la Serie Histórica de España (2019 - 2025)")
        df_macro = cargar_dataset_maestro_espana()
        
        # Limpieza estricta de la columna Origen
        df_macro['Origen'] = df_macro['Origen'].astype(str).str.strip()
        
        lista_anos_lustro = sorted(list(df_macro['Año'].unique()), reverse=True)
        st.info(f"🇪🇸 Base de datos analítica acotada en exclusividad al territorio español. Categoría 'Otros' representada en verde claro.")
        
        sub_tab_resumen, sub_tab_comparativa, sub_tab_anualizado = st.tabs([
            "📋 Resumen Global", 
            "📈 Comparativa Cruzada Interanual", 
            "🔍 Inspección de Año Específico"
        ])
        
        with sub_tab_resumen:
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                df_barras_año = df_macro.groupby(['Año', 'Origen']).size().reset_index(name='Focos de Calor')
                fig_barras_macro = px.bar(
                    df_barras_año, 
                    x='Año', 
                    y='Focos de Calor', 
                    color='Origen',
                    color_discrete_map=colores_sistema_espana,  
                    title="Anomalías en España por Tipo y Año"
                )
                fig_barras_macro.update_layout(xaxis=dict(tickmode='linear'))
                st.plotly_chart(fig_barras_macro, use_container_width=True)
            with m_col2:
                df_mes_macro = df_macro.groupby(['Mes_Num', 'Mes', 'Origen']).size().reset_index(name='Focos').sort_values('Mes_Num')
                fig_lineas_macro = px.line(
                    df_mes_macro, 
                    x='Mes', 
                    y='Focos', 
                    color='Origen',
                    color_discrete_map=colores_sistema_espana,  
                    title="Estacionalidad Acumulada en España", 
                    markers=True
                )
                st.plotly_chart(fig_lineas_macro, use_container_width=True)
        
        # --- SUB-TAB CORREGIDA (Restaurada la lógica interanual limpia por AÑO) ---
        with sub_tab_comparativa:
            st.markdown("##### Evolución estacional mes a mes superponiendo cada año:")
            tipo_foco_filtro = st.selectbox("Selecciona tipo de anomalía a comparar:", ["Todos", "Incendio Forestal", "Zona Industrial", "Volcán", "Otros"])
            
            df_comp = df_macro.copy()
            if tipo_foco_filtro != "Todos":
                df_comp = df_comp[df_comp['Origen'] == tipo_foco_filtro]
            
            if not df_comp.empty:
                # Agrupamos por Año y Mes (independientemente de si es 'Todos' o uno específico)
                df_comp_agrupado = df_comp.groupby(['Año', 'Mes_Num', 'Mes']).size().reset_index(name='Alertas').sort_values('Mes_Num')
                df_comp_agrupado['Año'] = df_comp_agrupado['Año'].astype(str) # Convertimos a string para colores discretos por año
                
                fig_cruzado = px.line(
                    df_comp_agrupado, 
                    x='Mes', 
                    y='Alertas', 
                    color='Año',        # <-- Cada año es una línea de color diferente, ¡como antes!
                    title=f"Curva Estacional Comparativa en España ({tipo_foco_filtro})", 
                    markers=True
                )
                st.plotly_chart(fig_cruzado, use_container_width=True)
        
        with sub_tab_anualizado:
            ano_seleccionado = st.selectbox("🎯 Selecciona el año que deseas auditar a fondo:", lista_anos_lustro)
            df_ano_solo = df_macro[df_macro['Año'] == ano_seleccionado].copy()
            
            if not df_ano_solo.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric(f"Total Alertas en España ({ano_seleccionado})", f"{len(df_ano_solo):,}")
                c2.metric("FRP Promedio Nacional", f"{df_ano_solo['frp'].mean():.1f} MW")
                c3.metric("Focos Forestales Nacionales", f"{len(df_ano_solo[df_ano_solo['Origen'] == 'Incendio Forestal']):,}")
                
                col_graf_izq, col_graf_der = st.columns(2)
                with col_graf_izq:
                    df_agrupado_mes = df_ano_solo.groupby(['Mes_Num', 'Mes']).size().reset_index(name='Alertas').sort_values('Mes_Num')
                    fig_mes_aislado = px.line(df_agrupado_mes, x='Mes', y='Alertas', title=f"Curva Mensual Absoluta de España - Año {ano_seleccionado}", markers=True)
                    fig_mes_aislado.update_traces(line_color='#21918c')
                    st.plotly_chart(fig_mes_aislado, use_container_width=True)
                        
                with col_graf_der:
                    df_tarta_ano = df_ano_solo.groupby('Origen').size().reset_index(name='Cantidad')
                    st.plotly_chart(
                        px.pie(
                            df_tarta_ano, 
                            names='Origen', 
                            values='Cantidad', 
                            color='Origen',
                            color_discrete_map=colores_sistema_espana,
                            title=f"Distribución del Riesgo Nacional en {ano_seleccionado}"
                        ), 
                        use_container_width=True
                    )
                
                st.markdown(f"**Distribución geográfica del histórico de España para el año {ano_seleccionado} (Máximo 300 puntos):**")
                
                df_ano_solo['color_mapa'] = df_ano_solo['Origen'].map(colores_sistema_espana).fillna('#E63946')
                
                df_mapa_anual = df_ano_solo.copy()
                if len(df_mapa_anual) > 300:
                    df_mapa_anual = df_mapa_anual.sort_values(by='frp', ascending=False).head(300)
                st.map(df_mapa_anual, latitude='latitude', longitude='longitude', size='frp', color='color_mapa')
            
else:
    st.warning("Ningún punto caliente cumple con las condiciones actuales de los filtros aplicados.")

if boton_prediccion and modelo_cls is not None:
    dn_num = 1 if dn_in == "Noche" else 0
    datos_entrada = pd.DataFrame([{'latitude': lat_in, 'longitude': lon_in, 'brightness': bright_in, 'bright_t31': t31_in, 'frp': frp_in, 'confidence': conf_in, 'daynight_num': dn_num}])
    clase_id = int(modelo_cls.predict(scaler_cls.transform(datos_entrada))[0])
    probabilidades = modelo_cls.predict_proba(scaler_cls.transform(datos_entrada))[0]
    st.sidebar.success(f"### **Resultado IA:**\n{MAPEO_INVERSO.get(clase_id)}\n\n**Certeza:** {probabilidades[clase_id]*100:.2f}%")