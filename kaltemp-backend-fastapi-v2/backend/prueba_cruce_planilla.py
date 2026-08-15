import duckdb
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDS_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\google_credentials.json"
SPREADSHEET_ID = "1CORzInmXIvjvbxfL3XHMOKstoNPkvW43exxnHUenQYM"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
DB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

def clean_text(text):
    if not text:
        return ""
    text = text.upper().strip()
    text = re.sub(r'[ÁÀÄÂ]', 'A', text)
    text = re.sub(r'[ÉÈËÊ]', 'E', text)
    text = re.sub(r'[ÍÌÏÎ]', 'I', text)
    text = re.sub(r'[ÓÒÖÔ]', 'O', text)
    text = re.sub(r'[ÚÙÜÛ]', 'U', text)
    text = re.sub(r'[^A-Z0-9\s]', '', text)
    return ' '.join(text.split())

def main():
    print("📊 Descargando data de Google Sheets ('CARGA FORMULARIO')...")
    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'CARGA FORMULARIO'!A1:ZZ10000"
    ).execute()
    
    rows = result.get("values", [])
    if not rows or len(rows) <= 1:
        print("❌ No se obtuvieron datos de la planilla.")
        return

    form_records = []
    for r in rows[1:]:
        vendedor = r[2].strip() if len(r) > 2 else ""
        doc = r[3].strip() if len(r) > 3 else ""
        pedido = r[4].strip() if len(r) > 4 else ""
        sku = r[6].strip() if len(r) > 6 else ""
        cliente_raw = r[8].strip() if len(r) > 8 else ""
        
        if "drive.google.com" in cliente_raw:
            cliente_raw = ""

        if vendedor or doc or cliente_raw:
            form_records.append({
                "vendedor": vendedor,
                "doc": doc,
                "pedido": pedido,
                "sku": sku,
                "cliente_clean": clean_text(cliente_raw)
            })

    print(f"✅ Se cargaron {len(form_records)} registros del formulario.")

    conn = duckdb.connect(DB_PATH, read_only=True)

    total_despachos = conn.execute("SELECT COUNT(*) FROM enviame_despachos").fetchone()[0]
    total_cruces = conn.execute("SELECT COUNT(*) FROM enviame_cruce_ventas").fetchone()[0]

    unassigned_df = conn.execute("""
        SELECT d.ID_INTERNO, d.N_ENVIO_REF, d.CLIENTE, d.FECHA_CREACION
        FROM enviame_despachos d
        LEFT JOIN enviame_cruce_ventas c ON d.ID_INTERNO = c.ID_INTERNO
        WHERE c.VENDEDOR IS NULL OR c.VENDEDOR = 'Sin Asignar'
    """).df()

    total_unassigned = len(unassigned_df)

    print(f"📦 Total envíos en enviame_despachos: {total_despachos}")
    print(f"✅ Envíos ya resueltos con Bsale: {total_cruces}")
    print(f"❓ Envíos pendientes sin match ('Sin Asignar'): {total_unassigned}")

    matched_by_name = 0
    matched_by_doc = 0
    matched_examples = []

    for idx, row in unassigned_df.iterrows():
        cliente_env = str(row['CLIENTE']) if row['CLIENTE'] else ""
        ref_env = str(row['N_ENVIO_REF']) if row['N_ENVIO_REF'] else ""
        
        cliente_clean = clean_text(cliente_env)
        ref_clean = ref_env.strip()
        
        m = None
        match_type = ""
        
        # 1. Match por Nombre Cliente
        if cliente_clean and cliente_clean != 'NONE':
            matches = [f for f in form_records if f["cliente_clean"] and f["cliente_clean"] == cliente_clean]
            if matches:
                m = matches[0]
                match_type = "Nombre Cliente"
                matched_by_name += 1

        # 2. Match por Documento / Pedido
        if not m and ref_clean and ref_clean != 'NONE':
            matches = [f for f in form_records if f["doc"] == ref_clean or f["pedido"] == ref_clean]
            if matches:
                m = matches[0]
                match_type = "Boleta/Factura"
                matched_by_doc += 1

        if m:
            id_val = row['ID_INTERNO']
            matched_examples.append((id_val, cliente_env, ref_clean, match_type, m["vendedor"], m["sku"]))

    total_recuperados = matched_by_name + matched_by_doc

    print("\n" + "="*80)
    print("🎯 RESULTADOS DEL CRUCE CON 'CARGA FORMULARIO' EN LOS ENVÍOS PENDIENTES:")
    print(f"  ► Resueltos por NOMBRE DE CLIENTE: {matched_by_name}")
    print(f"  ► Resueltos por BOLETA / FACTURA / PEDIDO: {matched_by_doc}")
    print(f"  ► TOTAL ENVÍOS RECUPERADOS: {total_recuperados} de {total_unassigned} sin match ({round(total_recuperados/total_unassigned*100, 1) if total_unassigned else 0}%)")
    nuevo_total = total_cruces + total_recuperados
    print(f"  🚀 COBERTURA TOTAL ESTIMADA: {nuevo_total} de {total_despachos} ({round(nuevo_total/total_despachos*100, 1)}%)")

    print("\n--- Muestra de casos resueltos gracias a la planilla ---")
    for ex in matched_examples[:15]:
        print(f"  • ID #{ex[0]} | Cliente: '{ex[1]}' (Ref: {ex[2]}) | Match por: {ex[3]} | Vendedor: '{ex[4]}' | SKU: '{ex[5]}'")

if __name__ == "__main__":
    main()