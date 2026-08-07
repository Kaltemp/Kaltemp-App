import os
import pandas as pd
from sync_marketing import descargar_csv_google_sheet, GOOGLE_SHEET_MKT_ID

df_piezas = descargar_csv_google_sheet(GOOGLE_SHEET_MKT_ID, ["Piezas Graficas", "Piezas Gráficas", "Piezas", "Imágenes"])

print("\n=== COLUMNAS EN PIEZAS GRAFICAS ===")
print(df_piezas.columns.tolist())

print("\n=== CONTENIDO DE PIEZAS GRAFICAS (Primeras 20 filas) ===")
if not df_piezas.empty:
    for idx, row in df_piezas.head(20).iterrows():
        print(f"Fila {idx+1}: {dict(row)}")
else:
    print("❌ La pestaña 'Piezas Graficas' se descargó vacía.")