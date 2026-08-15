"""
diagnostico_categorias_desactualizadas.py — Verifica si hay SKUs con
categoría manual asignada en kaltemp_categorias.db que TODAVÍA aparecen
como "Sin Tipo" / "Sin Categoría Mapeada" en ventas.CATEGORIA (señal de
que sync_ventas.py no se ha vuelto a correr desde que se categorizaron).

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_categorias_desactualizadas.py
"""
import os
import duckdb
import sqlite3
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))
CAT_DB_FILE = os.getenv("CATEGORIAS_DB_PATH", os.path.join(_AQUI, "kaltemp_categorias.db"))

print("=" * 80)
print("DIAGNÓSTICO — CATEGORÍAS MANUALES vs. VENTAS.CATEGORIA")
print("=" * 80)
print(f"📁 DuckDB:  {DB_FILE}")
print(f"📁 SQLite:  {CAT_DB_FILE}")
print()

if not os.path.exists(CAT_DB_FILE):
    print("❌ kaltemp_categorias.db no existe todavía.")
    exit(1)

con_cat = sqlite3.connect(CAT_DB_FILE)
con_cat.row_factory = sqlite3.Row
manual_rows = con_cat.execute("SELECT sku, categoria FROM categorias_manual").fetchall()
mapa_manual = {row["sku"]: row["categoria"] for row in manual_rows}
con_cat.close()

print(f"📋 SKUs con categoría manual asignada (kaltemp_categorias.db): {len(mapa_manual)}")
print()

if not mapa_manual:
    print("⚠️  No hay ninguna categoría manual guardada todavía.")
    exit(0)

con = duckdb.connect(DB_FILE, read_only=True)

skus_lista = list(mapa_manual.keys())
placeholders = ", ".join(["?"] * len(skus_lista))
filas = con.execute(f"""
    SELECT SKU_BSALE, ANY_VALUE(CATEGORIA) AS categoria_en_ventas,
           SUM(CANTIDAD) AS unidades, COUNT(*) AS lineas
    FROM ventas
    WHERE SKU_BSALE IN ({placeholders})
    GROUP BY SKU_BSALE
""", skus_lista).fetchall()

desactualizados = []
actualizados = []
for sku, cat_en_ventas, unidades, lineas in filas:
    cat_manual = mapa_manual.get(sku, "")
    if cat_en_ventas in ("Sin Tipo", "Sin Categoría Mapeada", None):
        desactualizados.append((sku, cat_manual, cat_en_ventas, unidades, lineas))
    elif cat_en_ventas != cat_manual:
        # Categoría distinta a la manual (puede ser normal si cambiaste de opinión,
        # o señal de la misma desactualización)
        desactualizados.append((sku, cat_manual, cat_en_ventas, unidades, lineas))
    else:
        actualizados.append((sku, cat_manual, unidades))

print(f"✅ SKUs ya sincronizados correctamente (ventas.CATEGORIA = manual): {len(actualizados)}")
print(f"⚠️  SKUs con categoría manual asignada pero SIN reflejar en ventas.CATEGORIA: {len(desactualizados)}")
print()

if desactualizados:
    print("Detalle de SKUs desactualizados (categoría manual guardada pero no aplicada):")
    print(f"{'SKU':<15} {'CATEGORÍA MANUAL':<25} {'CATEGORÍA EN VENTAS':<25} {'UNIDADES':>9}")
    print("-" * 80)
    total_unidades_afectadas = 0
    for sku, cat_manual, cat_ventas, unidades, lineas in sorted(desactualizados, key=lambda x: x[3] or 0, reverse=True)[:30]:
        print(f"{sku:<15} {cat_manual:<25} {str(cat_ventas):<25} {unidades or 0:>9}")
        total_unidades_afectadas += (unidades or 0)
    print()
    print(f"🔢 Total de unidades vendidas afectadas por esta desactualización: {total_unidades_afectadas}")
    print()
    print("👉 SOLUCIÓN: corre sync_ventas.py (o sync_master.py) para que")
    print("   ventas.CATEGORIA se actualice con las categorías manuales guardadas.")
else:
    print("✅ Todo sincronizado -- las categorías manuales SÍ están reflejadas en ventas.")
    print("   Si el gráfico sigue mal, el problema es otro (SKUs realmente sin categorizar).")

con.close()
print()
print("=" * 80)