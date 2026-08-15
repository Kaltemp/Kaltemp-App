import os
import re
import duckdb
from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2"
DB_PATH = os.path.join(BASE_DIR, "kaltemp_matrix.duckdb")
CREDS_PATH = os.path.join(BASE_DIR, "google_credentials.json")
SPREADSHEET_ID = "1CORzInmXIvjvbxfL3XHMOKstoNPkvW43exxnHUenQYM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def clean_text(text):
    if not text:
        return ""
    text = str(text).upper().strip()
    text = re.sub(r'[ÁÀÄÂ]', 'A', text)
    text = re.sub(r'[ÉÈËÊ]', 'E', text)
    text = re.sub(r'[ÍÌÏÎ]', 'I', text)
    text = re.sub(r'[ÓÒÖÔ]', 'O', text)
    text = re.sub(r'[ÚÙÜÛ]', 'U', text)
    text = re.sub(r'[^A-Z0-9\s]', '', text)
    return ' '.join(text.split())

def run():
    print("📋 [sync_planilla_despachos] Iniciando descarga desde Google Sheets...")
    if not os.path.exists(CREDS_PATH):
        print(f"❌ Error: Archivo de credenciales no encontrado en {CREDS_PATH}")
        return False

    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDS_PATH, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'CARGA FORMULARIO'!A1:ZZ10000"
        ).execute()

        rows = result.get("values", [])
        if not rows or len(rows) <= 1:
            print("⚠️ No se obtuvieron datos de 'CARGA FORMULARIO'.")
            return False

        records = []
        for idx, r in enumerate(rows[1:], start=2):
            marca_temp = r[0].strip() if len(r) > 0 else ""
            fecha_ingreso = r[1].strip() if len(r) > 1 else ""
            vendedor = r[2].strip() if len(r) > 2 else ""
            boleta_factura = r[3].strip() if len(r) > 3 else ""
            pedido = r[4].strip() if len(r) > 4 else ""
            despacho_retiro = r[5].strip() if len(r) > 5 else ""
            sku = r[6].strip() if len(r) > 6 else ""
            cantidad = r[7].strip() if len(r) > 7 else "1"
            nombre_cliente = r[8].strip() if len(r) > 8 else ""
            
            if "drive.google.com" in nombre_cliente:
                nombre_cliente = ""

            telefono = r[9].strip() if len(r) > 9 else ""
            correo = r[10].strip() if len(r) > 10 else ""
            direccion = r[11].strip() if len(r) > 11 else ""
            comuna = r[12].strip() if len(r) > 12 else ""
            observaciones = r[13].strip() if len(r) > 13 else ""

            cliente_clean = clean_text(nombre_cliente)

            if vendedor or boleta_factura or pedido or cliente_clean or sku:
                records.append((
                    idx, marca_temp, fecha_ingreso, vendedor, boleta_factura,
                    pedido, despacho_retiro, sku, cantidad, nombre_cliente,
                    cliente_clean, telefono, correo, direccion, comuna, observaciones
                ))

        conn = duckdb.connect(DB_PATH)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS planilla_despachos (
                fila_num INTEGER,
                marca_temporal VARCHAR,
                fecha_ingreso VARCHAR,
                vendedor VARCHAR,
                boleta_factura VARCHAR,
                pedido VARCHAR,
                despacho_retiro VARCHAR,
                sku VARCHAR,
                cantidad VARCHAR,
                nombre_cliente VARCHAR,
                cliente_clean VARCHAR,
                telefono VARCHAR,
                correo VARCHAR,
                direccion VARCHAR,
                comuna VARCHAR,
                observaciones VARCHAR,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("DELETE FROM planilla_despachos")

        conn.executemany("""
            INSERT INTO planilla_despachos (
                fila_num, marca_temporal, fecha_ingreso, vendedor, boleta_factura,
                pedido, despacho_retiro, sku, cantidad, nombre_cliente,
                cliente_clean, telefono, correo, direccion, comuna, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

        conn.close()
        print(f"✅ [sync_planilla_despachos] {len(records)} filas guardadas en DuckDB.")
        return True

    except Exception as e:
        print(f"❌ Error en sync_planilla_despachos: {e}")
        return False

def sync_planilla_despachos():
    return run()

if __name__ == "__main__":
    run()