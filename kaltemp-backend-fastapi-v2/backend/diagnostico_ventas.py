import duckdb

conn = duckdb.connect(r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb", read_only=True)
cols = [c[0] for c in conn.execute("DESCRIBE ventas").fetchall()]
print(f"📋 Columnas en 'ventas': {cols}")