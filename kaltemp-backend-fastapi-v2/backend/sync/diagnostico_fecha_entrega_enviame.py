# ============================================================
# ARCHIVO: diagnostico_fecha_entrega_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_fecha_entrega_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_fecha_entrega_enviame.py
# ============================================================
"""
diagnostico_fecha_entrega_enviame.py — Trae 3 envíos YA ENTREGADOS
(status DELIVERED) desde la API de Envíame y dumpea el JSON completo,
para encontrar el campo exacto de fecha de entrega (candidatos típicos:
"delivered_at", "delivery_date", o un array "status_history"/"tracking"
con timestamps por estado). sync_enviame.py hoy solo guarda
"created_at" -- no sabemos si el listado trae la fecha de entrega
directamente o si hay que consultar otro endpoint por ID.

FIX (12-ago-2026): la primera versión de este script asumía que vivía
en backend\\ (un nivel hasta la raíz) y por eso el .env con las
credenciales nunca se cargaba al correrlo desde backend\\sync\\ (dos
niveles hasta la raíz) -- API_KEY quedaba vacío y la API respondía 401
"No autenticado", que no tenía nada que ver con headers ni con la API
en sí. Ahora prueba ambas rutas candidatas, igual que sync_enviame.py.

Uso (desde backend\\sync\\, junto al resto de los scripts de sync):
    python diagnostico_fecha_entrega_enviame.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
# Prueba ambas ubicaciones posibles (backend\ o backend\sync\) sin que
# haga falta saber de antemano dónde quedó guardado el archivo.
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)  # si vive en backend\sync\
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)        # si vive en backend\ (o backend\.env)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    print("❌ No se pudo cargar ENVIAME_API_KEY / COMPANY_ID desde ningún .env candidato.")
    print(f"   Revisa que exista: {os.path.abspath(os.path.join(_AQUI, '..', '..', '.env'))}")
    raise SystemExit(1)

print(f"✅ Credenciales cargadas (API_KEY largo={len(API_KEY)}, COMPANY_ID={COMPANY_ID}).\n")

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}


def main():
    url = f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries"
    res = requests.get(url, headers=HEADERS, params={"limit": 30}, timeout=30)
    if res.status_code != 200:
        print(f"❌ Error ({res.status_code}): {res.text[:300]}")
        return

    items = res.json().get("data", [])
    entregados = [
        e for e in items
        if "DELIVER" in str((e.get("status") or {}).get("code", "")).upper()
        or "ENTREGADO" in str((e.get("status") or {}).get("name", "")).upper()
    ]

    if not entregados:
        print("No se encontró ningún 'entregado' en los primeros 30 registros -- "
              "sube el 'limit' o revisa manualmente cuáles están DELIVERED.")
        entregados = items[:3]

    print(f"Mostrando {min(3, len(entregados))} envío(s) entregado(s), JSON completo:\n")
    for e in entregados[:3]:
        print("=" * 80)
        print(json.dumps(e, indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()