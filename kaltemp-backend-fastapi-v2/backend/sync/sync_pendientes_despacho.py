"""
sync_pendientes_documentos.py — Puebla `pendientes_despacho_docs` en
kaltemp_matrix.duckdb: el detalle por DOCUMENTO (boleta/factura)
de qué SKUs tiene reservados y sin despachar, con vendedor y monto, para
poder hacer tracking operativo.

==========================================================================
MÉTODO DE CRUCE Y FILTRADO (BSALE):
==========================================================================
- Guía de Despacho (codeSii=52): línea.relatedDetailId == doc.details[].id -> DESPACHADO
- Nota de Crédito (codeSii=61):  línea.relatedDetailId == doc.details[].id -> ANULADO/DEVUELTO

Si una línea de documento NO tiene Guía de Despacho Y NO tiene Nota de Crédito,
se considera PENDIENTE REAL de despacho.

Uso:
    export BSALE_ACCESS_TOKEN=...
    export DUCKDB_PATH=/ruta/a/kaltemp_matrix.duckdb
    export PXD_FECHA_DESDE=2026-01-01
    python sync/sync_pendientes_documentos.py
"""
import os
import sys
import duckdb
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
FECHA_DESDE_STR = os.getenv("PXD_FECHA_DESDE", "2026-01-01")

CODESII_BOLETA = 39
CODESII_FACTURA = 33
CODESII_GUIA = 52
CODESII_NOTA_CREDITO = 61  # Identifica Notas de Crédito en Bsale
DOCTYPEID_COTIZACION = 24  # "COTIZACION DE VENTA" -- sin codeSii propio


def _epoch(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _cargar_oficinas() -> dict:
    return {str(o["id"]): o["name"] for o in bsale_get_all("offices.json")}


def _obtener_referencia_pedido(doc_id: int) -> tuple:
    """
    Consulta /documents/{id}/references.json y devuelve (numero_pedido, origen).
    Ejemplo real (Boleta N° 37658): {"number": "3220829208", "reason": "FALABELLA"}.
    """
    try:
        referencias = list(bsale_get_all(f"documents/{doc_id}/references.json"))
    except Exception as e:
        print(f"    [aviso] no se pudo consultar references.json de doc {doc_id}: {e}")
        return None, None
    if not referencias:
        return None, None
    primera = referencias[0]
    return primera.get("number"), primera.get("reason")


def _extraer_items_details(doc: dict, doc_id: int) -> list:
    details = doc.get("details")
    if isinstance(details, dict):
        items = details.get("items", [])
        count = details.get("count", len(items))
        if items and len(items) >= count:
            return items
    elif isinstance(details, list) and details:
        return details
    return list(bsale_get_all(f"documents/{doc_id}/details.json"))


def _construir_mapa_related_detail_ids(fecha_desde: int, fecha_hasta: int) -> dict:
    """relatedDetailId -> totalAmount de la guía que despachó esa línea."""
    mapa = {}
    total_guias = 0
    for guia in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_GUIA,
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
            "expand": "[details]",
        },
    ):
        total_guias += 1
        items = guia.get("details")
        if isinstance(items, dict) and items.get("items"):
            lineas = items["items"]
        else:
            lineas = _extraer_items_details(guia, guia["id"])
        for linea in lineas:
            rid = linea.get("relatedDetailId")
            if rid:
                mapa[rid] = float(guia.get("totalAmount", 0) or 0)
        if total_guias % 500 == 0:
            print(f"  {total_guias} guías revisadas...")
    print(f"  {total_guias} guías revisadas, {len(mapa)} relatedDetailId en guías encontrados")
    return mapa


def _construir_mapa_nc_detail_ids(fecha_desde: int, fecha_hasta: int) -> set:
    """
    Construye un conjunto con todos los relatedDetailId referenciados por
    Notas de Crédito (codeSii=61). Si una línea de boleta/factura aparece acá,
    fue ANULADA/DEVUELTA y NO debe figurar como pendiente de despacho.
    """
    set_nc = set()
    total_ncs = 0
    for nc in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_NOTA_CREDITO,
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
            "expand": "[details]",
        },
    ):
        total_ncs += 1
        items = nc.get("details")
        if isinstance(items, dict) and items.get("items"):
            lineas = items["items"]
        else:
            lineas = _extraer_items_details(nc, nc["id"])
        for linea in lineas:
            rid = linea.get("relatedDetailId")
            if rid:
                set_nc.add(rid)
        if total_ncs % 500 == 0:
            print(f"  {total_ncs} Notas de Crédito revisadas...")
    print(f"  {total_ncs} Notas de Crédito revisadas, {len(set_nc)} líneas anuladas identificadas")
    return set_nc


def _iterar_documentos_venta(fecha_desde: int, fecha_hasta: int):
    """
    Boletas + Facturas (por codesii).
    """
    fuentes = [
        ("BOLETA", {"codesii": CODESII_BOLETA}),
        ("FACTURA", {"codesii": CODESII_FACTURA}),
    ]
    for tipo, filtro_extra in fuentes:
        print(f"[{datetime.now()}] Revisando documentos tipo {tipo}...")
        total = 0
        params = {
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
            "expand": "[client,details,sellers,office]",
            **filtro_extra,
        }
        for doc in bsale_get_all("documents.json", params=params):
            total += 1
            if total % 500 == 0:
                print(f"  {total} documentos {tipo} revisados...")
            yield tipo, doc


