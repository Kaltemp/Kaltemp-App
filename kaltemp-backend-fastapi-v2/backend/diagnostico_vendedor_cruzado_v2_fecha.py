# ============================================================
# ARCHIVO: diagnostico_vendedor_cruzado_v2_fecha.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_vendedor_cruzado_v2_fecha.py
# ============================================================
"""
diagnostico_vendedor_cruzado_v2_fecha.py — Segunda vuelta del diagnóstico
de falsos cruces (ver diagnostico_vendedor_cruzado_enviame.py). Idea de
William (12-ago-2026): un cruce por NUMERO_DOCUMENTO = N_ENVIO_REF que
sea real debería tener el envío creado A LOS POCOS DÍAS de emitido el
documento Bsale -- un cruce que coincide por pura casualidad numérica
puede tener meses o años de diferencia entre ambas fechas.

Este script:
  1) Calcula, para cada cruce, los días de diferencia entre
     FECHA_CREACION (envío) y FECHA_EMISION (documento Bsale).
  2) Prueba varios umbrales (0, 3, 5, 7, 10, 14, 30 días) y para cada
     uno reporta: cuántos cruces quedarían DENTRO de la ventana, y de
     esos, cuántos SIGUEN siendo sospechosos por nombre de cliente
     (mismo chequeo que el diagnóstico v1).
  3) Así se puede elegir la ventana de días que maximiza matches reales
     y minimiza falsos positivos, con datos reales en vez de adivinar.

Solo lee datos, no modifica nada.

Uso:
    cd backend
    python diagnostico_vendedor_cruzado_v2_fecha.py
"""
import os
import re
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

UMBRALES_DIAS = [0, 3, 5, 7, 10, 14, 30]


def _normalizar(nombre: str) -> set:
    if not nombre:
        return set()
    limpio = re.sub(r"[^a-záéíóúñ\s]", "", nombre.lower())
    return set(p for p in limpio.split() if len(p) > 2)


def main():
    con = duckdb.connect(DB_FILE, read_only=True)

    # FECHA_EMISION de `ventas` -- usamos FECHA_OBJ, que ya sabemos por
    # los principios financieros del proyecto que es la fecha real
    # confiable (no BRUTO/generationDate). ANY_VALUE porque un mismo
    # documento tiene varias líneas con la misma fecha.
    filas = con.execute("""
        SELECT
            e.N_ENVIO_REF,
            e.CLIENTE AS CLIENTE_ENVIAME,
            TRY_CAST(e.FECHA_CREACION AS DATE) AS FECHA_ENVIO,
            v.CLIENTE_VENTAS,
            v.FECHA_DOC,
            v.VENDEDOR,
            v.ORIGEN
        FROM enviame_despachos e
        JOIN (
            SELECT
                CAST(NUMERO_DOCUMENTO AS VARCHAR) AS NUMERO_DOCUMENTO,
                ANY_VALUE(CLIENTE) AS CLIENTE_VENTAS,
                ANY_VALUE(CAST(FECHA_OBJ AS DATE)) AS FECHA_DOC,
                ANY_VALUE(VENDEDOR) AS VENDEDOR,
                ANY_VALUE(ORIGEN) AS ORIGEN
            FROM ventas
            WHERE NUMERO_DOCUMENTO IS NOT NULL
            GROUP BY CAST(NUMERO_DOCUMENTO AS VARCHAR)
        ) v ON v.NUMERO_DOCUMENTO = e.N_ENVIO_REF
        WHERE e.N_ENVIO_REF IS NOT NULL AND TRIM(e.N_ENVIO_REF) != ''
    """).fetchall()

    print(f"Total de cruces por NUMERO_DOCUMENTO = N_ENVIO_REF: {len(filas)}\n")

    con_diferencia = []
    sin_fecha = 0
    for ref, cliente_e, fecha_envio, cliente_v, fecha_doc, vendedor, origen in filas:
        if fecha_envio is None or fecha_doc is None:
            sin_fecha += 1
            continue
        dias = (fecha_envio - fecha_doc).days
        sospechoso = not bool(_normalizar(cliente_e) & _normalizar(cliente_v))
        con_diferencia.append((ref, cliente_e, cliente_v, fecha_envio, fecha_doc, dias, sospechoso, vendedor, origen))

    if sin_fecha:
        print(f"({sin_fecha} cruces sin fecha utilizable en algún lado, excluidos del análisis)\n")

    print(f"{'Ventana (días)':<18}{'Cruces dentro':<16}{'Sospechosos dentro':<20}{'% sospechoso dentro'}")
    print("-" * 80)
    for umbral in UMBRALES_DIAS:
        dentro = [f for f in con_diferencia if 0 <= f[5] <= umbral]
        sospechosos_dentro = [f for f in dentro if f[6]]
        pct = (len(sospechosos_dentro) / len(dentro) * 100) if dentro else 0.0
        print(f"{umbral:<18}{len(dentro):<16}{len(sospechosos_dentro):<20}{pct:.1f}%")

    # También casos con dias NEGATIVOS (envío creado ANTES del documento --
    # no debería pasar en un cruce real, es otra señal de falso positivo).
    negativos = [f for f in con_diferencia if f[5] < 0]
    print(f"\nCruces con envío creado ANTES que el documento (dias < 0): {len(negativos)} "
          f"({sum(1 for f in negativos if f[6])} de esos son también sospechosos por nombre)")

    print(f"\n--- Detalle de los primeros 30 casos con 0 <= días <= 7 (candidato a ventana real) ---")
    detalle = [f for f in con_diferencia if 0 <= f[5] <= 7]
    print(f"{'REF':<12}{'DÍAS':<6}{'CLIENTE ENVÍAME':<26}{'CLIENTE VENTAS':<26}{'¿SOSPECHOSO?':<14}{'ORIGEN'}")
    for ref, cliente_e, cliente_v, fecha_envio, fecha_doc, dias, sospechoso, vendedor, origen in detalle[:30]:
        marca = "SÍ" if sospechoso else "no"
        print(f"{str(ref):<12}{dias:<6}{str(cliente_e)[:24]:<26}{str(cliente_v)[:24]:<26}{marca:<14}{origen}")

    con.close()


if __name__ == "__main__":
    main()