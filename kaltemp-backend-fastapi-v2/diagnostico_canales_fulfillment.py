"""
Muestra, para cada CANAL de la tabla `ventas`, el ORIGEN, la fecha mas
antigua y mas reciente, y el monto bruto total -- para identificar
cuales canales corresponden a fulfillment de marketplaces (aparte de
Falabella) y desde cuando Bsale empezo a registrarlos como "consumo".

Uso:
    python diagnostico_canales_fulfillment.py
"""
import duckdb

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

con = duckdb.connect(DUCKDB_PATH, read_only=True)

print("=" * 100)
print("RESUMEN POR CANAL + ORIGEN (tabla ventas)")
print("=" * 100)
filas = con.execute("""
    SELECT
        CANAL,
        ORIGEN,
        COUNT(*)                          AS n_filas,
        MIN(CAST(FECHA_OBJ AS DATE))      AS fecha_min,
        MAX(CAST(FECHA_OBJ AS DATE))      AS fecha_max,
        SUM(BRUTO_TOTAL)                  AS monto_bruto_total
    FROM ventas
    GROUP BY CANAL, ORIGEN
    ORDER BY CANAL, ORIGEN
""").fetchall()

cols = ["CANAL", "ORIGEN", "n_filas", "fecha_min", "fecha_max", "monto_bruto_total"]
for fila in filas:
    d = dict(zip(cols, fila))
    print(f"\nCANAL={d['CANAL']!r}  ORIGEN={d['ORIGEN']!r}")
    print(f"  Filas:              {d['n_filas']:,}")
    print(f"  Fecha más antigua:  {d['fecha_min']}")
    print(f"  Fecha más reciente: {d['fecha_max']}")
    print(f"  Monto bruto total:  {d['monto_bruto_total']:,.0f}")

print()
print("=" * 100)
print("Lista simple de todos los CANAL distintos (por si alguno no es obvio)")
print("=" * 100)
canales = con.execute("SELECT DISTINCT CANAL FROM ventas ORDER BY CANAL").fetchall()
for (c,) in canales:
    print(f"  - {c}")