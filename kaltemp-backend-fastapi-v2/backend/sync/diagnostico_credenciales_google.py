# ============================================================
# ARCHIVO: diagnostico_credenciales_google.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_credenciales_google.py
# ============================================================
"""
diagnostico_credenciales_google.py — Aísla si "invalid_grant: Invalid
JWT Signature" es un problema del ARCHIVO de credenciales (corrupto,
vencido, o de otra cuenta) o algo específico de la librería de GA4.

Hace 2 pruebas independientes:
  1. Refresca el token de acceso DIRECTO con google-auth (el mismo
     mecanismo interno que usa sync_marketing.py para Sheets, que sí
     funciona) -- si esto también falla con "Invalid JWT Signature",
     el problema es el archivo de credenciales en sí, no GA4.
  2. Si el token se obtiene bien, prueba usarlo para llamar
     directamente al endpoint REST de la Analytics Data API (sin pasar
     por la librería google-analytics-data), para aislar si el
     problema está en esa librería específica.

Uso:
    python diagnostico_credenciales_google.py
"""
import os
import json
import requests
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath(os.path.join(BACKEND_DIR, "..", "google_credentials.json")))
PROPERTY_ID_KALTEMP = os.getenv("GA4_PROPERTY_ID_KALTEMP")

print("=" * 70)
print("1) Revisión básica del archivo de credenciales")
print("=" * 70)
print(f"Ruta: {CREDS_PATH}")
print(f"¿Existe?: {os.path.exists(CREDS_PATH)}")

if not os.path.exists(CREDS_PATH):
    print("❌ No se encontró el archivo. Nada más que revisar.")
    raise SystemExit(1)

with open(CREDS_PATH, "r", encoding="utf-8") as f:
    raw = f.read()

try:
    data = json.loads(raw)
except Exception as e:
    print(f"❌ El archivo NO es JSON válido: {e}")
    raise SystemExit(1)

print(f"client_email: {data.get('client_email')}")
print(f"project_id: {data.get('project_id')}")
print(f"private_key_id: {data.get('private_key_id')}")

private_key = data.get("private_key", "")
tiene_saltos_linea_reales = "\n" in private_key
tiene_secuencia_escapada = "\\n" in private_key
print(f"private_key -- longitud: {len(private_key)} caracteres")
print(f"private_key -- ¿tiene saltos de línea reales?: {tiene_saltos_linea_reales}")
print(f"private_key -- ¿tiene '\\\\n' literal (sin convertir)?: {tiene_secuencia_escapada}")
print(f"private_key -- empieza con: {private_key[:35]!r}")
print(f"private_key -- termina con: {private_key[-35:]!r}")

print()
print("=" * 70)
print("2) Intento de refresh DIRECTO con google-auth (mismo mecanismo que Sheets)")
print("=" * 70)
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    credentials.refresh(Request())
    print(f"✅ Token obtenido con éxito. Primeros 25 caracteres: {credentials.token[:25]}...")
    token_ok = True
except Exception as e:
    print(f"❌ Falló el refresh directo: {e}")
    token_ok = False

if not token_ok:
    print()
    print("El archivo de credenciales en sí está fallando -- no es un tema")
    print("específico de la librería de GA4. Posibles causas:")
    print("  - La clave fue revocada/eliminada en Google Cloud Console")
    print("    (IAM y administración -> Cuentas de servicio -> Claves).")
    print("  - El archivo se corrompió al copiarlo/editarlo (los saltos de")
    print("    línea del campo private_key deben ser reales, no '\\n' literal).")
    print("  - Es un archivo de OTRA cuenta de servicio distinta a la que")
    print("    tiene los permisos otorgados en Analytics.")
    raise SystemExit(1)

print()
print("=" * 70)
print("3) Prueba del token contra la Analytics Data API (REST directo, sin la librería)")
print("=" * 70)
if not PROPERTY_ID_KALTEMP:
    print("⚠️ Falta GA4_PROPERTY_ID_KALTEMP en el .env -- no se puede probar el reporte.")
else:
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROPERTY_ID_KALTEMP}:runReport"
    headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}
    body = {
        "dimensions": [{"name": "date"}],
        "metrics": [{"name": "sessions"}],
        "dateRanges": [{"startDate": "7daysAgo", "endDate": "today"}],
    }
    res = requests.post(url, headers=headers, json=body, timeout=20)
    print(f"status_code: {res.status_code}")
    print(f"respuesta (primeros 500 caracteres): {res.text[:500]}")