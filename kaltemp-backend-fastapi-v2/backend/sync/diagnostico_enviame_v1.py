# ============================================================
# ARCHIVO: diagnostico_enviame_v1.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_enviame_v1.py
# ============================================================
"""
diagnostico_enviame_v1.py — La API s2/v2 (GET /deliveries/{id}) NO
devuelve el campo "Observaciones" aunque existe y se ve en la
plataforma web (confirmado real: envío 458795144, "FACTURA #
'PEDIDO PUEBA'" guardado pero ausente del JSON de s2/v2).

Este script prueba varias rutas alternativas de la API s1/v1 (que
actualizar_fletes_enviame.py ya usa para /carriers) y algunos
parámetros de expansión, a ver si alguna sí trae Observaciones.

Uso:
    python diagnostico_enviame_v1.py 458795144
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
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")
IDENTIFIER = sys.argv[1] if len(sys.argv) > 1 else "458795144"

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}

candidatos = [
    f"https://api.enviame.io/api/s1/v1/companies/{COMPANY_ID}/deliveries/{IDENTIFIER}",
    f"https://api.enviame.io/api/s1/v1/deliveries/{IDENTIFIER}",
    f"https://api.enviame.io/api/s1/v1/companies/{COMPANY_ID}/orders/{IDENTIFIER}",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}?expand=all",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}?include=notes,observations",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/notes",
    f"https://api.enviame.io/api/s2/v2/deliveries/{IDENTIFIER}/history",
]

for url in candidatos:
    print("=" * 70)
    print(f"GET {url}")
    print("=" * 70)
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        print(f"status_code: {res.status_code}")
        texto = res.text[:1500]
        if res.status_code == 200:
            # Busca "obs" u "pedido pueba" (nuestro texto de prueba) en la respuesta cruda
            contiene_pista = "pueba" in res.text.lower() or "observ" in res.text.lower()
            print(f"¿Contiene 'observ' o nuestro texto de prueba 'PUEBA'?: {contiene_pista}")
        print(texto)
    except Exception as e:
        print(f"❌ Error: {e}")
    print()