"""
Diagnostico de SOLO LECTURA -- para el problema "Sigo en cero..." en el
dashboard (Vista Principal Ejecutiva) para el rango 10/08/2026-16/08/2026,
a pesar de que 'ventas' tiene datos reales (confirmado por
intentar_reparar_duckdb.py: 56.015+ filas).

Objetivo: descartar que sea un problema de DATOS (vs. backend/cache/uvicorn).

Uso:
    python diagnostico_zeros_dashboard.py
"""
import duckdb

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

con = duckdb.connect(DB_PATH, read_only=True)

print("=" * 100)
print("1) ¿Hay filas en 'ventas' para el rango 2026-08-10 a 2026-08-16?")
print("=" * 100)
r = con.execute("""
    SELECT COUNT(*), SUM(BRUTO_TOTAL), SUM(NETO_TOTAL), SUM(CONTRIBUCION)
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-08-10' AND '2026-08-16'
""").fetchone()
print(f"  filas={r[0]}  bruto=${(r[1] or 0):,.0f}  neto=${(r[2] or 0):,.0f}  contribucion=${(r[3] or 0):,.0f}")

print()
print("=" * 100)
print("2) Desglose por ORIGEN en ese mismo rango (por si un ORIGEN especifico esta vacio)")
print("=" * 100)
filas = con.execute("""
    SELECT ORIGEN, COUNT(*), SUM(BRUTO_TOTAL)
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-08-10' AND '2026-08-16'
    GROUP BY ORIGEN
    ORDER BY ORIGEN
""").fetchall()
for origen, n, bruto in filas:
    print(f"  {origen:25s} filas={n:5d}  bruto=${(bruto or 0):,.0f}")

print()
print("=" * 100)
print("3) Desglose por CANAL en ese mismo rango")
print("=" * 100)
filas2 = con.execute("""
    SELECT CANAL, COUNT(*), SUM(BRUTO_TOTAL)
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-08-10' AND '2026-08-16'
    GROUP BY CANAL
    ORDER BY CANAL
""").fetchall()
for canal, n, bruto in filas2:
    print(f"  {str(canal):25s} filas={n:5d}  bruto=${(bruto or 0):,.0f}")

print()
print("=" * 100)
print("4) Tipo de dato real de FECHA_OBJ (por si hay un mismatch de tipos que rompe el filtro del API)")
print("=" * 100)
tipo = con.execute("""
    SELECT data_type FROM information_schema.columns
    WHERE table_name = 'ventas' AND column_name = 'FECHA_OBJ'
""").fetchone()
print(f"  FECHA_OBJ es de tipo: {tipo[0] if tipo else '???'}")

muestra = con.execute("""
    SELECT FECHA_OBJ, typeof(FECHA_OBJ) FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN '2026-08-10' AND '2026-08-16'
    LIMIT 3
""").fetchall()
for f in muestra:
    print(f"  valor={f[0]}  typeof={f[1]}")

print()
print("=" * 100)
print("5) Ultimas 5 fechas con ventas (para confirmar que 'hoy' realmente tiene datos)")
print("=" * 100)
recientes = con.execute("""
    SELECT CAST(FECHA_OBJ AS DATE) AS fecha, COUNT(*), SUM(BRUTO_TOTAL)
    FROM ventas
    GROUP BY fecha
    ORDER BY fecha DESC
    LIMIT 5
""").fetchall()
for fecha, n, bruto in recientes:
    print(f"  {fecha}  filas={n:5d}  bruto=${(bruto or 0):,.0f}")

con.close()

print()
print("=" * 100)
print("Si el punto 1 muestra filas > 0 pero el dashboard sigue en $0, el problema NO es de datos.")
print("En ese caso lo mas probable es:")
print("  a) uvicorn no se reinicio despues de la reparacion -> reiniciarlo (Ctrl+C y volver a correr)")
print("  b) uvicorn quedo con una conexion vieja/cacheada a la DB -> reinicio deberia arreglarlo")
print("  c) cache del navegador/frontend -> Ctrl+Shift+R (hard refresh)")
print("Si el punto 1 muestra 0 filas, entonces SI es un problema de datos para ese rango puntual")
print("y hay que revisar por que ese rango en particular quedo vacio.")
print("=" * 100)