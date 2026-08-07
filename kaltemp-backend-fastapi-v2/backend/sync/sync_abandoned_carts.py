"""
sync/sync_abandoned_carts.py — Sincroniza los carritos abandonados de Shopify
hacia la tabla `abandoned_checkouts` en kaltemp_matrix.duckdb.
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

SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "kaltemp.myshopify.com")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

# Normalizar URL de la tienda
if SHOPIFY_STORE:
    SHOPIFY_STORE = SHOPIFY_STORE.replace("https://", "").replace("http://", "").strip("/")


def parsear_fecha(val_fecha):
    if not val_fecha:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        s = str(val_fecha).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def descargar_checkouts_shopify():
    """Descarga los carritos abandonados desde la API Admin de Shopify"""
    if not SHOPIFY_TOKEN or not SHOPIFY_STORE:
        print("⚠️ Falta SHOPIFY_TOKEN y/o SHOPIFY_STORE en el archivo .env")
        return []

    checkouts = []
    # API Admin Endpoint para Checkouts de Shopify
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-04/checkouts.json?limit=250&status=any"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            data = res.json()
            checkouts = data.get("checkouts", [])
        else:
            print(f"⚠️ Error consultando Shopify ({res.status_code}): {res.text[:300]}")
    except Exception as e:
        print(f"⚠️ Error de conexión con Shopify: {e}")

    return checkouts


def sync_abandoned_carts(progress_callback=None):
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    report(5, "🛒 Conectando con API de Shopify para sincronizar Carritos Abandonados...")
    raw_checkouts = descargar_checkouts_shopify()
    report(40, f"📥 {len(raw_checkouts)} carritos/checkouts descargados de Shopify.")

    filas = []
    for c in raw_checkouts:
        if not isinstance(c, dict):
            continue

        id_checkout = str(c.get("id") or c.get("token") or "")
        fecha_obj = parsear_fecha(c.get("created_at") or c.get("updated_at"))
        
        # Cliente / Contacto
        customer = c.get("customer") or {}
        email = str(c.get("email") or customer.get("email") or "Sin email").strip()
        
        nombre_cli = ""
        if isinstance(customer, dict):
            fn = customer.get("first_name", "") or ""
            ln = customer.get("last_name", "") or ""
            nombre_cli = f"{fn} {ln}".strip()
        if not nombre_cli:
            nombre_cli = email if email != "Sin email" else "CLIENTE SHOPIFY"

        total_price = float(c.get("total_price") or c.get("subtotal_price") or 0.0)
        
        # Estado: Recuperado si completed_at existe, de lo contrario Abandonado
        completed_at = c.get("completed_at")
        estado = "RECUPERADO" if completed_at else "ABANDONADO"

        # Detalle de Líneas de Producto
        line_items = c.get("line_items") or []
        if line_items:
            for item in line_items:
                producto = str(item.get("title") or item.get("name") or "PRODUCTO SHOPIFY").strip().upper()
                sku = str(item.get("sku") or "").strip().upper()
                precio_unitario = float(item.get("price") or 0.0)

                filas.append((
                    id_checkout, fecha_obj, nombre_cli.upper(), email,
                    producto, sku, precio_unitario, total_price, estado
                ))
        else:
            # Si el carrito no trajo items desagregados, guarda la cabecera
            filas.append((
                id_checkout, fecha_obj, nombre_cli.upper(), email,
                "VARIOS PRODUCTOS", "", total_price, total_price, estado
            ))

    report(70, f"💾 Escribiendo {len(filas)} filas en 'abandoned_checkouts' de DuckDB...")

    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS abandoned_checkouts (
                ID_CHECKOUT VARCHAR, FECHA_OBJ TIMESTAMP, CLIENTE VARCHAR,
                EMAIL VARCHAR, PRODUCTO VARCHAR, SKU VARCHAR,
                PRECIO_UNITARIO DOUBLE, TOTAL_PRICE DOUBLE, ESTADO VARCHAR
            )
        """)
        con.execute("DELETE FROM abandoned_checkouts")
        con.executemany(
            """INSERT INTO abandoned_checkouts
               (ID_CHECKOUT, FECHA_OBJ, CLIENTE, EMAIL, PRODUCTO, SKU, PRECIO_UNITARIO, TOTAL_PRICE, ESTADO)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["abandoned_checkouts", datetime.now(timezone.utc).replace(tzinfo=None)]
        )

    report(100, f"✨ Sincronización de Carritos Abandonados completa ({len(filas)} filas guardadas).")


if __name__ == "__main__":
    sync_abandoned_carts()