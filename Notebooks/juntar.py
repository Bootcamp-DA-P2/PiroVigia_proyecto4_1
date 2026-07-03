import glob
import os
import pandas as pd

archivos_csv = glob.glob("modis_2024_*.csv")

lista_dataframes = []

for archivo in archivos_csv:
    nombre_archivo = os.path.basename(archivo)

   
    nombre_pais = (
        nombre_archivo.replace("modis_2024_", "")
        .replace(".csv", "")
        .replace("_", " ")
    )

    df = pd.read_csv(archivo)

    df["pais"] = nombre_pais

    lista_dataframes.append(df)

df_final = pd.concat(lista_dataframes, ignore_index=True)

df_final.to_csv("modis_2024_unificado.csv", index=False)

print(
    f"¡Hecho! Se han unificado {len(archivos_csv)} archivos en 'modis_2024_unificado.csv' sin errores de nombres."
)