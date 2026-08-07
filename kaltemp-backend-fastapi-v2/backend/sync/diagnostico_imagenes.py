"""
sync/diagnostico_imagenes.py — Verifica la cobertura de imágenes en DuckDB.
"""
import os
import duckdb

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))

def analizar_cobertura():
    if not os.path.exists(DB_FILE):
        print(f"❌ Base de datos no encontrada en: {DB_FILE}")
        return

    print("📊 === DIAGNÓSTICO DE COBERTURA DE IMÁGENES DUCKDB ===")
    
    with duckdb.connect(DB_FILE) as con:
        tablas = [t[0] for t in con.execute("SHOW TABLES").fetchall()]

        for t in ["mkt_inversion_meta", "mkt_inversion_google"]:
            if t in tablas:
                total = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                con_img = con.execute(f"SELECT COUNT(*) FROM {t} WHERE Imagen IS NOT NULL AND TRIM(Imagen) != '' AND Imagen LIKE 'http%'").fetchone()[0]
                porcentaje = (con_img / total * 100) if total > 0 else 0
                print(f"  📌 Tabla '{t}': {con_img}/{total} filas con imagen ({porcentaje:.1f}% de cobertura)")
            else:
                print(f"  ⚠️ Tabla '{t}' no existe aún en DuckDB.")

if __name__ == "__main__":
    analizar_cobertura()