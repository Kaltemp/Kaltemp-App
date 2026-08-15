# ============================================================
# ARCHIVO: diagnostico_tiempo_ventas.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_tiempo_ventas.py
# ============================================================
"""
diagnostico_tiempo_ventas.py — Estima cuántos lotes faltan y el tiempo
restante de la sync de "ventas" en curso.

La barra de progreso del motor está topada en 40% durante toda la
descarga de Bsale (fórmula real en sync_ventas.py: min(2 + lote*2, 40)
-- se congela desde el lote 19 en adelante, sin importar cuántos falten
en total). Este script consulta a Bsale el "count" real de documentos
en el mismo rango de fechas que está pidiendo la sync (1825 días por
defecto -- AJUSTA la variable DIAS_ATRAS abajo si usaste otro número),
para poder calcular:
  - Cuántos lotes de 50 documentos hay en total.
  - Cuántos van descargados (según el número de lote que ves en el
    modal, ej. "lote 308").
  - Tiempo restante estimado, si le pasas cuántos segundos tardó entre
    dos lotes que hayas visto pasar en la consola de uvicorn.

Uso:
    python diagnostico_tiempo_ventas.py
"""
import os
import datetime
import requests
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN")
TZ_CHILE = ZoneInfo("America/Santiago")

# --------- AJUSTA ESTOS 2 VALORES ANTES DE CORRER ---------
DIAS_ATRAS = 1825          # el mismo número que pusiste en el campo de días
LOTE_ACTUAL_VISTO = 308    # el número de lote que ves ahora mismo en el modal
# ------------------------------------------------------------

if not BSALE_TOKEN:
    print("❌ No se encontró BSALE_TOKEN.")
    raise SystemExit(1)

hoy = datetime.date.today()
f_inicio = hoy - datetime.timedelta(days=DIAS_ATRAS)
f_fin = hoy

api_inicio = f_inicio - datetime.timedelta(days=1)
api_fin = f_fin + datetime.timedelta(days=1)
start_dt = datetime.datetime.combine(api_inicio, datetime.time.min).replace(tzinfo=TZ_CHILE)
end_dt = datetime.datetime.combine(api_fin, datetime.time.max).replace(tzinfo=TZ_CHILE)
start_ts, end_ts = int(start_dt.timestamp()), int(end_dt.timestamp())

headers = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
url = f"https://api.bsale.cl/v1/documents.json?emissiondaterange=[{start_ts},{end_ts}]&limit=1&offset=0"

print(f"Consultando total de documentos Bsale para los últimos {DIAS_ATRAS} días...")
res = requests.get(url, headers=headers, timeout=30)
if res.status_code != 200:
    print(f"❌ Error {res.status_code}: {res.text[:300]}")
    raise SystemExit(1)

data = res.json()
total_documentos = data.get("count", 0)
total_lotes = -(-total_documentos // 50)  # división hacia arriba

lotes_restantes = max(0, total_lotes - LOTE_ACTUAL_VISTO)
pct_real = (LOTE_ACTUAL_VISTO / total_lotes * 100) if total_lotes else 0

print()
print("=" * 60)
print(f"Total de documentos Bsale en el rango: {total_documentos}")
print(f"Total de lotes estimados (50 c/u): {total_lotes}")
print(f"Lote actual visto en el modal: {LOTE_ACTUAL_VISTO}")
print(f"Lotes restantes: {lotes_restantes}")
print(f"Progreso REAL estimado: {pct_real:.1f}% (el modal muestra 40% fijo)")
print("=" * 60)
print()
print("Para estimar el tiempo restante: cronometra cuántos segundos")
print("tarda en avanzar el número de lote en la consola de uvicorn")
print("(ej. 5 segundos entre 'lote 100' y 'lote 105' = 1 seg/lote),")
print("y multiplica ese ritmo por los lotes restantes de arriba.")