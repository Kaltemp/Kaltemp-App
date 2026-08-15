"""
Backfill de ES_GLOSA_SERVICIO -- NO vuelve a sincronizar desde Bsale.

Motivo: la lógica de _es_glosa_no_producto() en sync_ventas.py está bien,
pero solo se aplica cuando una fila se sincroniza/actualiza. Las filas que
ya estaban en `ventas` ANTES de que esa lógica existiera (o antes de la
última corrección) se quedaron con ES_GLOSA_SERVICIO=False para siempre,
aunque su SKU/nombre sí califique como despacho/reparación/repuesto
genérico. Este script recalcula el flag sobre TODO lo que ya existe en la
base, en un solo UPDATE, sin llamar a la API de Bsale.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python backfill_es_glosa_servicio.py

IMPORTANTE: cierra uvicorn antes de correr esto (o al menos no hagas
requests mientras corre) -- DuckDB permite un solo escritor a la vez, y
si el backend tiene una conexión activa puede chocar.
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))
print(f"💾 DB_FILE: {DB_FILE}\n")


def _es_glosa_no_producto(sku, producto) -> bool:
    """Copia EXACTA de la función en sync_ventas.py -- no la reinventes,
    si esa función cambia, este backfill debe actualizarse junto con ella."""
    sku_limpio = str(sku or "").strip()
    if sku_limpio.isdigit() and len(sku_limpio) >= 5:
        return True
    texto_a_revisar = f"{sku_limpio} {str(producto or '').strip()}".upper()
    palabras_excluidas = ("REPARACION", "REPARACIÓN", "REPUESTO", "DESPACHO")
    return any(p in texto_a_revisar for p in palabras_excluidas)


con = duckdb.connect(DB_FILE, read_only=False)

print("-" * 70)
print("ANTES del backfill")
print("-" * 70)
antes = con.execute("SELECT ES_GLOSA_SERVICIO, COUNT(*) FROM ventas GROUP BY 1").df()
print(antes.to_string(index=False))

# Trae los pares únicos (SKU_BSALE, PRODUCTO) -- el flag es una función
# pura de esos 2 campos, así que no hace falta tocar fila por fila.
pares = con.execute("""
    SELECT DISTINCT SKU_BSALE, PRODUCTO
    FROM ventas
""").df()
print(f"\nPares únicos (SKU_BSALE, PRODUCTO) a evaluar: {len(pares)}")

pares["ES_GLOSA_SERVICIO_CORRECTO"] = pares.apply(
    lambda r: _es_glosa_no_producto(r["SKU_BSALE"], r["PRODUCTO"]), axis=1
)

con.register("temp_flags", pares)

resultado = con.execute("""
    UPDATE ventas v
    SET ES_GLOSA_SERVICIO = t.ES_GLOSA_SERVICIO_CORRECTO
    FROM temp_flags t
    WHERE v.SKU_BSALE = t.SKU_BSALE
      AND (v.PRODUCTO = t.PRODUCTO OR (v.PRODUCTO IS NULL AND t.PRODUCTO IS NULL))
      AND v.ES_GLOSA_SERVICIO IS DISTINCT FROM t.ES_GLOSA_SERVICIO_CORRECTO
""")
con.commit()

print()
print("-" * 70)
print("DESPUÉS del backfill")
print("-" * 70)
despues = con.execute("SELECT ES_GLOSA_SERVICIO, COUNT(*) FROM ventas GROUP BY 1").df()
print(despues.to_string(index=False))

con.close()
print("\n✅ Listo. Reinicia uvicorn (o solo recarga el navegador si ya usa --reload).")