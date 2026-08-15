# ============================================================
# ARCHIVO: diagnostico_vendedor_cruzado_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_vendedor_cruzado_enviame.py
# ============================================================
"""
diagnostico_vendedor_cruzado_enviame.py — Detecta falsos cruces del JOIN
actual entre `enviame_despachos` y `ventas` (por NUMERO_DOCUMENTO =
N_ENVIO_REF, usado en /api/enviame-shipments para traer VENDEDOR y
PRODUCTO). Un cruce es sospechoso si el nombre del cliente que trae
Envíame no se parece en nada al nombre del cliente en `ventas` para el
mismo NUMERO_DOCUMENTO -- eso indica que el número coincidió por
casualidad entre dos documentos completamente distintos (venta de
Showroom vs pedido de otro canal), no que el envío realmente
corresponda a esa venta.

Solo lee datos, no modifica nada.

Uso:
    cd backend
    python diagnostico_vendedor_cruzado_enviame.py
"""
import os
import re
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))


def _normalizar(nombre: str) -> set:
    if not nombre:
        return set()
    limpio = re.sub(r"[^a-záéíóúñ\s]", "", nombre.lower())
    return set(p for p in limpio.split() if len(p) > 2)


def main():
    con = duckdb.connect(DB_FILE, read_only=True)

    filas = con.execute("""
        SELECT
            e.N_ENVIO_REF, e.CLIENTE AS CLIENTE_ENVIAME, e.COURIER, e.FECHA_CREACION,
            v.CLIENTE AS CLIENTE_VENTAS, v.VENDEDOR, v.ORIGEN, v.PRODUCTO
        FROM enviame_despachos e
        JOIN ventas v ON CAST(v.NUMERO_DOCUMENTO AS VARCHAR) = e.N_ENVIO_REF
        WHERE e.N_ENVIO_REF IS NOT NULL AND TRIM(e.N_ENVIO_REF) != ''
    """).fetchall()

    print(f"Total de filas con cruce ventas<->enviame por NUMERO_DOCUMENTO: {len(filas)}\n")

    sospechosas = []
    for ref, cliente_e, courier, fecha, cliente_v, vendedor, origen, producto in filas:
        palabras_e = _normalizar(cliente_e)
        palabras_v = _normalizar(cliente_v)
        coincide = bool(palabras_e & palabras_v)
        if not coincide:
            sospechosas.append((ref, cliente_e, courier, fecha, cliente_v, vendedor, origen, producto))

    print(f"⚠️  Cruces SOSPECHOSOS (cliente no coincide entre Envíame y ventas): {len(sospechosas)}\n")
    print(f"{'N_ENVIO_REF':<15}{'CLIENTE ENVÍAME':<28}{'CLIENTE VENTAS':<28}{'VENDEDOR':<20}{'ORIGEN':<18}{'COURIER'}")
    print("-" * 130)
    for ref, cliente_e, courier, fecha, cliente_v, vendedor, origen, producto in sospechosas[:60]:
        print(f"{str(ref):<15}{str(cliente_e)[:26]:<28}{str(cliente_v)[:26]:<28}{str(vendedor)[:18]:<20}{str(origen)[:16]:<18}{courier}")

    if len(sospechosas) > 60:
        print(f"\n... y {len(sospechosas) - 60} más (se truncó la salida a 60 filas).")

    con.close()


if __name__ == "__main__":
    main()