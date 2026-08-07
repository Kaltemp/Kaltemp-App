"""
diagnostico_composicion_ventas.py — Desglosa exactamente qué está sumando
`ventas` para un rango de fechas específico, agrupado por TIPO_DOCUMENTO
y ORIGEN. Sirve para comparar contra el total que muestra el panel nativo
de Bsale y encontrar la diferencia exacta (documentos duplicados, notas
de crédito no restadas, un canal que Bsale excluye, etc.)

Uso:
    python diagnostico_composicion_ventas.py 2026-07-20 2026-07-26
"""
import os
import sys
import duckdb
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")

if len(sys.argv) != 3:
    print("Uso: python diagnostico_composicion_ventas.py FECHA_INICIO FECHA_FIN")
    print("Ejemplo: python diagnostico_composicion_ventas.py 2026-07-20 2026-07-26")
    sys.exit(1)

fecha_inicio, fecha_fin = sys.argv[1], sys.argv[2]

con = duckdb.connect(DB_PATH, read_only=True)

print("=" * 90)
print(f"COMPOSICIÓN DE `ventas` entre {fecha_inicio} y {fecha_fin}")
print("=" * 90)

print("\n--- Por TIPO_DOCUMENTO ---")
filas = con.execute("""
    SELECT TIPO_DOCUMENTO,
           COUNT(*) AS filas,
           COUNT(DISTINCT DOCUMENTO) AS docs_unicos,
           SUM(BRUTO_TOTAL) AS suma_bruto,
           SUM(NETO_TOTAL) AS suma_neto
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
    GROUP BY TIPO_DOCUMENTO
    ORDER BY suma_bruto DESC
""", [fecha_inicio, fecha_fin]).fetchall()
for f in filas:
    print(f"  {f[0]:<35} filas={f[1]:<6} docs_unicos={f[2]:<6} bruto=${f[3]:>15,.0f}  neto=${f[4]:>15,.0f}")

print("\n--- Por ORIGEN ---")
filas = con.execute("""
    SELECT ORIGEN,
           COUNT(*) AS filas,
           SUM(BRUTO_TOTAL) AS suma_bruto
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
    GROUP BY ORIGEN
    ORDER BY suma_bruto DESC
""", [fecha_inicio, fecha_fin]).fetchall()
for f in filas:
    print(f"  {str(f[0]):<20} filas={f[1]:<6} bruto=${f[2]:>15,.0f}")

print("\n--- Totales generales del rango ---")
total = con.execute("""
    SELECT
        COUNT(*) AS filas,
        COUNT(DISTINCT DOCUMENTO) AS docs_unicos,
        SUM(BRUTO_TOTAL) AS suma_bruto,
        SUM(NETO_TOTAL) AS suma_neto
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
""", [fecha_inicio, fecha_fin]).fetchone()
print(f"  Filas: {total[0]}  |  Documentos únicos: {total[1]}")
print(f"  Suma BRUTO_TOTAL: ${total[2]:,.0f}")
print(f"  Suma NETO_TOTAL:  ${total[3]:,.0f}")

print("\n--- Solo BOLETA/FACTURA (excluyendo notas de crédito y otros) ---")
solo_ventas = con.execute("""
    SELECT
        COUNT(*) AS filas,
        SUM(BRUTO_TOTAL) AS suma_bruto,
        SUM(NETO_TOTAL) AS suma_neto
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
      AND TIPO_DOCUMENTO NOT ILIKE '%NOTA DE CREDITO%'
""", [fecha_inicio, fecha_fin]).fetchone()
print(f"  Filas: {solo_ventas[0]}")
print(f"  Suma BRUTO_TOTAL: ${solo_ventas[1]:,.0f}")
print(f"  Suma NETO_TOTAL:  ${solo_ventas[2]:,.0f}")

con.close()
