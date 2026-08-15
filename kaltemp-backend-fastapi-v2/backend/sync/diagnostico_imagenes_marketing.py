"""
GUARDAR EN: C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync\\diagnostico_imagenes_marketing.py

Diagnóstico de imágenes de campañas de Marketing.
No modifica nada -- solo lee mkt_inversion_meta desde DuckDB y muestra,
por categoría de producto, qué imagen quedó registrada y de qué campaña
salió, para poder confirmar visualmente si corresponde a la campaña
ACTIVA más reciente (y no a una vieja/archivada).

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python sync\\diagnostico_imagenes_marketing.py
"""
import os
import sys
import unicodedata
import duckdb
import pandas as pd
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))

load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))
print(f"💾 DB_FILE resuelto: {DB_FILE}\n")


def _normalizar(s: str) -> str:
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("-", " ").replace("_", " ")
    return s


def _extraer_categoria(nombre_campana: str):
    n = _normalizar(nombre_campana)
    if "PISCINA" in n: return "PISCINA"
    if "SANITARIA" in n: return "SANITARIA"
    if "BOMBA" in n and "CALEFAC" in n: return "BOMBA_CALEFACCION"
    if "GENERADOR" in n: return "GENERADOR"
    if "CALEFACTOR" in n: return "CALEFACTOR"
    if "CALEFAC" in n and "EXT" in n: return "CALEFACCION_EXTERIOR"
    if "CALEF" in n and "EXT" in n: return "CALEFACCION_EXTERIOR"
    if "EXTERIOR" in n: return "CALEFACCION_EXTERIOR"
    if "PERGOLA" in n: return "PERGOLA"
    if "TERMO" in n: return "TERMO"
    if "VENTILACION" in n: return "VENTILACION"
    if "HOT TUB" in n or "HOTTUB" in n: return "HOT_TUB"
    if "AIRE" in n: return "AIRE_ACONDICIONADO"
    if "HERRAMIENTA" in n: return "HERRAMIENTAS"
    if "MANGUERA" in n: return "MANGUERAS"
    if "ILUMINACION" in n or "LIGHTING" in n: return "ILUMINACION"
    if "OUTDOOR" in n or "EXTERIORES" in n: return "OUTDOOR_TP"
    return None


def _col(df, *nombres_posibles):
    for col in df.columns:
        limpio = _normalizar(col)
        for n in nombres_posibles:
            if _normalizar(n) == limpio:
                return col
    return None


with duckdb.connect(DB_FILE, read_only=True) as con:
    tablas = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    print(f"📋 Tablas encontradas: {tablas}\n")

    if "mkt_inversion_meta" not in tablas:
        print("❌ mkt_inversion_meta NO existe en esta base. sync_marketing.py nunca corrió con éxito para Meta.")
        sys.exit(1)

    df_meta = con.execute("SELECT * FROM mkt_inversion_meta").fetchdf()

print(f"✅ mkt_inversion_meta cargada: {len(df_meta)} filas, columnas: {list(df_meta.columns)}\n")

col_camp = _col(df_meta, "Campaña", "Campaign", "Nombre") or df_meta.columns[3]
col_img = _col(df_meta, "Imagen", "Image", "ImageUrl")
col_marca = _col(df_meta, "Marca")
col_fecha = _col(df_meta, "Fecha", "Date", "fecha")
col_estado = _col(df_meta, "Estado", "Status", "estado")

if not col_img:
    print("❌ No se encontró columna de Imagen en mkt_inversion_meta. Columnas disponibles:")
    print(list(df_meta.columns))
    sys.exit(1)

df_meta["_categoria"] = df_meta[col_camp].apply(_extraer_categoria)

print("=" * 100)
print("RESUMEN: última imagen registrada por categoría (según orden en que quedó la tabla)")
print("=" * 100)

vistos = set()
for _, fila in df_meta.iterrows():
    cat = fila["_categoria"]
    if not cat or cat in vistos:
        continue
    vistos.add(cat)
    marca = fila[col_marca] if col_marca else "?"
    fecha = fila[col_fecha] if col_fecha else "?"
    estado = fila[col_estado] if col_estado else "?"
    img = str(fila[col_img]).strip()
    print(f"\n🏷️  Categoría: {cat}  |  Marca: {marca}")
    print(f"   Campaña: {fila[col_camp]}")
    print(f"   Fecha: {fecha}  |  Estado: {estado}")
    print(f"   Imagen: {img}")

print("\n" + "=" * 100)
print("FOCO: campañas que contienen 'CALEF-EXT' / 'CALEFACCION_EXTERIOR' (caso reportado LDK)")
print("=" * 100)
mask = df_meta[col_camp].astype(str).str.contains("CALEF", case=False, na=False)
cols_mostrar = [c for c in [col_camp, col_marca, col_fecha, col_estado, col_img] if c]
print(df_meta.loc[mask, cols_mostrar].to_string(index=False))

print("\n" + "=" * 100)
print("Duplicados: ¿hay más de una campaña ACTIVA para la misma categoría+marca? (posible ambigüedad)")
print("=" * 100)
if col_estado:
    activas = df_meta[df_meta[col_estado].astype(str).str.upper().str.contains("ACTIVE", na=False)]
else:
    activas = df_meta
    print("⚠️ No hay columna de Estado -- no se puede filtrar por ACTIVE, mostrando todo.")

dup = activas.dropna(subset=["_categoria"]).groupby(
    ["_categoria"] + ([col_marca] if col_marca else [])
).size()
dup = dup[dup > 1]
if len(dup) == 0:
    print("✅ Ninguna categoría tiene más de una campaña activa -- sin ambigüedad de imagen.")
else:
    print("⚠️ Categorías con más de una campaña activa (la más nueva debería ganar, revisar orden):")
    print(dup)