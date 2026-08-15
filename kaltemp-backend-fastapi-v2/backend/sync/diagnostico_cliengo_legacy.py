# ============================================================
# ARCHIVO: diagnostico_cliengo_legacy.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_cliengo_legacy.py
# ============================================================
"""
diagnostico_cliengo_legacy.py — Confirmado que CLIENGO_API_KEY es un
token LEGACY (formato UUID), no válido para la API nueva Connect v1
(requiere sk_... o JWT). Este script prueba el endpoint legacy
(api.cliengo.com/1.0/contacts) directamente, página por página, para
ver si realmente pagina más allá del registro 50 o si también se corta
ahí por otro motivo (esto también nos dice si el total real de leads
de William es mayor a 50, como él espera).

Uso:
    python diagnostico_cliengo_legacy.py
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

print(f"Probando endpoint LEGACY (api.cliengo.com/1.0/contacts) con la API key actual...")
print()

total_acumulado = 0
ids_vistos = []

for page in range(1, 2):
    print("=" * 70)
    print(f"PÁGINA {page} (legacy)")
    print("=" * 70)
    url = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&page={page}&limit=50"
    try:
        res = requests.get(url, timeout=25)
    except Exception as e:
        print(f"  ❌ Excepción de conexión: {e}")
        break

    print(f"  status_code: {res.status_code}")

    if res.status_code != 200:
        print(f"  ⚠️ Cuerpo crudo (primeros 500 caracteres): {res.text[:500]!r}")
        break

    try:
        data = res.json()
    except Exception as e:
        print(f"  ❌ Respuesta no es JSON válido: {e}")
        print(f"    {res.text[:500]!r}")
        break

    if isinstance(data, dict):
        print(f"  Claves de nivel superior: {list(data.keys())}")
        print(f"  Contenido completo de 'paging': {json.dumps(data.get('paging'), indent=2, default=str)}")
        items = data.get("contacts") or data.get("results") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []

    print(f"  Cantidad de contactos en esta página: {len(items)}")

    if items:
        primer_id = items[0].get("id") if isinstance(items[0], dict) else None
        ultimo_id = items[-1].get("id") if isinstance(items[-1], dict) else None
        print(f"  Primer id: {primer_id} -- Último id: {ultimo_id}")
        ids_vistos.append((primer_id, ultimo_id))
        if page == 1:
            print(f"  JSON completo del PRIMER contacto (para ver en qué campo viene la fecha):")
            print(f"    {json.dumps(items[0], indent=2, default=str, ensure_ascii=False)}")

    total_acumulado += len(items)

    if not items:
        print("  -> Página vacía, fin de la paginación real.")
        break
    if len(items) < 50:
        print("  -> Página con menos de 50, probablemente es la última.")
        break

print()
print("=" * 70)
print(f"TOTAL acumulado en las páginas probadas: {total_acumulado}")
print(f"IDs de inicio/fin por página (para detectar si se repite la misma página): {ids_vistos}")
print("=" * 70)

# Si 'page=' no funcionó (todas las páginas devuelven lo mismo), prueba
# con 'offset=' -- mecanismo común en APIs REST antiguas tipo esta.
print()
print("=" * 70)
print("PRUEBA ALTERNATIVA: paginación por 'offset=' en vez de 'page='")
print("=" * 70)
for offset in (0, 50, 100):
    url_offset = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset={offset}&limit=50"
    try:
        res = requests.get(url_offset, timeout=25)
        data = res.json() if res.status_code == 200 else None
        items = (data.get("contacts") or data.get("results") or []) if isinstance(data, dict) else []
        primer_id = items[0].get("id") if items and isinstance(items[0], dict) else None
        print(f"  offset={offset}: status={res.status_code}, items={len(items)}, primer_id={primer_id}")
    except Exception as e:
        print(f"  offset={offset}: ❌ error {e}")

# Prueba si el API acepta filtrar directo por fecha -- si alguno de estos
# funciona, evitamos tener que descargar los 108k contactos completos
# solo para filtrar del lado del cliente.
print()
print("=" * 70)
print("PRUEBA: ¿el API acepta algún parámetro de filtro por fecha?")
print("=" * 70)
CUTOFF = "2023-01-01"
candidatos_fecha = ["date_from", "createdAtFrom", "created_at_min", "from", "since", "startDate", "start_date"]
for param in candidatos_fecha:
    url_fecha = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&offset=0&limit=5&{param}={CUTOFF}"
    try:
        res = requests.get(url_fecha, timeout=25)
        data = res.json() if res.status_code == 200 else None
        paging = data.get("paging") if isinstance(data, dict) else None
        total_con_filtro = paging.get("total") if paging else None
        print(f"  {param}={CUTOFF}: status={res.status_code}, total reportado={total_con_filtro} (vs 108113 sin filtro)")
    except Exception as e:
        print(f"  {param}: ❌ error {e}")