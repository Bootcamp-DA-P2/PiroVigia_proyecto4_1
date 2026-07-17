import sqlite3
import pandas as pd

DB_NAME = "pirovigia.db"

def obtener_conexion():
    """Establece una conexión con la base de datos SQLite."""
    return sqlite3.connect(DB_NAME)

def inicializar_base_de_datos():
    """Crea las tablas necesarias en la base de datos si no existen."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Crear tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detecciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL DEFAULT NULL,
            longitude REAL DEFAULT NULL,
            brightness REAL DEFAULT NULL,
            scan REAL DEFAULT NULL,
            track REAL DEFAULT NULL,
            acq_date TEXT DEFAULT NULL,
            acq_time INTEGER DEFAULT NULL,
            satellite TEXT DEFAULT NULL,
            instrument TEXT DEFAULT 'MODIS',
            confidence INTEGER DEFAULT NULL,
            version TEXT DEFAULT NULL,
            bright_t31 REAL DEFAULT NULL,
            frp REAL DEFAULT NULL,
            daynight TEXT DEFAULT NULL,
            type INTEGER,
            pais TEXT DEFAULT NULL
        )''')

    # Crear tabla de productos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS españa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL DEFAULT NULL,
        longitude REAL DEFAULT NULL,
        brightness REAL DEFAULT NULL,
        scan REAL DEFAULT NULL,
        track REAL DEFAULT NULL,
        acq_date TEXT DEFAULT NULL,
        acq_time INTEGER DEFAULT NULL,
        satellite TEXT DEFAULT NULL,
        instrument TEXT DEFAULT 'MODIS',
        confidence INTEGER DEFAULT NULL,
        version TEXT DEFAULT NULL,
        bright_t31 REAL DEFAULT NULL,
        frp REAL DEFAULT NULL,
        daynight TEXT DEFAULT NULL
    )''')

    cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_detecciones_unicas 
    ON detecciones (latitude, longitude, acq_date, acq_time, satellite)
    ''')
    
    cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_españa_unicas 
    ON españa (latitude, longitude, acq_date, acq_time, satellite)
    ''')

    conexion.commit()
    conexion.close()

def guardar_deteccion(df, tabla="detecciones"):
    """Guarda un DataFrame de Pandas en la tabla especificada.
    Filtra solo las columnas que existen en el esquema SQL para evitar errores."""
    if df.empty:
        return
    conexion = obtener_conexion()

    columnas_sql = [
        "latitude", "longitude", "brightness", "scan", "track",
        "acq_date", "acq_time", "satellite", "instrument",
        "confidence", "version", "bright_t31", "frp",
        "daynight", "type", "pais"
    ]

    if tabla == "detecciones":
        columnas_sql.append("type")

    df_to_save = df[[col for col in columnas_sql if col in df.columns]].copy()

    if 'acq_date' in df_to_save.columns:
        df_to_save['acq_date'] = df_to_save['acq_date'].astype(str)

    df_to_save.to_sql(tabla, conexion, if_exists='append', index=False)

def obtener_detecciones():
    """Obtiene todas las detecciones de la base de datos y las devuelve como un DataFrame de Pandas."""
    conexion = obtener_conexion()
    query = "SELECT * FROM detecciones"
    df = pd.read_sql_query(query, conexion)
    conexion.close()
    return df
    



