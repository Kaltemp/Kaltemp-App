# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_descripcion_producto_enviame.py
"""
diagnostico_descripcion_producto_enviame.py

Objetivo: encontrar EXACTAMENTE por dónde expone la API de Envíame el
campo "Descripción del producto" (para un envío donde ya sabemos que
tiene cargado un N° de documento), y si contiene el número esperado.

Prueba en orden:
1. GET /deliveries/{id} (endpoint normal) -- ¿aparece ahí directo,
   a diferencia de Observaciones que confirmamos que NO aparece?
2. GET /deliveries/{id}/tracking (el mismo endpoint que ya usa el Plan
   A para Observaciones) -- ¿aparece como evento de edición, con qué
   texto exacto?

Uso:
    python diagnostico_descripcion_producto_enviame.py <ID_INTERNO_o_identifier>

Si no sabés el ID_INTERNO a mano, dejalo vacío y el script toma el
envío más reciente de enviame_despachos.
"""
import sys
import os
import json
import duckdb
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}


def obtener_identifier(arg):
    if arg:
        return arg
    con = duckdb.connect(DB_FILE, read_only=True)
    fila = con.execute(
        "SELECT ID_INTERNO, TRACKING_NUMBER, CLIENTE FROM enviame_despachos "
        "WHERE ID_INTERNO IS NOT NULL AND ID_INTERNO != '' "
        "ORDER BY FECHA_CREACION DESC LIMIT 1"
    ).fetchone()
    con.close()
    if not fila:
        print("❌ No encontré ningún ID_INTERNO en enviame_despachos.")
        sys.exit(1)
    print(f"(usando el envío más reciente: {fila[1]} / {fila[2]})")
    return fila[0]


def main():
    identifier = obtener_identifier(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"\nID_INTERNO / identifier: {identifier}\n")

    print("=" * 70)
    print("PRUEBA 1: GET /deliveries/{id} (endpoint normal)")
    print("=" * 70)
    url1 = f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}"
    res1 = requests.get(url1, headers=HEADERS, timeout=15)
    print(f"Status: {res1.status_code}")
    if res1.status_code == 200:
        print(json.dumps(res1.json(), indent=2, ensure_ascii=False))
    else:
        print(res1.text[:500])

    print("\n" + "=" * 70)
    print("PRUEBA 2: GET /deliveries/{id}/tracking (el que ya usa el Plan A)")
    print("=" * 70)
    url2 = f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}/tracking"
    res2 = requests.get(url2, headers=HEADERS, timeout=15)
    print(f"Status: {res2.status_code}")
    if res2.status_code == 200:
        print(json.dumps(res2.json(), indent=2, ensure_ascii=False))
    else:
        print(res2.text[:500])


if __name__ == "__main__":
    main()