def sync_pendientes_documentos(dias_atras: int = None, progress_callback=None):
    if dias_atras is not None:
        fecha_desde_dt = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        print(f"[{datetime.now()}] Rango: últimos {dias_atras} días (desde {fecha_desde_dt.date()}) → hoy")
    else:
        fecha_desde_dt = datetime.strptime(FECHA_DESDE_STR, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(f"[{datetime.now()}] Rango: {FECHA_DESDE_STR} → hoy")
    fecha_desde = _epoch(fecha_desde_dt)
    fecha_hasta = _epoch(datetime.now(timezone.utc))

    print(f"[{datetime.now()}] Cargando mapa de oficinas/bodegas...")
    mapa_oficinas = _cargar_oficinas()
    print(f"  {len(mapa_oficinas)} oficinas encontradas")

    print(f"[{datetime.now()}] Indexando líneas de guías de despacho...")
    mapa_detail_id_a_monto_guia = _construir_mapa_related_detail_ids(fecha_desde, fecha_hasta)

    print(f"[{datetime.now()}] Indexando líneas de Notas de Crédito (anulaciones)...")
    set_lineas_anuladas_nc = _construir_mapa_nc_detail_ids(fecha_desde, fecha_hasta)

    filas = []
    total_docs = 0
    docs_con_pedido = 0
    docs_anulados_descartados = 0

    for tipo, doc in _iterar_documentos_venta(fecha_desde, fecha_hasta):
        total_docs += 1
        lineas = _extraer_items_details(doc, doc["id"])

        # Una línea está realmente pendiente si:
        # 1. NO tiene Guía de Despacho asociada
        # 2. NO fue anulada por Nota de Crédito
        lineas_pendientes = [
            linea for linea in lineas
            if linea.get("id") not in mapa_detail_id_a_monto_guia
            and linea.get("id") not in set_lineas_anuladas_nc
        ]

        if not lineas_pendientes:
            if lineas:
                docs_anulados_descartados += 1
            continue

        emision = datetime.fromtimestamp(doc["emissionDate"], tz=timezone.utc) if doc.get("emissionDate") else None
        if not emision:
            continue

        cliente_obj = doc.get("client")
        if isinstance(cliente_obj, dict):
            cliente = cliente_obj.get("company") or f"{cliente_obj.get('firstName', '')} {cliente_obj.get('lastName', '')}".strip()
        else:
            cliente = None

        sellers_obj = doc.get("sellers")
        nombres_vendedores = []
        if isinstance(sellers_obj, dict):
            for s in sellers_obj.get("items", []):
                nombre = f"{s.get('firstName', '')} {s.get('lastName', '')}".strip()
                if nombre:
                    nombres_vendedores.append(nombre)
        vendedor = ", ".join(nombres_vendedores) if nombres_vendedores else "Sin vendedor"

        office_obj = doc.get("office")
        office_id = str(office_obj.get("id")) if isinstance(office_obj, dict) else None
        bodega = mapa_oficinas.get(office_id, "Sin bodega") if office_id else "Sin bodega"

        monto_doc = float(doc.get("totalAmount", 0) or 0)
        documento_label = f"{tipo} N° {doc.get('number')}"

        pedido_numero, pedido_origen = _obtener_referencia_pedido(doc["id"])
        if pedido_numero:
            docs_con_pedido += 1
            if docs_con_pedido % 50 == 0:
                print(f"    {docs_con_pedido} documentos con N° de pedido identificado hasta ahora...")

        for linea in lineas_pendientes:
            variant = linea.get("variant")
            sku = variant.get("code") if isinstance(variant, dict) else None
            descripcion = (variant.get("description") if isinstance(variant, dict) else None) or linea.get("note")
            cantidad = float(linea.get("quantity", 0) or 0)

            filas.append((
                sku or "",
                descripcion or "",
                documento_label,
                tipo,
                cliente or "Sin cliente",
                vendedor,
                bodega,
                emision.replace(tzinfo=None),
                monto_doc,
                cantidad,
                pedido_numero,
                pedido_origen,
            ))

    print(f"[{datetime.now()}] {total_docs} documentos revisados, {len(filas)} líneas pendientes encontradas "
          f"({len(set(f[2] for f in filas))} documentos distintos con algo pendiente, "
          f"{docs_con_pedido} con N° de pedido, "
          f"{docs_anulados_descartados} documentos omitidos por estar completados/anulados por NC).")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        con.execute("DROP TABLE IF EXISTS pendientes_despacho_docs")
        con.execute("""
            CREATE TABLE pendientes_despacho_docs (
                SKU VARCHAR, DESCRIPCION VARCHAR, DOCUMENTO VARCHAR, TIPO_DOCUMENTO VARCHAR,
                CLIENTE VARCHAR, VENDEDOR VARCHAR, BODEGA VARCHAR,
                FECHA_EMISION TIMESTAMP, MONTO_DOCUMENTO DOUBLE, CANTIDAD DOUBLE,
                PEDIDO_NUMERO VARCHAR, PEDIDO_ORIGEN VARCHAR
            )
        """)
        con.executemany(
            """INSERT INTO pendientes_despacho_docs
               (SKU, DESCRIPCION, DOCUMENTO, TIPO_DOCUMENTO, CLIENTE, VENDEDOR, BODEGA,
                FECHA_EMISION, MONTO_DOCUMENTO, CANTIDAD, PEDIDO_NUMERO, PEDIDO_ORIGEN)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas,
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["pendientes_despacho_docs", datetime.now(timezone.utc)],
        )
        con.commit()
        print(f"[{datetime.now()}] ✅ pendientes_despacho_docs actualizada ({len(filas)} filas)")
    finally:
        con.close()


if __name__ == "__main__":
    sync_pendientes_documentos()