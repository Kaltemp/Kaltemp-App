"""
Intento rapido de reparacion -- conecta SIN read_only (escritura) y
fuerza un CHECKPOINT. A veces esto repara punteros de metadata
corruptos que una conexion read_only no puede arreglar. Tambien prueba
tabla por tabla para ver cuales estan realmente afectadas.

IMPORTANTE: cierra uvicorn y cualquier otro proceso antes de correr esto.

Uso:
    python intentar_reparar_duckdb.py
"""
import duckdb

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

print("Intentando conectar (escritura)...")
try:
    con = duckdb.connect(DB_PATH, read_only=False)
    print("✅ Conexión de escritura abierta.")
except Exception as e:
    print(f"❌ No se pudo ni conectar: {e}")
    raise SystemExit(1)

print("\nListando tablas...")
try:
    tablas = con.execute("SELECT table_name FROM information_schema.tables ORDER BY table_name").fetchall()
    tablas = [t[0] for t in tablas]
    print(f"Tablas encontradas: {tablas}")
except Exception as e:
    print(f"❌ Error listando tablas: {e}")
    tablas = []

print("\nProbando SELECT COUNT(*) en cada tabla, una por una...")
tablas_ok = []
tablas_rotas = []
for t in tablas:
    try:
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"  ✅ {t}: {n} filas")
        tablas_ok.append(t)
    except Exception as e:
        print(f"  ❌ {t}: ERROR -- {e}")
        tablas_rotas.append(t)

print("\nIntentando CHECKPOINT...")
try:
    con.execute("CHECKPOINT")
    print("✅ CHECKPOINT completado sin error.")
except Exception as e:
    print(f"❌ CHECKPOINT falló: {e}")

con.close()

print("\n" + "=" * 80)
print(f"RESUMEN: {len(tablas_ok)} tablas OK, {len(tablas_rotas)} tablas con error.")
if tablas_rotas:
    print(f"Tablas afectadas: {tablas_rotas}")
print("Ahora vuelve a probar conectando de nuevo (o abre uvicorn) para ver si mejoró.")
print("=" * 80)