# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_estructura_marketing.py
"""
diagnostico_estructura_marketing.py

Para reemplazar los YoY/WoW inventados (gasto*0.8, etc.) por datos
reales, necesito saber EXACTAMENTE cómo está estructurada la data:
¿una fila por campaña por día (con una sola fecha), o una fila por
campaña con un rango Fecha Inicio/Fecha Fin?

Uso (desde backend/, con venv activo):
    python diagnostico_estructura_marketing.py
"""
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"), override=True)
DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

con = duckdb.connect(DB_PATH, read_only=True)
print(f"(usando DB_PATH: {DB_PATH})\n")

for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    print("=" * 70)
    print(f"TABLA: {tabla}")
    print("=" * 70)

    cols = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?", [tabla]
    ).fetchall()
    print("Columnas:")
    for c in cols:
        print(f"  {c[0]} ({c[1]})")

    total = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"\nTotal filas: {total}")

    print("\nMuestra de 5 filas (todas las columnas):")
    filas = con.execute(f"SELECT * FROM {tabla} LIMIT 5").df()
    print(filas.to_string())

    print("\n--- ¿Cuántas filas distintas por campaña? (para saber si es 1 fila x día o 1 fila total) ---")
    col_camp = cols[3][0] if len(cols) > 3 else None
    if col_camp:
        muestra_campana = con.execute(f'SELECT "{col_camp}" FROM {tabla} LIMIT 1').fetchone()
        if muestra_campana:
            nombre = muestra_campana[0]
            conteo = con.execute(
                f'SELECT COUNT(*) FROM {tabla} WHERE "{col_camp}" = ?', [nombre]
            ).fetchone()[0]
            print(f"  Campaña de ejemplo: {nombre!r} -> aparece en {conteo} filas")
    print()