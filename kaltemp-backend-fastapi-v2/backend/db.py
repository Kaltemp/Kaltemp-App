"""
Conexión centralizada a DuckDB en modo SOLO LECTURA.
Respeta la arquitectura de separación lectura/escritura:
  - Este backend (FastAPI) SOLO lee.
  - sync_master.py / sync_bsale_operativo.py siguen siendo los únicos
    procesos que escriben en kaltemp_matrix.duckdb (vía cron).
"""
import os
import duckdb
from contextlib import contextmanager

DB_PATH = os.getenv("DUCKDB_PATH", "/data/kaltemp_matrix.duckdb")


@contextmanager
def get_connection():
    """
    Abre una conexión read_only por request y la cierra al terminar.
    DuckDB permite múltiples lectores concurrentes en read_only=True
    incluso mientras el proceso de sync escribe, así que no hay
    riesgo de bloqueo de archivo (file lock) para la API.
    """
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        yield con
    finally:
        con.close()
