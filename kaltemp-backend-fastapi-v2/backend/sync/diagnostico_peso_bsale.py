"""
sync/diagnostico_peso_bsale.py — Diagnóstico exploratorio (Fase 1): ¿Bsale
tiene cargado el peso real por SKU para los productos de Kaltemp?

El campo de peso/dimensiones (variantShipping) vive dentro del módulo
"Descripción Web" de Bsale -- la tienda en línea NATIVA de Bsale, distinta
de Shopify. Requiere un idMarket en la ruta:
    GET /v1/markets/{idMarket}/products/market_info.json?expand=[variantShipping]&code={sku}

Este script primero revisa si existe algún "market" (tienda) configurado
en la cuenta (GET /v1/markets.json). Si no hay ninguno, es señal fuerte
de que este dato no está disponible (Kaltemp usa Shopify para D2C, no la
tienda nativa de Bsale) -- se detiene ahí sin gastar más llamadas.
Si hay markets, prueba variantShipping contra los SKUs indicados.

Uso:
    python sync\\diagnostico_peso_bsale.py SKU_REAL_1 SKU_REAL_2 SKU_REAL_3
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

TOKEN = os.getenv("BSALE_ACCESS_TOKEN")
if not TOKEN:
    raise RuntimeError("Falta BSALE_ACCESS_TOKEN en backend/.env")

HEADERS = {"access_token": TOKEN, "Content-Type": "application/json"}
BASE = "https://api.bsale.io"


def obtener_markets():
    url = f"{BASE}/v1/markets.json"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        return res.status_code, res.json() if res.status_code == 200 else res.text[:400]
    except Exception as e:
        return None, str(e)


def consultar_variant_shipping(id_market, sku):
    url = f"{BASE}/v1/markets/{id_market}/products/market_info.json"
    params = {"expand": "[variantShipping]", "code": sku}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return res.status_code, res.text[:800]
    except Exception as e:
        return None, str(e)


def consultar_variant_basico(sku):
    url = f"{BASE}/v1/variants.json"
    params = {"code": sku}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return res.status_code, res.text[:400]
    except Exception as e:
        return None, str(e)


def main():
    skus = sys.argv[1:]
    if not skus:
        print("Uso: python sync\\diagnostico_peso_bsale.py SKU_REAL_1 SKU_REAL_2 SKU_REAL_3")
        print("(pásame 3-4 códigos SKU reales tuyos, idealmente de productos pesados como termos o calefonts)")
        return

    print("🔎 Paso 1: ¿existe algún 'market' (tienda en línea nativa de Bsale) configurado?")
    status, data = obtener_markets()
    print(f"   GET /v1/markets.json -> {status}")
    print(f"   {data}\n")

    markets = []
    if status == 200 and isinstance(data, dict):
        markets = data.get("items", [])

    if not markets:
        print("=" * 70)
        print("🛑 No hay ningún 'market' configurado en esta cuenta Bsale.")
        print("   Esto confirma que el módulo 'Descripción Web' (tienda nativa Bsale)")
        print("   no está en uso -- coherente con que Kaltemp usa Shopify para D2C.")
        print("   El peso por SKU probablemente NO está disponible por esta vía.")
        print("   Recomendación: seguir con el % de ajuste (enviame_factor_ajuste),")
        print("   ya calculado y funcionando, como solución principal.")
        print("=" * 70)
        return

    print(f"✅ {len(markets)} market(s) encontrado(s) -- probando variantShipping con el primero (id={markets[0]['id']}).\n")
    id_market = markets[0]["id"]

    con_peso = 0
    for sku in skus:
        print("=" * 70)
        print(f"🔎 SKU: {sku}")

        status_a, texto_a = consultar_variant_shipping(id_market, sku)
        print(f"   [A] /v1/markets/{id_market}/products/market_info.json?expand=[variantShipping] -> {status_a}")
        print(f"       {texto_a}")
        if status_a == 200 and '"weight"' in texto_a and '"weight":0' not in texto_a.replace(" ", ""):
            con_peso += 1

        status_b, texto_b = consultar_variant_basico(sku)
        print(f"   [B] /v1/variants.json?code={sku} -> {status_b}")
        print(f"       {texto_b[:300]}")
        print()

    print("=" * 70)
    print(f"\n📊 Resumen: {con_peso}/{len(skus)} SKUs con peso aparentemente cargado.")


if __name__ == "__main__":
    main()