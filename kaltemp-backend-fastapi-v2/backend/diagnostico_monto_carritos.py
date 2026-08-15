# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_monto_carritos.py
"""
diagnostico_monto_carritos.py

Revisa los datos reales de abandoned_checkouts para entender por qué
"Oportunidad Perdida" sale $0 aunque haya 35 carritos abandonados.

Uso (desde backend/, con venv activo):
    python diagnostico_monto_carritos.py
"""
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"), override=True)  # backend/.env -- tiene DUCKDB_PATH

DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))
print(f"(usando DB_PATH: {DB_PATH})\n")

con = duckdb.connect(DB_PATH, read_only=True)

print("=== 1) Distribución de ESTADO ===")
print(con.execute(
    "SELECT ESTADO, COUNT(*), COUNT(DISTINCT ID_CHECKOUT) FROM abandoned_checkouts GROUP BY 1"
).fetchall())

print("\n=== 2) Estadísticas de TOTAL_PRICE (todas las filas) ===")
print(con.execute(
    "SELECT COUNT(*), COUNT(TOTAL_PRICE), SUM(TOTAL_PRICE), AVG(TOTAL_PRICE), "
    "MIN(TOTAL_PRICE), MAX(TOTAL_PRICE) FROM abandoned_checkouts"
).fetchall())

print("\n=== 3) Estadísticas de TOTAL_PRICE SOLO para ESTADO='ABANDONADO' ===")
print(con.execute(
    "SELECT COUNT(*), SUM(TOTAL_PRICE), AVG(TOTAL_PRICE) "
    "FROM abandoned_checkouts WHERE ESTADO = 'ABANDONADO'"
).fetchall())

print("\n=== 4) Muestra de 10 filas crudas (ID_CHECKOUT, ESTADO, TOTAL_PRICE, PRECIO_UNITARIO, FECHA_OBJ) ===")
for row in con.execute(
    "SELECT ID_CHECKOUT, ESTADO, TOTAL_PRICE, PRECIO_UNITARIO, FECHA_OBJ "
    "FROM abandoned_checkouts ORDER BY FECHA_OBJ DESC LIMIT 10"
).fetchall():
    print(f"  {row}")

print("\n=== 5) ¿Hay TOTAL_PRICE NULL? ===")
print(con.execute(
    "SELECT COUNT(*) FROM abandoned_checkouts WHERE TOTAL_PRICE IS NULL"
).fetchall())

print("\n=== 6) Tipo de dato real de la columna TOTAL_PRICE ===")
print(con.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name = 'abandoned_checkouts' AND column_name IN ('TOTAL_PRICE', 'ESTADO')"
).fetchall())

con.close()