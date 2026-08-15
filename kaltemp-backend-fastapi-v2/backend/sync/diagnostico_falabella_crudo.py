# ============================================================
# ARCHIVO: diagnostico_falabella_crudo.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_falabella_crudo.py
# ============================================================
"""
diagnostico_falabella_crudo.py — sync_falabella_estados.py solo
encontró 2 pedidos en 3.5 años (2023-01-01 a hoy), y esos 2 no trajeron
ningún item -- cuando `ventas` sí muestra venta real de Falabella cada
semana. Este script llama a GetOrders Y GetOrderItems directo, sin pasar
por el parseo de falabella_client.py, para ver la respuesta CRUDA
completa y detectar si es un problema de rango de fecha, paginación,
permisos de la cuenta, o el nombre real del campo de items.

Uso:
    python diagnostico_falabella_crudo.py
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
print(f"UserID configurado: {user_id}")
print(f"API Key -- longitud: {len(api_key) if api_key else 0}")
print()

# ------------------------------------------------------------
# 1) GetOrders crudo, ventana amplia
# ------------------------------------------------------------
fecha_inicio = datetime.date(2023, 1, 1)
fecha_fin = datetime.date.today()

params = {
    "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
    "UserID": user_id, "Version": "1.0",
    "CreatedAfter": fecha_inicio.strftime("%Y-%m-%dT00:00:00-04:00"),
    "CreatedBefore": fecha_fin.strftime("%Y-%m-%dT23:59:59-04:00"),
    "Limit": "100", "Offset": "0",
}
params["Signature"] = _falabella_firmar(api_key, params)

print("=" * 70)
print("1) GetOrders -- respuesta CRUDA completa")
print("=" * 70)
res = requests.get(FALABELLA_URL, params=params, timeout=20)
print(f"status_code: {res.status_code}")
data = res.json()
print(json.dumps(data, indent=2, ensure_ascii=False)[:4000])

pedidos = data.get("SuccessResponse", {}).get("Body", {}).get("Orders", {}).get("Order", [])
if isinstance(pedidos, dict):
    pedidos = [pedidos]
print(f"\n-> {len(pedidos)} pedido(s) extraídos con el parseo actual.")

# ------------------------------------------------------------
# 2) GetOrderItems crudo, para el primer pedido encontrado
# ------------------------------------------------------------
if pedidos:
    primer_pedido = pedidos[0]
    order_id = primer_pedido.get("OrderId")
    print()
    print("=" * 70)
    print(f"2) GetOrderItems -- respuesta CRUDA para OrderId={order_id}")
    print("=" * 70)
    print("Campos disponibles en el pedido:", list(primer_pedido.keys()))

    params2 = {
        "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
        "UserID": user_id, "Version": "1.0", "OrderId": str(order_id),
    }
    params2["Signature"] = _falabella_firmar(api_key, params2)
    res2 = requests.get(FALABELLA_URL, params=params2, timeout=20)
    print(f"status_code: {res2.status_code}")
    print(json.dumps(res2.json(), indent=2, ensure_ascii=False)[:4000])
else:
    print("\n⚠️ No hay pedidos para probar GetOrderItems.")

# ------------------------------------------------------------
# 3) Probar una ventana MÁS CHICA y reciente (últimos 30 días) --
#    para descartar que el problema sea específico de rangos largos.
# ------------------------------------------------------------
print()
print("=" * 70)
print("3) GetOrders -- ventana chica (últimos 30 días), para comparar")
print("=" * 70)
fecha_inicio_corta = datetime.date.today() - datetime.timedelta(days=30)
params3 = {
    "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
    "UserID": user_id, "Version": "1.0",
    "CreatedAfter": fecha_inicio_corta.strftime("%Y-%m-%dT00:00:00-04:00"),
    "CreatedBefore": fecha_fin.strftime("%Y-%m-%dT23:59:59-04:00"),
    "Limit": "100", "Offset": "0",
}
params3["Signature"] = _falabella_firmar(api_key, params3)
res3 = requests.get(FALABELLA_URL, params=params3, timeout=20)
print(f"status_code: {res3.status_code}")
data3 = res3.json()
pedidos3 = data3.get("SuccessResponse", {}).get("Body", {}).get("Orders", {}).get("Order", [])
if isinstance(pedidos3, dict):
    pedidos3 = [pedidos3]
print(f"-> {len(pedidos3)} pedido(s) en los últimos 30 días.")
if not pedidos3:
    print(json.dumps(data3, indent=2, ensure_ascii=False)[:2000])