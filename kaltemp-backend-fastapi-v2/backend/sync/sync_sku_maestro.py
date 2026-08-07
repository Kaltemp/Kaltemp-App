"""
sync/sync_sku_maestro.py — Descarga el catálogo maestro completo de variantes
y categorías desde Bsale y puebla la tabla `sku_maestro` en DuckDB.
"""
import os
import sys
import requests
import duckdb
from datetime import datetime, timezone
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}


def sync_sku_maestro():
    print(f"[{datetime.now()}] 📦 Descargando catálogo maestro de SKUs y Categorías desde Bsale...")
    if not BSALE_TOKEN:
        print("❌ Falta BSALE_TOKEN en el archivo .env")
        return

    # 1. Traer categorías
    mapa_categorias = {}
    try:
        res_cat = requests.get("https://api.bsale.cl/v1/product_types.json", headers=HEADERS, timeout=20)
        if res_cat.status_code == 200:
            for cat in res_cat.json().get("items", []):
                mapa_categorias[str(cat.get("id"))] = str(cat.get("name", "")).strip()
    except Exception as e:
        print(f"⚠️ Error cargando categorías de Bsale: {e}")

    # 2. Traer productos
    mapa_productos_cat = {}
    try:
        offset = 0
        limit = 50
        while True:
            res_prod = requests.get(f"https://api.bsale.cl/v1/products.json?limit={limit}&offset={offset}", headers=HEADERS, timeout=20)
            if res_prod.status_code != 200:
                break
            items = res_prod.json().get("items", [])
            if not items:
                break
            for p in items:
                prod_id = str(p.get("id"))
                cat_obj = p.get("product_type") or {}
                cat_id = str(cat_obj.get("id")) if isinstance(cat_obj, dict) else ""
                cat_nombre = mapa_categorias.get(cat_id, "Sin Categoría Mapeada")
                mapa_productos_cat[prod_id] = (str(p.get("name", "")).strip().upper(), cat_nombre)
            offset += limit
    except Exception as e:
        print(f"⚠️ Error cargando productos de Bsale: {e}")

    # 3. Traer variantes (SKUs)
    filas = []
    try:
        offset = 0
        limit = 50
        while True:
            res_var = requests.get(f"https://api.bsale.cl/v1/variants.json?limit={limit}&offset={offset}&expand=[product]", headers=HEADERS, timeout=20)
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
                
                nombre_prod, categoria = mapa_productos_cat.get(prod_id, (str(v.get("description", sku)).upper(), "Sin Categoría Mapeada"))
                
                filas.append((sku, nombre_prod, categoria))
            offset += limit
    except Exception as e:
        print(f"⚠️ Error cargando variantes de Bsale: {e}")

    print(f"[{datetime.now()}] 💾 Escribiendo {len(filas)} SKUs maestros en DuckDB...")

    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS sku_maestro (
                SKU VARCHAR PRIMARY KEY, PRODUCTO VARCHAR, CATEGORIA VARCHAR
            )
        """)
        con.execute("DELETE FROM sku_maestro")
        con.executemany(
            "INSERT OR REPLACE INTO sku_maestro (SKU, PRODUCTO, CATEGORIA) VALUES (?, ?, ?)",
            filas
        )
        print(f"[{datetime.now()}] ✅ sku_maestro actualizada ({len(filas)} SKUs mapeados con su categoría Bsale).")


if __name__ == "__main__":
    sync_sku_maestro()