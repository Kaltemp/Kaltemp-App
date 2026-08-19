"""
Diagnostico: para cada valor distinto de ORIGEN en la tabla `ventas`,
muestra cuantas filas hay, la fecha mas antigua (MIN FECHA_OBJ) y la mas
reciente (MAX FECHA_OBJ), y el monto bruto total. Sirve para saber desde
cuando hay datos de fulfillment ("full", todo lo que no es ORIGEN='BSALE')
cargados automaticamente, y asi identificar el tramo que falta rellenar
con la carga manual antigua.

Uso:
    python diagnostico_origen_fulfillment.py
"""
import duckdb

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

con = duckdb.connect(DUCKDB_PATH, read_only=True)

print("=" * 90)
print("RESUMEN POR ORIGEN (tabla ventas)")
print("=" * 90)
filas = con.execute("""
    SELECT
        ORIGEN,
        COUNT(*)                          AS n_filas,
        COUNT(DISTINCT DOCUMENTO)         AS n_documentos,
        MIN(CAST(FECHA_OBJ AS DATE))      AS fecha_min,
        MAX(CAST(FECHA_OBJ AS DATE))      AS fecha_max,
        SUM(BRUTO_TOTAL)                  AS monto_bruto_total
    FROM ventas
    GROUP BY ORIGEN
    ORDER BY n_filas DESC
""").fetchall()

cols = ["ORIGEN", "n_filas", "n_documentos", "fecha_min", "fecha_max", "monto_bruto_total"]
for fila in filas:
    d = dict(zip(cols, fila))
    print(f"\nORIGEN = {d['ORIGEN']!r}")
    print(f"  Filas:            {d['n_filas']:,}")
    print(f"  Documentos únicos:{d['n_documentos']:,}")
    print(f"  Fecha más antigua: {d['fecha_min']}")
    print(f"  Fecha más reciente:{d['fecha_max']}")
    print(f"  Monto bruto total: {d['monto_bruto_total']:,.0f}")

print()
print("=" * 90)
print("RESUMEN AGRUPADO: BSALE vs FULL (todo lo que NO es ORIGEN='BSALE')")
print("=" * 90)
resumen = con.execute("""
    SELECT
        CASE WHEN ORIGEN = 'BSALE' THEN 'BSALE' ELSE 'FULL (no-Bsale)' END AS grupo,
        COUNT(*)                     AS n_filas,
        MIN(CAST(FECHA_OBJ AS DATE)) AS fecha_min,
        MAX(CAST(FECHA_OBJ AS DATE)) AS fecha_max,
        SUM(BRUTO_TOTAL)             AS monto_bruto_total
    FROM ventas
    GROUP BY grupo
""").fetchall()
cols2 = ["grupo", "n_filas", "fecha_min", "fecha_max", "monto_bruto_total"]
for fila in resumen:
    d = dict(zip(cols2, fila))
    print(f"\n{d['grupo']}")
    print(f"  Filas:              {d['n_filas']:,}")
    print(f"  Fecha más antigua:  {d['fecha_min']}")
    print(f"  Fecha más reciente: {d['fecha_max']}")
    print(f"  Monto bruto total:  {d['monto_bruto_total']:,.0f}")

print()
print("=" * 90)
print("Primeras 20 fechas distintas con datos NO-BSALE (para ver si el inicio")
print("automático fue de golpe o hay huecos)")
print("=" * 90)
primeras = con.execute("""
    SELECT CAST(FECHA_OBJ AS DATE) AS fecha, COUNT(*) AS n_filas, SUM(BRUTO_TOTAL) AS monto
    FROM ventas
    WHERE ORIGEN != 'BSALE'
    GROUP BY fecha
    ORDER BY fecha ASC
    LIMIT 20
""").fetchall()
for fecha, n, monto in primeras:
    print(f"  {fecha}   filas={n:>4}   monto={monto:,.0f}")