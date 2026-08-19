"""
Diagnostico de SOLO LECTURA -- trae TODOS los consumos de la bodega
FULL MKP (417 en total, tamano manejable), clasifica los que siguen el
patron "Consumo por pedido {Canal} #{numero} precio unitario ${precio}"
vs los que no (ajustes administrativos viejos), y resume por canal:
cuantos hay, y el rango de fechas (primero y ultimo) -- para saber
exactamente desde cuando arranco el registro de ventas de fulfillment
via consumo, canal por canal.

No modifica nada -- solo lee.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python diagnostico_consumos_full_completo.py
"""
import os
import re
import datetime
import requests
from dotenv import load_dotenv
from collections import defaultdict

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE = "https://api.bsale.cl/v1"
OFFICE_ID = 2  # FULL MKP

if not BSALE_TOKEN:
    print("❌ Falta BSALE_TOKEN (o BSALE_ACCESS_TOKEN) en el .env")
    raise SystemExit(1)

PATRON = re.compile(r"Consumo por pedido\s+(.+?)\s+#(\S+)\s+precio unitario\s*\$([\d.,]+)", re.IGNORECASE)

todos = []
limit = 50  # Bsale limita a 50 por pagina como maximo, aunque se pida mas
offset = 0
while True:
    res = requests.get(
        f"{BASE}/stocks/consumptions.json",
        params={"officeid": OFFICE_ID, "limit": limit, "offset": offset},
        headers=HEADERS, timeout=30,
    )
    if res.status_code != 200:
        print(f"⚠️ status {res.status_code} en offset {offset}: {res.text[:300]}")
        break
    items = res.json().get("items", [])
    if not items:
        break
    todos.extend(items)
    offset += limit
    if len(items) < limit:
        break
    if offset > 2000:  # freno de seguridad, no deberiamos llegar aca con 417 totales
        print("⚠️ freno de seguridad activado en offset > 2000")
        break

print(f"Total consumos traidos: {len(todos)}")
print()

matcheados = []
no_matcheados = []
for item in todos:
    note = item.get("note", "") or ""
    m = PATRON.search(note)
    fecha_unix = item.get("consumptionDate")
    fecha = (
        datetime.datetime.fromtimestamp(fecha_unix, tz=datetime.timezone.utc).date()
        if fecha_unix else None
    )
    if m:
        canal_raw = m.group(1).strip()
        pedido = m.group(2).strip()
        precio_raw = m.group(3).strip()
        matcheados.append({
            "id": item.get("id"), "fecha": fecha, "canal_raw": canal_raw,
            "pedido": pedido, "precio_raw": precio_raw, "note": note,
        })
    else:
        no_matcheados.append({"id": item.get("id"), "fecha": fecha, "note": note})

print("=" * 100)
print(f"CONSUMOS QUE SIGUEN EL PATRON 'Consumo por pedido ...' : {len(matcheados)}")
print(f"CONSUMOS QUE NO (ajustes administrativos, etc.)        : {len(no_matcheados)}")
print("=" * 100)

por_canal = defaultdict(list)
for m in matcheados:
    por_canal[m["canal_raw"]].append(m)

for canal_raw, filas in sorted(por_canal.items()):
    fechas = [f["fecha"] for f in filas if f["fecha"]]
    print(f"\nCanal (texto tal cual aparece en note): {canal_raw!r}")
    print(f"  Cantidad de consumos: {len(filas)}")
    if fechas:
        print(f"  Fecha más antigua:    {min(fechas)}")
        print(f"  Fecha más reciente:   {max(fechas)}")

print()
print("=" * 100)
print("Fechas de los NO-matcheados (para confirmar que son solo viejos/administrativos)")
print("=" * 100)
fechas_no_match = [f["fecha"] for f in no_matcheados if f["fecha"]]
if fechas_no_match:
    print(f"  Fecha más antigua: {min(fechas_no_match)}")
    print(f"  Fecha más reciente: {max(fechas_no_match)}")
    recientes_no_match = sorted(no_matcheados, key=lambda x: x["fecha"] or datetime.date.min, reverse=True)[:10]
    print("\n  Los 10 NO-matcheados más recientes (para revisar si hay algo raro colándose):")
    for f in recientes_no_match:
        print(f"    id={f['id']} fecha={f['fecha']} note={f['note']!r}")

print()
print("=" * 100)
print("Primeros 5 consumos MATCHEADOS de cada canal (los más antiguos) -- para ver el cutover exacto")
print("=" * 100)
for canal_raw, filas in sorted(por_canal.items()):
    filas_ordenadas = sorted(filas, key=lambda x: x["fecha"] or datetime.date.max)
    print(f"\nCanal: {canal_raw!r}")
    for f in filas_ordenadas[:5]:
        print(f"  id={f['id']} fecha={f['fecha']} pedido={f['pedido']} precio={f['precio_raw']}")