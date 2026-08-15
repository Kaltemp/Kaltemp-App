# ============================================================
# ARCHIVO: diagnostico_falabella_fix.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_falabella_fix.py
# ============================================================
"""
diagnostico_falabella_fix.py — Prueba 2 hipótesis de arreglo:

1. GetOrderItems: "Invalid Order ID" con OrderId=1028501148 (parámetro
   suelto) -- prueba con OrderIdList=[1028501148] (formato de lista,
   típico de APIs estilo Lazada Open Platform, que es la base de
   Falabella Seller Center).

2. GetOrders con rango amplio (2023-2026) solo trae TotalCount=2, pero
   los últimos 30 días solos traen 100+ -- prueba con ventanas de 1 año
   para ver si el TotalCount cambia (confirma si hay un límite oculto
   en rangos de fecha muy amplios).

Uso:
    python diagnostico_falabella_fix.py
"""
import os
import sys
import json
import time
import datetime
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

sys.path.insert(0, _AQUI)
from falabella_client import _credenciales, _falabella_timestamp, _falabella_firmar, FALABELLA_URL  # noqa: E402

api_key, user_id = _credenciales()

print("=" * 70)
print("1) GetOrderItems con OrderIdList=[...] en vez de OrderId=...")
print("=" * 70)
order_id = "1028501148"
params = {
    "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
    "UserID": user_id, "Version": "1.0",
    "OrderIdList": json.dumps([int(order_id)]),
}
params["Signature"] = _falabella_firmar(api_key, params)
res = requests.get(FALABELLA_URL, params=params, timeout=20)
print(f"status_code: {res.status_code}")
print(json.dumps(res.json(), indent=2, ensure_ascii=False)[:2500])

print()
print("=" * 70)
print("2) GetOrders por ventanas de 1 año -- ¿el TotalCount cambia?")
print("=" * 70)
rangos = [
    (datetime.date(2023, 1, 1), datetime.date(2023, 12, 31)),
    (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31)),
    (datetime.date(2025, 1, 1), datetime.date(2025, 12, 31)),
    (datetime.date(2026, 1, 1), datetime.date.today()),
]
for inicio, fin in rangos:
    params2 = {
        "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
        "UserID": user_id, "Version": "1.0",
        "CreatedAfter": inicio.strftime("%Y-%m-%dT00:00:00-04:00"),
        "CreatedBefore": fin.strftime("%Y-%m-%dT23:59:59-04:00"),
        "Limit": "1", "Offset": "0",
    }
    params2["Signature"] = _falabella_firmar(api_key, params2)
    res2 = requests.get(FALABELLA_URL, params=params2, timeout=20)
    total_count = None
    if res2.status_code == 200:
        total_count = res2.json().get("SuccessResponse", {}).get("Head", {}).get("TotalCount")
    print(f"  {inicio} -> {fin}: status={res2.status_code}, TotalCount={total_count}")
    time.sleep(0.3)