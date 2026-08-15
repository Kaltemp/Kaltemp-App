# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_abandoned_carts.py
"""
diagnostico_abandoned_carts.py

Llama DIRECTO a la API de Shopify (sin tragar el error, a diferencia de
descargar_checkouts_shopify()) para ver qué está pasando realmente:
- ¿Las credenciales están cargadas?
- ¿Qué status code / mensaje devuelve Shopify?
- Si devuelve datos, ¿cuántos checkouts trae y hay más páginas (Link header)?

Uso (desde backend/sync/, con venv activo):
    python diagnostico_abandoned_carts.py
"""
import os
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "kaltemp.myshopify.com")
if SHOPIFY_STORE:
    SHOPIFY_STORE = SHOPIFY_STORE.replace("https://", "").replace("http://", "").strip("/")


def main():
    print("=== Credenciales ===")
    print(f"SHOPIFY_STORE: {SHOPIFY_STORE!r}")
    print(f"SHOPIFY_TOKEN presente: {bool(SHOPIFY_TOKEN)} (largo: {len(SHOPIFY_TOKEN) if SHOPIFY_TOKEN else 0})")

    if not SHOPIFY_TOKEN or not SHOPIFY_STORE:
        print("\n❌ Faltan credenciales -- revisar SHOPIFY_TOKEN / SHOPIFY_STORE en el .env de la raíz.")
        return

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-04/checkouts.json?limit=250&status=any"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

    print(f"\n=== Llamando: {url} ===")
    res = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {res.status_code}")
    print(f"Headers de respuesta relevantes:")
    for h in ("Link", "X-Shopify-Shop-Api-Call-Limit", "X-Shopify-API-Version"):
        if h in res.headers:
            print(f"  {h}: {res.headers[h]}")

    print(f"\nCuerpo (primeros 2000 caracteres):")
    print(res.text[:2000])

    if res.status_code == 200:
        data = res.json()
        checkouts = data.get("checkouts", [])
        print(f"\n✅ {len(checkouts)} checkouts devueltos en esta página.")
        if "Link" in res.headers:
            print("⚠️ Hay más páginas disponibles (Link header presente) -- confirma que falta paginación.")
        else:
            print("ℹ️ No hay Link header -- esta parece ser la única página (o Shopify no pagina esta ruta).")
    elif res.status_code == 401:
        print("\n❌ 401 Unauthorized -- el SHOPIFY_TOKEN es inválido o venció.")
    elif res.status_code == 403:
        print("\n❌ 403 Forbidden -- el token no tiene el scope/permiso para leer checkouts "
              "(revisar permisos de la app privada/custom en Shopify Admin).")
    elif res.status_code == 404:
        print("\n❌ 404 -- este endpoint puede estar deprecado/no disponible para esta tienda "
              "en la versión de API 2024-04 (Shopify deprecó checkouts.json REST para varias cuentas).")


if __name__ == "__main__":
    main()