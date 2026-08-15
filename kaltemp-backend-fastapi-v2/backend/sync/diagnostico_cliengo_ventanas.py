# ============================================================
# ARCHIVO: diagnostico_cliengo_ventanas.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_cliengo_ventanas.py
# ============================================================
"""
diagnostico_cliengo_ventanas.py — Confirmado: la API de Cliengo legacy
tiene un límite duro de offset<=1000 (error real: "Offset cannot be
greater than 1000"). Como además viene ordenado del contacto más
reciente al más antiguo, con since=2023-01-01 solo se alcanzan los
últimos ~1.050 contactos, sin llegar a 2023 real.

Este script prueba:
  1) Si existe un parámetro de fecha límite SUPERIOR (until/to/before/
     etc.) que, combinado con since=, permita acotar el total de cada
     ventana a menos de 1000 -- necesario para poder paginar por ventanas
     de tiempo en vez de offset puro.
  2) Confirma el orden real de los resultados (más reciente primero o
     más antiguo primero) mirando la fecha del primer y último contacto
     de una ventana chica.

Uso:
    python diagnostico_cliengo_ventanas.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

CLIENGO_API_KEY = os.getenv("CLIENGO_API_KEY")
if not CLIENGO_API_KEY:
    print("❌ No se encontró CLIENGO_API_KEY.")
    raise SystemExit(1)

print("=" * 70)
print("1) ¿Existe un parámetro de fecha límite SUPERIOR?")
print("=" * 70)
print("   (comparando el 'total' reportado contra since=2023-01-01 solo, sin límite superior: 29281)")
print()

candidatos_hasta = ["until", "to", "before", "date_to", "end_date", "createdAtTo", "created_at_max"]
for param in candidatos_hasta:
    url = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset=0&limit=5&since=2023-01-01&{param}=2023-02-01"
    try:
        res = requests.get(url, timeout=25)
        data = res.json() if res.status_code == 200 else None
        paging = data.get("paging") if isinstance(data, dict) else None
        total = paging.get("total") if paging else None
        print(f"  {param}=2023-02-01 (junto a since=2023-01-01): status={res.status_code}, total={total}")
    except Exception as e:
        print(f"  {param}: ❌ error {e}")

print()
print("=" * 70)
print("2) Orden real de los resultados (mirando fechas de una ventana chica)")
print("=" * 70)
url_orden = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset=0&limit=10&since=2023-01-01"
res = requests.get(url_orden, timeout=25)
if res.status_code == 200:
    data = res.json()
    items = data.get("contacts") or data.get("results") or []
    for it in items:
        print(f"  id={it.get('id')} creationDate={it.get('creationDate')}")
else:
    print(f"  status={res.status_code}: {res.text[:300]!r}")

print()
print("=" * 70)
print("3) Prueba de 'sort'/'order' -- por si se puede pedir ascendente directo")
print("=" * 70)
candidatos_orden = ["sort", "order", "orderBy", "sortBy"]
for param in candidatos_orden:
    for valor in ("asc", "creationDate", "creationDate:asc", "1"):
        url = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset=0&limit=3&since=2023-01-01&{param}={valor}"
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                items = data.get("contacts") or data.get("results") or []
                primera_fecha = items[0].get("creationDate") if items else None
                print(f"  {param}={valor}: status=200, primera_fecha={primera_fecha}")
        except Exception:
            pass