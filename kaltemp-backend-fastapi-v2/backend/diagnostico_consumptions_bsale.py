"""
Diagnostico de SOLO LECTURA contra la API de Bsale -- no escribe nada en
ningun lado. Objetivo: ver el formato REAL del campo `note`/observacion
de un consumo de stock (GET /v1/stocks/consumptions.json), y encontrar
el ID de la bodega "Full MKP", antes de construir el sync automatico de
fulfillment (Mercado Libre / Paris / Ripley, todo lo que no es Falabella).

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python diagnostico_consumptions_bsale.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE = "https://api.bsale.cl/v1"

if not BSALE_TOKEN:
    print("❌ Falta BSALE_TOKEN (o BSALE_ACCESS_TOKEN) en el .env")
    raise SystemExit(1)

print("=" * 90)
print("1) BODEGAS (offices.json) -- buscando 'Full MKP' o similar")
print("=" * 90)
res = requests.get(f"{BASE}/offices.json?limit=50", headers=HEADERS, timeout=30)
print(f"status_code = {res.status_code}")
oficinas = []
if res.status_code == 200:
    for o in res.json().get("items", []):
        oficinas.append((o.get("id"), o.get("name")))
        print(f"  id={o.get('id'):<6} name={o.get('name')!r}")
else:
    print(res.text[:500])

candidatas = [o for o in oficinas if "full" in str(o[1]).lower() or "mkp" in str(o[1]).lower()]
print()
print(f"Bodegas candidatas a 'Full MKP': {candidatas}")

print()
print("=" * 90)
print("2) MUESTRA de consumos de stock (stocks/consumptions.json) -- primeros 10, crudo")
print("=" * 90)
res2 = requests.get(
    f"{BASE}/stocks/consumptions.json",
    params={"limit": 10, "expand": "[office,variant]"},
    headers=HEADERS,
    timeout=30,
)
print(f"status_code = {res2.status_code}")
if res2.status_code == 200:
    data = res2.json()
    print(f"count total reportado por Bsale: {data.get('count')}")
    items = data.get("items", [])
    for i, item in enumerate(items):
        print(f"\n--- item {i} (JSON completo) ---")
        print(json.dumps(item, indent=2, ensure_ascii=False))
else:
    print(res2.text[:1000])

print()
print("=" * 90)
print("3) Si alguna bodega candidata apareció arriba, muestra 10 consumos FILTRADOS a ella")
print("=" * 90)
if candidatas:
    office_id = candidatas[0][0]
    res3 = requests.get(
        f"{BASE}/stocks/consumptions.json",
        params={"limit": 10, "officeid": office_id, "expand": "[office,variant]"},
        headers=HEADERS,
        timeout=30,
    )
    print(f"Filtrando por officeid={office_id} ({candidatas[0][1]!r})")
    print(f"status_code = {res3.status_code}")
    if res3.status_code == 200:
        data3 = res3.json()
        print(f"count total reportado por Bsale para esta bodega: {data3.get('count')}")
        for i, item in enumerate(data3.get("items", [])):
            print(f"\n--- item {i} (JSON completo) ---")
            print(json.dumps(item, indent=2, ensure_ascii=False))
    else:
        print(res3.text[:1000])
else:
    print("(no se encontró ninguna bodega con 'full' o 'mkp' en el nombre -- revisa la lista completa de arriba)")