import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDS_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\google_credentials.json"
SPREADSHEET_ID = "1CORzInmXIvjvbxfL3XHMOKstoNPkvW43exxnHUenQYM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def main():
    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)

    print("📊 Leyendo pestaña 'CARGA FORMULARIO'...")
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'CARGA FORMULARIO'!A1:ZZ10000"
    ).execute()

    rows = result.get("values", [])
    if not rows:
        print("❌ No se encontraron datos")
        return

    headers = rows[0]
    data = rows[1:]
    print(f"✅ Total filas en 'CARGA FORMULARIO': {len(data)}")
    print(f"📋 Cabeceras: {headers}\n")

    print("--- Últimas 10 filas registradas en el formulario ---")
    for idx, r in enumerate(data[-10:], start=len(data)-9):
        print(f"Fila {idx}: {r}")

if __name__ == "__main__":
    main()