# ============================================================
# ARCHIVO: probar_credenciales_v3_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\probar_credenciales_v3_enviame.py
# ============================================================
"""
probar_credenciales_v3_enviame.py — Comprobación empírica (en vez de
confiar solo en la documentación) de si las credenciales actuales
(ENVIAME_API_KEY / COMPANY_ID, usadas hoy para la API s2/v2) también
sirven para la API v3 (https://api.enviame.io/v3), y de paso confirma
qué endpoint de v3 es alcanzable con qué método de auth.

Prueba 3 formas de mandar la credencial actual:
  1) Como header api-key/x-api-key (igual que en v2)
  2) Como header Authorization: Bearer <API_KEY> (por si v3 acepta la
     misma key como si fuera un token)
  3) Sin ningún header de auth (para ver el mensaje de error exacto
     que devuelve v3 -- a veces el mensaje de error dice más que la
     documentación)

Uso:
    cd backend
    python probar_credenciales_v3_enviame.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    print("❌ No se pudo cargar ENVIAME_API_KEY / COMPANY_ID.")
    raise SystemExit(1)

# Endpoint de v3 más simple/barato de probar (GET, no requiere body):
# tracking de un envío ya conocido -- usamos el mismo caso real que ya
# confirmamos existe en v2 (envío 21459, identifier 458835962).
URL_V3 = "https://api.enviame.io/v3/deliveries/458835962/tracking"

INTENTOS = [
    ("api-key/x-api-key (igual que v2)", {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}),
    ("Authorization: Bearer <API_KEY actual>", {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}),
    ("Sin ningún header de auth", {"Accept": "application/json"}),
]


def main():
    print(f"Probando GET {URL_V3}\n")
    for nombre, headers in INTENTOS:
        try:
            r = requests.get(URL_V3, headers=headers, timeout=15)
            print(f"--- {nombre} ---")
            print(f"  Status: {r.status_code}")
            try:
                print(f"  Body: {json.dumps(r.json(), ensure_ascii=False)[:500]}")
            except Exception:
                print(f"  Body (no JSON): {r.text[:300]}")
            print()
        except Exception as e:
            print(f"--- {nombre} ---\n  ERROR de red: {e}\n")


if __name__ == "__main__":
    main()