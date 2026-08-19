"""
Diagnostico de SOLO LECTURA contra la API de Bsale -- continuacion de
diagnostico_consumptions_bsale.py. Ese primer diagnostico solo trajo
los consumos MAS VIEJOS de la bodega FULL MKP (id=2) -- movimientos
administrativos de 2016 ("prueba", "Elimina Recepcion", etc.), nada
que ver con ventas de fulfillment.

Este script:
  1) Trae los consumos MAS RECIENTES de la bodega FULL MKP (probando
     el parametro de rango de fecha; si Bsale no lo acepta, usa el
     offset mas alto como respaldo para igual llegar a los recientes).
  2) Para cada uno, pide el sub-recurso /details.json (ahi vive el
     SKU/variante y cantidad de cada linea -- consumptions.json en si
     no trae el detalle de producto).

No modifica nada -- solo lee.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python diagnostico_consumptions_recientes.py
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
OFFICE_ID = 2  # FULL MKP, confirmado en el diagnostico anterior

if not BSALE_TOKEN:
    print("❌ Falta BSALE_TOKEN (o BSALE_ACCESS_TOKEN) en el .env")
    raise SystemExit(1)

print("=" * 90)
print("1) Intentando filtrar por rango de fecha (ultimos 180 dias) con 'consumptiondaterange'")
print("=" * 90)
hoy = datetime.date.today()
hace_180 = hoy - datetime.timedelta(days=180)
start_ts = int(datetime.datetime.combine(hace_180, datetime.time.min).timestamp())
end_ts = int(datetime.datetime.combine(hoy, datetime.time.max).timestamp())

res = requests.get(
    f"{BASE}/stocks/consumptions.json",
    params={
        "officeid": OFFICE_ID,
        "consumptiondaterange": f"[{start_ts},{end_ts}]",
        "limit": 25,
    },
    headers=HEADERS,
    timeout=30,
)
print(f"status_code = {res.status_code}")
items = []
if res.status_code == 200:
    data = res.json()
    print(f"count reportado por Bsale (con filtro de fecha): {data.get('count')}")
    items = data.get("items", [])
    print(f"items devueltos: {len(items)}")
else:
    print(res.text[:500])

if not items:
    print()
    print("El filtro de fecha no trajo nada (puede que el nombre del parametro sea otro).")
    print("Respaldo: pido el total de consumos de esta bodega y salto al offset mas alto")
    print("para llegar igual a los mas recientes (asumiendo orden ascendente por id).")
    res_count = requests.get(
        f"{BASE}/stocks/consumptions.json",
        params={"officeid": OFFICE_ID, "limit": 1},
        headers=HEADERS, timeout=30,
    )
    total = res_count.json().get("count", 0) if res_count.status_code == 200 else 0
    print(f"Total consumos en FULL MKP: {total}")
    offset_final = max(total - 25, 0)
    res2 = requests.get(
        f"{BASE}/stocks/consumptions.json",
        params={"officeid": OFFICE_ID, "limit": 25, "offset": offset_final},
        headers=HEADERS, timeout=30,
    )
    print(f"status_code (offset={offset_final}) = {res2.status_code}")
    if res2.status_code == 200:
        items = res2.json().get("items", [])
        print(f"items devueltos: {len(items)}")
    else:
        print(res2.text[:500])

print()
print("=" * 90)
print("2) Para cada consumo encontrado: fecha, note, y su DETALLE (SKU/variante/cantidad)")
print("=" * 90)
for item in items:
    cid = item.get("id")
    fecha_unix = item.get("consumptionDate")
    fecha_str = datetime.datetime.utcfromtimestamp(fecha_unix).strftime("%Y-%m-%d") if fecha_unix else "?"
    note = item.get("note", "")
    print(f"\n--- Consumo id={cid}  fecha={fecha_str} ---")
    print(f"  note: {note!r}")

    href_detalle = (item.get("details") or {}).get("href")
    if not href_detalle:
        href_detalle = f"{BASE}/stocks/consumptions/{cid}/details.json"
    try:
        res_det = requests.get(href_detalle, headers=HEADERS, params={"expand": "[variant]"}, timeout=20)
        if res_det.status_code == 200:
            det_items = res_det.json().get("items", [])
            for d in det_items:
                print(f"    DETALLE (crudo): {json.dumps(d, ensure_ascii=False)}")
        else:
            print(f"    (no se pudo traer detalle: status {res_det.status_code})")
    except Exception as e:
        print(f"    (error trayendo detalle: {e})")

print()
print("=" * 90)
print(f"FIN -- se revisaron {len(items)} consumos recientes de la bodega FULL MKP")
print("=" * 90)