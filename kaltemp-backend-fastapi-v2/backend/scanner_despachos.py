import os
import json
import sys

CREDS_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\google_credentials.json"
SPREADSHEET_ID = "1CORzInmXIvjvbxfL3XHMOKstoNPkvW43exxnHUenQYM"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def main():
    if not os.path.exists(CREDS_PATH):
        print(f"❌ No se encontró el archivo de credenciales en: {CREDS_PATH}")
        return

    print(f"🔑 Usando credenciales de: {CREDS_PATH}")
    print(f"📊 Leyendo planilla ID: {SPREADSHEET_ID}\n")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            CREDS_PATH, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=credentials)

        # 1. Obtener metadata de las pestañas
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = spreadsheet.get("sheets", [])

        print(f"📌 Título de la planilla: {spreadsheet.get('properties', {}).get('title')}")
        print(f"📑 Pestañas encontradas ({len(sheets)}):")
        for s in sheets:
            props = s.get("properties", {})
            print(f"   - {props.get('title')} (ID: {props.get('sheetId')})")

        print("\n" + "="*80)

        # 2. Leer primeras filas de cada pestaña
        for s in sheets:
            sheet_title = s.get("properties", {}).get("title")
            print(f"\n📄 PESTAÑA: '{sheet_title}'")
            
            range_name = f"'{sheet_title}'!A1:ZZ10"
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=range_name
            ).execute()
            
            rows = result.get("values", [])
            if not rows:
                print("   (Pestaña vacía o sin datos en A1:ZZ10)")
                continue

            print(f"   ► Cabeceras (Fila 1): {rows[0]}")
            print("   ► Muestra de datos (filas 2 a 6):")
            for idx, row in enumerate(rows[1:6], start=2):
                print(f"      Fila {idx}: {row}")

    except Exception as e:
        print(f"❌ Error al consultar Google Sheets API: {e}")

if __name__ == "__main__":
    main()