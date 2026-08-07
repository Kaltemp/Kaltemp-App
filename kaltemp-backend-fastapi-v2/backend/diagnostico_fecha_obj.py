"""
diagnostico_fecha_obj.py — Investiga por qué /api/acumulado-ytd devuelve
0 a pesar de que /api/tendencia-mensual sí muestra datos reales (mismo
mes, misma tabla `ventas`). Corre esto en la carpeta backend/ con el
venv activado:

    python diagnostico_fecha_obj.py

No modifica nada -- solo lee y muestra información.
"""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import duckdb
from db import DB_PATH

print(f"DB_PATH resuelto: {DB_PATH}")
print()

con = duckdb.connect(DB_PATH, read_only=True)

print("=" * 70)
print("1) Tipo de dato real de la columna FECHA_OBJ")
print("=" * 70)
tipos = con.execute("DESCRIBE ventas").fetchall()
for nombre, tipo, *_ in tipos:
    if nombre == "FECHA_OBJ":
        print(f"FECHA_OBJ -> tipo declarado: {tipo}")

print()
print("=" * 70)
print("2) Muestra cruda de FECHA_OBJ (primeras 5 filas, sin CAST)")
print("=" * 70)
muestra = con.execute("SELECT FECHA_OBJ, BRUTO_TOTAL FROM ventas LIMIT 5").fetchall()
for fecha, bruto in muestra:
    print(f"  FECHA_OBJ={fecha!r} (tipo Python: {type(fecha).__name__})  BRUTO_TOTAL={bruto}")

print()
print("=" * 70)
print("3) Rango real de fechas en la tabla (MIN/MAX de FECHA_OBJ)")
print("=" * 70)
rango = con.execute("SELECT MIN(CAST(FECHA_OBJ AS DATE)), MAX(CAST(FECHA_OBJ AS DATE)), COUNT(*) FROM ventas").fetchone()
print(f"  MIN={rango[0]}  MAX={rango[1]}  TOTAL_FILAS={rango[2]}")

print()
print("=" * 70)
print("4) Prueba EXACTA de lo que hace /api/acumulado-ytd (BETWEEN con fechas Python)")
print("=" * 70)
from datetime import date
inicio_actual = date(2026, 1, 1)
f_corte = date(2026, 8, 2)
resultado_between = con.execute(
    "SELECT SUM(BRUTO_TOTAL), COUNT(*) FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?",
    [inicio_actual, f_corte]
).fetchone()
print(f"  BETWEEN {inicio_actual} AND {f_corte} -> SUMA={resultado_between[0]}  FILAS_MATCH={resultado_between[1]}")

print()
print("=" * 70)
print("5) Misma pregunta pero con fechas como STRING en vez de objeto date()")
print("=" * 70)
resultado_str = con.execute(
    "SELECT SUM(BRUTO_TOTAL), COUNT(*) FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?",
    ["2026-01-01", "2026-08-02"]
).fetchone()
print(f"  BETWEEN '2026-01-01' AND '2026-08-02' (string) -> SUMA={resultado_str[0]}  FILAS_MATCH={resultado_str[1]}")

print()
print("=" * 70)
print("6) Lo que SÍ usa tendencia-mensual (EXTRACT YEAR) -- para comparar")
print("=" * 70)
resultado_year = con.execute(
    "SELECT SUM(BRUTO_TOTAL), COUNT(*) FROM ventas WHERE EXTRACT(YEAR FROM CAST(FECHA_OBJ AS DATE)) = 2026"
).fetchone()
print(f"  EXTRACT(YEAR)=2026 -> SUMA={resultado_year[0]}  FILAS_MATCH={resultado_year[1]}")

con.close()
print()
print("Listo. Copia y pega TODO este resultado.")