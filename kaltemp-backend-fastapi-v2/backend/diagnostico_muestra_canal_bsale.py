"""
Diagnostico de SOLO LECTURA. Objetivo: confirmar empiricamente que
CANAL IN ('MERCADOLIBRE','PARIS','RIPLEY','FALABELLA') + ORIGEN='BSALE'
corresponde a boletas/facturas NORMALES de Bsale (documento real, con
numero), y NO a fulfillment -- segun lo que dice el codigo de
sync_ventas.py (el campo CANAL sale de mapear el "vendedor" del
documento contra MAPEO_CANALES, nada que ver con consumos de bodega).

No modifica nada -- solo lee y muestra filas de ejemplo.

Uso:
    python diagnostico_muestra_canal_bsale.py
"""
import duckdb

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

con = duckdb.connect(DUCKDB_PATH, read_only=True)

canales = ["MERCADOLIBRE", "PARIS", "RIPLEY", "FALABELLA"]

for canal in canales:
    print("=" * 100)
    print(f"CANAL = {canal!r}  (ORIGEN = 'BSALE')  -- 5 filas de muestra, las mas recientes")
    print("=" * 100)
    filas = con.execute("""
        SELECT DOCUMENTO, TIPO_DOCUMENTO, NUMERO_DOCUMENTO, VENDEDOR, CLIENTE,
               SUCURSAL, PRODUCTO, BRUTO_TOTAL, CAST(FECHA_OBJ AS DATE) AS fecha
        FROM ventas
        WHERE CANAL = ? AND ORIGEN = 'BSALE'
        ORDER BY FECHA_OBJ DESC
        LIMIT 5
    """, [canal]).fetchall()
    cols = ["DOCUMENTO", "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO", "VENDEDOR", "CLIENTE",
            "SUCURSAL", "PRODUCTO", "BRUTO_TOTAL", "fecha"]
    if not filas:
        print("  (sin filas)")
    for fila in filas:
        d = dict(zip(cols, fila))
        print(f"\n  DOCUMENTO:         {d['DOCUMENTO']}")
        print(f"  TIPO_DOCUMENTO:    {d['TIPO_DOCUMENTO']}")
        print(f"  NUMERO_DOCUMENTO:  {d['NUMERO_DOCUMENTO']}")
        print(f"  VENDEDOR:          {d['VENDEDOR']}")
        print(f"  CLIENTE:           {d['CLIENTE']}")
        print(f"  SUCURSAL:          {d['SUCURSAL']}")
        print(f"  PRODUCTO:          {d['PRODUCTO']}")
        print(f"  BRUTO_TOTAL:       {d['BRUTO_TOTAL']:,.0f}")
        print(f"  FECHA:             {d['fecha']}")
    print()

print("=" * 100)
print("Comparacion: 5 filas de FALABELLA con ORIGEN='FALABELLA_API' (para contrastar formato)")
print("=" * 100)
filas2 = con.execute("""
    SELECT DOCUMENTO, TIPO_DOCUMENTO, NUMERO_DOCUMENTO, VENDEDOR, CLIENTE,
           SUCURSAL, PRODUCTO, BRUTO_TOTAL, CAST(FECHA_OBJ AS DATE) AS fecha
    FROM ventas
    WHERE CANAL = 'FALABELLA' AND ORIGEN = 'FALABELLA_API'
    ORDER BY FECHA_OBJ DESC
    LIMIT 5
""").fetchall()
cols = ["DOCUMENTO", "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO", "VENDEDOR", "CLIENTE",
        "SUCURSAL", "PRODUCTO", "BRUTO_TOTAL", "fecha"]
for fila in filas2:
    d = dict(zip(cols, fila))
    print(f"\n  DOCUMENTO:         {d['DOCUMENTO']}")
    print(f"  TIPO_DOCUMENTO:    {d['TIPO_DOCUMENTO']}")
    print(f"  NUMERO_DOCUMENTO:  {d['NUMERO_DOCUMENTO']}")
    print(f"  VENDEDOR:          {d['VENDEDOR']}")
    print(f"  CLIENTE:           {d['CLIENTE']}")
    print(f"  SUCURSAL:          {d['SUCURSAL']}")
    print(f"  PRODUCTO:          {d['PRODUCTO']}")
    print(f"  BRUTO_TOTAL:       {d['BRUTO_TOTAL']:,.0f}")
    print(f"  FECHA:             {d['fecha']}")