# ============================================================
# ARCHIVO: diagnostico_falabella_reciente.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_falabella_reciente.py
# ============================================================
"""
diagnostico_falabella_reciente.py — GetOrderItems con OrderId=1028501148
(un pedido de ENERO 2023, el más antiguo) da "Invalid Order ID" aunque
el parámetro y el valor son correctos. Prueba con un pedido RECIENTE
(últimos 30 días, sabemos que hay 100+) para aislar si el problema es
la antigüedad del pedido específico, no el formato de la llamada.

Uso:
    python diagnostico_falabella_reciente.py
"""
import os
import sys
import json
import datetime
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

sys.path.insert(0, _AQUI)
from falabella_client import _credenciales, _falabella_timestamp, _falabella_firmar, FALABELLA_URL  # noqa: E402

api_key, user_id = _credenciales()

# 1) Traer 3 pedidos recientes
fecha_inicio = datetime.date.today() - datetime.timedelta(days=30)
fecha_fin = datetime.date.today()
params = {
    "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
    "UserID": user_id, "Version": "1.0",
    "CreatedAfter": fecha_inicio.strftime("%Y-%m-%dT00:00:00-04:00"),
    "CreatedBefore": fecha_fin.strftime("%Y-%m-%dT23:59:59-04:00"),
    "Limit": "3", "Offset": "0",
}
params["Signature"] = _falabella_firmar(api_key, params)
res = requests.get(FALABELLA_URL, params=params, timeout=20)
pedidos = res.json().get("SuccessResponse", {}).get("Body", {}).get("Orders", {}).get("Order", [])
if isinstance(pedidos, dict):
    pedidos = [pedidos]

print(f"{len(pedidos)} pedidos recientes encontrados.\n")

# 2) Probar GetOrderItems con cada uno
for pedido in pedidos:
    order_id = pedido.get("OrderId")
    created_at = pedido.get("CreatedAt")
    print("=" * 70)
    print(f"OrderId={order_id} (creado {created_at})")
    print("=" * 70)

    params2 = {
        "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
        "UserID": user_id, "Version": "1.0", "OrderId": str(order_id),
    }
    params2["Signature"] = _falabella_firmar(api_key, params2)
    res2 = requests.get(FALABELLA_URL, params=params2, timeout=20)
    data2 = res2.json()
    if "SuccessResponse" in data2:
        items = data2.get("SuccessResponse", {}).get("Body", {}).get("OrderItems", {}).get("OrderItem", [])
        if isinstance(items, dict):
            items = [items]
        print(f"✅ ÉXITO -- {len(items)} item(s)")
        if items:
            print(json.dumps(items[0], indent=2, ensure_ascii=False)[:1500])
    else:
        err = data2.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "")
        print(f"❌ error: {err}")
    print()