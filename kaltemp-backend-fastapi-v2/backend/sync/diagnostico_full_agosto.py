"""
Diagnostico de SOLO LECTURA -- confirma si falta fulfillment de
Mercado Libre/Paris/Ripley (via consumos bodega "Full MKP") para agosto
2026, comparando:
  A) Lo que HOY esta guardado en `ventas` con ORIGEN='BSALE_FULL'
  B) Lo que Bsale tiene AHORA MISMO en la bodega Full MKP (consumos reales,
     re-procesados en vivo con la misma logica de sync_ventas_full.py,
     pero SIN escribir nada -- solo para comparar)
Tambien muestra hace cuanto se sincronizo 'leads' por ultima vez.

Uso:
    python diagnostico_full_agosto.py
"""
import os
import re
import sys
import datetime
import requests
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
# Mismo patron que sync_ventas_full.py -- guardar este script en backend\sync\
# para que estas rutas relativas encuentren el .env correcto.
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"
BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE_URL = "https://api.bsale.cl/v1"
NOMBRE_BODEGA_FULL = "FULL MKP"

CANAL_MAP = {"MERCADO LIBRE": "MERCADOLIBRE", "MERCADOLIBRE": "MERCADOLIBRE", "PARIS": "PARIS", "RIPLEY": "RIPLEY"}
PATRON_NOTE = re.compile(r"Consumo por pedido\s+(.+?)\s+#(\S+)\s+precio unitario\s*\$\s*([\d.,]+)", re.IGNORECASE)

print("=" * 100)
print("A) LO QUE HOY ESTA EN `ventas` CON ORIGEN='BSALE_FULL' -- TODO AGOSTO 2026")
print("=" * 100)
if not os.path.exists(DB_PATH):
    print(f"  ⚠️ No se encontro la DB en {DB_PATH} -- ajusta la ruta si es distinta.")
else:
    con = duckdb.connect(DB_PATH, read_only=True)
    filas = con.execute("""
        SELECT CAST(FECHA_OBJ AS DATE) AS fecha, CANAL, DOCUMENTO, SKU_BSALE, CANTIDAD, BRUTO_TOTAL
        FROM ventas
        WHERE ORIGEN = 'BSALE_FULL' AND CAST(FECHA_OBJ AS DATE) BETWEEN '2026-08-01' AND '2026-08-19'
        ORDER BY fecha
    """).fetchall()
    if not filas:
        print("  (CERO filas -- no hay NINGUN BSALE_FULL en todo agosto en la base actual)")
    for f in filas:
        print(f"  {f[0]}  {f[1]:15s}  {f[2]:30s}  SKU={f[3]:12s}  cant={f[4]}  bruto=${f[5]:,.0f}")

    print()
    print("  Ultima fecha de sync registrada para 'leads' (si existe columna de fecha reconocible):")
    try:
        cols = con.execute("SELECT column_name FROM information_schema.columns WHERE table_name='leads'").fetchall()
        cols = [c[0] for c in cols]
        print(f"  columnas de 'leads': {cols}")
        col_fecha = next((c for c in cols if "FECHA" in c.upper() or "DATE" in c.upper()), None)
        if col_fecha:
            r = con.execute(f'SELECT MAX(CAST("{col_fecha}" AS DATE)), COUNT(*) FROM leads').fetchone()
            print(f"  Fecha mas reciente en leads ({col_fecha}): {r[0]}  (total filas: {r[1]})")
    except Exception as e:
        print(f"  ⚠️ No se pudo revisar 'leads': {e}")
    con.close()

print()
print("=" * 100)
print("B) LO QUE BSALE TIENE AHORA MISMO EN LA BODEGA 'FULL MKP' -- reprocesado EN VIVO (sin escribir nada)")
print("=" * 100)
if not BSALE_TOKEN:
    print("  ❌ Falta BSALE_TOKEN en el .env -- no se puede consultar Bsale.")
    sys.exit(1)

resp = requests.get(f"{BASE_URL}/offices.json", headers=HEADERS, params={"limit": 50}, timeout=20)
office_id = None
for o in resp.json().get("items", []):
    if str(o.get("name", "")).strip().upper() == NOMBRE_BODEGA_FULL:
        office_id = o.get("id")
if not office_id:
    print("  ❌ No se encontro la bodega 'FULL MKP'.")
    sys.exit(1)
print(f"  Bodega 'FULL MKP' encontrada: office_id={office_id}")

todos = []
limit, offset = 50, 0
while True:
    r = requests.get(f"{BASE_URL}/stocks/consumptions.json",
                      params={"officeid": office_id, "limit": limit, "offset": offset},
                      headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"  ⚠️ Error {r.status_code} en offset {offset}: {r.text[:200]}")
        break
    items = r.json().get("items", [])
    if not items:
        break
    todos.extend(items)
    offset += limit
    if len(items) < limit or offset > 20000:
        break
print(f"  Total consumos traidos de la bodega (todo el historial): {len(todos)}")

print()
print("  Consumos con fecha entre 2026-08-01 y 2026-08-19, sea cual sea su note:")
print("  " + "-" * 96)
n_en_rango = 0
n_match_ml_paris_ripley = 0
for c in todos:
    fecha_unix = c.get("consumptionDate")
    if not fecha_unix:
        continue
    fecha_obj = datetime.datetime.fromtimestamp(fecha_unix, tz=datetime.timezone.utc).replace(tzinfo=None).date()
    if not (datetime.date(2026, 8, 1) <= fecha_obj <= datetime.date(2026, 8, 19)):
        continue
    n_en_rango += 1
    note = (c.get("note", "") or "").strip()
    m = PATRON_NOTE.search(note)
    if m:
        canal_raw = m.group(1).strip().upper()
        pedido = m.group(2).strip()
        precio = m.group(3).strip()
        canal = CANAL_MAP.get(canal_raw, canal_raw)
        es_falabella = canal_raw == "FALABELLA"
        estado = "❌ FALABELLA (excluido a proposito)" if es_falabella else f"✅ MATCH -> canal={canal}"
        if not es_falabella and canal_raw in CANAL_MAP:
            n_match_ml_paris_ripley += 1
        print(f"  id={c.get('id'):8}  fecha={fecha_obj}  {estado}  pedido={pedido}  precio=${precio}")
        print(f"      note completo: {note!r}")
    else:
        print(f"  id={c.get('id'):8}  fecha={fecha_obj}  ⚠️ SIN match de patron (ajuste manual o formato distinto)")
        print(f"      note completo: {note!r}")

print()
print(f"  Total consumos en rango 01-19 ago: {n_en_rango}")
print(f"  De esos, con match real Mercado Libre/Paris/Ripley (no Falabella): {n_match_ml_paris_ripley}")
print()
print("=" * 100)
print("CONCLUSION:")
print("  - Si (B) muestra consumos MATCH para ML/Paris/Ripley en 10-16 ago pero (A) esta vacio para")
print("    esas fechas -> el sync SI encuentra los datos reales pero no quedaron guardados: hay que")
print("    volver a correr sync_ventas_full.py cubriendo ese rango (dias_atras >= 19 para llegar al 01-ago).")
print("  - Si (B) tampoco muestra nada para esas fechas -> Bsale simplemente no tiene consumos con el")
print("    patron esperado en ese rango (revisar si el pedido real quedo con otro texto en el note,")
print("    o si el consumo aun no se genero en Bsale para esas ventas).")
print("=" * 100)