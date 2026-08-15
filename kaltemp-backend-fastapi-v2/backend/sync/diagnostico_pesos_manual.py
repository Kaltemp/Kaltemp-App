# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_pesos_manual.py
"""
diagnostico_pesos_manual.py — Chequeo rápido de la tabla pesos_manual.

Uso (desde backend/sync/, con venv activo):
    python diagnostico_pesos_manual.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from categorias_db import get_categorias_connection, init_categorias_db  # noqa: E402

init_categorias_db()

with get_categorias_connection() as con:
    total = con.execute("SELECT COUNT(*) AS n FROM pesos_manual").fetchone()
    print(f"Total filas en pesos_manual: {total['n']}")

    con_peso = con.execute(
        "SELECT COUNT(*) AS n FROM pesos_manual WHERE descontinuado = 0 AND peso_kg IS NOT NULL"
    ).fetchone()
    print(f"Con peso real cargado (no descontinuados): {con_peso['n']}")

    descontinuados = con.execute(
        "SELECT COUNT(*) AS n FROM pesos_manual WHERE descontinuado = 1"
    ).fetchone()
    print(f"Marcados descontinuados: {descontinuados['n']}")

    print("\nMuestra de 5 filas:")
    for row in con.execute("SELECT sku, peso_kg, descontinuado FROM pesos_manual LIMIT 5").fetchall():
        print(f"  {dict(row)}")