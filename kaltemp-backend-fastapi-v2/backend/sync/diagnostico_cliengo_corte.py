# ============================================================
# ARCHIVO: diagnostico_cliengo_corte.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_cliengo_corte.py
# ============================================================
"""
diagnostico_cliengo_corte.py — sync_leads.py corregido trajo 1.050 leads
en vez de los ~29.281 esperados con since=2023-01-01. Este script salta
a distintos offsets grandes para ver EXACTAMENTE dónde se corta: si es
un error de la API (status != 200, rate limit), si el campo 'total'
cambia según el offset (inconsistencia del filtro), o si a partir de
cierto punto la API simplemente devuelve una página vacía antes de
llegar al total reportado.

Uso:
    python diagnostico_cliengo_corte.py
"""
import os
import json
import time
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

FECHA_DESDE = "2023-01-01"

# 1) Confirmar el total reportado en varios offsets distintos -- si
# cambia, el filtro 'since' no es estable a través de la paginación.
print("=" * 70)
print("1) ¿El total reportado por 'paging' es estable en distintos offsets?")
print("=" * 70)
for offset in (0, 500, 1000, 1049, 1050, 1100, 5000, 15000, 29000):
    url = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset={offset}&limit=5&since={FECHA_DESDE}"
    try:
        res = requests.get(url, timeout=25)
    except Exception as e:
        print(f"  offset={offset}: ❌ excepción {e}")
        continue

    if res.status_code != 200:
        print(f"  offset={offset}: ⚠️ status={res.status_code} body={res.text[:300]!r}")
        continue

    data = res.json()
    paging = data.get("paging") or {}
    items = data.get("contacts") or data.get("results") or []
    print(f"  offset={offset}: status=200, total_reportado={paging.get('total')}, items_devueltos={len(items)}")
    time.sleep(0.3)  # evitar rate limit por ráfaga

print()
print("=" * 70)
print("2) Recorrido fino cerca de offset=1050 (donde se cortó la sync real)")
print("=" * 70)
for offset in (950, 1000, 1025, 1040, 1045, 1050, 1055, 1060, 1075, 1100):
    url = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset={offset}&limit=25&since={FECHA_DESDE}"
    try:
        res = requests.get(url, timeout=25)
    except Exception as e:
        print(f"  offset={offset}: ❌ excepción {e}")
        continue

    print(f"  offset={offset}: status={res.status_code}", end="")
    if res.status_code == 200:
        data = res.json()
        paging = data.get("paging") or {}
        items = data.get("contacts") or data.get("results") or []
        print(f", total={paging.get('total')}, items_devueltos={len(items)}")
    else:
        print(f", body={res.text[:300]!r}")
    time.sleep(0.3)