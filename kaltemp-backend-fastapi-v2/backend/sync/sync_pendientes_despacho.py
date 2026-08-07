"""
sync_pendientes_despacho.py — Puebla `pendientes_despacho` en kaltemp_matrix.duckdb.

Audita TODAS las boletas y facturas del período (no solo las pendientes) y
clasifica cada una en:
  - ⏳ Pendiente          / Sin guía asociada   -> ninguna línea despachada
  - ✅ Despachado         / Entregado OK        -> guía(s) con monto > 0
  - ✅ Despachado         / Guía con costo $0   -> al menos una guía asociada
                                                    quedó en $0 (revisar en Bsale)

==========================================================================
MÉTODO VALIDADO CONTRA UN CASO REAL (31-jul-2026, boleta 41660 / guía 57648):
==========================================================================
El vínculo entre una Guía de Despacho y su boleta/factura original NO vive
en /references.json (ese campo está vacío casi siempre -- es para
referencias manuales, como una Orden de Compra). Vive a NIVEL DE LÍNEA DE
DETALLE:

    guía.details[].relatedDetailId  ==  boleta.details[].id

Es decir: cada línea de producto de la guía apunta al id de la línea de
producto original de la boleta que despachó. Confirmado con el JSON real
de Bsale (ver diagnostico_referencia_especifica.py).

Para no hacer una llamada API extra por cada documento (que sería otra
vez un proceso de horas), se usa expand=[details] directo en el listado
paginado de documents.json -- los detalles vienen embebidos en la misma
respuesta que ya se pedía.

Uso:
    export BSALE_ACCESS_TOKEN=...
    export DUCKDB_PATH=/ruta/a/kaltemp_matrix.duckdb
    export PXD_DIAS_ATRAS=180
    python sync_pendientes_despacho.py
"""
import os
import sys
import duckdb
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
DIAS_ATRAS = int(os.getenv("PXD_DIAS_ATRAS", "180"))

CODESII_BOLETA = 39
CODESII_FACTURA = 33
CODESII_GUIA = 52


def _cargar_oficinas() -> dict:
    """office_id -> nombre real de la bodega/sucursal (mismo método probado en sync_stock_bsale.py)"""
    return {str(o["id"]): o["name"] for o in bsale_get_all("offices.json")}


def _epoch(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _extraer_items_details(doc: dict, doc_id: int) -> list:
    """
    Con expand=[details], Bsale normalmente embebe la lista completa en
    doc["details"]["items"]. Si por algún motivo viene truncada (documento
    con muchísimas líneas) o no vino expandida (solo href), se hace un
    fallback puntual a GET /documents/{id}/details.json para ESE documento
    en particular -- no para todos, así que el costo extra es mínimo.
    """
    details = doc.get("details")
    if isinstance(details, dict):
        items = details.get("items", [])
        count = details.get("count", len(items))
        if items and len(items) >= count:
            return items
    elif isinstance(details, list) and details:
        return details

    # Fallback puntual (debería ser poco frecuente)
    return list(bsale_get_all(f"documents/{doc_id}/details.json"))


def _construir_mapa_related_detail_ids(fecha_desde: int, fecha_hasta: int) -> dict:
    """
    Mapa relatedDetailId -> totalAmount de la guía que despachó esa línea,
    para TODAS las guías del período. Antes esto era un set() (solo
    existencia); ahora se retiene el monto de la guía para poder distinguir
    'Entregado OK' de 'Guía con costo $0' (guía emitida pero con valor cero,
    señal de que algo quedó mal cargado en Bsale y conviene auditar).
    Si una misma línea aparece en más de una guía (caso raro, ej. guía
    anulada y reemitida), se queda con el monto de la ÚLTIMA guía procesada
    -- suficiente para el propósito de auditoría de este módulo.
    """
    mapa = {}
    total_guias = 0
    fallback_usado = 0
    for guia in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_GUIA,
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
            "expand": "[details]",
        },
    ):
        total_guias += 1
        monto_guia = float(guia.get("totalAmount", 0) or 0)
        items = guia.get("details")
        if isinstance(items, dict) and items.get("items"):
            lineas = items["items"]
        else:
            lineas = _extraer_items_details(guia, guia["id"])
            fallback_usado += 1
        for linea in lineas:
            rid = linea.get("relatedDetailId")
            if rid:
                mapa[rid] = monto_guia
        if total_guias % 500 == 0:
            print(f"  {total_guias} guías revisadas...")
    print(f"  {total_guias} guías revisadas ({fallback_usado} con fallback puntual), "
          f"{len(mapa)} relatedDetailId encontrados")
    return mapa


