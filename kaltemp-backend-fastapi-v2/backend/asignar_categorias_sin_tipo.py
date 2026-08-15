"""
Asignación masiva -- kaltemp_categorias.db (SQLite, NO toca kaltemp_matrix.duckdb)

Categoriza los 34 SKUs reales que estaban en "Sin Tipo" (ver diagnóstico
07-ago-2026), usando como fuente el maestro SKU.csv que compartió William
(Titulo en Marketplace / Categoría / Categoria Max) más 4 confirmaciones
manuales para los SKUs que no aparecían en ese maestro.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python asignar_categorias_sin_tipo.py
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
ASIGNADO_POR = "william@kaltemp.cl (asignación masiva 'Sin Tipo' 07-ago-2026, fuente SKU.csv)"

# --- Del maestro SKU.csv (32 SKUs) ---
ASIGNACIONES = {
    "KLES0067": "Calefacción",
    "KLES0088": "Calefacción",
    "KLES0089": "Calefacción",
    "KLES0087": "Calefacción",
    "KLES0012": "Calefacción",
    "KLES0014": "Calefacción",
    "KLES0096": "Calefacción",
    "KLES0066": "Calefacción",
    "KLES0073": "Calefacción",
    "KLES0065": "Calefacción",
    "KLES0093": "Calefacción",
    "KLGE0002": "Generadores",
    "KLGE0003": "Generadores",
    "KLGE0015": "Generadores",
    "KLBC0091": "Temperado de Piscina",
    "KLBC0074": "Temperado de Piscina",
    "KLBC0092": "Temperado de Piscina",
    "KLBC0095": "Temperado de Piscina",
    "KLBC0063": "BC Agua Sanitaria",
    "KLBC0090": "BC Agua Sanitaria",
    "KLCP0005": "Temperado de Piscina",
    "LOJM0001": "Jardín",
    "LOJM0002": "Jardín",
    "LOIE0001": "Iluminación",
    "LOIE0004": "Iluminación",
    "KLPE005A": "Pérgolas",
    "KLVE0001": "Ventilación",
    "KLST0008": "Calefacción",
    "KLBC0098": "Outlet",
    "KLES0092": "Outlet",
    # --- Confirmadas a mano por William (no estaban en SKU.csv) ---
    "EXTP0005": "Iluminación",
    "KLES0095": "Outlet",
    "KLST0000": "Termos",  # ajustar aquí si prefieres "BC Agua Sanitaria"
    "KLST0001": "Termos",
}

con = sqlite3.connect(CATEGORIAS_DB_PATH)
con.row_factory = sqlite3.Row

print("-" * 70)
print(f"Asignando categoría a {len(ASIGNACIONES)} SKUs")
print("-" * 70)
for sku, categoria in ASIGNACIONES.items():
    antes = con.execute("SELECT categoria FROM categorias_manual WHERE sku = ?", [sku]).fetchone()
    con.execute("""
        INSERT INTO categorias_manual (sku, categoria, asignado_por, actualizado_en)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            categoria = excluded.categoria,
            asignado_por = excluded.asignado_por,
            actualizado_en = excluded.actualizado_en
    """, [sku, categoria, ASIGNADO_POR, AHORA])
    con.execute("INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)", [categoria])
    estado = f"'{antes['categoria']}' -> " if antes else "(nuevo) -> "
    print(f"  {sku:12s} {estado}'{categoria}'")

con.commit()
con.close()

print()
print("=" * 70)
print("✅ Listo. Corre sync_ventas.py para que se refleje en ventas.CATEGORIA")
print("   (esta tabla es SQLite, se aplica en la PRÓXIMA corrida del sync,")
print("   igual que la vez pasada con los SKUs de Tom Palmer).")
print("=" * 70)