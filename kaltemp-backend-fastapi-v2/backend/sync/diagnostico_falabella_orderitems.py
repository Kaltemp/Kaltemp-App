# ============================================================
# ARCHIVO: diagnostico_falabella_orderitems.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_falabella_orderitems.py
# ============================================================
"""
diagnostico_falabella_orderitems.py — Prueba varias combinaciones de
nombre/formato de parámetro para GetOrderItems, ya que ni OrderId=X ni
OrderIdList=[X] (json) funcionaron. Usa el OrderNumber real también
(no solo el OrderId), por si la API espera ese campo en su lugar.

Uso:
    python diagnostico_falabella_orderitems.py
"""
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

sys.path.insert(0, _AQUI)
from falabella_client import _credenciales, _falabella_timestamp, _falabella_firmar, FALABELLA_URL  # noqa: E402

api_key, user_id = _credenciales()

ORDER_ID = "1028501148"
ORDER_NUMBER = "2045181292"

candidatos = [
    {"OrderId": ORDER_ID},
    {"OrderIdList": f"[{ORDER_ID}]"},
    {"OrderIdList": ORDER_ID},
    {"OrderIds": ORDER_ID},
    {"OrderIds": f"[{ORDER_ID}]"},
    {"OrderItemIds": ORDER_ID},
    {"OrderNumber": ORDER_NUMBER},
    {"OrderNumberList": f"[{ORDER_NUMBER}]"},
]

for extra_params in candidatos:
    params = {
        "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
        "UserID": user_id, "Version": "1.0",
        **extra_params,
    }
    params["Signature"] = _falabella_firmar(api_key, params)

    print("=" * 70)
    print(f"Probando: {extra_params}")
    print("=" * 70)
    try:
        res = requests.get(FALABELLA_URL, params=params, timeout=20)
        data = res.json()
        if "SuccessResponse" in data:
            print(f"✅ ÉXITO -- status={res.status_code}")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        else:
            err = data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "")
            print(f"❌ status={res.status_code}, error: {err}")
    except Exception as e:
        print(f"❌ Excepción: {e}")
    print()
    time.sleep(0.3)