def sync_pendientes_despacho():
    fecha_desde = _epoch(datetime.now(timezone.utc) - timedelta(days=DIAS_ATRAS))
    fecha_hasta = _epoch(datetime.now(timezone.utc))

    print(f"[{datetime.now()}] Cargando mapa de oficinas/bodegas...")
    mapa_oficinas = _cargar_oficinas()
    print(f"  {len(mapa_oficinas)} oficinas encontradas")

    print(f"[{datetime.now()}] Sync pendientes_despacho: indexando líneas de guías (últimos {DIAS_ATRAS} días)...")
    mapa_detail_id_a_monto_guia = _construir_mapa_related_detail_ids(fecha_desde, fecha_hasta)

    # docs_auditoria guarda TODOS los documentos (despachados y pendientes),
    # ya clasificados con ESTADO/MOTIVO. tipo_bucket es solo para desambiguar
    # el cruce con `ventas` más abajo (Bsale numera boletas y facturas en
    # series independientes, así que puede existir boleta Nº41660 Y factura
    # Nº41660 al mismo tiempo -- si cruzáramos solo por número sin tipo, uno
    # pisaría el vendedor del otro).
    docs_auditoria = []
    for codesii in (CODESII_BOLETA, CODESII_FACTURA):
        tipo_bucket = "BOLETA" if codesii == CODESII_BOLETA else "FACTURA"
        print(f"[{datetime.now()}] Revisando documentos codeSii={codesii}...")
        total = 0
        for doc in bsale_get_all(
            "documents.json",
            params={
                "codesii": codesii,
                "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
                "expand": "[client,details,sellers,office]",
            },
        ):
            total += 1
            lineas = _extraer_items_details(doc, doc["id"])
            ids_propios = {d.get("id") for d in lineas if d.get("id")}

            montos_guias_asociadas = [
                mapa_detail_id_a_monto_guia[rid]
                for rid in ids_propios
                if rid in mapa_detail_id_a_monto_guia
            ]

            if not montos_guias_asociadas:
                estado, motivo = "⏳ Pendiente", "Sin guía asociada"
            elif any(monto == 0 for monto in montos_guias_asociadas):
                estado, motivo = "✅ Despachado", "Guía con costo $0"
            else:
                estado, motivo = "✅ Despachado", "Entregado OK"

            emision = datetime.fromtimestamp(doc["emissionDate"], tz=timezone.utc) if doc.get("emissionDate") else None
            if not emision:
                continue

            cliente_obj = doc.get("client")
            if isinstance(cliente_obj, dict):
                cliente = cliente_obj.get("company") or f"{cliente_obj.get('firstName', '')} {cliente_obj.get('lastName', '')}".strip()
            else:
                cliente = None

            # VENDEDOR directo desde Bsale (expand=sellers), no depende de que
            # `ventas` tenga sincronizada la misma ventana de fechas -- cubre
            # el 100% del período auditado, a diferencia del cruce anterior
            # contra `ventas` que solo llegaba al 27% (ventana corta de 53d).
            # Un documento puede tener 1+ vendedores (ej. si se generó a
            # partir de varias notas de venta); se listan todos separados
            # por coma.
            sellers_obj = doc.get("sellers")
            nombres_vendedores = []
            if isinstance(sellers_obj, dict):
                for s in sellers_obj.get("items", []):
                    nombre = f"{s.get('firstName', '')} {s.get('lastName', '')}".strip()
                    if nombre:
                        nombres_vendedores.append(nombre)
            vendedor = ", ".join(nombres_vendedores) if nombres_vendedores else "Sin vendedor"

            # Bodega/sucursal que emitió el documento (mismo mapa de oficinas
            # que ya usa el módulo Stock -- resuelto por id, no confiando en
            # que `expand=[office]` traiga el nombre embebido, porque no
            # siempre lo hace).
            office_obj = doc.get("office")
            office_id = str(office_obj.get("id")) if isinstance(office_obj, dict) else None
            bodega = mapa_oficinas.get(office_id, "Sin bodega") if office_id else "Sin bodega"

            docs_auditoria.append({
                "numero": str(doc.get("number")),
                "tipo_bucket": tipo_bucket,
                "cliente": cliente or "Sin cliente",
                "vendedor": vendedor,
                "bodega": bodega,
                "emision": emision,
                "monto": float(doc.get("totalAmount", 0) or 0),
                "estado": estado,
                "motivo": motivo,
            })
            if total % 500 == 0:
                print(f"  {total} documentos codeSii={codesii} revisados...")

    total_pendientes = sum(1 for d in docs_auditoria if d["estado"] == "⏳ Pendiente")
    total_costo_cero = sum(1 for d in docs_auditoria if d["motivo"] == "Guía con costo $0")
    total_ok = sum(1 for d in docs_auditoria if d["motivo"] == "Entregado OK")
    print(f"[{datetime.now()}] {len(docs_auditoria)} documentos auditados: "
          f"{total_pendientes} pendientes, {total_ok} entregados OK, "
          f"{total_costo_cero} con guía de costo $0.")

    # ------------------------------------------------------------------
    # Cruce CANAL contra `ventas` (Bsale no tiene concepto de "canal de
    # venta" propio -- es una categorización interna de Kaltemp que solo
    # vive en `ventas`). VENDEDOR ya NO se cruza acá: viene directo de
    # Bsale (expand=sellers) arriba, con cobertura del 100% del período
    # auditado, a diferencia de este cruce por documento que depende de
    # que `ventas` tenga sincronizada la misma ventana de fechas.
    # ------------------------------------------------------------------
    con_lookup = duckdb.connect(DB_PATH, read_only=True)
    try:
        filas_ventas = con_lookup.execute("""
            SELECT
                regexp_extract(NUMERO_DOCUMENTO, '(\\d+)', 1) AS num_limpio,
                UPPER(TIPO_DOCUMENTO) AS tipo_doc,
                ANY_VALUE(CANAL) AS canal
            FROM ventas
            WHERE NUMERO_DOCUMENTO IS NOT NULL AND TRIM(NUMERO_DOCUMENTO) != ''
            GROUP BY 1, 2
        """).fetchall()
    finally:
        con_lookup.close()

    canal_por_doc = {}
    for num_limpio, tipo_doc, canal in filas_ventas:
        if not num_limpio:
            continue
        bucket = "BOLETA" if "BOLETA" in (tipo_doc or "") else ("FACTURA" if "FACTURA" in (tipo_doc or "") else None)
        if bucket is None:
            continue
        canal_por_doc[(num_limpio, bucket)] = canal or ""

    sin_match_canal = 0
    excluidos_servicio_tecnico = 0

    # Canales excluidos a propósito de este módulo (decisión validada con
    # William): SERVICIO TÉCNICO nunca genera guía de despacho (evidencia
    # real: 45/45 documentos del canal marcados "pendiente", 0 despachados
    # -- es un canal de servicios, no de envío de mercadería, así que
    # contarlo como "pendiente por despachar" es ruido, no una alerta
    # operativa real). Los demás canales dudosos (SHOWROOM, OFICINA,
    # DISTRIBUIDORES, INMOBILIARIAS) quedan visibles: la cobertura de CANAL
    # todavía es parcial (~27%, limitada por la ventana de `ventas`) y no
    # hay evidencia suficiente para excluirlos sin arriesgar falsos negativos.
    CANALES_EXCLUIDOS = {"SERVICIO TÉCNICO", "SERVICIO TECNICO"}

    filas = []
    for d in docs_auditoria:
        canal = canal_por_doc.get((d["numero"], d["tipo_bucket"]))
        if canal is None:
            sin_match_canal += 1
            canal = ""
        if canal.upper() in CANALES_EXCLUIDOS:
            excluidos_servicio_tecnico += 1
            continue
        filas.append((
            f"Doc. N° {d['numero']}",
            d["cliente"],
            d["emision"],
            d["monto"],
            d["estado"],
            d["motivo"],
            d["vendedor"],
            canal,
            d["bodega"],
        ))
    if docs_auditoria:
        con_vendedor = sum(1 for d in docs_auditoria if d["vendedor"] != "Sin vendedor")
        print(f"[{datetime.now()}] VENDEDOR resuelto directo de Bsale: {con_vendedor}/{len(docs_auditoria)} documentos.")
        print(f"[{datetime.now()}] Cruce CANAL contra `ventas`: {len(docs_auditoria) - sin_match_canal}/{len(docs_auditoria)} "
              f"documentos resueltos ({sin_match_canal} sin match -- probablemente fuera del rango "
              f"sincronizado en `ventas` o con documento anulado).")
        print(f"[{datetime.now()}] Excluidos por ser canal SERVICIO TÉCNICO: {excluidos_servicio_tecnico} documentos "
              f"(no se guardan en pendientes_despacho).")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS pendientes_despacho (
                DOCUMENTO VARCHAR, CLIENTE VARCHAR, FECHA_EMISION TIMESTAMP,
                MONTO DOUBLE, ESTADO VARCHAR, MOTIVO VARCHAR,
                VENDEDOR VARCHAR, CANAL VARCHAR, BODEGA VARCHAR
            )
        """)
        # Defensivo: si la tabla ya existía de una corrida anterior a este
        # cambio (sin estas columnas), se agregan sin perder datos.
        columnas_existentes = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'pendientes_despacho'"
            ).fetchall()
        }
        if "VENDEDOR" not in columnas_existentes:
            con.execute("ALTER TABLE pendientes_despacho ADD COLUMN VENDEDOR VARCHAR")
        if "CANAL" not in columnas_existentes:
            con.execute("ALTER TABLE pendientes_despacho ADD COLUMN CANAL VARCHAR")
        if "BODEGA" not in columnas_existentes:
            con.execute("ALTER TABLE pendientes_despacho ADD COLUMN BODEGA VARCHAR")

        con.execute("DELETE FROM pendientes_despacho")
        con.executemany(
            """INSERT INTO pendientes_despacho
               (DOCUMENTO, CLIENTE, FECHA_EMISION, MONTO, ESTADO, MOTIVO, VENDEDOR, CANAL, BODEGA)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas,
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["pendientes_despacho", datetime.now(timezone.utc)],
        )
        con.commit()
        print(f"[{datetime.now()}] ✅ pendientes_despacho actualizada ({len(filas)} filas)")
    finally:
        con.close()


if __name__ == "__main__":
    sync_pendientes_despacho()