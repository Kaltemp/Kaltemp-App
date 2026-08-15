"""
Diagnóstico READ-ONLY -- 2 preguntas:
  1) ¿ES_GLOSA_SERVICIO está bien marcado para las líneas de despacho que
     siguen apareciendo en las tablas de producto/categoría?
  2) ¿Qué SKUs concretos son la categoría "Sin Tipo" (207 unidades en el
     gráfico de Cumplimiento Ventas)?

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_despacho_sintipo.py
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))
print(f"💾 DB_FILE: {DB_FILE}\n")

con = duckdb.connect(DB_FILE, read_only=True)
pd.set_option("display.max_rows", 100)
pd.set_option("display.width", 160)

print("-" * 70)
print("1) ¿La columna ES_GLOSA_SERVICIO existe y qué valores tiene?")
print("-" * 70)
cols = [c[0] for c in con.execute("SELECT * FROM ventas LIMIT 0").description]
print(f"¿Existe ES_GLOSA_SERVICIO en ventas? {'ES_GLOSA_SERVICIO' in cols}")
if "ES_GLOSA_SERVICIO" in cols:
    dist = con.execute("SELECT ES_GLOSA_SERVICIO, COUNT(*) FROM ventas GROUP BY 1").df()
    print(dist.to_string(index=False))

print()
print("-" * 70)
print("2) Líneas de despacho del ciclo actual (25-jul al 24-ago-2026) y su flag")
print("-" * 70)
df_despacho = con.execute("""
    SELECT SKU_BSALE, PRODUCTO, CATEGORIA, ES_GLOSA_SERVICIO,
           CANTIDAD, BRUTO_TOTAL, CONTRIBUCION, FECHA_OBJ
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-07-25' AND '2026-08-24'
      AND (UPPER(TRIM(PRODUCTO)) LIKE '%DESPACHO%'
           OR UPPER(TRIM(SKU_BSALE)) LIKE '%DESPACHO%'
           OR TRY_CAST(SKU_BSALE AS BIGINT) IS NOT NULL)
    ORDER BY FECHA_OBJ DESC
""").df()
print(df_despacho.to_string(index=False))
print(f"\nTotal filas: {len(df_despacho)}")
if "ES_GLOSA_SERVICIO" in df_despacho.columns:
    print(f"De esas, con ES_GLOSA_SERVICIO=True: {df_despacho['ES_GLOSA_SERVICIO'].sum()}")

print()
print("-" * 70)
print("3) ¿Qué productos concretos son la categoría 'Sin Tipo' (ciclo actual)?")
print("-" * 70)
df_sintipo = con.execute("""
    SELECT SKU_BSALE, PRODUCTO, COUNT(DISTINCT DOCUMENTO) AS txs,
           SUM(CANTIDAD) AS unidades, SUM(BRUTO_TOTAL) AS venta
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-07-25' AND '2026-08-24'
      AND CATEGORIA = 'Sin Tipo'
      AND (ES_GLOSA_SERVICIO IS NULL OR ES_GLOSA_SERVICIO = FALSE)
    GROUP BY SKU_BSALE, PRODUCTO
    ORDER BY unidades DESC
""").df()
print(df_sintipo.to_string(index=False))
print(f"\nTotal SKUs distintos en 'Sin Tipo': {df_sintipo['SKU_BSALE'].nunique() if not df_sintipo.empty else 0}")
print(f"Total unidades: {df_sintipo['unidades'].sum() if not df_sintipo.empty else 0}")

con.close()