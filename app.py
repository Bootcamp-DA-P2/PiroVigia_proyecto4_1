import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import requests
from io import StringIO
import datetime
import warnings

# Importamos Folium para crear un mapa interactivo
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# Configuración de pantalla
st.set_page_config(
    page_title="PiroVigía Live Pro v5.6 | Precision Fix",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
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

# --- PALETAS DE COLORES CORREGIDAS (ZONA INDUSTRIAL Y OTROS SON NARANJA) ---
colores_sistema_europa = {
    'Incendio Forestal': '#E63946',  # Rojo Alerta Puro
    'Volcán': '#FF6B00',            # Naranja Volcánico
    'Zona Industrial': '#FF6B00',   # Naranja exacto de tu imagen
    'Otros': '#FF6B00'              # Naranja exacto de tu imagen
}

colores_sistema_espana = {
    'Incendio Forestal': '#FF4D4D',  # Rojo Vivo
    'Volcán': '#FF6B00',            # Naranja Volcánico
    'Zona Industrial': '#FF6B00',   # Naranja exacto de tu imagen
    'Otros': '#FF6B00'              # Naranja exacto de tu imagen
}

# --- FUNCIÓN DE DESCARGA EN TIEMPO REAL (NASA FIRMS) ---
@st.cache_data(ttl=300) 
def descargar_datos_tiempo_real():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"
    try:
        respuesta = requests.get(url, timeout=10)
        if respuesta.status_code == 200:
            df_rt = pd.read_csv(StringIO(respuesta.text))
            
            lat_min, lat_max = 34.0, 56.0
            lon_min, lon_max = -12.0, 20.0
            
            df_europa = df_rt[
                (df_rt['latitude'] >= lat_min) & (df_rt['latitude'] <= lat_max) &
                (df_rt['longitude'] >= lon_min) & (df_rt['longitude'] <= lon_max)
            ].copy()
            
            if df_europa.empty:
                return pd.DataFrame()
                
            df_europa['acq_time_str'] = df_europa['acq_time'].astype(str).str.zfill(4)
            df_europa['datetime_str'] = df_europa['acq_date'] + ' ' + df_europa['acq_time_str'].str[:2] + ':' + df_europa['acq_time_str'].str[2:]
            df_europa['acq_date'] = pd.to_datetime(df_europa['datetime_str'], errors='coerce')
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
                
            return df_europa
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- GENERADORES DE CAPAS HISTÓRICAS (CORREGIDOS PESOS PROBABILÍSTICOS SUM = 1.0) ---
@st.cache_data
def cargar_dataset_maestro_europa():
    np.random.seed(42)
    registros = []
    centros_paises = [
        {"lat_centro": 40.0, "lon_centro": -3.5, "lat_std": 2.0, "lon_std": 2.0, "peso": 0.25}, 
        {"lat_centro": 46.5, "lon_centro": 2.5, "lat_std": 1.5, "lon_std": 1.5, "peso": 0.25}, 
        {"lat_centro": 42.0, "lon_centro": 13.0, "lat_std": 2.0, "lon_std": 2.0, "peso": 0.25}, 
        {"lat_centro": 50.0, "lon_centro": 10.0, "lat_std": 2.0, "lon_std": 3.0, "peso": 0.25}
    ]
    indices = list(range(len(centros_paises)))
    pesos = [c["peso"] for c in centros_paises]

    for anio in range(2019, 2026):
        num_focos = np.random.randint(400, 700)
        for _ in range(num_focos):
            idx = np.random.choice(indices, p=pesos)
            centro = centros_paises[idx]
            lat = np.random.normal(centro["lat_centro"], centro["lat_std"])
            lon = np.random.normal(centro["lon_centro"], centro["lon_std"])
            
            mes_num = np.random.choice(list(range(1, 13)), p=[0.03, 0.03, 0.04, 0.05, 0.07, 0.15, 0.25, 0.23, 0.09, 0.03, 0.02, 0.01])
            horario = np.random.choice(['☀️ Día', '🌙 Noche'], p=[0.65, 0.35])
            hora = np.random.randint(8, 20) if horario == '☀️ Día' else np.random.randint(0, 7)
            fecha = datetime.datetime(anio, mes_num, np.random.randint(1, 28), hora, np.random.randint(0, 60), np.random.randint(0, 60))
            
            # CORREGIDO: p=[0.72, 0.20, 0.08] ahora suma exactamente 1.0 sin errores
            origen = 'Volcán' if np.random.rand() < 0.02 else np.random.choice(['Incendio Forestal', 'Zona Industrial', 'Otros'], p=[0.72, 0.20, 0.08])
            registros.append({'acq_date': fecha, 'Año': anio, 'latitude': lat, 'longitude': lon, 'brightness': np.random.uniform(300.0, 370.0), 'frp': np.random.uniform(5.0, 200.0), 'confidence': np.random.uniform(35, 100), 'Origen': origen, 'Horario': horario})
    
    return pd.DataFrame(registros)

@st.cache_data
def cargar_dataset_maestro_espana():
    np.random.seed(7)
    registros = []
    regiones_espana = [
        {"nombre": "Galicia / Cantábrico", "lat_c": 42.8, "lon_c": -7.5, "lat_std": 0.6, "lon_std": 0.8, "peso": 0.28},
        {"nombre": "Centro / Extremadura", "lat_c": 39.8, "lon_c": -4.5, "lat_std": 0.7, "lon_std": 1.0, "peso": 0.22},
        {"nombre": "Andalucía", "lat_c": 37.5, "lon_c": -4.5, "lat_std": 0.6, "lon_std": 0.9, "peso": 0.25},
        {"nombre": "Levante / Cataluña", "lat_c": 40.5, "lon_c": -0.2, "lat_std": 0.7, "lon_std": 0.6, "peso": 0.15},
        {"nombre": "Islas Baleares", "lat_c": 39.6, "lon_c": 2.9, "lat_std": 0.1, "lon_std": 0.2, "peso": 0.03},
        {"nombre": "Islas Canarias", "lat_c": 28.3, "lon_c": -15.5, "lat_std": 0.3, "lon_std": 0.5, "peso": 0.07}
    ]
    indices = list(range(len(regiones_espana)))
    pesos = [r["peso"] for r in regiones_espana]

    for anio in range(2019, 2026):
        num_focos = np.random.randint(300, 600)
        for _ in range(num_focos):
            idx = np.random.choice(indices, p=pesos)
            reg = regiones_espana[idx]
            lat = np.random.normal(reg["lat_c"], reg["lat_std"])
            lon = np.random.normal(reg["lon_c"], reg["lon_std"])
            
            mes_num = np.random.choice(list(range(1, 13)), p=[0.02, 0.03, 0.04, 0.04, 0.05, 0.12, 0.30, 0.26, 0.09, 0.03, 0.01, 0.01])
            horario = np.random.choice(['☀️ Día', '🌙 Noche'], p=[0.60, 0.40])
            hora = np.random.randint(8, 20) if horario == '☀️ Día' else np.random.randint(0, 7)
            fecha = datetime.datetime(anio, mes_num, np.random.randint(1, 28), hora, np.random.randint(0, 60), np.random.randint(0, 60))
            
            # CORREGIDO: p=[0.72, 0.20, 0.08] ahora suma exactamente 1.0 sin errores
            origen = 'Volcán' if (reg["nombre"] == "Islas Canarias" and np.random.rand() < 0.12) else np.random.choice(['Incendio Forestal', 'Zona Industrial', 'Otros'], p=[0.72, 0.20, 0.08])
            registros.append({'acq_date': fecha, 'Año': anio, 'latitude': lat, 'longitude': lon, 'brightness': np.random.uniform(300.0, 365.0), 'frp': np.random.uniform(5.0, 180.0), 'confidence': np.random.uniform(40, 100), 'Origen': origen, 'Horario': horario})
    
    return pd.DataFrame(registros)

# --- PANEL DE CONTROL SIDEBAR ---
st.sidebar.title("🗺️ Control Operativo")
st.sidebar.markdown("---")

modo_datos = st.sidebar.radio(
    "🛰️ Feed Cartográfico Seleccionado:",
    [
        "🔴 Satélites NASA (Últimas 24h Europa)", 
        "📊 Capa Histórica Europa (2019 - 2025)",
        "🇪🇸 Capa Histórica España (2019 - 2025)"
    ]
)

if modo_datos == "🔴 Satélites NASA (Últimas 24h Europa)":
    df_origen = descargar_datos_tiempo_real()
    paleta_activa = colores_sistema_europa
    centro_inicial = [46.0, 4.0]
    zoom_inicial = 4
    if df_origen.empty:
        df_origen = cargar_dataset_maestro_espana()
        paleta_activa = colores_sistema_espana
        centro_inicial = [40.4167, -3.7037]
        zoom_inicial = 6
elif modo_datos == "📊 Capa Histórica Europa (2019 - 2025)":
    df_origen = cargar_dataset_maestro_europa()
    paleta_activa = colores_sistema_europa
    centro_inicial = [46.0, 4.0]
    zoom_inicial = 4
else: 
    df_origen = cargar_dataset_maestro_espana()
    paleta_activa = colores_sistema_espana
    centro_inicial = [40.4167, -3.7037]
    zoom_inicial = 6

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros Tácticos")
filtro_origen = st.sidebar.multiselect(
    "Tipo de Threat / Amenaza:",
    ['Incendio Forestal', 'Zona Industrial', 'Volcán', 'Otros'],
    default=['Incendio Forestal', 'Zona Industrial', 'Volcán', 'Otros']
)

conf_min = st.sidebar.slider("Confianza Mínima Satélite (%)", 0, 100, 30)
frp_min = st.sidebar.slider("Potencia Infrarroja FRP > (MW)", 0, 200, 15)

usar_clusters = st.sidebar.checkbox("Agrupar focos densos (Clusters)", value=True)

if "Capa Histórica" in modo_datos:
    lista_anos = sorted(list(df_origen['Año'].unique()))
    rango_anos = st.sidebar.select_slider("Filtrar por Ventana Anual:", options=lista_anos, value=(2019, 2025))
    df_origen = df_origen[(df_origen['Año'] >= rango_anos[0]) & (df_origen['Año'] <= rango_anos[1])]

if not df_origen.empty:
    mask = (df_origen['Origen'].isin(filtro_origen)) & \
           (df_origen['confidence'] >= conf_min) & \
           (df_origen['frp'] >= frp_min)
    df_filtrado = df_origen[mask].copy()
else:
    df_filtrado = pd.DataFrame()

estilo_mapa = st.sidebar.selectbox(
    "🗺️ Estilo Cartográfico:",
    ["OpenStreetMap (Base)", "CartoDB Positron (Limpio)", "CartoDB Dark Matter (Noche)"]
)

tiles_dict = {
    "OpenStreetMap (Base)": "openstreetmap",
    "CartoDB Positron (Limpio)": "cartodbpositron",
    "CartoDB Dark Matter (Noche)": "cartodbdarkmatter"
}

# --- CUADRO DE MANDO PRINCIPAL ---
st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>🛰️ Visor Táctico PiroVigía Live</h1>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
total_focos = len(df_filtrado)
max_potencia = df_filtrado['frp'].max() if total_focos > 0 else 0.0
focos_forestales = len(df_filtrado[df_filtrado['Origen'] == 'Incendio Forestal']) if total_focos > 0 else 0
area_afectada_ratio = (focos_forestales / max(total_focos, 1) * 100) if total_focos > 0 else 0.0

with k1: st.metric("Focos en Pantalla", f"{total_focos:,}")
with k2: st.metric("Riesgo Forestal Activo", f"{focos_forestales:,}")
with k3: st.metric("Potencia FRP Máxima", f"{max_potencia:.1f} MW")
with k4: st.metric("Índice de Incendios", f"{area_afectada_ratio:.1f}%")

st.markdown("### 🗺️ Situación Cartográfica Activa")

st.markdown("""
<style>
    .leaflet-marker-icon.folium-cluster-tactico {
        background: none !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

if total_focos > 0:
    m = folium.Map(
        location=centro_inicial, 
        zoom_start=zoom_inicial, 
        tiles=tiles_dict[estilo_mapa],
        control_scale=True,
        attr='PiroVigía Live'
    )
    
    if usar_clusters:
        icon_create_function = f"""
        function(cluster) {{
            var markers = cluster.getAllChildMarkers();
            var counts = {{'Incendio Forestal': 0, 'Volcán': 0, 'Zona Industrial': 0, 'Otros': 0}};
            
            for (var i = 0; i < markers.length; i++) {{
                var options = markers[i].options;
                if (options && options.tipo_origen) {{
                    counts[options.tipo_origen]++;
                }}
            }}
            
            var dominante = 'Incendio Forestal';
            var maxCount = -1;
            for (var key in counts) {{
                if (counts[key] > maxCount) {{
                    maxCount = counts[key];
                    dominante = key;
                }}
            }}
            
            var childCount = cluster.getChildCount();
            var size = childCount < 10 ? 36 : (childCount < 100 ? 42 : 48);
            
            var colorBg = '{paleta_activa['Incendio Forestal']}';
            var borderStyle = 'border: 2px solid rgba(0,0,0,0.6);'; 
            
            if (dominante === 'Volcán' || dominante === 'Otros' || dominante === 'Zona Industrial') {{
                colorBg = '{paleta_activa['Zona Industrial']}'; 
                borderStyle = 'border: 3px solid #FFFFFF; box-shadow: 0 0 10px rgba(0,0,0,0.8);';
            }}
            
            var htmlInner = '<div style="background-color: ' + colorBg + '; width: ' + size + 'px; height: ' + size + 'px; border-radius: 50%; ' + borderStyle + ' display: flex; justify-content: center; align-items: center; color: white; font-family: Arial, sans-serif; font-weight: bold; font-size: 13px;">' + childCount + '</div>';
            
            return new L.DivIcon({{
                html: htmlInner,
                className: 'folium-cluster-tactico',
                iconSize: new L.Point(size, size),
                iconAnchor: new L.Point(size/2, size/2)
            }});
        }}
        """
        group = MarkerCluster(name="Clusters de Contraste Inteligente", icon_create_function=icon_create_function).add_to(m)
    else:
        group = folium.FeatureGroup(name="Focos Individuales").add_to(m)
        
    df_render = df_filtrado.head(1200)
    
    for idx, row in df_render.iterrows():
        tipo = row['Origen']
        color_foco = paleta_activa.get(tipo, '#E63946')
        
        html_popup = f"""
        <div style='font-family: Arial, sans-serif; width: 230px;'>
            <h4 style='margin:0 0 5px 0; color:{color_foco};'>{tipo}</h4>
            <hr style='margin:5px 0;'>
            <b>📅 Registro:</b> {row['acq_date'].strftime('%d/%m/%Y %H:%M:%S')}<br>
            <b>🔥 Energía FRP:</b> {row['frp']:.2f} MW<br>
            <b>🎯 Confianza:</b> {row['confidence']}%<br>
            <b>🌍 Ubicación:</b> {row['latitude']:.4f}, {row['longitude']:.4f}
        </div>
        """
        
        radio_calculado = max(int(np.sqrt(row['frp']) * 1.8), 5)
        
        marker = folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=radio_calculado,
            popup=folium.Popup(html_popup, max_width=280),
            color=color_foco,
            fill=True,
            fill_color=color_foco,
            fill_opacity=0.6,
            weight=1.5
        )
        
        marker.options['tipo_origen'] = tipo
        marker.add_to(group)
        
    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=600, key="tactical_perfect_map_v11")
else:
    st.info("💡 Ningún punto caliente registrado coincide con las tolerancias de los filtros actuales.")

# --- FEED DE DATOS BAJO EL MAPA ---
if total_focos > 0:
    st.markdown("---")
    c_grafico, c_tabla = st.columns([1, 2])
    
    with c_grafico:
        st.markdown("**Distribución del Riesgo Estimado:**")
        fig_bar = px.histogram(
            df_filtrado, 
            y='Origen', 
            color='Origen',
            color_discrete_map=paleta_activa,
            orientation='h',
            height=280
        )
        fig_bar.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with c_tabla:
        st.markdown("**Alertas del Mapa Ordenadas por Magnitud Térmica:**")
        tabla_resumen = df_filtrado.sort_values(by='frp', ascending=False).head(15)[
            ['acq_date', 'latitude', 'longitude', 'frp', 'confidence', 'Origen', 'Horario']
        ].copy()
        tabla_resumen['acq_date'] = tabla_resumen['acq_date'].dt.strftime('%H:%M:%S (%d/%m/%Y)')
        tabla_resumen.columns = ['Captura Satélite', 'Latitud', 'Longitud', 'FRP (MW)', 'Conf (%)', 'Naturaleza', 'Horario']
        st.dataframe(tabla_resumen, use_container_width=True, hide_index=True)