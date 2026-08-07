"""
diagnostico_canal_pendientes.py — Solo lectura (read_only=True) sobre
kaltemp_matrix.duckdb, no llama a la API de Bsale. No modifica nada.

Valida la hipótesis: el backlog de 1499 "pendientes" reconstruido por
sync_pendientes_despacho.py está inflado porque incluye ventas de canales
que NUNCA generan guía de despacho (ej. SHOWROOM, retiro en tienda), no
porque haya un problema logístico real de esa magnitud.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync
    python diagnostico_canal_pendientes.py
"""
import os
import duckdb

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", DB_PATH)

con = duckdb.connect(DB_PATH, read_only=True)

print("=" * 70)
print("1) Distribución ESTADO x CANAL (solo donde el cruce con `ventas`")
print("   sí resolvió canal -- 1356/5090 documentos)")
print("=" * 70)
for canal, estado, n, monto in con.execute("""
    SELECT CANAL, ESTADO, COUNT(*), SUM(MONTO)
    FROM pendientes_despacho
    WHERE CANAL IS NOT NULL AND TRIM(CANAL) != ''
    GROUP BY CANAL, ESTADO
    ORDER BY CANAL, ESTADO
""").fetchall():
    print(f"  {canal:20s} {estado:15s} {n:5d} docs   ${monto:,.0f}")

print()
print("=" * 70)
print("2) De los 'Pendiente', ¿cuántos son MUY antiguos (>60 días) y sin")
print("   canal resuelto? (candidatos a ser ventas de mostrador viejas,")
print("   nunca destinadas a tener guía)")
print("=" * 70)
antiguos_sin_canal = con.execute("""
    SELECT COUNT(*), MIN(FECHA_EMISION), MAX(FECHA_EMISION)
    FROM pendientes_despacho
    WHERE ESTADO = '⏳ Pendiente'
      AND (CANAL IS NULL OR TRIM(CANAL) = '')
      AND FECHA_EMISION < CURRENT_DATE - INTERVAL 60 DAY
""").fetchone()
print(f"  {antiguos_sin_canal[0]} documentos, rango {antiguos_sin_canal[1]} a {antiguos_sin_canal[2]}")

print()
print("=" * 70)
print("3) Distribución completa de 'Pendiente' por antigüedad (con y sin canal)")
print("=" * 70)
for rango, n in con.execute("""
    SELECT
        CASE
            WHEN FECHA_EMISION >= CURRENT_DATE - INTERVAL 7 DAY THEN '0-7 días (operativo real)'
            WHEN FECHA_EMISION >= CURRENT_DATE - INTERVAL 30 DAY THEN '8-30 días'
            WHEN FECHA_EMISION >= CURRENT_DATE - INTERVAL 60 DAY THEN '31-60 días'
            ELSE '60+ días (sospechoso)'
        END AS rango,
        COUNT(*)
    FROM pendientes_despacho
    WHERE ESTADO = '⏳ Pendiente'
    GROUP BY 1
    ORDER BY 1
""").fetchall():
    print(f"  {rango:28s} {n:5d} docs")

con.close()