# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_abandoned_carts.py
"""
sync/sync_abandoned_carts.py — Sincroniza los carritos abandonados de Shopify
hacia la tabla `abandoned_checkouts` en kaltemp_matrix.duckdb.

CORREGIDO (11-ago-2026, 3 bugs reales confirmados con diagnóstico):
1. Sin ventana de fecha: pedía checkouts.json sin `created_at_min`, así
   que Shopify devolvía los 250 MÁS VIEJOS de toda la tienda (ordena por
   ID ascendente por default) -- confirmado real: la primera página
   traía un checkout de octubre 2023, nada útil para seguimiento de
   carritos abandonados recientes. Ahora se filtra con created_at_min,
   ventana configurable vía ABANDONED_CARTS_DIAS_ATRAS (default 60,
   mismo patrón que ENVIAME_DIAS_ATRAS).
2. Sin paginación: se quedaba con la primera página (limit=250) aunque
   el header `Link` de la respuesta confirmara que había más páginas
   (rel="next") -- confirmado real con diagnóstico. Ahora sigue ese
   header hasta agotar las páginas.
3. Error tragado en silencio: si la llamada a Shopify fallaba (token
   vencido, DNS, timeout), el código seguía de largo, hacía
   `DELETE FROM abandoned_checkouts` e insertaba la lista vacía que
   quedaba -- dejando la tabla vacía sin ningún aviso visible más allá
   de un print(). Ahora, si la descarga no fue exitosa, NO se toca la
   tabla (se conserva lo que había de la corrida anterior).
"""
import os
import time
import requests
import duckdb
from datetime import datetime, timedelta, timezone
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

# Límite defensivo de páginas -- 250 checkouts/página; 200 páginas cubre
# hasta 50.000 checkouts en la ventana pedida. Evita un loop infinito si
# Shopify alguna vez devolviera un Link mal formado que apunte a sí mismo.
_MAX_PAGINAS = 200


def parsear_fecha(val_fecha):
    if not val_fecha:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        s = str(val_fecha).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def _extraer_siguiente_url(headers) -> str | None:
    """Parsea el header Link estilo RFC 5988 que devuelve Shopify, ej.:
    '<https://.../checkouts.json?...>; rel="next"' (puede traer también
    rel="previous" en la misma cabecera, separados por coma)."""
    link_header = headers.get("Link")
    if not link_header:
        return None
    for parte in link_header.split(","):
        if 'rel="next"' in parte:
            inicio = parte.find("<")
            fin = parte.find(">")
            if inicio != -1 and fin != -1:
                return parte[inicio + 1:fin]
    return None


def descargar_checkouts_shopify(dias_atras: int = 60):
    """Descarga los carritos abandonados desde la API Admin de Shopify,
    paginando con el header Link hasta agotar las páginas o llegar a
    _MAX_PAGINAS. Devuelve (checkouts, exito) -- exito=False si hubo
    CUALQUIER error de red/HTTP, para que el llamador NO borre lo que
    ya había en la tabla."""
    if not SHOPIFY_TOKEN or not SHOPIFY_STORE:
        print("⚠️ Falta SHOPIFY_TOKEN y/o SHOPIFY_STORE en el archivo .env")
        return [], False

    fecha_desde = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).strftime("%Y-%m-%dT00:00:00Z")
    headers_req = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    url = (
        f"https://{SHOPIFY_STORE}/admin/api/2024-04/checkouts.json"
        f"?limit=250&status=any&created_at_min={fecha_desde}"
    )

    checkouts = []
    pagina = 0
    try:
        while url and pagina < _MAX_PAGINAS:
            pagina += 1
            res = requests.get(url, headers=headers_req, timeout=30)
            if res.status_code != 200:
                print(f"⚠️ Error consultando Shopify ({res.status_code}) en página {pagina}: {res.text[:300]}")
                return checkouts, False

            data = res.json()
            checkouts.extend(data.get("checkouts", []))
            url = _extraer_siguiente_url(res.headers)
            if url:
                time.sleep(0.3)  # no saturar el rate limit de Shopify entre páginas

        if pagina >= _MAX_PAGINAS and url:
            print(f"⚠️ Se alcanzó el límite de {_MAX_PAGINAS} páginas con más datos disponibles -- "
                  f"considera acortar ABANDONED_CARTS_DIAS_ATRAS.")

    except Exception as e:
        print(f"⚠️ Error de conexión con Shopify (página {pagina}): {e}")
        return checkouts, False

    return checkouts, True


def sync_abandoned_carts(progress_callback=None, dias_atras: int = None):
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    if dias_atras is None:
        dias_atras = int(os.getenv("ABANDONED_CARTS_DIAS_ATRAS", "60"))

    report(5, f"🛒 Conectando con API de Shopify para sincronizar Carritos Abandonados (últimos {dias_atras} días)...")
    raw_checkouts, exito = descargar_checkouts_shopify(dias_atras=dias_atras)

    if not exito:
        report(100, "❌ Falló la descarga desde Shopify -- se conserva la tabla anterior sin cambios "
                     "(no se borra por un error de red/API).")
        return

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
        # FIX (15-ago-2026, a pedido de William -- ver auditoría del chat):
        # antes esto era `DELETE FROM abandoned_checkouts` SIN WHERE --
        # borraba la tabla ENTERA y la dejaba con solo lo que se acababa
        # de descargar (la ventana de dias_atras). Con dias_atras=30 (el
        # que ya manda "Actualizar Ahora" hoy) esto ya estaba perdiendo
        # cualquier carrito histórico más viejo. Ahora solo se borra +
        # reinserta la ventana de fechas que efectivamente se volvió a
        # descargar de Shopify -- el resto del histórico queda intacto.
        fecha_corte = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).date()
        con.execute(
            "DELETE FROM abandoned_checkouts WHERE CAST(FECHA_OBJ AS DATE) >= CAST(? AS DATE)",
            [fecha_corte],
        )
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