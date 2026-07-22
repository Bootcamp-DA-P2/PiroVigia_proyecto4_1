import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import warnings
import requests
import swifter
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
    "User-Agent": "PiroVigia/2.0",
    "Accept-Encoding": "gzip, deflate"
})
# Reutiliza conexiones abiertas para no renegociar TLS en cada llamada
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount('https://', adapter)

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(
    page_title="PiroVigía Localizador v1.0",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CLASIFICADOR HEURÍSTICO DE FOCOS TÉRMICOS ---
def clasificar_origen(row):
    lat, lon = row['latitude'], row['longitude']
    frp = row['frp']
    horario = row['horario']
    bright = row.get('brightness', row.get('bright_ti24', 300.0))

    if (27.5 <= lat <= 29.5) and (-18.0 <= lon <= -13.0):
        if frp > 120 and bright > 345:
            return 'Zona volcánica'

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
        
    if frp < 3.0 and horario == '☀️ Día':
        return 'Otros'
    
    return 'Incendio forestal'

@st.cache_data(ttl=3600)  # Caché de 1 hora
def cargar_historico_sqlite(db_path="Base-de-datos/pirovigia.db"):
    try:
        conn = sqlite3.connect(db_path)
        
        # Comprobamos si la tabla de histórico existe
        query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='detecciones';"
        if pd.read_sql_query(query_check, conn).empty:
            conn.close()
            st.warning("⚠️ La tabla 'detecciones' no existe en la base de datos.")
            return pd.DataFrame()
        
        df_bd = pd.read_sql_query("SELECT * FROM detecciones", conn)
        conn.close()
        
        if not df_bd.empty:
            # 1. Normalizar columnas a minúsculas para consistencia
            df_bd.columns = [c.lower() for c in df_bd.columns]
            
            # Asegurar numéricos clave
            for col in ['latitude', 'longitude', 'frp', 'confidence']:
                if col in df_bd.columns:
                    df_bd[col] = pd.to_numeric(df_bd[col], errors='coerce').fillna(0.0)
            
            # 2. Formato de fecha y Año
            if 'acq_date' in df_bd.columns:
                df_bd['acq_date'] = pd.to_datetime(df_bd['acq_date'], errors='coerce')
                df_bd['Año'] = df_bd['acq_date'].dt.year
            
            # 3. Calcular 'horario' si no existe
            if 'horario' not in df_bd.columns:
                if 'daynight' in df_bd.columns:
                    df_bd['horario'] = df_bd['daynight'].astype(str).str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
                else:
                    df_bd['horario'] = '☀️ Día'
            
            # 4. Asignar 'Region' si no existe
            if 'region' in df_bd.columns:
                df_bd['Region'] = df_bd['region']
            elif 'Region' not in df_bd.columns:
                df_bd['Region'] = df_bd.apply(asociar_region, axis=1)
                
            # 5. Clasificar 'Origen' si no existe
            if 'origen' in df_bd.columns:
                df_bd['Origen'] = df_bd['origen']
            elif 'Origen' not in df_bd.columns:
                df_bd['Origen'] = df_bd.apply(clasificar_origen, axis=1)

        return df_bd

    except Exception as e:
        st.error(f"Error al cargar el histórico desde SQLite: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300) 

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

def descarga_tiempo_real(rango_dias=1):
    try: 
        MAP_KEY = st.secrets["nasa_map_key"]
    except Exception:
        MAP_KEY = "31b2805e7d68126bba3d47e6a00ddeba"
    
    bbox_espana = "-19,27,5,44"
    sensores = ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT"]

    def descargar_sensor(sensor, api_key):
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{MAP_KEY}/{sensor}/{bbox_espana}/{rango_dias}"
        )
        try:
            respuesta = session.get(url, timeout=20)
            if respuesta.status_code != 200:
                print(f"Error en sensor {sensor}: Código de respuesta {respuesta.status_code}")
                return None
            texto_respuesta = respuesta.text.strip()
            if "Bad Map Key" in texto_respuesta or "Invalid" in texto_respuesta:
                print(f"Error en sensor {sensor}: MAP_KEY inválida o rechazada por la NASA")
                return None
            
            if not texto_respuesta or "No data available" in texto_respuesta:
                return None

            df = pd.read_csv(StringIO(texto_respuesta))
            if df.empty:
                return None
            df.columns = [c.lower() for c in df.columns]

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

    for s in sensores:
        res = descargar_sensor(s, MAP_KEY)
        if res is not None and not res.empty:
            df_acumulado.append(res)

    if not df_acumulado:
        print("No se ha detectado ningún foco activo de VIIRS de las últimas 24 horas")
        return pd.DataFrame()

    df_total = pd.concat(df_acumulado, ignore_index=True)
    
    df_total['lat_redond'] = df_total['latitude'].round(3)
    df_total['lon_redond'] = df_total['longitude'].round(3)
    
    df_total = df_total.sort_values(by='frp', ascending=False)

    df_total['acq_date_str'] = df_total['acq_date'].astype(str)
    df_total = df_total.drop_duplicates(subset=['lat_redond', 'lon_redond', 'acq_date', 'acq_time'], keep='first')
    df_total = df_total.drop(columns=['lat_redond', 'lon_redond', 'acq_date_str'])
 
    df_total['Region'] = df_total.apply(asociar_region, axis=1)
    df_espana = df_total[df_total['Region'].notna()].copy()

    if df_espana.empty:
        return pd.DataFrame()
    
    df_espana['acq_time_str'] = df_espana['acq_time'].astype(str).str.split('.').str[0].str.zfill(4)
    df_espana['datetime_str'] = df_espana['acq_date'].astype(str).str.split(' ').str[0] + ' ' + df_espana['acq_time_str'].str[:2] + ':' + df_espana['acq_time_str'].str[2:]
    df_espana['acq_date'] = pd.to_datetime(df_espana['datetime_str'], errors='coerce')
    
    if 'daynight' in df_espana.columns:
        df_espana['horario'] = df_espana['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')
    else:
        df_espana['horario'] = '☀️ Día'

    df_espana['Año'] = df_espana['acq_date'].dt.year
    df_espana['Origen'] = df_espana.apply(clasificar_origen, axis=1)


    return df_espana


@st.cache_data(ttl=600)
def descarga_alertas_terrestres(rango_dias=1):
    MAP_KEY = st.secrets.get("nasa_map_key", "31b2805e7d68126bba3d47e6a00ddeba") 
    
    bbox_espana = "-19,27,5,44"

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
            
        df_temp.columns = [col.lower() for col in df_temp.columns]
        
        df_temp['Origen'] = "Alerta Terrestre Oficial"
        df_temp['Region'] = "Reporte Oficial"
        
        df_temp['confidence'] = pd.to_numeric(df_temp['confidence'], errors='coerce').fillna(100.0)
        
        st.sidebar.success(f"✓ ¡{len(df_temp)} Alertas Terrestres (MODIS) integradas con éxito!")
        return df_temp

    except Exception as e:
        st.sidebar.error(f"Fallo de resolución o conexión: {str(e)}")
        return pd.DataFrame()
    
def guardar_en_sqlite(df, db_path="Base-de-datos/pirovigia.db"):
    if df.empty:
        return False, "No hay datos para guardar."
    
    # 1. Aseguramos que la columna de fecha sea texto para SQLite
    df_sql = df.copy()
    if 'acq_date' in df_sql.columns:
        df_sql['acq_date'] = df_sql['acq_date'].astype(str)
        
    try:
        # 2. Conectamos a la base de datos (se crea el archivo si no existe)
        conn = sqlite3.connect(db_path)
        
        # 3. Volcamos el dataframe a una tabla temporal
        df_sql.to_sql("temp_focos", conn, if_exists="replace", index=False)
        
        # 4. Creamos la tabla principal asegurando una clave ÚNICA 
        # (Latitud, Longitud, Fecha y Hora) para evitar duplicados
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deteccion_tiemporeal (
                latitude REAL,
                longitude REAL,
                frp REAL,
                confidence REAL,
                acq_date TEXT,
                acq_time TEXT,
                satelite_sensor TEXT,
                Region TEXT,
                Origen TEXT,
                horario TEXT,
                UNIQUE(latitude, longitude, acq_date, acq_time)
            )
        """)
        
        # 5. Insertamos de la temporal a la principal ignorando los que ya existan
        # Obtenemos las columnas comunes para evitar errores si falta alguna
        columnas_df = [c for c in df_sql.columns if c in ['latitude', 'longitude', 'frp', 'confidence', 'acq_date', 'acq_time', 'satelite_sensor', 'Region', 'Origen', 'horario']]
        columnas_str = ", ".join(columnas_df)
        
        cursor = conn.execute(f"""
            INSERT OR IGNORE INTO deteccion_tiemporeal ({columnas_str})
            SELECT {columnas_str} FROM temp_focos
        """)
        
        filas_insertadas = cursor.rowcount
        conn.commit()
        return True, f"Datos guardados. {filas_insertadas} focos nuevos añadidos a la BD."
        
    except Exception as e:
        return False, f"Error al guardar: {e}"
    finally:
        conn.close()

@st.cache_data(ttl=60) # Refresca la caché cada 60s por si guardas datos nuevos
def cargar_tiemporeal_sqlite(db_path="Base-de-datos/pirovigia.db"):
    try:
        conn = sqlite3.connect(db_path)
        
        # Comprobamos si la tabla existe primero
        query_check = "SELECT name FROM sqlite_master WHERE type='table' AND name='deteccion_tiemporeal';"
        if pd.read_sql_query(query_check, conn).empty:
            conn.close()
            st.warning("La base de datos SQLite está vacía. Guarda datos en tiempo real primero.")
            return pd.DataFrame()
        
        df_bd = pd.read_sql_query("SELECT * FROM deteccion_tiemporeal", conn)
        conn.close()
        
        if not df_bd.empty:
            df_bd['acq_date'] = pd.to_datetime(df_bd['acq_date'], errors='coerce')
            df_bd['Año'] = df_bd['acq_date'].dt.year
            
        return df_bd
    except Exception as e:
        st.error(f"Error al cargar la base de datos SQLite: {e}")
        return pd.DataFrame()
    
# --- PANEL DE CONTROL SIDEBAR --- 
# --- PANEL DE CONTROL SIDEBAR --- 
st.sidebar.title("🗺️ Control de Feed")
st.sidebar.markdown("---")

modo_datos = st.sidebar.radio(
    "🛰️ Selecciona el origen de datos:",
    [
        "🔴 Satélites NASA (Tiempo real 24h España)", 
        "📊 Histórico Base de Datos (SQLite)",
        "🗄️ Tiempo real Base de Datos (SQLite)"
    ]
)

rango_dias = st.sidebar.select_slider(
    "📅 Ventana de tiempo (Días):",
    options=[1, 2, 3],
    value=1,
    help="Selecciona cuántos días atrás buscar en los servidores de la NASA"
)

# --- PROCESAMIENTO Y AUTO-GUARDADO ---
if modo_datos == "🔴 Satélites NASA (Tiempo real 24h España)":
    df_sat = descarga_tiempo_real(rango_dias)
    df_terr = descarga_alertas_terrestres(rango_dias)

    if not df_sat.empty and not df_terr.empty:
        df_origen = pd.concat([df_sat, df_terr], ignore_index=True)
    elif not df_sat.empty:
        df_origen = df_sat
    else: 
        df_origen = df_terr

    if not df_origen.empty:
        df_origen['acq_time_str'] = df_origen['acq_time'].astype(str).str.split('.').str[0].str.zfill(4)
        df_origen['datetime_str'] = df_origen['acq_date'].astype(str).str.split(' ').str[0] + ' ' + df_origen['acq_time_str'].str[:2] + ':' + df_origen['acq_time_str'].str[2:]
        df_origen['acq_date'] = pd.to_datetime(df_origen['datetime_str'], errors='coerce').fillna(df_origen['acq_date'])
        
        if 'daynight' in df_origen.columns:
            df_origen['horario'] = df_origen['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')

        # -----------------------------------------------------------------
        # 🔄 AUTO-GUARDADO AUTOMÁTICO EN SQLITE AL ENTRAR / ACTUALIZAR
        # -----------------------------------------------------------------
        exito, mensaje = guardar_en_sqlite(df_origen)
        if exito:
            cargar_tiemporeal_sqlite.clear()  # Limpiamos la caché del histórico SQLite para reflejar los nuevos datos inmediatamente
            st.sidebar.caption("🟢 **BD Sincronizada:** Feed de la NASA guardado automáticamente.")
        else:
            st.sidebar.caption(f"⚠️ **BD Estado:** {mensaje}")

elif modo_datos == "📊 Histórico Base de Datos (SQLite)":
    df_origen = cargar_historico_sqlite()
elif modo_datos == "🗄️ Tiempo real Base de Datos (SQLite)":
    df_origen = cargar_tiemporeal_sqlite()
    
    # Aplicamos el filtro del slider de la ventana de tiempo (rango_dias)
    if not df_origen.empty:
        df_origen['acq_date'] = pd.to_datetime(df_origen['acq_date'], errors='coerce')
        hoy_medianoche = pd.Timestamp.now().normalize()
        fecha_limite = hoy_medianoche - pd.Timedelta(days=rango_dias - 1)
        df_origen = df_origen[df_origen['acq_date'] >= fecha_limite]

modos_historicos = ["📊 Histórico Base de Datos (SQLite)", "🗄️ Tiempo real Base de Datos (SQLite)"]

if modo_datos in modos_historicos and not df_origen.empty:
    if 'Año' in df_origen.columns:
        lista_anos = sorted(list(df_origen['Año'].dropna().unique()))
        if len(lista_anos) > 1:
            rango_anos = st.sidebar.slider(
                "Filtrar por ventana anual:", 
                min_value=int(lista_anos[0]), 
                max_value=int(lista_anos[-1]), 
                value=(int(lista_anos[0]), int(lista_anos[-1]))
            )
            df_origen = df_origen[(df_origen['Año'] >= rango_anos[0]) & (df_origen['Año'] <= rango_anos[1])]

# --- FILTROS TÁCTICOS ---
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros de amenaza")
categorias_base = ['Incendio forestal', 'Zona industrial', 'Zona volcánica', 'Otros', 'Alerta Terrestre Oficial']
if not df_origen.empty and 'Origen' in df_origen.columns:
    opciones_disponibles = list(set(categorias_base) | set(df_origen['Origen'].dropna().unique()))
else:
    opciones_disponibles = categorias_base
    
filtro_origen = st.sidebar.multiselect(
    "Tipo de amenaza / Origen:",
    options=opciones_disponibles,
    default=opciones_disponibles
)

conf_min = st.sidebar.slider("Confianza Mínima Satélite (%)", 0, 100, 0)
frp_min = st.sidebar.slider("Potencia Infrarroja FRP > (MW)", 0, 50, 0)
usar_clusters = st.sidebar.checkbox("Agrupar focos densos (Clusters)", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros geográficos")

if not df_origen.empty and 'Region' in df_origen.columns:
    comunidades_disponibles = sorted(df_origen['Region'].dropna().unique())
else:
    comunidades_disponibles = ["Andalucía", "Aragón", "Asturias", "Baleares", "Canarias", "Cantabria", "Castilla-La Mancha", "Castilla y León", "Cataluña", "Comunidad Valenciana", "Extremadura", "Galicia", "La Rioja", "Madrid", "Navarra", "País Vasco", "Región de Murcia"]

filtro_comunidades = st.sidebar.multiselect(
    "Selecciona la Comunidad Autónoma:",
    options=comunidades_disponibles,
    default=comunidades_disponibles,
    help="Filtra los focos térmicos según la comunidad asignada"
)


if not df_origen.empty:
    es_alerta_terrestre = df_origen['Origen'] == 'Alerta Terrestre Oficial'
    
    mask_comunidad = df_origen['Region'].isin(filtro_comunidades) | (df_origen['Region'].isna())

    mask_satelites = (df_origen['Origen'].isin(filtro_origen)) & \
                     (df_origen['confidence'] >= conf_min) & \
                     (df_origen['frp'] >= frp_min)
                     
    mask_final = ((mask_satelites) | (es_alerta_terrestre & df_origen['Origen'].isin(filtro_origen))) & mask_comunidad
    
    df_filtrado = df_origen[mask_final].copy()
else:
    df_filtrado = pd.DataFrame()

paleta_activa = {
    'Incendio forestal': '#E63946',
    'Zona volcánica': '#FF6B00',
    'Zona industrial': '#FFD166',
    'Otros': '#4EA8DE',
    'Alerta Terrestre Oficial': '#9B5DE5'
}

estilo_mapa = "OpenStreetMap (Base)"
tiles_dict = {
    "OpenStreetMap (Base)": "openstreetmap",
}

# --- CUADRO DE MANDO PRINCIPAL ---
st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>🛰️ Visor Táctico PiroVigía Live Pro</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: gray;'>Origen de datos activo: <b>{modo_datos}</b></p>", unsafe_allow_html=True)

total_focos = len(df_filtrado)
max_potencia = df_filtrado['frp'].max() if total_focos > 0 else 0.0
focos_forestales = len(df_filtrado[df_filtrado['Origen'] == 'Incendio forestal']) if total_focos > 0 else 0
area_afectada_ratio = (focos_forestales / max(total_focos, 1) * 100) if total_focos > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("Focos Activos", f"{total_focos:,}")
with k2: st.metric("Riesgo Forestal", f"{focos_forestales:,}")
with k3: st.metric("FRP Máximo", f"{max_potencia:.1f} MW")
with k4: st.metric("Porcentaje de Incendios", f"{area_afectada_ratio:.1f}%")

st.markdown("### 🗺️ Situación Cartográfica Activa")

st.markdown("""
<style>
    .leaflet-marker-icon.folium-cluster-tactico {
        background: none !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

centro_inicial = [40.4167, -3.7037]
zoom_inicial = 6

# --- FIX DE RENDIMIENTO: límite real de puntos a dibujar ---
# Antes se calculaba df_render pero el bucle usaba df_filtrado completo,
# lo que en modo histórico podía intentar dibujar cientos de miles de
# CircleMarker. Ahora limitamos de verdad y usamos una muestra aleatoria
# representativa cuando se supera el límite.
LIMITE_RENDER = 1500

if total_focos > LIMITE_RENDER:
    # Selecciona directamente los 1.500 focos de mayor potencia térmica
    df_render = df_filtrado.sort_values(by='frp', ascending=False).head(LIMITE_RENDER)
    
    st.caption(
        f"⚠️ Mostrando los {LIMITE_RENDER:,} focos con mayor FRP de un total de {total_focos:,} "
        f"para mantener el mapa fluido."
    )
else:
    df_render = df_filtrado

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
            
            for (var i = 0; i < markers.length; i++) {{
                var options = markers[i].options;
                if (options && options.tipo_origen) {{
                    counts[options.tipo_origen]++;
                }}
            }}
            
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

    # --- FIX: iteramos sobre df_render (limitado), no sobre df_filtrado completo ---
    for row in df_render.itertuples():
        tipo = getattr(row, 'Origen')
        color_foco = paleta_activa.get(tipo, '#E63946')
        frp_val = getattr(row, 'frp', 5.0)
        frp_seguro = frp_val if not pd.isnull(frp_val) and frp_val > 0 else 5.0
    
        fecha_val = getattr(row, 'acq_date')
        fecha_fmt = fecha_val.strftime('%d/%m/%Y %H:%M:%S') if pd.notnull(fecha_val) else 'N/A'
        
        html_popup = f"""
        <div style='font-family: Arial, sans-serif; width: 230px;'>
            <h4 style='margin:0 0 5px 0; color:{color_foco};'>{tipo}</h4>
            <hr style='margin:5px 0; border:0; border-top:1px solid #ccc;'>
            <b>📅 Captura:</b> {fecha_fmt}<br>
            <b>🔥 Energía FRP:</b> {frp_seguro:.2f} MW<br>
            <b>🎯 Confianza:</b> {getattr(row, 'confidence', 50)}%<br>
            <p style='color: #007BFF; margin: 5px 0 0 0; font-size: 11px;'><i>👉 Haz clic para ubicar localidad</i></p>
        </div>
        """
        
        radio_calculado = max(int(np.sqrt(frp_seguro)* 2.2), 6)
        
        marker = folium.CircleMarker(
            location=[getattr(row,'latitude'), getattr(row, 'longitude')],
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