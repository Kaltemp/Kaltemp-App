# ============================================================
# ARCHIVO: diagnostico_notas_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_notas_enviame.py
# ============================================================
"""
diagnostico_notas_enviame.py — Confirma si /deliveries de Envíame trae
un campo de notas/observaciones (donde bodega escribiría "Factura
12345" o "Boleta 12345" al crear un envío manual), y en qué nombre
exacto vive ese campo.

sync_enviame.py hoy NO captura ese campo porque nunca se necesitó --
este diagnóstico trae el JSON crudo completo de unos pocos envíos
recientes para verlo entero, sin filtrar nada.

Uso:
    python diagnostico_notas_enviame.py
"""
import os
import json
import datetime
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    print("❌ Faltan ENVIAME_API_KEY / ENVIAME_COMPANY_ID en el .env raíz.")
    raise SystemExit(1)

HEADERS = {"api-key": API_KEY, "Accept": "application/json"}

hoy = datetime.date.today()
fecha_desde = (hoy - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

url = (
    f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries"
    f"?date_from={fecha_desde}&page=1&limit=5"
)

print(f"Consultando los últimos 5 envíos (desde {fecha_desde})...")
res = requests.get(url, headers=HEADERS, timeout=30)
print(f"status_code: {res.status_code}\n")

if res.status_code != 200:
    print(f"❌ Error: {res.text[:500]}")
    raise SystemExit(1)

data = res.json()
items = data.get("data", data) if isinstance(data, dict) else data

if not items:
    print("⚠️ No se encontraron envíos en los últimos 30 días para revisar.")
    raise SystemExit(0)

print(f"✅ {len(items)} envíos encontrados. Mostrando el JSON completo de cada uno:\n")

candidatos_nota = []
for i, envio in enumerate(items):
    print("=" * 70)
    print(f"ENVÍO #{i + 1}")
    print("=" * 70)
    print(json.dumps(envio, indent=2, ensure_ascii=False, default=str)[:3000])
    print()

    # Busca cualquier campo cuyo NOMBRE suene a nota/observación/comentario
    for k, v in envio.items():
        if any(pista in k.lower() for pista in ("note", "observ", "comment", "reference", "remark")):
            candidatos_nota.append((k, v))

print("=" * 70)
print("CAMPOS CANDIDATOS A CONTENER LA NOTA (nombre + valor de ejemplo):")
print("=" * 70)
if candidatos_nota:
    for k, v in candidatos_nota:
        print(f"  {k!r}: {v!r}")
else:
    print("  Ninguno encontrado por nombre -- revisa el JSON completo de arriba a mano,")
    print("  puede que el campo tenga un nombre menos obvio (ej. 'description', 'label_note').")