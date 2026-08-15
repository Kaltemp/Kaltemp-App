import duckdb

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"
conn = duckdb.connect(DB_PATH, read_only=True)

rows = conn.execute("""
    SELECT 
        DOCUMENTO, 
        TIPO_DOCUMENTO, 
        NUMERO_DOCUMENTO, 
        PRODUCTO, 
        BRUTO_TOTAL, 
        NETO_TOTAL, 
        CLIENTE,
        FECHA_OBJ
    FROM ventas
    WHERE CAST(NUMERO_DOCUMENTO AS VARCHAR) LIKE '%21437%' OR lower(CLIENTE) LIKE '%blanca%maturana%'
""").fetchall()

print("🔍 Filas en 'ventas' para Factura 21437 o Blanca Maturana:")
for r in rows:
    print(f"  • Doc: {r[0]} | N°: {r[2]} | Prod: '{r[3]}' | Bruto: ${r[4]} | Neto: ${r[5]} | Fecha: {r[7]}")