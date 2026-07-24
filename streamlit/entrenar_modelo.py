import os
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json

# 1. Definir rutas correctamente desde la carpeta streamlit
base_dir = os.path.dirname(os.path.abspath(__file__))
input_csv = os.path.join(base_dir, "..", "data", "extraccion_basedatos", "detecciones_unificadas.csv")

output_csv = os.path.join(base_dir, "predicciones_prophet.csv")
output_json = os.path.join(base_dir, "prophet_model.json")

# 2. Cargar los datos
print(f"Cargando datos desde: {input_csv}")
df = pd.read_csv(input_csv, low_memory=False)

# 3. Preprocesamiento básico
if 'acq_date' in df.columns:
    df['acq_date'] = pd.to_datetime(df['acq_date'])
    df.set_index('acq_date', inplace=True)
    df.sort_index(inplace=True)

# Filtrar columnas no deseadas si están presentes
columns_to_drop = ['acq_time', 'satellite', 'instrument', 'version', 'daynight']
existing_to_drop = [col for col in columns_to_drop if col in df.columns]
if existing_to_drop:
    df.drop(columns=existing_to_drop, inplace=True)

# Forzar que 'frp' sea numérico y extraer únicamente esa columna para el resampleo
df['frp'] = pd.to_numeric(df['frp'], errors='coerce')
df_resampled = df[['frp']].resample('D').median()
df_resampled.dropna(inplace=True)

# 4. Formatear datos para Prophet (ds y y)
df_prophet = df_resampled.reset_index().rename(columns={'acq_date': 'ds', 'frp': 'y'})

# 5. Inicializar y entrenar el modelo Prophet
print("Entrenando el modelo Prophet...")
model = Prophet()
model.fit(df_prophet)

# 6. Generar predicciones
forecast = model.predict(df_prophet)

# 7. Guardar las predicciones en un CSV
forecast.to_csv(output_csv, index=False)
print(f"Predicciones guardadas en: {output_csv}")

# 8. Guardar el modelo Prophet en un JSON usando model_to_json
with open(output_json, 'w') as fout:
    fout.write(model_to_json(model))
print(f"Modelo guardado en formato JSON en: {output_json}")