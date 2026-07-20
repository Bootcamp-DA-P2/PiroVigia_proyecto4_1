import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
<<<<<<< HEAD:streamlit/app.py
import requests
from io import StringIO
=======
>>>>>>> main:app.py
import datetime
import warnings
import requests
from io import StringIO
from geopy.geocoders import Nominatim
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

# Importamos Folium para crear un mapa interactivo
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# ---- SESIÓN HTTP ----
session = requests.Session()
session.headers.update({
    "User-Agent": "PiroVigia/2.0"
})

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(
<<<<<<< HEAD:streamlit/app.py
    page_title="PiroVigía Pro v4.5 | Real-Time Live Intelligence",
=======
    page_title="PiroVigía Localizador v1.0",
>>>>>>> main:app.py
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

<<<<<<< HEAD:streamlit/app.py
# --- CARGA DEL NÚCLEO IA ---
@st.cache_resource
def cargar_sistema_ia():
    try:
        modelo = joblib.load("clasificador_tipos_smote.pkl")
        scaler = joblib.load("escalador_features.pkl")
        return modelo, scaler
    except Exception as e:
        return None, None
=======
# --- CLASIFICADOR HEURÍSTICO DE FOCOS TÉRMICOS ---
def clasificar_origen(row):
    lat, lon = row['latitude'], row['longitude']
    frp = row['frp']
    horario = row['horario']
    # Obtenmos brightness (csv local) o bright_ti24 (real time); si no existieran, usamos un valor neutro por defecto de 300
    bright = row.get('brightness', row.get('bright_ti24', 300.0))
>>>>>>> main:app.py

    # 1. Volcanes (Canarias)
    if (27.5 <= lat <= 29.5) and (-18.0 <= lon <= -13.0):
        if frp > 120 and bright > 345:
            return 'Zona volcánica'

    # 2. Zonas industriales
    focos_industriales = [
        {"nombre": "Polo Químico Huelva", "lat": 37.2, "lon": -6.9, "radio": 0.15},
        {"nombre": "Refinería San Roque / Algeciras", "lat": 36.18, "lon": -5.4, "radio": 0.1},
        {"nombre": "Refinería Cartagena / Escombreras", "lat": 37.57, "lon": -0.96, "radio": 0.1},
        {"nombre": "Polo Petroquímico Tarragona", "lat": 41.12, "lon": 1.2, "radio": 0.15},
        {"nombre": "Refinería Puertollano", "lat": 38.68, "lon": -4.1, "radio": 0.1},
        {"nombre": "Siderurgia Avilés / Gijón", "lat": 43.55, "lon": -5.7, "radio": 0.15},
        {"nombre": "Refinería Castellón", "lat": 39.95, "lon": 0.01, "radio": 0.1}
    ]

    for foco in focos_industriales:
        dist = np.sqrt((lat - foco["lat"])**2 + (lon - foco["lon"])**2)
        if dist <= foco["radio"]:
            return 'Zona industrial'
        
    # 3. Otros (quemas agrícolas, reflejos solares)
    if frp < 3.0 and horario == '☀️ Día':
        return 'Otros'
    
    # 4. Incendio forestal (por defecto)
    return 'Incendio forestal'

# --- CARGA DEL CSV LOCAL (histórico 2020-2026)---
@st.cache_data
def cargar_csv():
    try:
        df = pd.read_csv("data/20-26focos_calor.csv")
        # Convertimos nombres de columnas a minúsculas para compatibilidad
        df.columns = [col.split(',')[0].lower() for col in df.columns]
        # Conversión de fechas
        df['acq_time_str'] = df['acq_time'].astype(str).str.zfill(4)
        df['datetime_str'] = df['acq_date'] + ' ' + df['acq_time_str'].str[:2] + ':' + df['acq_time_str'].str[2:]
        df['acq_date'] = pd.to_datetime(df['datetime_str'], errors='coerce')
        df['horario'] = df['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
        
        
        # Robusto frente a distintos dtypes de pandas (object, string[pyarrow], etc.)
        if not pd.api.types.is_numeric_dtype(df['confidence']):
            df['confidence'] = (
                df['confidence'].astype(str).str.strip().str.lower()
                .map({'l': 30.0, 'n': 70.0, 'h': 100.0})
                .fillna(50.0)
            )
        else:
            df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce').fillna(50.0)

        df['Año'] = df['acq_date'].dt.year
        df['Origen'] = df.apply(clasificar_origen, axis=1)
        df['Region'] = df.apply(asociar_region, axis=1)
        return df
    except Exception as e:
        st.error(f"Error al cargar el CSV local: {e}")
        return pd.DataFrame()
    
# --- CARGA DE DATOS EN TIEMPO REAL (NASA FIRMS) ---
@st.cache_data(ttl=300) 

# --- FILTRADO GEOGRÁFICO DE REGIONES (EXCLUSIÓN DE ÁFRICA) ---
def asociar_region(row):
    lat, lon = row['latitude'], row['longitude']
    mejor_region = None
    distancia_minima = float('inf')

    es_canarias = (27.0 <= lat <= 29.5) and (-18.5 <= lon <= -13.0)
    es_peninsula = False
    
    if (35.9 <= lat <= 43.8) and (-9.5 <= lon <= 4.5):
        if lon > -2.0 and lat < 36.6:
            es_peninsula = False
        else:
            es_peninsula = True

    es_baleares = (38.3 <= lat <= 40.5) and (1.0 <= lon <= 4.5)

    if not (es_canarias or es_peninsula or es_baleares):
        return None

    regiones_espana = [
        {"nombre": "Andalucía", "lat_c": 37.5, "lon_c": -4.5, "lat_std": 0.8, "lon_std": 1.2},
        {"nombre": "Galicia", "lat_c": 42.8, "lon_c": -7.8, "lat_std": 0.5, "lon_std": 0.6},
        {"nombre": "Extremadura", "lat_c": 39.2, "lon_c": -6.1, "lat_std": 0.6, "lon_std": 0.6},
        {"nombre": "Castilla-La Mancha", "lat_c": 39.5, "lon_c": -3.0, "lat_std": 0.9, "lon_std": 1.2},
        {"nombre": "Castilla y León", "lat_c": 41.6, "lon_c": -4.7, "lat_std": 1.0, "lon_std": 1.5},
        {"nombre": "Aragón", "lat_c": 41.5, "lon_c": -0.8, "lat_std": 0.8, "lon_std": 0.8},
        {"nombre": "Cataluña", "lat_c": 41.8, "lon_c": 1.5, "lat_std": 0.5, "lon_std": 0.8},
        {"nombre": "Comunidad Valenciana", "lat_c": 39.5, "lon_c": -0.5, "lat_std": 0.8, "lon_std": 0.4},
        {"nombre": "Región de Murcia", "lat_c": 38.0, "lon_c": -1.5, "lat_std": 0.4, "lon_std": 0.4},
        {"nombre": "Comunidad de Madrid", "lat_c": 40.5, "lon_c": -3.7, "lat_std": 0.3, "lon_std": 0.4},
        {"nombre": "Principado de Asturias", "lat_c": 43.3, "lon_c": -6.0, "lat_std": 0.3, "lon_std": 0.6},
        {"nombre": "Cantabria", "lat_c": 43.2, "lon_c": -4.0, "lat_std": 0.2, "lon_std": 0.4},
        {"nombre": "País Vasco", "lat_c": 43.0, "lon_c": -2.5, "lat_std": 0.3, "lon_std": 0.4},
        {"nombre": "Comunidad Foral de Navarra", "lat_c": 42.6, "lon_c": -1.6, "lat_std": 0.4, "lon_std": 0.4},
        {"nombre": "La Rioja", "lat_c": 42.3, "lon_c": -2.5, "lat_std": 0.2, "lon_std": 0.4},
        {"nombre": "Islas Baleares", "lat_c": 39.6, "lon_c": 2.9, "lat_std": 0.3, "lon_std": 0.5},
        {"nombre": "Islas Canarias", "lat_c": 28.3, "lon_c": -15.5, "lat_std": 0.5, "lon_std": 1.0}
    ]

    for r in regiones_espana:
        umbral_lat = r['lat_std'] * 4.0
        umbral_lon = r['lon_std'] * 4.0
        
        if (abs(lat - r['lat_c']) <= umbral_lat) and (abs(lon - r['lon_c']) <= umbral_lon):
            dist = np.sqrt((lat - r['lat_c'])**2 + (lon - r['lon_c'])**2)
            if dist < distancia_minima:
                distancia_minima = dist
                mejor_region = r['nombre']
    
    if mejor_region is None:
        if es_baleares:
            mejor_region = "Islas Baleares"
        elif es_canarias:
            mejor_region = "Islas Canarias"
        elif es_peninsula:
            mejor_region = "Península (Zona de Transición)"
                
    return mejor_region

# rango_dias controla cuántos días hacia atrás solicitar a la API (por defecto 1 = últimas 24h)
def descarga_tiempo_real(rango_dias=1):
    # Recuperamos MAP_KEY de los secretos
    try: 
        MAP_KEY = st.secrets["nasa_map_key"]
    # Clave de respaldo por si falla la carga del archivo secrets.toml
    except Exception:
        MAP_KEY = "31b2805e7d68126bba3d47e6a00ddeba"
    
    # Caja delimitadora estricta para España (para evitar descargar datos mundiales innecesarios)
    bbox_espana = "-19,27,5,44"
    # Listado de los 3 sensores VIIRS de alta resolución activa (375m)
    sensores = ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT"]

    def descargar_sensor(sensor, api_key):
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{MAP_KEY}/{sensor}/{bbox_espana}/{rango_dias}"
        )
        try:
            respuesta = session.get(url, timeout=20)
            # Verificación estándar de HTTP
            if respuesta.status_code != 200:
                print(f"Error en sensor {sensor}: Código de respuesta {respuesta.status_code}")
                return None
            # Verificación de errores de API
            texto_respuesta = respuesta.text.strip()
            if "Bad Map Key" in texto_respuesta or "Invalid" in texto_respuesta:
                print(f"Error en sensor {sensor}: MAP_KEY inválida o rechazada por la NASA")
                return None
            
            if not texto_respuesta or "No data available" in texto_respuesta:
                return None

            # Conversión a dataframe
            df = pd.read_csv(StringIO(texto_respuesta))
            if df.empty:
                return None
            # Estandarizamos los nombres de las columnas a minúsculas
            df.columns = [c.lower() for c in df.columns]

            # Saneamos columnas críticas asegurando tipos numéricos
            df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            df['frp'] = pd.to_numeric(df['frp'], errors='coerce').fillna(0.0)
            df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce').fillna(50.0)

            df = df.dropna(subset=['latitude', 'longitude'])
            df["satelite_sensor"] = sensor

            return df
        
        except Exception as e:
            print(f"Fallo crítico en hilo del sensor {sensor}: {e}")
            return None
    
    df_acumulado = []

    # Realizamos una petición secuencial segura
    for s in sensores:
        res = descargar_sensor(s, MAP_KEY)
        if res is not None and not res.empty:
            df_acumulado.append(res)

    if not df_acumulado:
        print("No se ha detectado ningún foco activo de VIIRS de las últimas 24 horas")
        return pd.DataFrame()

    # Concatenamos satélites
    df_total = pd.concat(df_acumulado, ignore_index=True)
    
    # --- ELIMINACIÓN INTELIGENTE DE DUPLICADOS ---
    # Si dos satélites pasan casi a la vez, pueden registrar coordenadas idénticas.
    # Redondeamos a 3 decimales (aprox. 100 metros de precisión) para detectar duplicados en el mismo foco.
    df_total['lat_redond'] = df_total['latitude'].round(3)
    df_total['lon_redond'] = df_total['longitude'].round(3)
    
    # Nos quedamos con el registro que tenga mayor FRP (intensidad de fuego) si hay solapamiento de coordenadas
    df_total = df_total.sort_values(by='frp', ascending=False)

    # Convertimos acq_date a string temporal para evitar conflictos de tipo en drop_duplicates
    df_total['acq_date_str'] = df_total['acq_date'].astype(str)
    df_total = df_total.drop_duplicates(subset=['lat_redond', 'lon_redond', 'acq_date', 'acq_time'], keep='first')
    df_total = df_total.drop(columns=['lat_redond', 'lon_redond', 'acq_date_str'])
 
    
    df_total['Region'] = df_total.apply(asociar_region, axis=1)
    df_espana = df_total[df_total['Region'].notna()].copy()

    if df_espana.empty:
        return pd.DataFrame()
    
    # Procesamiento final de tipos de datos y mapeos
    df_espana['acq_time_str'] = df_espana['acq_time'].astype(str).str.split('.').str[0].str.zfill(4)
    df_espana['datetime_str'] = df_espana['acq_date'].astype(str).str.split(' ').str[0] + ' ' + df_espana['acq_time_str'].str[:2] + ':' + df_espana['acq_time_str'].str[2:]
    df_espana['acq_date'] = pd.to_datetime(df_espana['datetime_str'], errors='coerce')
    
    if 'daynight' in df_espana.columns:
        df_espana['horario'] = df_espana['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
    else:
        df_espana['horario'] = '☀️ Día'

    df_espana['Año'] = df_espana['acq_date'].dt.year
    df_espana['Origen'] = df_espana.apply(clasificar_origen, axis=1)


    # --- GUARDADO AUTOMÁTICO EN BASE DE DATOS ---
    try:
        # 1. Conectamos a la base de datos (se creará el archivo si no existe)
        conexion = sqlite3.connect("Base-de-datos/pirovigia.db")
        
        # 2. Preparamos una copia del dataframe solo con las columnas que queremos guardar
        df_para_bd = df_espana.copy()
        
        # Renombramos la columna 'Origen' a 'origen_calculado' para que coincida con la tabla SQL
        df_para_bd.rename(columns={'Origen': 'origen_calculado'}, inplace=True)
        
        # Eliminamos columnas temporales que creaste para cálculos internos y que no están en SQL
        columnas_a_ignorar = ['datetime_str', 'acq_time_str', 'horario', 'Año', 'Region', 'satelite_sensor']
        df_para_bd = df_para_bd.drop(columns=[col for col in columnas_a_ignorar if col in df_para_bd.columns], errors='ignore')
        
        # 3. Guardamos en la tabla SQL (append = añade al final sin borrar lo anterior)
        df_para_bd.to_sql("detecciones_tiemporeal", conexion, if_exists="append", index=False)
        
        conexion.close()
        st.sidebar.success("💾 Datos guardados en la base de datos local.")
        
    except Exception as e:
        st.sidebar.error(f"Error al guardar en base de datos: {e}")

    
    return df_espana


# --- ALERTAS RÁPIDAS COPERNICUS --- 
@st.cache_data(ttl=600)
def descarga_alertas_terrestres(rango_dias=1):
    # Usamos la API key de tus secretos
    MAP_KEY = st.secrets.get("nasa_map_key", "31b2805e7d68126bba3d47e6a00ddeba") 
    
    # Caja delimitadora estricta para España
    bbox_espana = "-19,27,5,44"

    # Sensor MODIS (Terra y Aqua), estándar de calibración terrestre internacional
    sensor = "MODIS_NRT"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{sensor}/{bbox_espana}/{rango_dias}"
    
    try:
        respuesta = session.get(url, timeout=10)
        
        if respuesta.status_code != 200:
            st.sidebar.error(f"Error de conexión con la red MODIS/Copernicus: Código {respuesta.status_code}")
            return pd.DataFrame()
            
        if "Bad Map Key" in respuesta.text or not respuesta.text.strip():
            st.sidebar.warning("API Key de la NASA inválida o sin respuesta activa.")
            return pd.DataFrame()
            
        df_temp = pd.read_csv(StringIO(respuesta.text))
        
        if df_temp.empty:
            st.sidebar.info("Sin focos terrestres MODIS en las últimas 24 horas.")
            return pd.DataFrame()
            
        # Normalizamos nombres de columnas a minúsculas
        df_temp.columns = [col.lower() for col in df_temp.columns]
        
        # Estructuramos los datos para asimilarlos como Alerta Terrestre Oficial
        df_temp['Origen'] = "Alerta Terrestre Oficial"
        df_temp['Region'] = "Reporte Oficial"
        
        # MODIS usa confianza de 0 a 100 directamente en formato numérico
        df_temp['confidence'] = pd.to_numeric(df_temp['confidence'], errors='coerce').fillna(100.0)
        
        st.sidebar.success(f"✓ ¡{len(df_temp)} Alertas Terrestres (MODIS) integradas con éxito!")
        return df_temp

    except Exception as e:
        st.sidebar.error(f"Fallo de resolución o conexión: {str(e)}")
        return pd.DataFrame()
    
# --- PANEL DE CONTROL SIDEBAR --- 
st.sidebar.title("🗺️ Control de Feed")
st.sidebar.markdown("---")

modo_datos = st.sidebar.radio(
    "🛰️ Selecciona el origen de datos:",
    ["🔴 Satélites NASA (Tiempo real 24h España)", "📊 Histórico local"]
)

rango_dias = st.sidebar.select_slider(
    "📅 Ventana de tiempo (Días):",
    options=[1,2,3],
    value=1,
    help="Selecciona cuántos días atrás buscar en los servidores de la NASA"
)

if modo_datos == "🔴 Satélites NASA (Tiempo real 24h España)":
    df_sat = descarga_tiempo_real(rango_dias)
    df_terr = descarga_alertas_terrestres(rango_dias)

    if not df_sat.empty and not df_terr.empty:
        df_origen = pd.concat([df_sat, df_terr], ignore_index=True)
    elif not df_sat.empty:
        df_origen = df_sat
    else: df_origen = df_terr

    # Formateo de seguridad de tiempos y tipos para el DataFrame unificado
    if not df_origen.empty:
        # Aseguramos que acq_time sea string y tenga 4 caracteres (ej. '0430')
        df_origen['acq_time_str'] = df_origen['acq_time'].astype(str).str.split('.').str[0].str.zfill(4)
        df_origen['datetime_str'] = df_origen['acq_date'].astype(str).str.split(' ').str[0] + ' ' + df_origen['acq_time_str'].str[:2] + ':' + df_origen['acq_time_str'].str[2:]
        df_origen['acq_date'] = pd.to_datetime(df_origen['datetime_str'], errors='coerce').fillna(df_origen['acq_date'])
        
        # Mapeamos el horario
        if 'daynight' in df_origen.columns:
            df_origen['horario'] = df_origen['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
else:
    df_origen = cargar_csv()

# --- FILTROS TÁCTICOS ---
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros de amenaza")
# Unimos las categorías clásicas con las que realmente existan en los datos descargados
categorias_base = ['Incendio forestal', 'Zona industrial', 'Zona volcánica', 'Otros', 'Alerta Terrestre Oficial']
if not df_origen.empty:
    # Obtenemos los valores únicos reales y añadimos "Alerta Terrestre Oficial" si no estuviera ya
    opciones_disponibles = list(set(categorias_base) | set(df_origen['Origen'].unique()))
else:
    opciones_disponibles = categorias_base

filtro_origen = st.sidebar.multiselect(
    "Tipo de amenaza / Origen:",
    options=opciones_disponibles,
    default=opciones_disponibles  # Marca todas por defecto al iniciar
)

conf_min = st.sidebar.slider("Confianza Mínima Satélite (%)", 0, 100, 0)
frp_min = st.sidebar.slider("Potencia Infrarroja FRP > (MW)", 0, 50, 0)
usar_clusters = st.sidebar.checkbox("Agrupar focos densos (Clusters)", value=True)

# Filtro geográfico
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros geográficos")

# Extraemos las comunidades autónomas únicas que estén presentes en los datos
if not df_origen.empty and 'Region' in df_origen.columns:
    # Filtramos nulos por seguridad y ordenamos alfabéticamente
    comunidades_disponibles = sorted(df_origen['Region'].dropna().unique())
else:
    comunidades_disponibles = ["Andalucía", "Aragón", "Asturias", "Baleares", "Canarias", "Cantabria", "Castilla-La Mancha", "Castilla y León", "Cataluña", "Comunidad Valenciana", "Extremadura", "Galicia", "La Rioja", "Madrid", "Navarra", "País Vasco", "Región de Murcia"]

filtro_comunidades = st.sidebar.multiselect(
    "Selecciona la Comunidad Autónoma:",
    options=comunidades_disponibles,
    default=comunidades_disponibles, # Todas activas por defecto
    help="Filtra los focos térmicos según la comunidad asignada"
)

# Filtro anual (solo para CSV local)
if modo_datos == "📊 Histórico local" and not df_origen.empty:
    lista_anos = sorted(list(df_origen['Año'].unique()))
    if len(lista_anos) > 1:
        rango_anos = st.sidebar.slider("Filtrar por ventana anual:", min_value=lista_anos[0], max_value=lista_anos[-1], value=(lista_anos[0], lista_anos[-1]))
        df_origen = df_origen[(df_origen['Año'] >= rango_anos[0]) & (df_origen['Año'] <= rango_anos[1])]

# Aplicación final de los filtros
if not df_origen.empty:
    # Las Alertas Terrestres Oficiales se muestran siempre que estén seleccionadas, saltándose los filtros de calidad del satélite
    es_alerta_terrestre = df_origen['Origen'] == 'Alerta Terrestre Oficial'
    
    mask_comunidad = df_origen['Region'].isin(filtro_comunidades) | (df_origen['Region'].isna())

    mask_satelites = (df_origen['Origen'].isin(filtro_origen)) & \
                     (df_origen['confidence'] >= conf_min) & \
                     (df_origen['frp'] >= frp_min)
                     
    mask_final = ((mask_satelites) | (es_alerta_terrestre & df_origen['Origen'].isin(filtro_origen))) & mask_comunidad
    
    df_filtrado = df_origen[mask_final].copy()
else:
    df_filtrado = pd.DataFrame()

<<<<<<< HEAD:streamlit/app.py
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
=======
# Paleta de colores
paleta_activa = {
    'Incendio forestal': '#E63946',  # Rojo Alerta
    'Zona volcánica': '#FF6B00',            # Naranja Volcánico
    'Zona industrial': '#FFD166',   # Amarillo Industrial
    'Otros': '#4EA8DE',              # Azul / Otros
    'Alerta Terrestre Oficial': '#9B5DE5' # Violeta táctico para reportes de emergencias
}
>>>>>>> main:app.py

estilo_mapa = "OpenStreetMap (Base)"
tiles_dict = {
    "OpenStreetMap (Base)": "openstreetmap",
}

# --- CUADRO DE MANDO PRINCIPAL ---
st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>🛰️ Visor Táctico PiroVigía Live Pro</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>Origen de datos activo: <b>{modo_datos}</b></p>", unsafe_allow_html=True)

# Cálculo de KPIs
total_focos = len(df_filtrado)
max_potencia = df_filtrado['frp'].max() if total_focos > 0 else 0.0
focos_forestales = len(df_filtrado[df_filtrado['Origen'] == 'Incendio forestal']) if total_focos > 0 else 0
area_afectada_ratio = (focos_forestales / max(total_focos, 1) * 100) if total_focos > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("Focos Activos", f"{total_focos:,}")
with k2: st.metric("Riesgo Forestal", f"{focos_forestales:,}")
with k3: st.metric("FRP Máximo", f"{max_potencia:.1f} MW")
with k4: st.metric("Porcentaje de Incendios", f"{area_afectada_ratio:.1f}%")

<<<<<<< HEAD:streamlit/app.py
with k1: st.metric("Anomalías Activas", f"{alertas_activas:,}")
with k2: st.metric("Potencia FRP Promedio", f"{frp_promedio:.1f} MW")
with k3: st.metric("Máximo Térmico Detectado", f"{max_termico:.1f} K")
with k4: st.metric("Índice de Riesgo Forestal", f"{ratio_riesgo:.1f}%")
=======
st.markdown("### 🗺️ Situación Cartográfica Activa")

# Estilo para los Clusters de Folium
st.markdown("""
<style>
    .leaflet-marker-icon.folium-cluster-tactico {
        background: none !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)
>>>>>>> main:app.py

centro_inicial = [40.4167, -3.7037]
zoom_inicial = 6

if total_focos > 0:
    m = folium.Map(
        location=centro_inicial, 
        zoom_start=zoom_inicial, 
        tiles=tiles_dict[estilo_mapa],
        control_scale=True,
        attr='PiroVigía Multifeed'
    )
    
    if usar_clusters:
        icon_create_function = f"""
        function(cluster) {{
            var markers = cluster.getAllChildMarkers();
            var counts = {{'Incendio forestal': 0, 'Zona volcánica': 0, 'Zona industrial': 0, 'Otros': 0}};
            
<<<<<<< HEAD:streamlit/app.py
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
=======
            for (var i = 0; i < markers.length; i++) {{
                var options = markers[i].options;
                if (options && options.tipo_origen) {{
                    counts[options.tipo_origen]++;
                }}
            }}
>>>>>>> main:app.py
            
            var dominante = 'Incendio forestal';
            var maxCount = -1;
            for (var key in counts) {{
                if (counts[key] > maxCount) {{
                    maxCount = counts[key];
                    dominante = key;
                }}
            }}
            
            var childCount = cluster.getChildCount();
            var size = childCount < 10 ? 36 : (childCount < 100 ? 42 : 48);
            
            var colorBg = '{paleta_activa["Incendio forestal"]}';
            var borderStyle = 'border: 2px solid rgba(0,0,0,0.6);'; 

            if (dominante === 'Alerta Terrestre Oficial') {{
                colorBg ='{paleta_activa["Alerta Terrestre Oficial"]}';
                borderStyle = 'border: 2px solid #FFFFFF; box-shadow: 0 0 8px rgba(155,93,229,0.6);';
            }} else if (dominante === 'Zona volcánica' || dominante === 'Zona industrial' || dominante === 'Otros') {{
                colorBg = '{paleta_activa["Zona industrial"]}'; 
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
        group = MarkerCluster(name="Clusters Activos", icon_create_function=icon_create_function).add_to(m)
    else:
        group = folium.FeatureGroup(name="Focos Individuales").add_to(m)

# Renderizamos hasta 600 puntos para optimizar la carga del navegador
    df_render = df_filtrado.head(600)
    
    for idx, row in df_render.iterrows():
        tipo = row['Origen']
        color_foco = paleta_activa.get(tipo, '#E63946')
        # Evitamos errores si el frp es nulo o 0
        frp_seguro = row['frp'] if not pd.isnull(row['frp']) and row['frp'] > 0 else 5.0
        
        html_popup = f"""
        <div style='font-family: Arial, sans-serif; width: 230px;'>
            <h4 style='margin:0 0 5px 0; color:{color_foco};'>{tipo}</h4>
            <hr style='margin:5px 0; border:0; border-top:1px solid #ccc;'>
            <b>📅 Captura:</b> {row['acq_date'].strftime('%d/%m/%Y %H:%M:%S') if not pd.isnull(row['acq_date']) else 'N/A'}<br>
            <b>🔥 Energía FRP:</b> {row['frp']:.2f} MW<br>
            <b>🎯 Confianza:</b> {row['confidence']}%<br>
            <p style='color: #007BFF; margin: 5px 0 0 0; font-size: 11px;'><i>👉 Haz clic para ubicar localidad</i></p>
        </div>
        """
        
        radio_calculado = max(int(np.sqrt(row['frp']) * 2.2), 6)
        
        marker = folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=radio_calculado,
            popup=folium.Popup(html_popup, max_width=250),
            color=color_foco,
            fill=True,
            fill_color=color_foco,
            fill_opacity=0.6,
            weight=1.5
        )
        
        marker.options['tipo_origen'] = tipo
        marker.add_to(group)
        
    folium.LayerControl().add_to(m)
    mapa_retorno = st_folium(m, width="100%", height=550, key="tactical_perfect_map_v12")
else:
    st.info("💡 No hay datos satelitales disponibles con las tolerancias de filtrado elegidas.")
    mapa_retorno = None

# --- GEOLOCALIZACIÓN REVERSA EN TIEMPO REAL AL HACER CLIC ---
if total_focos > 0 and mapa_retorno and mapa_retorno.get("last_object_clicked") is not None:
    click_coords = mapa_retorno["last_object_clicked"]
    lat_click = click_coords.get("lat")
    lon_click = click_coords.get("lng")
    
    if lat_click and lon_click:
        @st.cache_data(ttl=3600)
        def obtener_localidad_click(lat, lon):
            try:
                geolocator = Nominatim(user_agent="pirovigia_live_click_multifeed")
                res = geolocator.reverse((lat, lon), exactly_one=True, timeout=3)
                if res and 'address' in res.raw:
                    addr = res.raw['address']
                    return addr.get('village', addr.get('town', addr.get('city', addr.get('municipality', 'Área no urbana / Forestal'))))
            except Exception as e:
                st.sidebar.exception(e)
            return "Zona aislada"

        nombre_pueblo = obtener_localidad_click(lat_click, lon_click)
        st.success(f"📍 **Punto térmico detectado:** Próximo a la localidad de **{nombre_pueblo}** ({lat_click:.4f}, {lon_click:.4f})")
else: 
    if total_focos > 0:
        st.info("💡 Pincha directamente en cualquiera de los círculos térmicos del mapa para calcular su pueblo o municipio aproximado.")

# --- ANALÍTICA DE DATOS ---
if total_focos > 0:
    st.markdown("---")
    c_grafico, c_tabla = st.columns([1, 2])
    
    with c_grafico:
        st.markdown("**Distribución Relativa por Naturaleza del Foco:**")
        fig_bar = px.histogram(
            df_filtrado, 
            y='Origen', 
            color='Origen',
            color_discrete_map=paleta_activa,
            orientation='h',
            height=280
        )
        fig_bar.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bar, width="stretch")
        
    with c_tabla:
        st.markdown("**Alertas del Feed Ordenadas de Mayor a Menor FRP:**")
        tabla_resumen = df_filtrado.sort_values(by='frp', ascending=False).head(15)[
            ['acq_date', 'latitude', 'longitude', 'frp', 'confidence', 'Origen', 'horario']
        ].copy()
        tabla_resumen['acq_date'] = tabla_resumen['acq_date'].dt.strftime('%H:%M:%S (%d/%m/%Y)')
        tabla_resumen.columns = ['Captura Satélite', 'Latitud', 'Longitud', 'FRP (MW)', 'Conf (%)', 'Clasificación', 'horario']
        st.dataframe(tabla_resumen, width="stretch", hide_index=True)