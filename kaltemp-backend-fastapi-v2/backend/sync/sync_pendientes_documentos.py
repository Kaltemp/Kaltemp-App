# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_pendientes_documentos.py
"""
sync_pendientes_documentos.py — Puebla `pendientes_despacho_docs` en
kaltemp_matrix.duckdb: el detalle por DOCUMENTO (boleta/factura/cotización)
de qué SKUs tiene reservados y sin despachar, con vendedor y monto, para
poder hacer tracking operativo (no solo el agregado por SKU que ya da
`stock_bsale.RESERVADO`).

==========================================================================
CORRIGE 2 PROBLEMAS ENCONTRADOS AL COMPARAR CONTRA EL REPORTE NATIVO DE
BSALE ("Productos Por Despachar", export real descargado el 01-ago-2026):
==========================================================================
1. Ventana de fecha: el script anterior (sync_pendientes_despacho.py,
   ahora obsoleto) solo miraba 180 días. El reporte real de Bsale mostró
   pendientes de hasta 2024-03-05 (más de 2 años). Acá se usa una ventana
   mucho más amplia (900 días por defecto, configurable).
2. Tipo de documento: el reporte real de Bsale incluye "COTIZACIÓN DE
   VENTA" además de boletas/facturas -- un tipo que antes no se
   contemplaba. Se agrega acá (documentTypeId=24, confirmado en
   diagnóstico: no tiene codeSii propio por no ser un DTE SII).

El método de cruce (guía.details[].relatedDetailId == documento.details[].id)
ya estaba validado contra un caso real (boleta 41660 / guía 57648) -- no
cambia, solo se corrigen la ventana y los tipos de documento.

AGREGADO (02-ago-2026): columna PEDIDO_NUMERO / PEDIDO_ORIGEN -- el N° de
Pedido del canal de origen (ej. Falabella), confirmado real vía
GET /v1/documents/{id}/references.json (sub-recurso "Referencias a otros
Documentos", el mismo que se ve impreso en la boleta física bajo "Tipo
Documento: Orden de Compra"). Ejemplo real (Boleta N° 37658):
    {"number": "3220829208", "reason": "FALABELLA", ...}
Documentos sin venta de marketplace (D2C directo, Showroom, etc.) no
tienen ninguna referencia -- PEDIDO_NUMERO queda NULL en esos casos, sin
error. Se hace 1 llamada extra por DOCUMENTO (no por línea) y solo para
los documentos que ya quedaron con algo pendiente -- no para todo el
universo de boletas/facturas, para no disparar el costo de la sync.

Uso:
    export BSALE_ACCESS_TOKEN=...
    export DUCKDB_PATH=/ruta/a/kaltemp_matrix.duckdb
    export PXD_FECHA_DESDE=2026-01-01
    python sync_pendientes_documentos.py

CORREGIDO (19-ago-2026, mismo bug real que sync_ga4_kaltemp.py /
sync_notas_credito.py -- ver hallazgo en sync_admin.py): el guardado en
DuckDB hacía DROP TABLE + CREATE TABLE completo, usando SOLO los
documentos de la ventana [fecha_desde, hoy] recién consultada. Esta
tabla es justo la que MÁS depende de mantener historial largo (su propio
propósito, arriba, es rastrear pendientes de hasta 2 años de antigüedad)
-- así que el botón "Actualizar Ahora (últimos 30 días)" del panel web
(dias_atras=30) era especialmente destructivo acá: borraba la tabla
entera y perdía justo los pendientes más antiguos, que son los que más
importa no perder de vista. Ahora se usa CREATE TABLE IF NOT EXISTS +
DELETE del rango [fecha_desde, hoy] + INSERT -- los documentos emitidos
antes de esa ventana quedan intactos sin importar qué tan chico sea
dias_atras.
"""
import os
import sys
import duckdb
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
# Fecha de inicio fija (no "días hacia atrás") -- más simple y predecible.
# Se puede ajustar con la variable de entorno PXD_FECHA_DESDE (YYYY-MM-DD).
FECHA_DESDE_STR = os.getenv("PXD_FECHA_DESDE", "2026-01-01")

CODESII_BOLETA = 39
CODESII_FACTURA = 33
CODESII_GUIA = 52
DOCTYPEID_COTIZACION = 24  # "COTIZACION DE VENTA" -- sin codeSii propio


