"""
Ajuste puntual -- kaltemp_categorias.db (SQLite, NO toca kaltemp_matrix.duckdb)

Hace 2 cosas:
  1. Cambia la campaña 'LDK | CONV | LIQUI | CL' de categoría única
     'Liquidación' -> multi-categoría 'Jardín, Herramientas, Iluminación'
     (requiere el cambio de channels.py que reparte el gasto entre
     varias categorías separadas por coma).
  2. Agrega el SKU EXTP0005 (única de las 26 detectadas que faltaba)
     -> 'Iluminación'.

Imprime el valor ANTES y DESPUÉS de cada cambio para poder confirmar.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python ajustar_liqui_y_extp0005.py
"""
import os
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

CATEGORIAS_DB_PATH = os.getenv("CATEGORIAS_DB_PATH", os.path.join(_AQUI, "kaltemp_categorias.db"))
print(f"💾 CATEGORIAS_DB_PATH: {CATEGORIAS_DB_PATH}\n")

AHORA = datetime.now(timezone.utc).isoformat()
ASIGNADO_POR = "william@kaltemp.cl (ajuste manual 07-ago-2026)"

con = sqlite3.connect(CATEGORIAS_DB_PATH)
con.row_factory = sqlite3.Row

# --- 1) Campaña LIQUI ---
print("-" * 70)
print("1) Campaña 'LDK | CONV | LIQUI | CL'")
print("-" * 70)
antes = con.execute("SELECT categoria FROM campanas_categoria WHERE campana = ?", ["LDK | CONV | LIQUI | CL"]).fetchone()
print(f"   ANTES:   {antes['categoria'] if antes else '(no existía)'}")

NUEVA_CATEGORIA_LIQUI = "Jardín, Herramientas, Iluminación"
con.execute("""
    INSERT INTO campanas_categoria (campana, plataforma, categoria, asignado_por, actualizado_en)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(campana) DO UPDATE SET
        categoria = excluded.categoria,
        asignado_por = excluded.asignado_por,
        actualizado_en = excluded.actualizado_en
""", ["LDK | CONV | LIQUI | CL", "Meta", NUEVA_CATEGORIA_LIQUI, ASIGNADO_POR, AHORA])
for cat_individual in [c.strip() for c in NUEVA_CATEGORIA_LIQUI.split(",") if c.strip()]:
    con.execute("INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)", [cat_individual])

despues = con.execute("SELECT categoria FROM campanas_categoria WHERE campana = ?", ["LDK | CONV | LIQUI | CL"]).fetchone()
print(f"   DESPUÉS: {despues['categoria']}")

# --- 2) SKU EXTP0005 ---
print()
print("-" * 70)
print("2) SKU 'EXTP0005'")
print("-" * 70)
antes_sku = con.execute("SELECT categoria FROM categorias_manual WHERE sku = ?", ["EXTP0005"]).fetchone()
print(f"   ANTES:   {antes_sku['categoria'] if antes_sku else '(no existía)'}")

con.execute("""
    INSERT INTO categorias_manual (sku, categoria, asignado_por, actualizado_en)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(sku) DO UPDATE SET
        categoria = excluded.categoria,
        asignado_por = excluded.asignado_por,
        actualizado_en = excluded.actualizado_en
""", ["EXTP0005", "Iluminación", ASIGNADO_POR, AHORA])

despues_sku = con.execute("SELECT categoria FROM categorias_manual WHERE sku = ?", ["EXTP0005"]).fetchone()
print(f"   DESPUÉS: {despues_sku['categoria']}")

con.commit()
con.close()

print()
print("=" * 70)
print("✅ Listo. La campaña LIQUI se aplica de inmediato (sin sync).")
print("   El SKU EXTP0005 -- y todos los demás ya categorizados antes --")
print("   se van a reflejar en ventas.CATEGORIA en la PRÓXIMA corrida de")
print("   sync_ventas.py (todavía no ha corrido desde que se cargaron).")
print("=" * 70)