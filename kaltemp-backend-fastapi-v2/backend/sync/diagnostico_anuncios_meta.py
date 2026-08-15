"""
GUARDAR EN: C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync\\diagnostico_anuncios_meta.py

Valida mkt_inversion_meta_anuncios: para cada campaña de interés,
muestra los anuncios individuales, su imagen (ID real, sin tokens de
firma), y si dentro de una misma campaña hay variedad real de piezas
gráficas -- y si CALEF-EXT vs CALEFACTORES ya tienen imágenes propias
en vez de compartir la misma.
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

pd.set_option("display.max_colwidth", 60)
pd.set_option("display.width", 220)

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))

with duckdb.connect(DB_FILE, read_only=True) as con:
    df = con.execute("SELECT * FROM mkt_inversion_meta_anuncios").fetchdf()

print(f"✅ mkt_inversion_meta_anuncios: {len(df)} filas, columnas: {list(df.columns)}\n")

df["_id_imagen"] = df["Imagen"].astype(str).str.split("?").str[0].str.extract(r"([\d]+_[\d]+_[\d]+)")

print("=" * 100)
print("CAMPAÑAS ÚNICAS encontradas y cuántos anuncios distintos tiene cada una")
print("=" * 100)
resumen = df.groupby("Campaña").agg(
    anuncios=("Anuncio", "nunique"),
    imagenes_distintas=("_id_imagen", "nunique")
).sort_values("anuncios", ascending=False)
print(resumen.to_string())

print("\n" + "=" * 100)
print("FOCO: CALEF-EXT vs CALEFACTORES -- anuncios individuales e imagen de cada uno")
print("=" * 100)
mask = df["Campaña"].str.contains("CALEF", case=False, na=False)
sub = df.loc[mask, ["Campaña", "Anuncio", "Fecha Fin", "_id_imagen"]].drop_duplicates(subset=["Campaña", "Anuncio"])
print(sub.sort_values(["Campaña", "Anuncio"]).to_string(index=False))

print("\n" + "=" * 100)
print("¿Algún anuncio quedó sin imagen (usando el logo de respaldo)?")
print("=" * 100)
sin_imagen = df[df["Imagen"].astype(str).str.contains("Logo_Horizontal|Diseno_sin_titulo", na=False)]
print(f"{sin_imagen['Anuncio'].nunique()} anuncio(s) únicos cayeron al logo de respaldo (sin imagen propia encontrada).")
if not sin_imagen.empty:
    print(sin_imagen[["Campaña", "Anuncio"]].drop_duplicates().to_string(index=False))