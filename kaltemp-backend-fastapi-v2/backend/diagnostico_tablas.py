import duckdb
import os

print("📁 Buscando todos los archivos .duckdb en C:\\kaltemp_app:")
for root, dirs, files in os.walk(r"C:\kaltemp_app"):
    for f in files:
        if f.endswith(".duckdb"):
            full_path = os.path.join(root, f)
            print(f"\n📊 Archivo: {full_path}")
            try:
                conn = duckdb.connect(full_path, read_only=True)
                tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
                print(f"   Tablas ({len(tables)}): {tables}")
            except Exception as e:
                print(f"   Error: {e}")