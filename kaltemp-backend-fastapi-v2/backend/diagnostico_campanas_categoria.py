"""
Diagnóstico READ-ONLY -- ¿Qué hay ya en campanas_categoria?

kaltemp_categorias.db es un SQLite separado de kaltemp_matrix.duckdb
(ver categorias_db.py). Este script solo LEE, no modifica nada.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_campanas_categoria.py
"""
import os
import sqlite3
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

CATEGORIAS_DB_PATH = os.getenv("CATEGORIAS_DB_PATH", os.path.join(_AQUI, "kaltemp_categorias.db"))
print(f"💾 CATEGORIAS_DB_PATH: {CATEGORIAS_DB_PATH}")
print(f"   ¿Existe el archivo? {os.path.exists(CATEGORIAS_DB_PATH)}\n")

con = sqlite3.connect(CATEGORIAS_DB_PATH)
con.row_factory = sqlite3.Row

print("-" * 70)
print("TODAS las campañas ya asignadas manualmente (campanas_categoria)")
print("-" * 70)
filas = con.execute("SELECT campana, plataforma, categoria, asignado_por, actualizado_en FROM campanas_categoria ORDER BY actualizado_en DESC").fetchall()
if not filas:
    print("(vacía -- no hay ninguna campaña asignada manualmente todavía)")
else:
    for f in filas:
        print(f"  '{f['campana']}'  [{f['plataforma']}]  ->  '{f['categoria']}'  (por {f['asignado_por']}, {f['actualizado_en']})")

print()
print("-" * 70)
print("TODOS los SKUs ya asignados manualmente (categorias_manual)")
print("-" * 70)
filas2 = con.execute("SELECT sku, categoria, asignado_por, actualizado_en FROM categorias_manual ORDER BY actualizado_en DESC").fetchall()
if not filas2:
    print("(vacía -- no hay ningún SKU asignado manualmente todavía)")
else:
    for f in filas2:
        print(f"  '{f['sku']}'  ->  '{f['categoria']}'  (por {f['asignado_por']}, {f['actualizado_en']})")

print()
print("-" * 70)
print("Catálogo de categorías (categorias_catalogo)")
print("-" * 70)
filas3 = con.execute("SELECT nombre FROM categorias_catalogo ORDER BY nombre").fetchall()
print(", ".join(f["nombre"] for f in filas3) if filas3 else "(vacío)")

con.close()