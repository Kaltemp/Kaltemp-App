"""
GUARDAR EN: C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync\\diagnostico_roas_cero.py

Inspecciona mkt_inversion_meta directo, sin pasar por marketing.py, para
confirmar si "Compras" y "Valor Compras" son genuinamente 0 (dato real
de Meta, ej. ventas que se cierran fuera del checkout online) o si el
código está leyendo la columna equivocada.
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

pd.set_option("display.max_colwidth", 30)
pd.set_option("display.width", 200)

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))

with duckdb.connect(DB_FILE, read_only=True) as con:
    df = con.execute("SELECT * FROM mkt_inversion_meta").fetchdf()

print(f"✅ mkt_inversion_meta: {len(df)} filas")
print(f"Columnas exactas (en orden): {list(df.columns)}\n")

# Ubicar las columnas EXACTAS de interés, sin fuzzy-matching -- directo
# por nombre, para no repetir el posible bug de detección.
for nombre in ["Compras", "Costo/Compra", "Valor Compras", "Leads", "Costo/Lead"]:
    if nombre in df.columns:
        serie = pd.to_numeric(df[nombre], errors="coerce").fillna(0)
        print(f"'{nombre}': suma total = {serie.sum():,.2f} | filas > 0: {(serie > 0).sum()} de {len(serie)} | máximo valor: {serie.max()}")
    else:
        print(f"'{nombre}': columna NO ENCONTRADA en el DataFrame")

print("\n" + "=" * 100)
print("MUESTRA: 15 filas con mayor gasto -- Campaña, Gasto, Compras, Valor Compras")
print("=" * 100)
if "Gasto" in df.columns:
    df["_gasto_num"] = pd.to_numeric(df["Gasto"], errors="coerce").fillna(0)
    muestra = df.sort_values("_gasto_num", ascending=False).head(15)
    cols_mostrar = [c for c in ["Campaña", "Fecha Fin", "Gasto", "Compras", "Costo/Compra", "Valor Compras"] if c in df.columns]
    print(muestra[cols_mostrar].to_string(index=False))

print("\n" + "=" * 100)
print("TOTALES agregados por campaña (todo el histórico en la tabla)")
print("=" * 100)
if "Campaña" in df.columns and "Gasto" in df.columns:
    df["_compras_num"] = pd.to_numeric(df.get("Compras", 0), errors="coerce").fillna(0)
    df["_valorcompras_num"] = pd.to_numeric(df.get("Valor Compras", 0), errors="coerce").fillna(0)
    resumen = df.groupby("Campaña").agg(
        gasto_total=("_gasto_num", "sum"),
        compras_total=("_compras_num", "sum"),
        valor_compras_total=("_valorcompras_num", "sum")
    ).sort_values("gasto_total", ascending=False)
    print(resumen.to_string())