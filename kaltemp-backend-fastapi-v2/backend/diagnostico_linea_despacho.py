import duckdb

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"
conn = duckdb.connect(DB_PATH, read_only=True)

df = conn.execute("""
    SELECT *
    FROM ventas
    WHERE lower(TIPO_DOCUMENTO) LIKE '%factura%' AND CAST(NUMERO_DOCUMENTO AS VARCHAR) = '21437'
""").df()

print("🔍 Registro completo de la Factura 21437 en 'ventas':")
print(df.to_string())