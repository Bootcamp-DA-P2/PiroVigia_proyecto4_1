import pandas as pd
import numpy as np

# Reutilizamos exactamente tus funciones originales
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

print("⏳ Procesando datos del CSV histórico...")
df = pd.read_csv("data/20-26focos_calor.csv")
df.columns = [col.split(',')[0].lower() for col in df.columns]

df['acq_time_str'] = df['acq_time'].astype(str).str.zfill(4)
df['datetime_str'] = df['acq_date'] + ' ' + df['acq_time_str'].str[:2] + ':' + df['acq_time_str'].str[2:]
df['acq_date'] = pd.to_datetime(df['datetime_str'], errors='coerce')
df['horario'] = df['daynight'].str.strip().str.upper().map({'D': '☀️ Día', 'N': '🌙 Noche'}).fillna('☀️ Día')

if not pd.api.types.is_numeric_dtype(df['confidence']):
    df['confidence'] = (
        df['confidence'].astype(str).str.strip().str.lower()
        .map({'l': 30.0, 'n': 70.0, 'h': 100.0})
        .fillna(50.0)
    )
else:
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce').fillna(50.0)

df['Año'] = df['acq_date'].dt.year

# Ejecutamos las clasificaciones pesadas
df['Origen'] = df.apply(clasificar_origen, axis=1)
df['Region'] = df.apply(asociar_region, axis=1)

# Guardamos el resultado procesado en la carpeta data/
df.to_feather("data/20-26focos_calor_procesado.feather")
print("✅ ¡Archivo 'data/20-26focos_calor_procesado.feather' generado con éxito!")