"""
Diagnóstico READ-ONLY -- Performance & TACOS por Categoría (Tom Palmer)

No modifica nada. Solo imprime en pantalla lo necesario para confirmar
por qué la tabla de Indicadores D2C no muestra campañas de Tom Palmer
correctamente cruzadas con venta.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_tacos_tompalmer.py
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

def linea():
    print("-" * 70)

# 1) ¿Existen las tablas de marketing y con qué columnas?
linea()
print("1) COLUMNAS DE mkt_inversion_meta / mkt_inversion_google")
linea()
for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    existe = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [tabla]
    ).fetchone()[0]
    if not existe:
        print(f"❌ {tabla} NO existe en la base.")
        continue
    df = con.execute(f"SELECT * FROM {tabla} LIMIT 1").df()
    print(f"✅ {tabla} -- columnas: {list(df.columns)}")

# 2) ¿Cuántas filas por Marca hay en cada tabla?
linea()
print("2) FILAS POR MARCA (columna 'Marca' si existe)")
linea()
for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    try:
        cols = [c[0] for c in con.execute(f"SELECT * FROM {tabla} LIMIT 0").description]
        col_marca = next((c for c in cols if c.lower() == "marca"), None)
        if not col_marca:
            print(f"⚠️ {tabla}: no tiene columna 'Marca' exacta. Columnas: {cols}")
            continue
        df = con.execute(f'SELECT "{col_marca}" AS marca, COUNT(*) AS filas FROM {tabla} GROUP BY 1').df()
        print(f"{tabla}:")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"❌ Error leyendo {tabla}: {e}")
    print()

# 3) Rango de fechas real en cada tabla (para comparar con el filtro fecha_inicio/fecha_fin)
linea()
print("3) RANGO DE FECHAS (columna 'Fecha Inicio' si existe)")
linea()
for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    try:
        cols = [c[0] for c in con.execute(f"SELECT * FROM {tabla} LIMIT 0").description]
        col_fi = next((c for c in cols if "fecha inicio" in c.lower().replace("ó", "o")), None)
        if not col_fi:
            print(f"⚠️ {tabla}: no encontré columna 'Fecha Inicio'. Columnas: {cols}")
            continue
        r = con.execute(f'SELECT MIN(TRY_CAST("{col_fi}" AS DATE)), MAX(TRY_CAST("{col_fi}" AS DATE)) FROM {tabla}').fetchone()
        print(f"{tabla}: min={r[0]}  max={r[1]}")
    except Exception as e:
        print(f"❌ Error leyendo {tabla}: {e}")

# 4) Categorías de venta reales de Tom Palmer (CANAL = 'Tom Palmer')
linea()
print("4) CATEGORIAS DE VENTA -- CANAL = 'Tom Palmer' (últimos 90 días)")
linea()
try:
    df_ventas_tp = con.execute("""
        SELECT CATEGORIA, COUNT(DISTINCT DOCUMENTO) AS txs, SUM(BRUTO_TOTAL) AS venta
        FROM ventas
        WHERE UPPER(CANAL) = 'TOM PALMER'
          AND CAST(FECHA_OBJ AS DATE) >= CURRENT_DATE - INTERVAL 90 DAY
        GROUP BY CATEGORIA
        ORDER BY venta DESC
    """).df()
    print(df_ventas_tp.to_string(index=False))
except Exception as e:
    print(f"❌ Error: {e}")

# 5) Nombres de campaña + gasto de Tom Palmer, y qué categoría les asignaría _mapear_categoria_real
linea()
print("5) CAMPAÑAS DE TOM PALMER -- últimos 90 días (nombre + gasto)")
linea()
import unicodedata

def _normalizar_texto(s) -> str:
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("-", " ").replace("_", " ")

_MAPA_CATEGORIA_REAL = [
    ("SANITARIA", "BC Agua Sanitaria"), ("PISCINA", "Temperado de Piscina"),
    ("GENERADOR", "Generadores"), ("CALEFACTOR", "Calefacción"),
    ("CALEFACCION", "Calefacción"), ("PERGOLA", "Pérgolas"), ("TERMO", "Termos"),
    ("VENTILACION", "Ventilación"), ("HOT TUB", "Hot Tub"), ("AIRE", "Aire Acondicionado"),
    ("HERRAMIENTA", "Herramientas"), ("MANGUERA", "Mangueras"), ("ILUMINACION", "Iluminación"),
]

def _mapear_categoria_real(nombre_campana: str):
    n = _normalizar_texto(nombre_campana)
    for palabra, categoria in _MAPA_CATEGORIA_REAL:
        if palabra in n:
            return categoria
    return None

for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    try:
        cols = [c[0] for c in con.execute(f"SELECT * FROM {tabla} LIMIT 0").description]
        col_marca = next((c for c in cols if c.lower() == "marca"), None)
        col_camp = next((c for c in cols if "campa" in c.lower()), None)
        col_gasto = next((c for c in cols if "gasto" in c.lower()), None)
        col_fi = next((c for c in cols if "fecha inicio" in c.lower().replace("ó", "o")), None)
        if not (col_marca and col_camp and col_gasto):
            print(f"⚠️ {tabla}: faltan columnas clave. cols={cols}")
            continue
        df = con.execute(f'''
            SELECT "{col_camp}" AS campana, "{col_gasto}" AS gasto, "{col_fi}" AS fecha
            FROM {tabla}
            WHERE "{col_marca}" = 'Tom Palmer'
              AND TRY_CAST("{col_fi}" AS DATE) >= CURRENT_DATE - INTERVAL 90 DAY
        ''').df()
        if df.empty:
            print(f"{tabla}: 0 filas de Tom Palmer en los últimos 90 días.")
            continue
        df["categoria_mapeada"] = df["campana"].apply(_mapear_categoria_real)
        resumen = df.groupby("campana", as_index=False).agg(
            gasto_total=("gasto", lambda s: pd.to_numeric(s, errors="coerce").fillna(0).sum()),
            categoria_mapeada=("categoria_mapeada", "first")
        )
        print(f"\n{tabla}:")
        print(resumen.to_string(index=False))
    except Exception as e:
        print(f"❌ Error leyendo {tabla}: {e}")

linea()
print("FIN DEL DIAGNÓSTICO -- pega esta salida completa de vuelta en el chat.")
linea()

con.close()