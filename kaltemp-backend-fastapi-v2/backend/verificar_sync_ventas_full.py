"""
Diagnostico de SOLO LECTURA -- para correr DESPUES de probar
sync_ventas_full.py, y ANTES de dejarlo enganchado en sync_master.py.
Muestra lo que quedo escrito en `ventas` con ORIGEN='BSALE_FULL'.

Uso:
    python verificar_sync_ventas_full.py
"""
import duckdb

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

con = duckdb.connect(DUCKDB_PATH, read_only=True)

print("=" * 100)
print("RESUMEN ORIGEN='BSALE_FULL' EN `ventas` -- por CANAL + mes")
print("=" * 100)
filas = con.execute("""
    SELECT CANAL, strftime(CAST(FECHA_OBJ AS DATE), '%Y-%m') AS ym,
           COUNT(*) AS n_filas, SUM(BRUTO_TOTAL) AS bruto_total
    FROM ventas
    WHERE ORIGEN = 'BSALE_FULL'
    GROUP BY CANAL, ym
    ORDER BY CANAL, ym
""").fetchall()
if not filas:
    print("  (sin filas todavía -- ¿ya corriste sync_ventas_full.py?)")
for canal, ym, n, bruto in filas:
    print(f"  {canal:15s} {ym}  filas={n:4d}  bruto=${bruto:,.0f}")

print()
print("=" * 100)
print("MUESTRA -- 10 filas completas más recientes")
print("=" * 100)
filas2 = con.execute("""
    SELECT DOCUMENTO, PRODUCTO, SKU_BSALE, CANTIDAD, BRUTO_TOTAL, NETO_TOTAL,
           COSTO_TOTAL, CONTRIBUCION, CANAL, CATEGORIA, CAST(FECHA_OBJ AS DATE) AS fecha
    FROM ventas
    WHERE ORIGEN = 'BSALE_FULL'
    ORDER BY FECHA_OBJ DESC
    LIMIT 10
""").fetchall()
cols = ["DOCUMENTO", "PRODUCTO", "SKU_BSALE", "CANTIDAD", "BRUTO_TOTAL", "NETO_TOTAL",
        "COSTO_TOTAL", "CONTRIBUCION", "CANAL", "CATEGORIA", "fecha"]
for f in filas2:
    d = dict(zip(cols, f))
    print(f"\n  {d['DOCUMENTO']}  |  {d['PRODUCTO']} (SKU {d['SKU_BSALE']})  |  cat: {d['CATEGORIA']}")
    print(f"  cantidad={d['CANTIDAD']}  bruto=${d['BRUTO_TOTAL']:,.0f}  neto=${d['NETO_TOTAL']:,.0f}  "
          f"costo=${d['COSTO_TOTAL']:,.0f}  contribucion=${d['CONTRIBUCION']:,.0f}  fecha={d['fecha']}")

print()
print("=" * 100)
print("Chequeo de seguridad: ¿algun consumo de Falabella se coló como BSALE_FULL? (debería ser 0)")
print("=" * 100)
chk = con.execute("SELECT COUNT(*) FROM ventas WHERE ORIGEN='BSALE_FULL' AND CANAL='FALABELLA'").fetchone()[0]
print(f"  Filas FALABELLA con ORIGEN=BSALE_FULL: {chk}  {'✅ OK' if chk == 0 else '❌ REVISAR -- esto duplicaría con FALABELLA_API'}")