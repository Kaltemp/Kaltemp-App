# ============================================================
# ARCHIVO: sync_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_enviame.py
# (Respaldar el archivo actual antes de reemplazar: Copy-Item sync_enviame.py sync_enviame.py.bak)
# ============================================================

"""
sync/sync_enviame.py — Sincroniza los envíos de Envíame (API s2/v2) hacia
la tabla `enviame_despachos` en kaltemp_matrix.duckdb.

COSTO_ENVIO se sincroniza aquí SIEMPRE en 0.0 -- este endpoint de listado
no trae el costo real facturado (confirmado en sesión de auditoría, caso
envío 19070 / Hernán Salinas: ni /deliveries ni /deliveries/{id} traen
price/seguro/total). El valor real (ESTIMADO vía tarificador) lo rellena
actualizar_fletes_enviame.py, que debe correr DESPUÉS de este script en
el mismo ciclo de sync_master.py.

Este script SOLO escribe (modo write, cron). La app web FastAPI se
conecta a kaltemp_matrix.duckdb en read_only=True y nunca debe correrlo.
"""
import os
import datetime
import requests
import duckdb
import pandas as pd
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
# .env raíz: credenciales (Bsale, Falabella, Envíame, Cliengo, Shopify).
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
# backend/.env: config específica del backend (DUCKDB_PATH, ALLOWED_ORIGINS).
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    raise RuntimeError(
        "Faltan ENVIAME_API_KEY / ENVIAME_COMPANY_ID en el .env de la raíz "
        "del proyecto."
    )

HEADERS = {"api-key": API_KEY, "Accept": "application/json"}
# Misma variable que usa db.py -- así todos los scripts escriben al mismo
# archivo que la app realmente lee.
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))


