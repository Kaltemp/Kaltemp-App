"""
Mapea la campana 'LDK | CONV | CALEF-EXT | CL' (Meta) a la categoria
'Calefaccion Exterior' en kaltemp_categorias.db (SQLite -- NO toca
kaltemp_matrix.duckdb). Mismo patron que ajustar_liqui_y_extp0005.py.

Imprime el valor ANTES y DESPUES para poder confirmar.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate      (si tu venv se llama distinto, ajusta)
    python agregar_categoria_calef_ext.py
"""
import os
import sqlite3
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    _AQUI = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
    load_dotenv(os.path.join(_AQUI, ".env"), override=True)
except ImportError:
    _AQUI = os.path.dirname(os.path.abspath(__file__))

CATEGORIAS_DB_PATH = os.getenv("CATEGORIAS_DB_PATH", os.path.join(_AQUI, "kaltemp_categorias.db"))
print(f"💾 CATEGORIAS_DB_PATH: {CATEGORIAS_DB_PATH}\n")

CAMPANA = "LDK | CONV | CALEF-EXT | CL"
PLATAFORMA = "Meta"
CATEGORIA = "Calefacción Exterior"
ASIGNADO_POR = "william@kaltemp.cl (ajuste manual)"
AHORA = datetime.now(timezone.utc).isoformat()

con = sqlite3.connect(CATEGORIAS_DB_PATH)
con.row_factory = sqlite3.Row

print("-" * 70)
print(f"Campaña '{CAMPANA}'")
print("-" * 70)
antes = con.execute("SELECT categoria FROM campanas_categoria WHERE campana = ?", [CAMPANA]).fetchone()
print(f"   ANTES:   {antes['categoria'] if antes else '(no existía)'}")

con.execute("""
    INSERT INTO campanas_categoria (campana, plataforma, categoria, asignado_por, actualizado_en)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(campana) DO UPDATE SET
        categoria = excluded.categoria,
        asignado_por = excluded.asignado_por,
        actualizado_en = excluded.actualizado_en
""", [CAMPANA, PLATAFORMA, CATEGORIA, ASIGNADO_POR, AHORA])
con.execute("INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)", [CATEGORIA])
con.commit()

despues = con.execute("SELECT categoria FROM campanas_categoria WHERE campana = ?", [CAMPANA]).fetchone()
print(f"   DESPUÉS: {despues['categoria']}")
con.close()

print()
print("Listo. La próxima vez que el dashboard consulte /api/indicadores-d2c,")
print("esos $21.941 deberían pasar de 'Sin Categoría' a 'Calefacción Exterior'.")
print("No hace falta reiniciar el backend para esto (se lee en cada request).")