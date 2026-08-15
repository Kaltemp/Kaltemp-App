import os
import re
import duckdb

BASE_DIR = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2"
DB_PATH = os.path.join(BASE_DIR, "kaltemp_matrix.duckdb")

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
    print("🔗 [sync_cruce_enviame_bsale] Iniciando proceso de cruce...")
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada en {DB_PATH}")
        return False

    conn = duckdb.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enviame_cruce_ventas (
                ID_INTERNO VARCHAR,
                N_ENVIO_REF VARCHAR,
                NUMERO_DOCUMENTO_MATCH VARCHAR,
                VENDEDOR VARCHAR,
                PRODUCTO VARCHAR,
                COBRO_BSALE_DESPACHO DOUBLE,
                METODO_MATCH VARCHAR,
                ACTUALIZADO_EN TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("DELETE FROM enviame_cruce_ventas")

        sku_map = {}
        try:
            skus = conn.execute("SELECT SKU, Titulo FROM sku_maestro").fetchall()
            for s_code, s_title in skus:
                if s_code and s_title:
                    sku_map[str(s_code).strip().upper()] = str(s_title).strip()
        except Exception:
            pass

        # ETAPA 1: Cruce Bsale por Nombre + Fecha (Ventana 5d)
        print("   ► Ejecutando Etapa 1: Bsale (Nombre + Ventana 5d)...")
        conn.execute("""
            INSERT INTO enviame_cruce_ventas (
                ID_INTERNO, N_ENVIO_REF, NUMERO_DOCUMENTO_MATCH, VENDEDOR, PRODUCTO, COBRO_BSALE_DESPACHO, METODO_MATCH
            )
            WITH env_clean AS (
                SELECT 
                    ID_INTERNO,
                    N_ENVIO_REF,
                    CLIENTE,
                    FECHA_CREACION,
                    regexp_replace(upper(trim(CLIENTE)), '[^A-Z0-9 ]', '', 'g') as cliente_clean
                FROM enviame_despachos
                WHERE CLIENTE IS NOT NULL AND CLIENTE != ''
            ),
            ventas_agg AS (
                SELECT 
                    NUMERO_DOCUMENTO,
                    VENDEDOR,
                    CLIENTE,
                    regexp_replace(upper(trim(CLIENTE)), '[^A-Z0-9 ]', '', 'g') as cliente_clean,
                    MIN(FECHA_DOCUMENTO) as fecha_doc,
                    STRING_AGG(DISTINCT LINEA_DETALLE, ' | ') as productos,
                    SUM(CASE WHEN lower(LINEA_DETALLE) LIKE '%despacho%' OR lower(LINEA_DETALLE) LIKE '%flete%' THEN TOTAL_LINEA ELSE 0 END) as cobro_despacho
                FROM ventas
                WHERE TIPO_DOCUMENTO != 'nota de crédito'
                GROUP BY NUMERO_DOCUMENTO, VENDEDOR, CLIENTE
            ),
            matches AS (
                SELECT 
                    e.ID_INTERNO,
                    e.N_ENVIO_REF,
                    v.NUMERO_DOCUMENTO,
                    v.VENDEDOR,
                    v.productos,
                    v.cobro_despacho,
                    ROW_NUMBER() OVER (PARTITION BY e.ID_INTERNO ORDER BY abs(date_diff('day', CAST(e.FECHA_CREACION AS DATE), v.fecha_doc))) as rn
                FROM env_clean e
                JOIN ventas_agg v ON e.cliente_clean = v.cliente_clean
                WHERE abs(date_diff('day', CAST(e.FECHA_CREACION AS DATE), v.fecha_doc)) <= 5
            )
            SELECT 
                ID_INTERNO,
                N_ENVIO_REF,
                CAST(NUMERO_DOCUMENTO AS VARCHAR),
                VENDEDOR,
                productos,
                cobro_despacho,
                'Bsale - Nombre + Fecha (5d)'
            FROM matches
            WHERE rn = 1
        """)
        m1 = conn.execute("SELECT COUNT(*) FROM enviame_cruce_ventas").fetchone()[0]
        print(f"     ✅ Etapa 1 resolvió {m1} envíos.")

        # ETAPA 2: Cruce Bsale por N° Documento + Fecha (Ventana 7d)
        print("   ► Ejecutando Etapa 2: Bsale (N° Documento + Ventana 7d)...")
        conn.execute("""
            INSERT INTO enviame_cruce_ventas (
                ID_INTERNO, N_ENVIO_REF, NUMERO_DOCUMENTO_MATCH, VENDEDOR, PRODUCTO, COBRO_BSALE_DESPACHO, METODO_MATCH
            )
            WITH env_pending AS (
                SELECT d.ID_INTERNO, d.N_ENVIO_REF, d.FECHA_CREACION
                FROM enviame_despachos d
                LEFT JOIN enviame_cruce_ventas c ON d.ID_INTERNO = c.ID_INTERNO
                WHERE c.ID_INTERNO IS NULL AND d.N_ENVIO_REF IS NOT NULL AND d.N_ENVIO_REF != ''
            ),
            ventas_agg AS (
                SELECT 
                    CAST(NUMERO_DOCUMENTO AS VARCHAR) as num_doc,
                    VENDEDOR,
                    MIN(FECHA_DOCUMENTO) as fecha_doc,
                    STRING_AGG(DISTINCT LINEA_DETALLE, ' | ') as productos,
                    SUM(CASE WHEN lower(LINEA_DETALLE) LIKE '%despacho%' OR lower(LINEA_DETALLE) LIKE '%flete%' THEN TOTAL_LINEA ELSE 0 END) as cobro_despacho
                FROM ventas
                WHERE TIPO_DOCUMENTO != 'nota de crédito'
                GROUP BY NUMERO_DOCUMENTO, VENDEDOR
            ),
            matches AS (
                SELECT 
                    e.ID_INTERNO,
                    e.N_ENVIO_REF,
                    v.num_doc,
                    v.VENDEDOR,
                    v.productos,
                    v.cobro_despacho,
                    ROW_NUMBER() OVER (PARTITION BY e.ID_INTERNO ORDER BY abs(date_diff('day', CAST(e.FECHA_CREACION AS DATE), v.fecha_doc))) as rn
                FROM env_pending e
                JOIN ventas_agg v ON trim(CAST(e.N_ENVIO_REF AS VARCHAR)) = trim(v.num_doc)
                WHERE abs(date_diff('day', CAST(e.FECHA_CREACION AS DATE), v.fecha_doc)) <= 7
            )
            SELECT 
                ID_INTERNO,
                N_ENVIO_REF,
                num_doc,
                VENDEDOR,
                productos,
                cobro_despacho,
                'Bsale - N° Documento + Fecha (7d)'
            FROM matches
            WHERE rn = 1
        """)
        m2 = conn.execute("SELECT COUNT(*) FROM enviame_cruce_ventas").fetchone()[0]
        print(f"     ✅ Etapa 2 resolvió {m2 - m1} envíos adicionales (Total Bsale: {m2}).")

        # ETAPA 3: Cruce con Planilla de Despachos
        print("   ► Ejecutando Etapa 3: Planilla de Despachos (Google Sheets)...")
        pending_env = conn.execute("""
            SELECT d.ID_INTERNO, d.N_ENVIO_REF, d.CLIENTE
            FROM enviame_despachos d
            LEFT JOIN enviame_cruce_ventas c ON d.ID_INTERNO = c.ID_INTERNO
            WHERE c.ID_INTERNO IS NULL
        """).fetchall()

        form_rows = conn.execute("""
            SELECT vendedor, boleta_factura, pedido, sku, nombre_cliente, cliente_clean
            FROM planilla_despachos
        """).fetchall()

        records_e3 = []
        for id_int, n_ref, cliente_env in pending_env:
            cliente_clean = clean_text(cliente_env)
            ref_clean = str(n_ref).strip() if n_ref else ""

            match = None
            metodo = ""

            if cliente_clean and cliente_clean != 'NONE':
                m_list = [f for f in form_rows if f[5] and f[5] == cliente_clean]
                if m_list:
                    match = m_list[0]
                    metodo = "Planilla - Nombre Cliente"

            if not match and ref_clean and ref_clean != 'NONE':
                m_list = [f for f in form_rows if (f[1] and f[1] == ref_clean) or (f[2] and f[2] == ref_clean)]
                if m_list:
                    match = m_list[0]
                    metodo = "Planilla - Boleta/Factura"

            if match:
                vendedor_f, doc_f, ped_f, sku_f, nom_f, c_clean_f = match
                num_doc_match = doc_f if doc_f else (ped_f if ped_f else ref_clean)
                
                sku_clean = str(sku_f).strip().upper()
                prod_nombre = sku_map.get(sku_clean, sku_clean) if sku_clean else "Producto de Planilla"

                records_e3.append((
                    id_int,
                    n_ref,
                    num_doc_match,
                    vendedor_f if vendedor_f else "Planilla Despachos",
                    prod_nombre,
                    0.0,
                    metodo
                ))

        if records_e3:
            conn.executemany("""
                INSERT INTO enviame_cruce_ventas (
                    ID_INTERNO, N_ENVIO_REF, NUMERO_DOCUMENTO_MATCH, VENDEDOR, PRODUCTO, COBRO_BSALE_DESPACHO, METODO_MATCH
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records_e3)

        m3 = conn.execute("SELECT COUNT(*) FROM enviame_cruce_ventas").fetchone()[0]
        print(f"     ✅ Etapa 3 resolvió {m3 - m2} envíos adicionales con la Planilla.")

        conn.close()

        total_desp = 1421
        try:
            conn_chk = duckdb.connect(DB_PATH, read_only=True)
            total_desp = conn_chk.execute("SELECT COUNT(*) FROM enviame_despachos").fetchone()[0]
            conn_chk.close()
        except Exception:
            pass

        cobertura = round((m3 / total_desp) * 100, 1) if total_desp else 0
        print(f"🎉 [sync_cruce_enviame_bsale] Proceso completado exitosamente: {m3} de {total_desp} envíos resueltos ({cobertura}% de cobertura).")
        return True

    except Exception as e:
        print(f"❌ Error en sync_cruce_enviame_bsale: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    run()