"""
inspeccionar_ga4.py — Diagnóstico de solo lectura: muestra las columnas
reales de ga4_metricas y unas filas de muestra, para poder replicar el
mismo formato al conectar la propiedad de GA4 de Tom Palmer.

Uso (desde backend/):
    python inspeccionar_ga4.py
"""
import os
import duckdb

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "kaltemp_matrix.duckdb"))
)

def inspeccionar():
    print(f"📂 Abriendo {DUCKDB_PATH}\n")
    con = duckdb.connect(DUCKDB_PATH, read_only=True)

    tablas = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
    print(f"📋 Tablas encontradas: {tablas}\n")

    if "ga4_metricas" not in tablas:
        print("❌ No existe una tabla llamada 'ga4_metricas'. Revisa el nombre exacto arriba.")
        return

    print("🗂️  Columnas de ga4_metricas:")
    columnas = con.execute("DESCRIBE ga4_metricas").fetchall()
    for col in columnas:
        print(f"   - {col[0]:30} {col[1]}")

    total_filas = con.execute("SELECT COUNT(*) FROM ga4_metricas").fetchone()[0]
    print(f"\n📊 Total de filas: {total_filas}")

    print("\n🔎 Primeras 5 filas de muestra:")
    muestra = con.execute("SELECT * FROM ga4_metricas LIMIT 5").df()
    print(muestra.to_string())

    con.close()

if __name__ == "__main__":
    inspeccionar()