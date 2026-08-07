"""
inspeccionar_bsale_crudo.py — Vuelca el JSON COMPLETO (sin filtrar
ningún campo) de varios endpoints de Bsale, para descubrir si la
categorización real de tus productos vive en otro lugar (Bsale tiene
un sistema separado llamado "Clasificaciones" -- classifications --
distinto de "Tipos de Producto" -- product_types -- y es común que se
use uno mientras el otro queda vacío).

Es de solo lectura -- no cambia nada.

Uso:
    python inspeccionar_bsale_crudo.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"))

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}


def _get(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        print(f"\n>>> GET {url}")
        print(f"    status: {res.status_code}")
        if res.status_code == 200:
            return res.json()
        else:
            print(f"    body: {res.text[:300]}")
    except Exception as e:
        print(f"    ERROR: {e}")
    return None


def inspeccionar():
    if not BSALE_TOKEN:
        print("❌ Falta BSALE_TOKEN en el archivo .env")
        return

    print("=" * 90)
    print("1) ¿Existe el endpoint de Clasificaciones? (sistema separado de product_types)")
    print("=" * 90)
    data = _get("https://api.bsale.cl/v1/classifications.json?limit=10")
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])

    print()
    print("=" * 90)
    print("2) JSON completo de los primeros 3 productos (SIN filtrar campos)")
    print("=" * 90)
    data = _get("https://api.bsale.cl/v1/products.json?limit=3&expand=[product_type,classification]")
    if data:
        for item in data.get("items", []):
            print(json.dumps(item, indent=2, ensure_ascii=False))
            print("-" * 60)

    print()
    print("=" * 90)
    print("3) JSON completo de las primeras 3 variantes/SKUs (SIN filtrar campos)")
    print("=" * 90)
    data = _get("https://api.bsale.cl/v1/variants.json?limit=3&expand=[product]")
    if data:
        for item in data.get("items", []):
            print(json.dumps(item, indent=2, ensure_ascii=False))
            print("-" * 60)

    print()
    print("=" * 90)
    print("4) ¿Existe algún atributo (attribute) usado como categoría?")
    print("=" * 90)
    data = _get("https://api.bsale.cl/v1/attributes.json?limit=20")
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])

    print()
    print("Listo. Copia y pégame TODO este resultado -- especialmente cualquier")
    print("campo que muestre nombres como 'Calefacción', 'Generadores', etc.")


if __name__ == "__main__":
    inspeccionar()