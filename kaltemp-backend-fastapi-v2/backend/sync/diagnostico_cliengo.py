# ============================================================
# ARCHIVO: diagnostico_cliengo.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_cliengo.py
# (o en la raíz del backend, donde ya tienes tus otros diagnostico_*.py)
# ============================================================
"""
diagnostico_cliengo.py — Confirma por qué sync_leads.py se está cortando
en 50 registros (página 1) en vez de traer todo el histórico desde 2023.

sync_leads.py tiene un bug: si la página 2 en adelante falla (status_code
distinto de 200), el loop hace 'break' SIN imprimir nada -- por eso el
motor de actualización muestra "OK" con solo 50 leads, sin ningún error
visible. Este script llama a la página 1 Y la página 2 por separado y
muestra el status code, el cuerpo crudo de la respuesta, y la estructura
de "pagination" que trae Cliengo -- para confirmar si es:
  a) Rate limit (429) en la segunda llamada
  b) Token sin permiso para paginar más allá de la página 1
  c) El campo de paginación que usa el código ("pagination"/"total") no
     es el que realmente devuelve la API (ej. podría ser "meta" en vez
     de "pagination")
  d) Cliengo realmente solo tiene 50 contactos en esta cuenta (poco
     probable según lo que reporta William, pero hay que descartarlo)

Uso:
    python diagnostico_cliengo.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
# Prueba ambas rutas típicas de .env del proyecto (raíz y backend/)
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

CLIENGO_API_KEY = os.getenv("CLIENGO_API_KEY")

print("=" * 70)
print("1) ¿Existe la API Key?")
print("=" * 70)
print(f"  CLIENGO_API_KEY encontrada: {CLIENGO_API_KEY is not None}")
print(f"  Longitud: {len(CLIENGO_API_KEY) if CLIENGO_API_KEY else 0}")
print()

if not CLIENGO_API_KEY:
    print("❌ No se encontró CLIENGO_API_KEY en ningún .env -- revisa la raíz del proyecto.")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {CLIENGO_API_KEY}",
    "Accept": "application/json"
}

for page in (1, 2, 3):
    print("=" * 70)
    print(f"PÁGINA {page}")
    print("=" * 70)
    url = f"https://connect.cliengo.com/v1/contacts?page={page}&limit=50"
    try:
        res = requests.get(url, headers=headers, timeout=25)
    except Exception as e:
        print(f"  ❌ Excepción de conexión: {e}")
        continue

    print(f"  status_code: {res.status_code}")
    print(f"  headers de respuesta relevantes:")
    for h in ("X-RateLimit-Remaining", "X-RateLimit-Limit", "Retry-After"):
        if h in res.headers:
            print(f"    {h}: {res.headers[h]}")

    if res.status_code != 200:
        print(f"  ⚠️ Cuerpo crudo de la respuesta (primeros 500 caracteres):")
        print(f"    {res.text[:500]!r}")
        continue

    try:
        data = res.json()
    except Exception as e:
        print(f"  ❌ La respuesta no es JSON válido: {e}")
        print(f"    {res.text[:500]!r}")
        continue

    print(f"  Claves de nivel superior en la respuesta: {list(data.keys())}")

    items = data.get("results") or data.get("contacts") or (data if isinstance(data, list) else [])
    print(f"  Cantidad de contactos en esta página: {len(items) if isinstance(items, list) else 'N/A'}")

    pagination = data.get("pagination")
    print(f"  Campo 'pagination': {pagination}")

    # Buscar cualquier otro campo que suene a paginación, por si el
    # nombre real es distinto (meta, page_info, totalCount, etc.)
    otros_candidatos = {k: v for k, v in data.items() if k not in ("results", "contacts", "pagination") and not isinstance(v, list)}
    if otros_candidatos:
        print(f"  Otros campos de nivel superior (por si la paginación real vive acá): {json.dumps(otros_candidatos, indent=2, default=str)[:800]}")

    print()

print("=" * 70)
print("Diagnóstico completo. Pega esta salida completa para revisar.")
print("=" * 70)