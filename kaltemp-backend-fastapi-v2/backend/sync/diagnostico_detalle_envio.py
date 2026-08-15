# ============================================================
# ARCHIVO: diagnostico_detalle_envio.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_detalle_envio.py
# ============================================================
"""
diagnostico_detalle_envio.py — Trae el JSON COMPLETO del endpoint de
DETALLE de un envío específico (GET /deliveries/{id}), a diferencia del
endpoint de listado que no trae campo de notas/observaciones. La idea es
ver si el detalle expone más campos que la lista -- aunque este envío en
particular no tenga nota escrita todavía (es un flujo nuevo), sirve para
mapear TODOS los campos disponibles antes de coordinar la prueba real
con bodega.

Uso:
    python diagnostico_detalle_envio.py 458792911
    (o sin argumento, usa el identifier de ejemplo de abajo)
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
if not API_KEY:
    print("❌ Falta ENVIAME_API_KEY en el .env raíz.")
    raise SystemExit(1)

HEADERS = {"api-key": API_KEY, "Accept": "application/json"}

IDENTIFIER = sys.argv[1] if len(sys.argv) > 1 else "458792911"

url = f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}"
print(f"Consultando detalle del envío {IDENTIFIER}...")
res = requests.get(url, headers=HEADERS, timeout=30)
print(f"status_code: {res.status_code}\n")

if res.status_code != 200:
    print(f"❌ Error: {res.text[:500]}")
    raise SystemExit(1)

data = res.json()
print("=" * 70)
print("JSON COMPLETO DEL DETALLE:")
print("=" * 70)
print(json.dumps(data, indent=2, ensure_ascii=False, default=str))

print()
print("=" * 70)
print("CAMPOS DE NIVEL SUPERIOR ENCONTRADOS:")
print("=" * 70)
contenido = data.get("data", data) if isinstance(data, dict) else data
if isinstance(contenido, dict):
    for k in contenido.keys():
        print(f"  - {k}")