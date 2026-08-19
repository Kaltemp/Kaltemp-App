# ============================================================
# ARCHIVO: sync_ga4_kaltemp.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_ga4_kaltemp.py
# ============================================================

"""
sync/sync_ga4_kaltemp.py — Trae Sesiones/Rebote/ATC/Checkouts/
Transacciones desde la propiedad de GA4 de Kaltemp (kaltemp.cl), usando
el mismo bot de servicio (google_credentials.json) que ya se usa para
Sheets y para GA4 Tom Palmer.

Escribe en `ga4_metricas` -- la tabla que ya consume channels.py para
el módulo Indicadores D2C cuando marca="Kaltemp". Hasta el 10-ago-2026
no había ningún script en el repo que la llenara (comentario en
sync_ga4_tompalmer.py: "no sabemos qué proceso la llena hoy"); este
script pasa a ser la fuente oficial de esa tabla, con el mismo shape de
columnas que ya usa channels.py (FECHA, DISPOSITIVO, SESIONES,
TASA_REBOTE, ADD_TO_CART, CHECKOUTS, TRANSACCIONES) -- exactamente el
mismo patrón que sync_ga4_tompalmer.py, solo que apuntando a la
propiedad y tabla de Kaltemp.

Requiere:
    pip install google-analytics-data --break-system-packages

Define GA4_PROPERTY_ID_KALTEMP en el .env (Admin -> Detalles de la
cuenta -> Información de la propiedad, en Google Analytics, dentro de
la propiedad de kaltemp.cl). Confirma también que la cuenta de servicio
(kaltemp-bot@...) tenga rol "Lector" en ESA propiedad específica -- es
el mismo bot que ya se usa para Tom Palmer y Sheets, pero los permisos
de GA4 son por propiedad, no se heredan automáticamente entre ellas.

CORREGIDO (19-ago-2026, bug real confirmado con el panel web "Motor de
Actualización" -- sync_admin.py): antes, el guardado en DuckDB SIEMPRE
hacía DROP TABLE + CREATE TABLE AS SELECT usando SOLO las filas
recién traídas de GA4 para la ventana [fecha_desde, hoy]. Eso significa
que el botón "Actualizar Ahora (últimos 30 días)" del panel web -- que
le pasa dias_atras=30 a TODAS las tablas que lo soportan, incluida esta
-- borraba TODO el histórico de ga4_metricas (~2 años) y lo dejaba solo
con los últimos 30 días. Ahora se usa el mismo patrón que ya corrigió
este mismo bug en sync_temperaturas.py: se borra e inserta SOLO el
rango [fecha_desde, hoy] que realmente se volvió a consultar -- el
resto del histórico queda intacto sin importar qué tan chico sea
dias_atras.
"""
import os
import duckdb
from datetime import datetime
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))

load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))
CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath(os.path.join(BACKEND_DIR, "..", "google_credentials.json")))

PROPERTY_ID = os.getenv("GA4_PROPERTY_ID_KALTEMP")

# Misma profundidad histórica que Tom Palmer, para poder comparar YoY
# ambas marcas en el módulo Indicadores D2C.
GA4_FECHA_DESDE = os.getenv("GA4_KALTEMP_FECHA_DESDE", "2024-01-01")