def sync_enviame(progress_callback=None, dias_atras: int = None):
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    # ENVIAME_DIAS_ATRAS (env var, default 60) -- antes estaba hardcodeado
    # a 60 días sin forma de pedir más histórico. El parámetro dias_atras
    # (si se pasa explícito, ej. desde el motor de Carga Histórica) tiene
    # prioridad sobre el env var. 10-ago-2026.
    if dias_atras is None:
        dias_atras = int(os.getenv("ENVIAME_DIAS_ATRAS", "60"))
    hoy = datetime.date.today()
    fecha_inicio_str = (hoy - datetime.timedelta(days=dias_atras)).strftime("%Y-%m-%d")

    report(2, f"🚚 Conectando con API de Envíame (desde {fecha_inicio_str})...")

    page = 1
    todos_los_envios = []
    total_paginas_est = 20

    while True:
        url = (
            f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries"
            f"?date_from={fecha_inicio_str}&page={page}&limit=100"
        )
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
        except Exception as e:
            report(100, f"❌ Error de conexión: {e}")
            return

        if response.status_code != 200:
            report(100, f"❌ Error en API ({response.status_code}): {response.text[:300]}")
            return

        json_data = response.json()
        items = json_data.get("data", json_data)

        if not items or not isinstance(items, list):
            break

        todos_los_envios.extend(items)
        pct_page = min(2 + int((page / total_paginas_est) * 80), 82)
        report(pct_page, f"📦 Página {page} descargada ({len(todos_los_envios)} registros)...")
        page += 1

    if not todos_los_envios:
        report(100, "⚠️ No se encontraron envíos en los últimos 60 días.")
        return

    report(88, "⚙️ Consolidando registros...")

    rows = []
    for e in todos_los_envios:
        carrier_obj = e.get("carrier") or {}
        carrier_name = carrier_obj.get("name") if isinstance(carrier_obj, dict) else str(carrier_obj)

        status_obj = e.get("status") or {}
        status_name = status_obj.get("name") if isinstance(status_obj, dict) else str(status_obj)
        status_code = status_obj.get("code") if isinstance(status_obj, dict) else ""

        dest_obj = e.get("shipping_address") or e.get("destination") or {}
        comuna = dest_obj.get("place") or dest_obj.get("name") or ""
        direccion = dest_obj.get("full_address") or ""

        cust_obj = e.get("customer") or {}
        house_obj = e.get("warehouse") or {}

        tracking_number = str(e.get("tracking_number") or "").strip()
        tracking_web = ""
        for l in (e.get("links") or []):
            if isinstance(l, dict) and l.get("rel") in ("tracking-web", "tracking"):
                tracking_web = l.get("href", "")
                break
        if not tracking_web and tracking_number:
            tracking_web = f"https://tracking.enviame.io/tracking?n={tracking_number}"

        code_upper = str(status_code).upper()
        status_upper = str(status_name).upper()
        es_incidencia = 1 if any(k in code_upper or k in status_upper for k in
                                  ("FAIL", "CANCEL", "EXPIRE", "RETURN", "UNDELIVER", "FALLA", "ANULADO", "DEVUELTO")) else 0
        es_entregado = 1 if any(k in code_upper or k in status_upper for k in
                                 ("DELIVERED", "ENTREGADO", "COMPLETED")) else 0

        # FECHA_ENTREGA (12-ago-2026): confirmado con diagnostico_fecha_entrega_enviame.py
        # que status.created_at es la fecha en que el envío pasó al estado
        # ACTUAL -- cuando ese estado es "Entregado" (code DELIVERED_DOM u
        # otro que matchee es_entregado), status.created_at ES la fecha real
        # de entrega (ej. caso real: identifier 458800459, status "Entregado"
        # con created_at "2026-08-12 13:00:00"). Si el envío todavía NO está
        # entregado, ese campo describe otro estado (en tránsito, etc.), así
        # que NO se guarda -- queda NULL hasta que sí esté entregado.
        fecha_entrega = status_obj.get("created_at") if es_entregado else None

        rows.append({
            "N_ENVIO_REF": e.get("imported_id") or e.get("n_packages_reference") or e.get("import_reference") or "",
            "ESTADO": status_name,
            "ESTADO_CODE": status_code,
            "ES_INCIDENCIA": es_incidencia,
            "ES_ENTREGADO": es_entregado,
            "TRACKING_NUMBER": tracking_number or "Sin info",
            "BODEGA": house_obj.get("name") if isinstance(house_obj, dict) else "",
            "CLIENTE": cust_obj.get("full_name") if isinstance(cust_obj, dict) else "",
            "TELEFONO": cust_obj.get("phone") if isinstance(cust_obj, dict) else "",
            "EMAIL": cust_obj.get("email") if isinstance(cust_obj, dict) else "",
            "COMUNA": comuna,
            "DIRECCION": direccion,
            "COURIER": carrier_name or "Por asignar",
            "SERVICIO": e.get("service") or "Estándar",
            "FECHA_CREACION": e.get("created_at"),
            "FECHA_ENTREGA": fecha_entrega,
            "COSTO_ENVIO": 0.0,
            "TRACKING_URL": tracking_web,
            "ID_INTERNO": str(e.get("identifier") or ""),
        })

    df_enviame = pd.DataFrame(rows)

    report(95, "💾 Actualizando 'enviame_despachos' en DuckDB...")

    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS enviame_despachos (
                ID_ENVIO_PK BIGINT,
                N_ENVIO_REF VARCHAR, ESTADO VARCHAR, ESTADO_CODE VARCHAR, ES_INCIDENCIA INTEGER,
                ES_ENTREGADO INTEGER, TRACKING_NUMBER VARCHAR, BODEGA VARCHAR, CLIENTE VARCHAR,
                TELEFONO VARCHAR, EMAIL VARCHAR, COMUNA VARCHAR, DIRECCION VARCHAR, COURIER VARCHAR,
                SERVICIO VARCHAR, FECHA_CREACION VARCHAR, FECHA_ENTREGA VARCHAR, COSTO_ENVIO DOUBLE,
                TRACKING_URL VARCHAR, ID_INTERNO VARCHAR
            )
        """)
        # FIX (12-ago-2026): FECHA_ENTREGA es columna nueva -- si la tabla
        # ya existía de una corrida anterior (sin esta columna), el CREATE
        # TABLE IF NOT EXISTS de arriba no la agrega solo. Este ALTER TABLE
        # defensivo sí la agrega sin tocar ninguna fila existente (quedan
        # con FECHA_ENTREGA = NULL hasta que se vuelvan a sincronizar).
        con.execute("ALTER TABLE enviame_despachos ADD COLUMN IF NOT EXISTS FECHA_ENTREGA VARCHAR")
        con.execute("CREATE SEQUENCE IF NOT EXISTS seq_enviame_pk START 1")

        con.execute(
            "DELETE FROM enviame_despachos WHERE TRY_CAST(FECHA_CREACION AS DATE) >= CAST(? AS DATE)",
            [fecha_inicio_str],
        )

        con.register("df_enviame_tmp", df_enviame)
        con.execute("""
            INSERT INTO enviame_despachos (
                ID_ENVIO_PK, N_ENVIO_REF, ESTADO, ESTADO_CODE, ES_INCIDENCIA, ES_ENTREGADO,
                TRACKING_NUMBER, BODEGA, CLIENTE, TELEFONO, EMAIL, COMUNA, DIRECCION, COURIER,
                SERVICIO, FECHA_CREACION, FECHA_ENTREGA, COSTO_ENVIO, TRACKING_URL, ID_INTERNO
            )
            SELECT
                nextval('seq_enviame_pk'), N_ENVIO_REF, ESTADO, ESTADO_CODE, ES_INCIDENCIA, ES_ENTREGADO,
                TRACKING_NUMBER, BODEGA, CLIENTE, TELEFONO, EMAIL, COMUNA, DIRECCION, COURIER,
                SERVICIO, FECHA_CREACION, FECHA_ENTREGA, COSTO_ENVIO, TRACKING_URL, ID_INTERNO
            FROM df_enviame_tmp
        """)

    report(100, f"✨ Sincronización completa: {len(df_enviame)} envíos ({fecha_inicio_str} → hoy).")


if __name__ == "__main__":
    sync_enviame()