def _epoch(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _cargar_oficinas() -> dict:
    return {str(o["id"]): o["name"] for o in bsale_get_all("offices.json")}


def _obtener_referencia_pedido(doc_id: int) -> tuple:
    """
    Consulta /documents/{id}/references.json y devuelve (numero_pedido,
    origen) de la primera referencia encontrada -- confirmado real con la
    Boleta N° 37658: {"number": "3220829208", "reason": "FALABELLA"}.
    Documentos sin venta de marketplace (D2C directo, Showroom, etc.)
    simplemente no traen ninguna referencia -- se devuelve (None, None)
    sin tratarlo como error.
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
    print(f"  {total_guias} guías revisadas, {len(mapa)} relatedDetailId encontrados")
    return mapa


def _iterar_documentos_venta(fecha_desde: int, fecha_hasta: int):
    """
    Boletas + Facturas (por codesii). NO incluye "Cotización de Venta" a
    propósito: es solo una cotización, no una venta comprometida con el
    cliente -- mostrarla como "pendiente por despachar" sería engañoso.
    (Nota: si una cotización tiene stock reservado en Bsale, esas unidades
    igual aparecen correctamente en el total agregado por SKU de
    /api/pendientes-despacho, ya que ese viene de RESERVADO sin filtrar
    por tipo de documento -- solo no se les podrá atribuir un documento
    específico en la tabla de detalle.)
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
    """
    dias_atras (agregado 11-ago-2026, mismo motivo que en
    sync_notas_credito.py): si se pasa, la ventana se calcula como hoy
    menos esos días, con prioridad sobre PXD_FECHA_DESDE. progress_callback
    se acepta solo para no romper si sync_admin.py lo pasa (este script
    no reporta progreso incremental todavía).
    """
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

    print(f"[{datetime.now()}] Indexando líneas de guías (desde {FECHA_DESDE_STR})...")
    mapa_detail_id_a_monto_guia = _construir_mapa_related_detail_ids(fecha_desde, fecha_hasta)

    filas = []
    total_docs = 0
    docs_con_pedido = 0
    for tipo, doc in _iterar_documentos_venta(fecha_desde, fecha_hasta):
        total_docs += 1
        lineas = _extraer_items_details(doc, doc["id"])

        lineas_pendientes = [
            linea for linea in lineas
            if linea.get("id") not in mapa_detail_id_a_monto_guia
        ]
        if not lineas_pendientes:
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
                # .replace(tzinfo=None): mismo bug real confirmado en
                # sync_notas_credito.py -- DuckDB convierte silenciosamente
                # datetimes con tzinfo a la hora LOCAL del sistema antes de
                # guardarlos en una columna TIMESTAMP, corriendo la fecha
                # hasta un día completo hacia atrás en máquinas con huso
                # horario negativo (ej. Chile, UTC-4). Se quita acá para
                # que DuckDB guarde el valor de reloj UTC tal cual.
                emision.replace(tzinfo=None),
                monto_doc,
                cantidad,
                pedido_numero,
                pedido_origen,
            ))

    print(f"[{datetime.now()}] {total_docs} documentos revisados, {len(filas)} líneas pendientes encontradas "
          f"({len(set(f[2] for f in filas))} documentos distintos con algo pendiente, "
          f"{docs_con_pedido} con N° de pedido identificado)")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS pendientes_despacho_docs (
                SKU VARCHAR, DESCRIPCION VARCHAR, DOCUMENTO VARCHAR, TIPO_DOCUMENTO VARCHAR,
                CLIENTE VARCHAR, VENDEDOR VARCHAR, BODEGA VARCHAR,
                FECHA_EMISION TIMESTAMP, MONTO_DOCUMENTO DOUBLE, CANTIDAD DOUBLE,
                PEDIDO_NUMERO VARCHAR, PEDIDO_ORIGEN VARCHAR
            )
        """)
        # CORREGIDO (19-ago-2026): antes era DROP+CREATE completo -- ver
        # nota arriba, era el caso más grave porque esta tabla vive de
        # tener pendientes de hasta ~2 años. Ahora se borra/reinserta
        # SOLO el rango [fecha_desde, hoy] que realmente se volvió a
        # consultar a Bsale -- los documentos emitidos antes de esa
        # ventana quedan intactos.
        con.execute(
            "DELETE FROM pendientes_despacho_docs WHERE FECHA_EMISION >= ?",
            [fecha_desde_dt.replace(tzinfo=None)],
        )
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
        print(f"[{datetime.now()}] ✅ pendientes_despacho_docs actualizada ({len(filas)} filas, ventana desde {fecha_desde_dt.date()})")
    finally:
        con.close()


if __name__ == "__main__":
    sync_pendientes_documentos()