def sync_ga4_kaltemp(progress_callback=None, dias_atras: int = None):
    """
    dias_atras (agregado 11-ago-2026, mismo motivo que en
    sync_notas_credito.py): si se pasa, la ventana se calcula como hoy
    menos esos días, con prioridad sobre GA4_KALTEMP_FECHA_DESDE.
    """
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    report(5, f"📊 Sincronizando GA4 Kaltemp hacia {DB_FILE}")

    if not PROPERTY_ID:
        report(100, "❌ Falta GA4_PROPERTY_ID_KALTEMP en el .env.")
        return

    print(f"   🔑 ¿Existe archivo de credenciales en {CREDS_PATH}? {os.path.exists(CREDS_PATH)}")

    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric,
    )

    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    # Refresh explícito antes de crear el cliente -- confirmado real
    # (10-ago-2026): sin esto, BetaAnalyticsDataClient manda la
    # petición SIN token adjunto, y Google responde 401 "invalid
    # authentication credentials" como si no hubiera credenciales en
    # absoluto (no es un tema de permiso 'Lector', es que el token
    # nunca se generó). Mismo truco que ya usa sync_marketing.py para
    # Sheets, que sí funciona.
    credentials.refresh(Request())
    print(f"   🔑 Cuenta de Servicio: {credentials.service_account_email}")

    # transport="rest" -- confirmado real (10-ago-2026): el transporte
    # gRPC (default) daba "invalid_grant: Invalid JWT Signature" con
    # esta cuenta de servicio, mientras que Sheets (REST puro, en
    # sync_marketing.py) sí funciona con la misma credencial. Forzar
    # REST acá evita el canal gRPC y reutiliza el mismo tipo de
    # intercambio de token que ya funciona.
    client = BetaAnalyticsDataClient(credentials=credentials, transport="rest")
    report(20, "📊 Consultando GA4 Kaltemp...")

    fecha_desde = GA4_FECHA_DESDE
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
        report(100, f"❌ Error al consultar GA4: {e} -- revisa que el bot tenga permiso 'Lector' en la propiedad de kaltemp.cl.")
        return

    filas = []
    for row in response.rows:
        fecha_raw = row.dimension_values[0].value  # "YYYYMMDD"
        dispositivo_raw = row.dimension_values[1].value  # "mobile" / "desktop" / "tablet"
        fecha = f"{fecha_raw[0:4]}-{fecha_raw[4:6]}-{fecha_raw[6:8]}"
        dispositivo = dispositivo_raw.capitalize()

        sesiones = int(float(row.metric_values[0].value or 0))
        tasa_rebote = float(row.metric_values[1].value or 0)
        atc = int(float(row.metric_values[2].value or 0))
        checkouts = int(float(row.metric_values[3].value or 0))
        transacciones = int(float(row.metric_values[4].value or 0))

        filas.append((fecha, dispositivo, sesiones, tasa_rebote, atc, checkouts, transacciones))

    if not filas:
        report(100, "ℹ️ GA4 no devolvió filas -- revisa el Property ID o el permiso del bot.")
        return

    report(70, f"✅ {len(filas)} filas recibidas de GA4. Escribiendo en DuckDB...")

    import pandas as pd
    df = pd.DataFrame(filas, columns=["FECHA", "DISPOSITIVO", "SESIONES", "TASA_REBOTE", "ADD_TO_CART", "CHECKOUTS", "TRANSACCIONES"])
    df["FECHA"] = pd.to_datetime(df["FECHA"])

    with duckdb.connect(DB_FILE) as con:
        con.register("df_ga4_kaltemp_tmp", df)
        existe = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'ga4_metricas'"
        ).fetchone()[0] > 0
        if not existe:
            con.execute("CREATE TABLE ga4_metricas AS SELECT * FROM df_ga4_kaltemp_tmp")
        else:
            # CORREGIDO (19-ago-2026): antes esto era un DROP TABLE +
            # CREATE TABLE completo -- pedir una ventana chica (ej.
            # dias_atras=30 desde "Actualizar Ahora") borraba TODO el
            # histórico y dejaba solo esos 30 días. Ahora solo se borra
            # y reinserta el rango [fecha_desde, hoy] que realmente se
            # volvió a consultar -- el resto del histórico queda intacto.
            con.execute("DELETE FROM ga4_metricas WHERE FECHA >= CAST(? AS DATE)", [fecha_desde])
            con.execute("INSERT INTO ga4_metricas SELECT * FROM df_ga4_kaltemp_tmp")

    report(100, f"✨ ga4_metricas actualizada con {len(df)} filas ({fecha_desde} → hoy).")


if __name__ == "__main__":
    sync_ga4_kaltemp()