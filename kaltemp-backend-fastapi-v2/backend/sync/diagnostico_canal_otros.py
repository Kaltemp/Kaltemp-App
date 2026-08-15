# ============================================================
# ARCHIVO: diagnostico_canal_otros.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_canal_otros.py
# ============================================================
"""
diagnostico_canal_otros.py — Revisa qué valores de VENDEDOR están
cayendo en CANAL='OTROS' en la tabla `ventas` ya sincronizada, y cuánto
dinero representa cada uno. Sirve para confirmar si el problema de
"Kaltemp Ripley" (visto en el reporte nativo de Bsale pero ausente en
la matriz de canales de la app) es por:
  a) Documentos con MÁS DE UN vendedor asignado (el VENDEDOR queda con
     coma, ej. "KALTEMP RIPLEY, OTRO NOMBRE" -- no matchea ninguna
     clave de MAPEO_CANALES, cae a OTROS sin importar quién sea).
  b) Un nombre de vendedor real que simplemente no está en el
     diccionario MAPEO_CANALES (typo, nombre nuevo, etc.).
  c) Otra causa -- para descartar antes de tocar el código.

No llama a Bsale -- lee directo de kaltemp_matrix.duckdb, ya sincronizada.

Uso:
    python diagnostico_canal_otros.py
    python diagnostico_canal_otros.py "2026-08-03" "2026-08-09"   (rango opcional)
"""
import os
import sys
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

f_desde = sys.argv[1] if len(sys.argv) > 1 else None
f_hasta = sys.argv[2] if len(sys.argv) > 2 else None

con = duckdb.connect(DB_FILE, read_only=True)

print("=" * 70)
print("1) Todos los VENDEDOR distintos con CANAL = 'OTROS', por monto")
print("=" * 70)

where_fecha = ""
params = []
if f_desde and f_hasta:
    where_fecha = "AND CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)"
    params = [f_desde, f_hasta]
    print(f"(filtrando rango {f_desde} -> {f_hasta})\n")

query = f"""
    SELECT VENDEDOR, COUNT(*) AS lineas, SUM(BRUTO_TOTAL) AS monto_total
    FROM ventas
    WHERE CANAL = 'OTROS' {where_fecha}
    GROUP BY VENDEDOR
    ORDER BY monto_total DESC
"""
filas = con.execute(query, params).fetchall()

total_otros = 0.0
con_coma = 0
monto_con_coma = 0.0
for vendedor, lineas, monto in filas:
    tiene_coma = "," in str(vendedor)
    if tiene_coma:
        con_coma += 1
        monto_con_coma += (monto or 0)
    total_otros += (monto or 0)
    marca = " ⚠️ MÚLTIPLES VENDEDORES (coma)" if tiene_coma else ""
    print(f"  {vendedor!r}: {lineas} líneas, ${monto:,.0f}{marca}")

print()
print(f"Total en canal OTROS: ${total_otros:,.0f}")
print(f"De eso, por documentos con múltiples vendedores (con coma): ${monto_con_coma:,.0f} "
      f"({con_coma} vendedores distintos afectados)")

print()
print("=" * 70)
print("2) ¿Aparece 'RIPLEY' en algún VENDEDOR, y con qué monto, EN EL RANGO DE FECHA?")
print("=" * 70)
where_fecha_2 = ""
params_2 = []
if f_desde and f_hasta:
    where_fecha_2 = "AND CAST(FECHA_OBJ AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)"
    params_2 = [f_desde, f_hasta]

filas_ripley = con.execute(f"""
    SELECT VENDEDOR, CANAL, COUNT(*) AS lineas, SUM(BRUTO_TOTAL) AS monto,
           MIN(CAST(FECHA_OBJ AS DATE)) AS fecha_min, MAX(CAST(FECHA_OBJ AS DATE)) AS fecha_max
    FROM ventas
    WHERE UPPER(VENDEDOR) LIKE '%RIPLEY%' {where_fecha_2}
    GROUP BY VENDEDOR, CANAL
    ORDER BY monto DESC
""", params_2).fetchall()

if not filas_ripley:
    print(f"  ⚠️ CERO filas con 'RIPLEY' en el VENDEDOR dentro de {f_desde} -> {f_hasta}.")
    print("     Esto confirma que el problema NO es de clasificación (el mapeo")
    print("     funciona bien en general) -- es que estos documentos específicos")
    print("     de esa semana simplemente no llegaron a la tabla ventas todavía.")
else:
    for vendedor, canal, lineas, monto, fmin, fmax in filas_ripley:
        print(f"  VENDEDOR={vendedor!r} -> CANAL={canal!r}: {lineas} líneas, ${monto:,.0f} (fechas {fmin} a {fmax})")

print()
print("=" * 70)
print("3) Última fecha de venta sincronizada en total (para saber si la tabla está al día)")
print("=" * 70)
ultima = con.execute("SELECT MAX(CAST(FECHA_OBJ AS DATE)) FROM ventas").fetchone()[0]
print(f"  Última fecha de venta en la tabla ventas: {ultima}")
print(f"  (si es anterior a {f_hasta or 'la fecha que estás revisando'}, la tabla simplemente no ha sido")
print(f"   actualizada hasta esa semana todavía -- correr 'Actualizar Ahora' lo resolvería)")

con.close()