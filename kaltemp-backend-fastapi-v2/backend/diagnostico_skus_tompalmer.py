"""
Diagnóstico READ-ONLY -- SKUs de Tom Palmer sin categorizar

Lista, para CANAL = 'Tom Palmer', qué SKU/Producto está detrás de cada
venta "Sin Tipo" / "Sin Categoría Mapeada", para poder asignarles una
categoría real que calce con las campañas (Hot Tub, Pérgolas,
Herramientas, Mangueras, Iluminación, etc.)

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_skus_tompalmer.py
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI))

load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))
print(f"💾 DB_FILE: {DB_FILE}\n")

con = duckdb.connect(DB_FILE, read_only=True)

pd.set_option("display.max_rows", 200)
pd.set_option("display.width", 160)

print("-" * 70)
print("SKUs de Tom Palmer sin categoría real (últimos 90 días)")
print("-" * 70)

df = con.execute("""
    SELECT
        SKU_BSALE,
        PRODUCTO,
        CATEGORIA,
        COUNT(DISTINCT DOCUMENTO) AS txs,
        SUM(CANTIDAD) AS unidades,
        SUM(BRUTO_TOTAL) AS venta
    FROM ventas
    WHERE UPPER(CANAL) = 'TOM PALMER'
      AND CAST(FECHA_OBJ AS DATE) >= CURRENT_DATE - INTERVAL 90 DAY
      AND (CATEGORIA IS NULL OR CATEGORIA IN ('Sin Tipo', 'Sin Categoría Mapeada', ''))
    GROUP BY SKU_BSALE, PRODUCTO, CATEGORIA
    ORDER BY venta DESC
""").df()

print(df.to_string(index=False))
print(f"\nTotal SKUs distintos: {df['SKU_BSALE'].nunique()}")
print(f"Venta total sin categorizar: {df['venta'].sum():,.0f}")

con.close()