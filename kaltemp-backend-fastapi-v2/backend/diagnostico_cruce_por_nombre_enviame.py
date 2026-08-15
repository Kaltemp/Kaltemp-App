# ============================================================
# ARCHIVO: diagnostico_cruce_por_nombre_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_cruce_por_nombre_enviame.py
# ============================================================
"""
diagnostico_cruce_por_nombre_enviame.py — Cruce ALTERNATIVO entre
enviame_despachos y ventas, SIN depender de N_ENVIO_REF (que ya
confirmamos que no es confiable). Idea: `customer.full_name` de
Envíame (guardado en enviame_despachos.CLIENTE) sí es un dato real y
confiable -- lo cruzamos contra ventas.CLIENTE, con la fecha del envío
dentro de una ventana desde la fecha de emisión del documento (mismo
criterio ya validado con N_ENVIO_REF).

A diferencia del cruce por número, este NO depende de que el canal
haya puesto el número correcto en ningún campo -- debería funcionar
para más envíos, a costa de que nombres de clientes comunes puedan
generar AMBIGÜEDAD (más de un documento del mismo cliente en la
ventana). Este script mide esa ambigüedad con datos reales.

Solo lee datos, no modifica nada.

Uso:
    cd backend
    python diagnostico_cruce_por_nombre_enviame.py
"""
import os
import re
import duckdb
from dotenv import load_dotenv
from collections import defaultdict

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

UMBRALES_DIAS = [3, 5, 7, 10, 14]


def _normalizar(nombre: str) -> str:
    """Nombre normalizado para comparar: minúsculas, sin tildes/símbolos,
    palabras ordenadas alfabéticamente (para que 'Juan Pérez' == 'Pérez Juan')."""
    if not nombre:
        return ""
    limpio = re.sub(r"[^a-záéíóúñ\s]", "", nombre.lower())
    palabras = sorted(p for p in limpio.split() if len(p) > 1)
    return " ".join(palabras)


def main():
    con = duckdb.connect(DB_FILE, read_only=True)

    envios = con.execute("""
        SELECT ID_INTERNO, N_ENVIO_REF, CLIENTE, TRY_CAST(FECHA_CREACION AS DATE) AS FECHA_ENVIO
        FROM enviame_despachos
        WHERE CLIENTE IS NOT NULL AND TRIM(CLIENTE) != ''
          AND FECHA_CREACION IS NOT NULL
    """).fetchall()

    docs = con.execute("""
        SELECT CAST(NUMERO_DOCUMENTO AS VARCHAR), CLIENTE, TRY_CAST(FECHA_OBJ AS DATE), VENDEDOR, PRODUCTO
        FROM ventas
        WHERE NUMERO_DOCUMENTO IS NOT NULL AND CLIENTE IS NOT NULL AND TRIM(CLIENTE) != ''
    """).fetchall()

    print(f"Envíos con cliente y fecha: {len(envios)}")
    print(f"Líneas de venta con documento y cliente: {len(docs)}\n")

    # Índice: nombre normalizado -> lista de (numero_doc, fecha, vendedor)
    indice_por_nombre = defaultdict(list)
    for numero_doc, cliente, fecha_doc, vendedor, producto in docs:
        if fecha_doc is None:
            continue
        indice_por_nombre[_normalizar(cliente)].append((numero_doc, fecha_doc, vendedor))

    for umbral in UMBRALES_DIAS:
        exactos = 0       # exactamente 1 documento candidato en la ventana
        ambiguos = 0       # más de 1 documento candidato en la ventana
        sin_match = 0
        for _, ref, cliente_e, fecha_envio in envios:
            if fecha_envio is None:
                sin_match += 1
                continue
            candidatos = [
                d for d in indice_por_nombre.get(_normalizar(cliente_e), [])
                if 0 <= (fecha_envio - d[1]).days <= umbral
            ]
            if len(candidatos) == 1:
                exactos += 1
            elif len(candidatos) > 1:
                ambiguos += 1
            else:
                sin_match += 1

        total = exactos + ambiguos + sin_match
        print(f"Ventana {umbral:>2} días -> match único: {exactos:>5} ({exactos/total*100:5.1f}%)  "
              f"ambiguo (2+): {ambiguos:>5} ({ambiguos/total*100:5.1f}%)  "
              f"sin match: {sin_match:>5} ({sin_match/total*100:5.1f}%)")

    # Detalle de los primeros 20 matches únicos con ventana de 5 días,
    # para inspección visual rápida.
    print(f"\n--- Primeros 20 matches ÚNICOS con ventana de 5 días ---")
    print(f"{'N_ENVIO_REF':<14}{'CLIENTE':<28}{'FECHA ENVÍO':<14}{'DOC. MATCH':<12}{'VENDEDOR'}")
    mostrados = 0
    for _, ref, cliente_e, fecha_envio in envios:
        if fecha_envio is None or mostrados >= 20:
            continue
        candidatos = [
            d for d in indice_por_nombre.get(_normalizar(cliente_e), [])
            if 0 <= (fecha_envio - d[1]).days <= 5
        ]
        if len(candidatos) == 1:
            numero_doc, fecha_doc, vendedor = candidatos[0]
            print(f"{str(ref):<14}{str(cliente_e)[:26]:<28}{str(fecha_envio):<14}{str(numero_doc):<12}{vendedor}")
            mostrados += 1

    con.close()


if __name__ == "__main__":
    main()