"""
falabella_client.py — Cliente para Falabella Seller Center API.

Portado (02-ago-2026) desde el app.py original de Streamlit
(obtener_ventas_falabella_api), donde ya estaba probado en producción.
Se mantiene la MISMA lógica de firma HMAC-SHA256 y llamadas GetOrders/
GetOrderItems -- solo se reorganiza como cliente reutilizable, sin
Streamlit ni caché de Streamlit (@st.cache_data), para usarlo desde
scripts de sync normales.

Requiere en backend/.env:
    FALABELLA_API_KEY=...
    FALABELLA_USER=...
"""
import os
import time
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# Igual que bsale_client.py: los scripts de sync corren sueltos (python
# sync_xxx.py), no a través de main.py, así que cargan el .env por su
# cuenta acá. OJO (confirmado 02-ago-2026): a diferencia de bsale_client.py
# (que usa backend/.env, un nivel arriba de backend/sync/), las
# credenciales de Falabella/Envíame/Cliengo/Shopify viven en el .env de la
# RAÍZ del proyecto (kaltemp-backend-fastapi-v2/.env) -- dos niveles arriba
# de este archivo, no uno.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

TZ_CHILE = ZoneInfo("America/Santiago")
FALABELLA_URL = "https://sellercenter-api.falabella.com"

# Límite real de Falabella: 30 requests / 3 segundos (confirmado en el
# código original -- se respeta la misma pausa entre pedidos).
_PAUSA_ENTRE_REQUESTS = 0.15


def _falabella_timestamp() -> str:
    ts = datetime.now(TZ_CHILE)
    t = ts.strftime("%Y-%m-%dT%H:%M:%S%z")
    return f"{t[:-2]}:{t[-2:]}"  # -0400 -> -04:00


def _falabella_firmar(api_key: str, params: dict) -> str:
    concatenated = urllib.parse.urlencode(sorted(params.items()))
    return hmac.new(api_key.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha256).hexdigest()


def _credenciales() -> tuple[str, str]:
    api_key = os.environ.get("FALABELLA_API_KEY")
    user_id = os.environ.get("FALABELLA_USER")
    if not api_key or not user_id:
        raise RuntimeError(
            "Faltan FALABELLA_API_KEY y/o FALABELLA_USER en backend/.env"
        )
    return api_key, user_id


def get_orders(fecha_inicio, fecha_fin) -> list[dict]:
    """
    GetOrders -- descubre qué pedidos existen creados en el rango
    [fecha_inicio, fecha_fin] (objetos date/datetime). Pagina de a 100.
    """
    api_key, user_id = _credenciales()
    pedidos = []
    limit, offset = 100, 0
    while True:
        params = {
            "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
            "UserID": user_id, "Version": "1.0",
            "CreatedAfter": fecha_inicio.strftime("%Y-%m-%dT00:00:00-04:00"),
            "CreatedBefore": fecha_fin.strftime("%Y-%m-%dT23:59:59-04:00"),
            "Limit": str(limit), "Offset": str(offset),
        }
        params["Signature"] = _falabella_firmar(api_key, params)

        resp = requests.get(FALABELLA_URL, params=params, timeout=20)
        if resp.status_code != 200:
            break
        data = resp.json()
        orders = data.get("SuccessResponse", {}).get("Body", {}).get("Orders", {}).get("Order", [])
        if isinstance(orders, dict):
            orders = [orders]
        if not orders:
            break
        pedidos.extend(orders)
        if len(orders) < limit:
            break
        offset += limit
        time.sleep(_PAUSA_ENTRE_REQUESTS)

    return pedidos


def get_order_items(order_id) -> list[dict]:
    """GetOrderItems -- detalle por SKU de un pedido, con Status real por línea."""
    api_key, user_id = _credenciales()
    params = {
        "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
        "UserID": user_id, "Version": "1.0", "OrderId": str(order_id),
    }
    params["Signature"] = _falabella_firmar(api_key, params)

    resp = requests.get(FALABELLA_URL, params=params, timeout=20)
    if resp.status_code != 200:
        return []
    data = resp.json()
    items = data.get("SuccessResponse", {}).get("Body", {}).get("OrderItems", {}).get("OrderItem", [])
    if isinstance(items, dict):
        items = [items]
    return items


# Traducción de los estados reales de Falabella (confirmados en el código
# original: pending, canceled, cancelled, returned, y los de despacho) a
# etiquetas legibles en español para la UI.
ESTADOS_LEGIBLES = {
    "pending": "Pendiente",
    "ready_to_ship": "Listo para despacho",
    "shipped": "Despachado",
    "delivered": "Entregado",
    "canceled": "Cancelado",
    "cancelled": "Cancelado",
    "returned": "Devuelto",
    "failed": "Fallido",
    "shipped_by_marketplace": "Despachado (Fulfillment)",
}


def estado_legible(estado_raw: str | None) -> str:
    if not estado_raw:
        return "Sin estado"
    clave = estado_raw.lower().strip()
    return ESTADOS_LEGIBLES.get(clave, estado_raw.capitalize())