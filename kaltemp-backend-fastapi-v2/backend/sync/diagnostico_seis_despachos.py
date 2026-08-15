# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_seis_despachos.py
"""
diagnostico_seis_despachos.py — Revisa los despachos que siguen en
COSTO_ENVIO = 0 después de correr actualizar_fletes_enviame.py, para ver
qué les falta (comuna vacía, courier no reconocido, etc.)

Uso (desde backend/sync/, con venv activo):
    python diagnostico_seis_despachos.py
"""
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

con = duckdb.connect(DB_PATH, read_only=True)

print(f"(usando DB_PATH: {DB_PATH})\n")

filas = con.execute("""
    SELECT ID_ENVIO_PK, N_ENVIO_REF, CLIENTE, COMUNA, COURIER, ESTADO, COSTO_ENVIO, FECHA_CREACION
    FROM enviame_despachos
    WHERE COSTO_ENVIO IS NULL OR COSTO_ENVIO = 0.0
""").fetchall()

print(f"Total en $0: {len(filas)}\n")
for f in filas:
    print(f"  {f}")

con.close()