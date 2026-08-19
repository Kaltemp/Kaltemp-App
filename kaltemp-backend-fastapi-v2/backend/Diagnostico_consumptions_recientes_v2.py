"""
Diagnostico de SOLO LECTURA -- v2. El intento anterior uso el parametro
'consumptiondaterange', que Bsale IGNORO silenciosamente (devolvio los
417 consumos sin filtrar, por eso salieron puros registros de 2016-2017).

Esta version fuerza el OFFSET mas alto (total - N) para llegar directo
a los consumos mas recientes de la bodega FULL MKP, sin depender de que
el filtro de fecha funcione.

No modifica nada -- solo lee.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python diagnostico_consumptions_recientes_v2.py
"""
import os
import json
import datetime
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE = "https://api.bsale.cl/v1"
OFFICE_ID = 2  # FULL MKP

if not BSALE_TOKEN:
    print("❌ Falta BSALE_TOKEN (o BSALE_ACCESS_TOKEN) en el .env")
    raise SystemExit(1)

print("=" * 90)
print("1) Total de consumos en la bodega FULL MKP")
print("=" * 90)
res_count = requests.get(
    f"{BASE}/stocks/consumptions.json",
    params={"officeid": OFFICE_ID, "limit": 1},
    headers=HEADERS, timeout=30,
)
total = res_count.json().get("count", 0) if res_count.status_code == 200 else 0
print(f"Total: {total}")

N = 40
offset_final = max(total - N, 0)
print(f"\nPidiendo los ultimos {N} (offset={offset_final})...")

res = requests.get(
    f"{BASE}/stocks/consumptions.json",
    params={"officeid": OFFICE_ID, "limit": N, "offset": offset_final},
    headers=HEADERS, timeout=30,
)
print(f"status_code = {res.status_code}")
items = []
if res.status_code == 200:
    items = res.json().get("items", [])
    print(f"items devueltos: {len(items)}")
else:
    print(res.text[:500])

print()
print("=" * 90)
print("2) Para cada consumo (mas reciente primero): fecha, note, updateStock, consumptionTypeId, detalle")
print("=" * 90)
# Ordenamos por id descendente para ver primero los mas nuevos
items_ordenados = sorted(items, key=lambda x: x.get("id", 0), reverse=True)

for item in items_ordenados:
    cid = item.get("id")
    fecha_unix = item.get("consumptionDate")
    fecha_str = (
        datetime.datetime.fromtimestamp(fecha_unix, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        if fecha_unix else "?"
    )
    note = item.get("note", "")
    update_stock = item.get("updateStock")
    ctype = item.get("consumptionTypeId")
    print(f"\n--- Consumo id={cid}  fecha={fecha_str}  updateStock={update_stock}  consumptionTypeId={ctype} ---")
    print(f"  note: {note!r}")

    href_detalle = (item.get("details") or {}).get("href") or f"{BASE}/stocks/consumptions/{cid}/details.json"
    try:
        res_det = requests.get(href_detalle, headers=HEADERS, params={"expand": "[variant]"}, timeout=20)
        if res_det.status_code == 200:
            det_items = res_det.json().get("items", [])
            for d in det_items:
                variant = d.get("variant") or {}
                print(f"    -> SKU={variant.get('code')!r}  producto={variant.get('description')!r}  "
                      f"cantidad={d.get('quantity')}  cost={d.get('cost')}")
        else:
            print(f"    (no se pudo traer detalle: status {res_det.status_code})")
    except Exception as e:
        print(f"    (error trayendo detalle: {e})")

print()
print("=" * 90)
print(f"FIN -- se revisaron {len(items_ordenados)} consumos (los mas recientes de FULL MKP)")
print("=" * 90)