"""
sync/migracion_pk.py — Migración de una sola vez: agrega la columna
ID_ENVIO_PK a la tabla `enviame_despachos` existente en producción.

Necesaria porque la tabla ya existía antes de este cambio -- el
CREATE TABLE IF NOT EXISTS de sync_enviame.py no modifica una tabla que
ya existe, así que hay que agregar la columna a mano una vez.

Uso:
    python sync\\migracion_pk.py

Es seguro correrlo más de una vez -- si la columna ya existe o ya no
quedan filas con ID_ENVIO_PK vacío, no hace nada.
"""
import os
import duckdb

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kaltemp_matrix.duckdb")


def migrar():
    print(f"🔄 Conectando a {DB_FILE}...")
    con = duckdb.connect(DB_FILE)

    cols = [c.upper() for c in con.table("enviame_despachos").columns]
    if "ID_ENVIO_PK" not in cols:
        print("➕ Agregando columna ID_ENVIO_PK...")
        con.execute("ALTER TABLE enviame_despachos ADD COLUMN ID_ENVIO_PK BIGINT")
    else:
        print("✅ La columna ID_ENVIO_PK ya existe.")

    con.execute("CREATE SEQUENCE IF NOT EXISTS seq_enviame_pk START 1")

    pendientes = con.execute(
        "SELECT COUNT(*) FROM enviame_despachos WHERE ID_ENVIO_PK IS NULL"
    ).fetchone()[0]

    if pendientes == 0:
        print("✅ Todas las filas ya tienen ID_ENVIO_PK asignado. Nada que hacer.")
    else:
        print(f"🔢 Asignando ID_ENVIO_PK a {pendientes} filas...")
        con.execute(
            "UPDATE enviame_despachos SET ID_ENVIO_PK = nextval('seq_enviame_pk') "
            "WHERE ID_ENVIO_PK IS NULL"
        )
        print("🎉 Migración completa.")

    con.close()


if __name__ == "__main__":
    migrar()