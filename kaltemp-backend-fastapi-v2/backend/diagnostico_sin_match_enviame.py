# ============================================================
# ARCHIVO: diagnostico_sin_match_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_sin_match_enviame.py
# ============================================================
"""
diagnostico_sin_match_enviame.py — Caracteriza los envíos que
sync_cruce_enviame_bsale.py NO pudo resolver (ni por nombre+fecha ni
por número+fecha). Objetivo: confirmar si son mayoritariamente D2C/
marketplace (donde es ESPERABLE que no haya match, porque el cliente
en Bsale es un placeholder del canal, no la persona real) o si hay una
porción real que se podría rescatar con otro criterio.

Solo lee datos, no modifica nada.

Uso:
    cd backend
    python diagnostico_sin_match_enviame.py
"""
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))


def main():
    con = duckdb.connect(DB_FILE, read_only=True)

    tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    if "enviame_cruce_ventas" not in tablas:
        print("❌ La tabla 'enviame_cruce_ventas' no existe todavía -- corre sync_cruce_enviame_bsale.py primero.")
        return

    print("--- Sin match, por COURIER ---")
    filas = con.execute("""
        SELECT e.COURIER, COUNT(*) AS total
        FROM enviame_despachos e
        LEFT JOIN enviame_cruce_ventas c ON c.ID_INTERNO = e.ID_INTERNO
        WHERE c.ID_INTERNO IS NULL
        GROUP BY e.COURIER
        ORDER BY total DESC
    """).fetchall()
    for courier, total in filas:
        print(f"  {courier or '(sin courier)':<20} {total}")

    print("\n--- Con match, por COURIER (para comparar) ---")
    filas = con.execute("""
        SELECT e.COURIER, COUNT(*) AS total
        FROM enviame_despachos e
        JOIN enviame_cruce_ventas c ON c.ID_INTERNO = e.ID_INTERNO
        GROUP BY e.COURIER
        ORDER BY total DESC
    """).fetchall()
    for courier, total in filas:
        print(f"  {courier or '(sin courier)':<20} {total}")

    print("\n--- Muestra de 20 casos SIN match (para revisión visual) ---")
    filas = con.execute("""
        SELECT e.N_ENVIO_REF, e.CLIENTE, e.COURIER, e.COMUNA, TRY_CAST(e.FECHA_CREACION AS DATE)
        FROM enviame_despachos e
        LEFT JOIN enviame_cruce_ventas c ON c.ID_INTERNO = e.ID_INTERNO
        WHERE c.ID_INTERNO IS NULL
        ORDER BY e.FECHA_CREACION DESC
        LIMIT 20
    """).fetchall()
    print(f"{'N_ENVIO_REF':<14}{'CLIENTE':<28}{'COURIER':<14}{'COMUNA':<18}{'FECHA'}")
    for ref, cliente, courier, comuna, fecha in filas:
        print(f"{str(ref):<14}{str(cliente)[:26]:<28}{str(courier):<14}{str(comuna)[:16]:<18}{fecha}")

    con.close()


if __name__ == "__main__":
    main()