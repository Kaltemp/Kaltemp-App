"""
explorar_categorias_bsale.py — Trae TODAS las categorías (Tipos de
Producto) que existen hoy en tu cuenta de Bsale, con el detalle de qué
productos tiene cada una y cuánto ha vendido cada producto. Es de solo
lectura -- no cambia nada en Bsale ni en tu base local.

Uso:
    python explorar_categorias_bsale.py

Genera dos archivos en la misma carpeta:
  - categorias_resumen.csv   -> una fila por categoría (cuántos SKUs, venta total)
  - categorias_detalle.csv   -> una fila por SKU, con su categoría y venta

Y muestra un resumen en pantalla.
"""
import os
import csv
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"))

import duckdb
from db import DB_PATH

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}


def explorar():
    if not BSALE_TOKEN:
        print("❌ Falta BSALE_TOKEN en el archivo .env")
        return

    # 1. Traer TODAS las categorías (Tipos de Producto) de Bsale, tal cual existen hoy
    print("📦 Descargando Tipos de Producto desde Bsale...")
    categorias = {}  # id -> nombre
    res_cat = requests.get("https://api.bsale.cl/v1/product_types.json?limit=50", headers=HEADERS, timeout=20)
    if res_cat.status_code == 200:
        for cat in res_cat.json().get("items", []):
            categorias[str(cat.get("id"))] = str(cat.get("name", "")).strip()
    print(f"   {len(categorias)} categorías encontradas en Bsale: {', '.join(categorias.values())}")

    # 2. Traer TODOS los productos con su categoría asignada
    print("📦 Descargando productos y su categoría asignada...")
    productos = {}  # product_id -> (nombre, categoria_id, categoria_nombre)
    offset = 0
    while True:
        res_prod = requests.get(
            f"https://api.bsale.cl/v1/products.json?limit=50&offset={offset}",
            headers=HEADERS, timeout=20
        )
        if res_prod.status_code != 200:
            break
        items = res_prod.json().get("items", [])
        if not items:
            break
        for p in items:
            prod_id = str(p.get("id"))
            nombre = str(p.get("name", "")).strip()
            cat_obj = p.get("product_type") or {}
            cat_id = str(cat_obj.get("id")) if isinstance(cat_obj, dict) else ""
            cat_nombre = categorias.get(cat_id, "(sin tipo asignado)")
            productos[prod_id] = (nombre, cat_id, cat_nombre)
        offset += 50
    print(f"   {len(productos)} productos encontrados en Bsale")

    # 3. Traer variantes (SKUs) para conectar cada SKU a su producto/categoría
    print("📦 Descargando variantes (SKUs)...")
    filas_sku = []  # (sku, producto_nombre, categoria_nombre)
    offset = 0
    while True:
        res_var = requests.get(
            f"https://api.bsale.cl/v1/variants.json?limit=50&offset={offset}&expand=[product]",
            headers=HEADERS, timeout=20
        )
        if res_var.status_code != 200:
            break
        items = res_var.json().get("items", [])
        if not items:
            break
        for v in items:
            sku = str(v.get("code") or "").strip().upper()
            if not sku:
                continue
            prod_obj = v.get("product") or {}
            prod_id = str(prod_obj.get("id")) if isinstance(prod_obj, dict) else ""
            nombre_prod, cat_id, cat_nombre = productos.get(prod_id, (sku, "", "(producto no encontrado)"))
            filas_sku.append((sku, nombre_prod, cat_nombre))
        offset += 50
    print(f"   {len(filas_sku)} SKUs/variantes encontrados\n")

    # 4. Cruzar contra venta real local (kaltemp_matrix.duckdb) para saber cuánto vende cada uno
    con = duckdb.connect(DB_PATH, read_only=True)
    ventas_por_sku = dict(con.execute("""
        SELECT SKU_BSALE, SUM(BRUTO_TOTAL) FROM ventas GROUP BY SKU_BSALE
    """).fetchall())
    con.close()

    # 5. Armar detalle por SKU
    ruta_detalle = os.path.join(_AQUI, "categorias_detalle.csv")
    with open(ruta_detalle, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "Producto", "Categoría en Bsale", "Venta total ($)"])
        for sku, nombre_prod, cat_nombre in sorted(filas_sku, key=lambda r: -(ventas_por_sku.get(r[0], 0) or 0)):
            writer.writerow([sku, nombre_prod, cat_nombre, int(ventas_por_sku.get(sku, 0) or 0)])

    # 6. Armar resumen por categoría
    resumen = {}  # categoria -> {skus: n, venta: total}
    for sku, nombre_prod, cat_nombre in filas_sku:
        r = resumen.setdefault(cat_nombre, {"skus": 0, "venta": 0})
        r["skus"] += 1
        r["venta"] += ventas_por_sku.get(sku, 0) or 0

    ruta_resumen = os.path.join(_AQUI, "categorias_resumen.csv")
    with open(ruta_resumen, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Categoría en Bsale", "Cantidad de SKUs", "Venta total ($)"])
        for cat_nombre, r in sorted(resumen.items(), key=lambda kv: -kv[1]["venta"]):
            writer.writerow([cat_nombre, r["skus"], int(r["venta"])])

    print("=" * 90)
    print("RESUMEN POR CATEGORÍA (ordenado por venta)")
    print("=" * 90)
    for cat_nombre, r in sorted(resumen.items(), key=lambda kv: -kv[1]["venta"]):
        print(f"  {cat_nombre[:40]:40} {r['skus']:>5} SKUs   ${r['venta']:>14,.0f}")

    print()
    print(f"📄 Detalle completo (por SKU) guardado en: {ruta_detalle}")
    print(f"📄 Resumen por categoría guardado en: {ruta_resumen}")


if __name__ == "__main__":
    explorar()