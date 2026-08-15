import duckdb

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"
conn = duckdb.connect(DB_PATH, read_only=True)

rows = conn.execute("""
    SELECT 
        d.ID_INTERNO, 
        d.CLIENTE, 
        c.VENDEDOR, 
        c.NUMERO_DOCUMENTO_MATCH as Factura_Match, 
        c.PRODUCTO, 
        c.COBRO_BSALE_DESPACHO, 
        c.METODO_MATCH
    FROM enviame_despachos d
    JOIN enviame_cruce_ventas c ON d.ID_INTERNO = c.ID_INTERNO
    WHERE lower(d.CLIENTE) LIKE '%blanca%maturana%'
""").fetchall()

print("🔍 Registro en enviame_cruce_ventas para Blanca Maturana:")
for r in rows:
    print(f"  • ID: {r[0]} | Cliente: '{r[1]}' | Vendedor: '{r[2]}' | Doc: {r[3]} | Cobro Bsale: ${r[5]:,.0f} CLP | Método: '{r[6]}'")