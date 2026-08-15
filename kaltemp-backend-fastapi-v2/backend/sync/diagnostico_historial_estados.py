# ============================================================
# ARCHIVO: diagnostico_historial_estados.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_historial_estados.py
# ============================================================
"""
diagnostico_historial_estados.py — Confirmado real: cuando se EDITA un
envío y se le agrega/cambia "Observaciones", Envíame registra el cambio
en status.info como "Cambio de texto observaciones: '' a 'Boleta
#41805'" -- pero eso es solo el estado MÁS RECIENTE, se perdería si el
envío cambia de estado después (ej. pasa a "en tránsito").

La plataforma web tiene una pestaña separada "Historial de estados"
(distinta de "Info del envío") -- esto sugiere que existe un endpoint
que guarda TODOS los cambios de estado con su propio "info", no solo
el actual. Este script prueba varias rutas candidatas para encontrarlo.

Uso:
    python diagnostico_historial_estados.py 458792843
"""
import os
import sys
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")
IDENTIFIER = sys.argv[1] if len(sys.argv) > 1 else "458792843"

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}

candidatos = [
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/statuses",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/status-history",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/status_history",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/logs",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/events",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/tracking",
    f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries/{IDENTIFIER}/statuses",
]

for url in candidatos:
    print("=" * 70)
    print(f"GET {url}")
    print("=" * 70)
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        print(f"status_code: {res.status_code}")
        print(res.text[:2000])
    except Exception as e:
        print(f"❌ Error: {e}")
    print()