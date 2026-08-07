"""
diagnostico_producto_sku.py — Inspecciona qué trae realmente Bsale para un
SKU específico: la variante, y si expand=[product] de verdad embebe el
nombre del producto o solo un href sin resolver.

Uso:
    python diagnostico_producto_sku.py KLEF0091
"""
import os
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402

if len(sys.argv) != 2:
    print("Uso: python diagnostico_producto_sku.py CODIGO_SKU")
    sys.exit(1)

sku = sys.argv[1]

print("=" * 70)
print(f"1) /v1/variants.json?code={sku}  (sin expand)")
print("=" * 70)
variante = None
for v in bsale_get_all("variants.json", params={"code": sku}):
    variante = v
    print(json.dumps(v, indent=2, ensure_ascii=False))

if not variante:
    print(f"❌ No se encontró ninguna variante con code={sku}")
    sys.exit(0)

print()
print("=" * 70)
print(f"2) /v1/variants.json?code={sku}&expand=[product]  (con expand)")
print("=" * 70)
variante_expandida = None
for v in bsale_get_all("variants.json", params={"code": sku, "expand": "[product]"}):
    variante_expandida = v
    print(json.dumps(v, indent=2, ensure_ascii=False))

print()
print("=" * 70)
print("3) ¿El campo 'product' vino embebido (dict con 'name') o solo href?")
print("=" * 70)
producto_campo = (variante_expandida or {}).get("product")
if isinstance(producto_campo, dict) and "name" in producto_campo:
    print(f"✅ Vino embebido. product.name = {producto_campo.get('name')!r}")
else:
    print(f"⚠️ NO vino embebido, solo: {producto_campo!r}")
    product_id = None
    if isinstance(producto_campo, dict):
        product_id = producto_campo.get("id")
        href = producto_campo.get("href", "")
        if not product_id and "/products/" in href:
            product_id = href.split("/products/")[1].split(".json")[0]

    if product_id:
        print()
        print("=" * 70)
        print(f"4) Fallback: GET /v1/products/{product_id}.json directo")
        print("=" * 70)
        detalle_producto = bsale_get_one(f"products/{product_id}.json")
        print(json.dumps(detalle_producto, indent=2, ensure_ascii=False))
        print()
        print(f"✅ Nombre real del producto: {detalle_producto.get('name')!r}")
