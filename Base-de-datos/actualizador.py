import requests
import pandas as pd
from io import StringIO
import sqlite3
from Backend import DB_NAME, inicializar_base_de_datos

def descargar_actualizar():
    url= 'https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv'
    print('iniciando descarga de datos')

    try:
        respuesta = requests.get(url, timeout=15)
        if respuesta.status_code != 200:
            print(f'No se pudo conectar con los datos de la NASA: {respuesta.status_code}')
            return
        df_rd = pd.read_csv(StringIO(respuesta.text))
        print(f'Descargadas {len(df_rd)} anomalías')

        df_europa = df_rd[
            ((df_rd['latitude'] >= 34.0) & (df_rd['latitude'] <= 72.0)) &
            ((df_rd['longitude'] >= -25.0) & (df_rd['longitude'] <= 68.0))
        ].copy()

        df_espana = df_rd[
            ((df_rd['latitude'] >= 35.0) & (df_rd['latitude'] <= 44.0)) & ((df_rd['longitude'] >= -10.0) & (df_rd['longitude'] <= 5.0)) |
            ((df_rd['latitude'] >= 27.0) & (df_rd['latitude'] <= 29.0)) & ((df_rd['longitude'] >= -18.5) & (df_rd['longitude'] <= -13.0))
        ].copy()

        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()

        columnas_europa = [
            'latitude', 'longitude', 'brightness', 'scan', 'track', 'acq_date',
            'acq_time', 'satellite', 'instrument', 'confidence', 'version',
            'bright_t31', 'frp', 'daynight', 'type' 
        ]
        insertar_en_tabla(cursor, 'detecciones', df_europa, columnas_europa)
        

        columnas_espana = [
            'latitude', 'longitude', 'brightness', 'scan', 'track', 'acq_date',
            'acq_time', 'satellite', 'instrument', 'confidence', 'version',
            'bright_t31', 'frp', 'daynight'
        ]
        insertar_en_tabla(cursor, 'españa', df_espana, columnas_espana)

        conexion.commit()
        conexion.close()
        print('Datos actualizados correctamente en la base de datos.')

    except Exception as e:
        print(f'Error al descargar o procesar los datos: {e}')

def insertar_en_tabla(cursor, nombre_tabla, dataframe, columnas):
    if dataframe.empty:
        print(f'No hay datos para insertar en la tabla {nombre_tabla}.')
        return
    
    df_filtrado = dataframe[[col for col in columnas if col in dataframe.columns]].copy()

    placeholders = ", ".join(["?"] * len(columnas))
    cols = ", ".join(columnas)

    query = f"INSERT OR IGNORE INTO {nombre_tabla} ({cols}) VALUES ({placeholders})"

    datos_tuplas = [tuple(x) for x  in df_filtrado.to_numpy()]

    cursor.executemany(query, datos_tuplas)
    print(f'Procesadas {len(datos_tuplas)} filas para la tabla {nombre_tabla}.')

if __name__ == "__main__":
    inicializar_base_de_datos()
    descargar_actualizar()



