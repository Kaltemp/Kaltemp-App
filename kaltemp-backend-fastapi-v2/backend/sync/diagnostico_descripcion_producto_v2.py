# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_descripcion_producto_v2.py
"""
diagnostico_descripcion_producto_v2.py

Apunta directo al envío 458792843 (el de la captura real, donde sabemos
que "Descripción del producto" = "APOLO 1500 INVERTER") y dumpea:
1. GET /deliveries/458792843 -- ¿aparece el campo directo acá?
2. GET /deliveries/458792843/tracking -- si no, ¿aparece como evento de
   edición? ¿con qué texto exacto describe Envíame ese cambio?

Busca la palabra "APOLO" en ambas respuestas para ubicar exactamente
dónde vive el dato, sin tener que leer todo el JSON a mano.

Uso:
    python diagnostico_descripcion_producto_v2.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}

IDENTIFIER = "458792843"


def buscar_apolo(data, ruta=""):
    """Recorre el JSON recursivamente e imprime la ruta de cualquier
    campo cuyo valor contenga 'APOLO' -- así ubicamos el campo exacto
    sin tener que leer todo el dump a mano."""
    encontrados = []
    if isinstance(data, dict):
        for k, v in data.items():
            encontrados.extend(buscar_apolo(v, f"{ruta}.{k}" if ruta else k))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            encontrados.extend(buscar_apolo(v, f"{ruta}[{i}]"))
    elif isinstance(data, str) and "APOLO" in data.upper():
        encontrados.append((ruta, data))
    return encontrados


def main():
    print("=" * 70)
    print(f"PRUEBA 1: GET /deliveries/{IDENTIFIER}")
    print("=" * 70)
    url1 = f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}"
    res1 = requests.get(url1, headers=HEADERS, timeout=15)
    print(f"Status: {res1.status_code}")
    if res1.status_code == 200:
        data1 = res1.json()
        print(json.dumps(data1, indent=2, ensure_ascii=False))
        print("\n--- Campos que contienen 'APOLO' ---")
        for ruta, val in buscar_apolo(data1):
            print(f"  {ruta} = {val!r}")
    else:
        print(res1.text[:500])

    print("\n" + "=" * 70)
    print(f"PRUEBA 2: GET /deliveries/{IDENTIFIER}/tracking")
    print("=" * 70)
    url2 = f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/tracking"
    res2 = requests.get(url2, headers=HEADERS, timeout=15)
    print(f"Status: {res2.status_code}")
    if res2.status_code == 200:
        data2 = res2.json()
        print(json.dumps(data2, indent=2, ensure_ascii=False))
        print("\n--- Campos que contienen 'APOLO' ---")
        for ruta, val in buscar_apolo(data2):
            print(f"  {ruta} = {val!r}")
    else:
        print(res2.text[:500])


if __name__ == "__main__":
    main()