# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_ga4_tompalmer.py
"""
sync/sync_ga4_tompalmer.py — Trae Sesiones/Rebote/ATC/Checkouts/
Transacciones desde la propiedad de GA4 de Tom Palmer (tompalmer.cl),
usando el mismo bot de servicio (google_credentials.json) que ya
usamos para Sheets -- ahora también con permiso de "Lector" en esa
propiedad de Analytics (06-ago-2026, confirmado con William).

Escribe en una tabla SEPARADA (ga4_metricas_tompalmer), NO en
ga4_metricas -- esa es la de Kaltemp, y no sabemos qué proceso la
llena hoy; tocar su estructura arriesga que el próximo sync de
Kaltemp la sobre-escriba sin la marca. Mismo patrón que usamos con
Google Ads de Tom Palmer: tabla propia, sin mezclar.

Requiere:
    pip install google-analytics-data --break-system-packages

Antes de correr, define el ID de la propiedad de GA4 de Tom Palmer
(Admin -> Detalles de la cuenta -> Información de la propiedad, en
Google Analytics) como variable de entorno GA4_PROPERTY_ID_TP, o
pásalo directo en la línea de comandos:

    python sync/sync_ga4_tompalmer.py 123456789
"""
import os
import sys
import duckdb
from datetime import datetime
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))

load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))
CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath(os.path.join(BACKEND_DIR, "..", "google_credentials.json")))

PROPERTY_ID = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GA4_PROPERTY_ID_TP")


def sync_ga4_tompalmer(progress_callback=None, dias_atras: int = None):
    """
    dias_atras (agregado 11-ago-2026, mismo motivo que en
    sync_notas_credito.py): si se pasa, la ventana se calcula como hoy
    menos esos días, en vez del "2024-01-01" fijo de siempre.
    progress_callback se acepta solo para no romper si sync_admin.py lo
    pasa (este script no reportaba progreso incremental).
    """
    print(f"[{datetime.now()}] 📊 Sincronizando GA4 Tom Palmer hacia {DB_FILE}")

    if not PROPERTY_ID:
        print("   ❌ Falta el Property ID de GA4 de Tom Palmer.")
        print("      Pásalo como argumento: python sync_ga4_tompalmer.py 123456789")
        print("      o defínelo como GA4_PROPERTY_ID_TP en el .env")
        return

    print(f"   🔑 ¿Existe archivo de credenciales en {CREDS_PATH}? {os.path.exists(CREDS_PATH)}")

    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric,
    )

    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    print(f"   🔑 Cuenta de Servicio: {credentials.service_account_email}")

    client = BetaAnalyticsDataClient(credentials=credentials)

    fecha_desde = "2024-01-01"
    if dias_atras is not None:
        from datetime import timedelta
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name="date"), Dimension(name="deviceCategory")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="bounceRate"),
            Metric(name="addToCarts"),
            Metric(name="checkouts"),
            Metric(name="transactions"),
        ],
        date_ranges=[DateRange(start_date=fecha_desde, end_date="today")],
    )

    try:
        response = client.run_report(request)
    except Exception as e:
        print(f"   ❌ Error al consultar GA4: {e}")
        return

    filas = []
    for row in response.rows:
        fecha_raw = row.dimension_values[0].value  # "YYYYMMDD"
        dispositivo_raw = row.dimension_values[1].value  # "mobile" / "desktop" / "tablet"
        fecha = f"{fecha_raw[0:4]}-{fecha_raw[4:6]}-{fecha_raw[6:8]}"
        dispositivo = dispositivo_raw.capitalize()  # "Mobile" -- misma convención que ga4_metricas de Kaltemp

        sesiones = int(float(row.metric_values[0].value or 0))
        tasa_rebote = float(row.metric_values[1].value or 0)
        atc = int(float(row.metric_values[2].value or 0))
        checkouts = int(float(row.metric_values[3].value or 0))
        transacciones = int(float(row.metric_values[4].value or 0))

        filas.append((fecha, dispositivo, sesiones, tasa_rebote, atc, checkouts, transacciones))

    if not filas:
        print("   ℹ️ GA4 no devolvió filas -- revisa el Property ID o el permiso del bot.")
        return

    print(f"   ✅ {len(filas)} filas recibidas de GA4.")

    import pandas as pd
    df = pd.DataFrame(filas, columns=["FECHA", "DISPOSITIVO", "SESIONES", "TASA_REBOTE", "ADD_TO_CART", "CHECKOUTS", "TRANSACCIONES"])
    df["FECHA"] = pd.to_datetime(df["FECHA"])

    with duckdb.connect(DB_FILE) as con:
        # FIX (15-ago-2026): mismo problema y misma solución que
        # sync_ga4_kaltemp.py -- ver ese archivo para el detalle completo.
        # Antes DROP+CREATE borraba todo el histórico en cada corrida con
        # dias_atras chico; ahora solo se reemplaza la ventana consultada.
        tablas = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        if "ga4_metricas_tompalmer" not in tablas:
            con.execute("""
                CREATE TABLE ga4_metricas_tompalmer (
                    FECHA TIMESTAMP, DISPOSITIVO VARCHAR, SESIONES BIGINT,
                    TASA_REBOTE DOUBLE, ADD_TO_CART BIGINT, CHECKOUTS BIGINT,
                    TRANSACCIONES BIGINT
                )
            """)
        con.execute(
            "DELETE FROM ga4_metricas_tompalmer WHERE CAST(FECHA AS DATE) >= CAST(? AS DATE)",
            [fecha_desde],
        )
        con.register("df_ga4_tp_tmp", df)
        con.execute("INSERT INTO ga4_metricas_tompalmer SELECT * FROM df_ga4_tp_tmp")
        print(f"[{datetime.now()}] ✅ ga4_metricas_tompalmer actualizada con {len(df)} filas (ventana desde {fecha_desde}).")


if __name__ == "__main__":
    sync_ga4_tompalmer()