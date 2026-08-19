# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_notas_credito.py
"""
sync_notas_credito.py — Puebla `notas_credito_desfase` en kaltemp_matrix.duckdb.

HALLAZGO CLAVE (resuelve la duda que el propio app.py dejaba pendiente en
un comentario: "pendiente de confirmar en qué campo vive la fecha de
caída real"): la documentación oficial de /v1/documents.json confirma
que el campo `rcofDate` es exactamente eso -- "fecha de envío RCOF"
(Registro de Compras y Ventas). Es decir:
    FECHA_EMISION = document.emissionDate
    FECHA_CAIDA   = document.rcofDate

Fuente API:
  GET /v1/returns.json?expand=[credit_note,reference_document,office]
      -> cada devolución trae el id de la nota de crédito generada
         (credit_note.id) y el documento original devuelto, ya
         expandido en reference_document (number, ted, document_type, etc.)

AGREGADO (02-ago-2026): además de la fecha de desfase, ahora también se
resuelve y guarda DOCUMENTO_REFERENCIA -- el label "BOLETA N° 37573" /
"FACTURA N° 19805" del documento ORIGINAL que fue devuelto/anulado por
esta nota de crédito, en el mismo formato que usa DOCUMENTO en
`pendientes_despacho_docs`. Esto permite que
/api/pendientes-despacho-documentos excluya boletas/facturas que ya
tienen una nota de crédito asociada.

CORREGIDO (02-ago-2026, 2do intento): el primer intento buscaba
document_type/documentTypeId directamente en reference_document -- Bsale
nunca lo expone ahí. Se cambió a extraer el codeSii desde el tag <TD> del
campo `ted` (timbre electrónico), que SÍ viene resuelto en el expand para
la gran mayoría de los casos (~93%, confirmado con diagnóstico real).

CORREGIDO (02-ago-2026, 3er intento): el enfoque de `ted` solo cubre
~93% de los casos -- el ~7% restante (confirmado con diagnóstico real
contra la Nota de Crédito N° 4304 / Boleta N° 37573) trae `"ted": null`
explícito en la respuesta de Bsale, aunque el documento sí fue procesado
correctamente por el SII. Para esos casos SÍ viene disponible
`document_type.id`, así que ahora se usa como respaldo: se resuelve
codeSii vía un mapa document_type_id -> codeSii (una sola llamada a
document_types.json al inicio del script, no por cada nota de crédito).
Con `ted` como método principal (sin llamada extra) y `document_type`
como respaldo (con un mapa ya cacheado), se cubre prácticamente el 100%
de los casos sin hacer ningún GET adicional por nota de crédito.

AGREGADO (02-ago-2026, 4to cambio): columna VENDEDOR -- confirmado real
que la vista (CreditNotesView.tsx) ya esperaba este campo, pero nunca se
capturaba ni se exponía, así que TODAS las filas mostraban "Sin
vendedor". `sellers` no viene incluido en el expand de /v1/returns.json
(ni anidado bajo credit_note), así que ahora se hace SIEMPRE un GET
puntual a /documents/{credit_note_id}.json con expand=[sellers] -- esto
reemplaza la lógica anterior de "solo pedir de refuerzo si faltan
emissionDate/rcofDate", que ahora siempre se ejecuta (1 llamada extra por
nota de crédito). Sube el tiempo de corrida, pero es la única forma
confiable de tener vendedor sin adivinar.

AGREGADO (02-ago-2026, 5to cambio, a pedido de William):
1. Ventana de fecha: antes se procesaba TODA la historia de notas de
   crédito (desde 2016). Ahora se filtra por FECHA_EMISION >= NC_FECHA_DESDE
   (default 2026-07-01) -- reduce el volumen de datos guardado en la tabla.
2. Columna DESCRIPCION_PRODUCTO: se agrega "details" al expand del GET
   puntual (junto con sellers) y se toma la descripción de la(s)
   variante(s) de la nota de crédito -- si tiene más de una línea, se unen
   con "; ".

CORREGIDO (02-ago-2026, 6to cambio -- BUG REAL, confirmado con corrida
real que se quedó 22 minutos "sin avanzar"): el filtro de fecha del punto
1 de arriba se aplicaba DESPUÉS del GET puntual caro (expand=[sellers,
details]) a cada nota de crédito. Como /v1/returns.json devuelve las
notas en orden cronológico ascendente y el historial arranca en 2016, el
script pagaba el GET caro para ~4.400 notas históricas SOLO para
descartarlas después al llegar a la ventana de julio 2026 -- ~22 minutos
perdidos. Ahora el filtro se aplica ANTES, usando el emissionDate que ya
viene incluido en el credit_note del propio expand de returns.json (sin
costo extra) -- solo se paga el GET caro para las notas que SÍ están
dentro de la ventana. También se agregó un contador de progreso
(`revisadas`) que no depende del filtro, para que nunca vuelva a parecer
"colgado" cuando en realidad está descartando historial en silencio.

Uso:
    export BSALE_ACCESS_TOKEN=...
    export DUCKDB_PATH=/ruta/a/kaltemp_matrix.duckdb
    export NC_DIAS_DESFASE_ALERTA=1   # opcional, default 1 día
    export NC_FECHA_DESDE=2026-07-01  # opcional, default 2026-07-01
    python sync_notas_credito.py

AGREGADO (02-ago-2026, 7mo cambio, aclarado con William tras confusión de
conceptos): Bsale distingue 3 fechas distintas en un mismo documento --
confirmado real con la Nota de Crédito N° 4678, cuyo PDF muestra:
    "Documento emitido con fecha 02/07/2026" -> emissionDate
    "Generado el 06/07/2026 04:57 PM"         -> generationDate
Es decir, el documento se CREÓ en Bsale el 06/07 pero se declaró con
fecha de emisión (backdateada, para efectos contables/SII) el 02/07.
Antes "FECHA CREACIÓN" en la UI mostraba emissionDate -- confuso, porque
esa no es la fecha en la que realmente se creó el documento. Ahora:
    GENERACION_DATE = document.generationDate -> "Fecha Creación" (cuándo
                       se hizo realmente en Bsale)
    FECHA_EMISION    = document.emissionDate   -> "Fecha Impacto" (la
                       fecha declarada/backdateada que cuenta para el SII)
    FECHA_CAIDA       = document.rcofDate       -> se mantiene igual, para
                       el cálculo de DIAS_DESFASE (emisión vs registro RCOF)

CORREGIDO (19-ago-2026, bug real confirmado junto con el mismo bug en
sync_ga4_kaltemp.py -- ver hallazgo en sync_admin.py): el guardado en
DuckDB hacía DROP TABLE + CREATE TABLE completo, usando SOLO las notas
de crédito de la ventana [fecha_desde, hoy] recién consultada. El botón
"Actualizar Ahora (últimos 30 días)" del panel web ("Motor de
Actualización") le pasa dias_atras=30 a esta función igual que a
cualquier otra que acepte ese parámetro -- así que borraba TODA la tabla
y la dejaba solo con notas de crédito de los últimos 30 días. La razón
original del DROP+CREATE (comentario más abajo) era una migración de
esquema puntual que ya ocurrió -- ahora se usa CREATE TABLE IF NOT
EXISTS + DELETE del rango [fecha_desde, hoy] + INSERT, igual que ya
corrige este mismo problema en sync_temperaturas.py: la ventana
consultada se refresca, el resto del histórico queda intacto.
"""
import os
import re
import sys
import duckdb
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
DIAS_ALERTA = int(os.getenv("NC_DIAS_DESFASE_ALERTA", "1"))
# Ventana de fecha (a pedido de William, 02-ago-2026): solo notas de
# crédito emitidas desde esta fecha en adelante.
FECHA_DESDE_STR = os.getenv("NC_FECHA_DESDE", "2026-07-01")

# Mismo criterio que sync_pendientes_documentos.py: solo Boleta y Factura
# cuentan como "documento de venta" pendiente/anulable; se identifican por
# codeSii (fijo entre cuentas Bsale), nunca por documentTypeId (varía).
CODESII_BOLETA = 39
CODESII_FACTURA = 33
CODESII_A_TIPO = {CODESII_BOLETA: "BOLETA", CODESII_FACTURA: "FACTURA"}

# El timbre electrónico SII (campo `ted`) trae el tag <TD>NN</TD> con el
# codeSii real del documento -- confirmado con diagnóstico real. Método
# principal: no requiere ninguna llamada API adicional.
_TED_TD_RE = re.compile(r"<TD>(\d+)</TD>")


def _fecha(ts) -> datetime | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _mapa_codesii_por_document_type_id() -> dict[int, int]:
    """
    document_type.id -> codeSii. Se usa como RESPALDO cuando `ted` viene
    null (confirmado real: ~7% de los casos, aunque el documento sí fue
    procesado por el SII). Una sola llamada a document_types.json por
    corrida completa, no por cada nota de crédito.
    """
    mapa = {}
    for dt in bsale_get_all("document_types.json"):
        code = dt.get("codeSii")
        if code is None:
            continue
        try:
            mapa[int(dt["id"])] = int(code)
        except (TypeError, ValueError):
            continue
    return mapa


def _resolver_documento_referencia(ref_doc: dict | None, mapa_codesii_doctype: dict) -> str | None:
    """
    A partir del `reference_document` (ya expandido) de una devolución,
    arma el label "BOLETA N° 37573" / "FACTURA N° 19805" del documento
    original.

    Método principal: extraer el codeSii del tag <TD> en `ted`.
    Respaldo (cuando `ted` es null/vacío, ~7% de los casos observados):
    resolver codeSii vía document_type.id contra el mapa ya cacheado.
    """
    if not isinstance(ref_doc, dict):
        return None

    numero = ref_doc.get("number")
    if numero is None:
        return None

    codesii = None

    ted = ref_doc.get("ted") or ""
    match = _TED_TD_RE.search(ted)
    if match:
        codesii = int(match.group(1))

    if codesii is None:
        doctype_obj = ref_doc.get("document_type")
        doctype_id = doctype_obj.get("id") if isinstance(doctype_obj, dict) else None
        if doctype_id is not None:
            try:
                codesii = mapa_codesii_doctype.get(int(doctype_id))
            except (TypeError, ValueError):
                codesii = None

    if codesii is None:
        return None

    tipo = CODESII_A_TIPO.get(codesii)
    if not tipo:
        return None  # documento referenciado no es Boleta ni Factura

    return f"{tipo} N° {numero}"


def sync_notas_credito(dias_atras: int = None, progress_callback=None):
    """
    dias_atras (agregado 11-ago-2026, para conectar el campo de 'días'
    del modal de sync a este paso): si se pasa, la ventana se calcula
    como hoy menos esos días, con prioridad sobre NC_FECHA_DESDE. Antes
    esta función no aceptaba ningún parámetro -- el mecanismo genérico
    de sync_admin.py ya intentaba pasarle dias_atras, pero como la firma
    no lo aceptaba, caía en silencio al fallback sin días (usando
    siempre el default fijo del .env). progress_callback no se usa acá
    todavía (el bucle de este script no reporta progreso incremental),
    se acepta solo para no romper si sync_admin.py lo pasa.
    """
    if dias_atras is not None:
        fecha_desde_dt = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        print(f"[{datetime.now()}] Ventana: últimos {dias_atras} días (desde {fecha_desde_dt.date()})")
    else:
        fecha_desde_dt = datetime.strptime(FECHA_DESDE_STR, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(f"[{datetime.now()}] Ventana: desde {FECHA_DESDE_STR} (NC_FECHA_DESDE)")

    print(f"[{datetime.now()}] Cargando mapa document_type -> codeSii (respaldo)...")
    mapa_codesii_doctype = _mapa_codesii_por_document_type_id()
    print(f"  {len(mapa_codesii_doctype)} tipos de documento mapeados")

    print(f"[{datetime.now()}] Sync notas_credito_desfase: leyendo devoluciones...")
    filas = []
    revisadas = 0
    descartadas_por_fecha = 0
    procesadas = 0
    con_referencia = 0
    via_ted = 0
    via_doctype = 0

    for devolucion in bsale_get_all(
        "returns.json", params={"expand": "[credit_note,reference_document,office]"}
    ):
        revisadas += 1
        if revisadas % 200 == 0:
            print(f"  {revisadas} devoluciones revisadas ({procesadas} guardadas, "
                  f"{descartadas_por_fecha} descartadas por fecha)...")

        credit_note = devolucion.get("credit_note")
        if not credit_note or not credit_note.get("id"):
            continue  # devolución sin nota de crédito electrónica asociada

        cn_id = credit_note["id"]

        # Filtro de fecha BARATO primero (a pedido de William, corregido
        # 02-ago-2026): si el propio expand de returns.json ya trae
        # emissionDate en credit_note (confirmado que pasa casi siempre),
        # se descarta ACÁ, SIN gastar el GET puntual caro. Antes se hacía
        # el GET completo (expand=[sellers,details]) para las ~4.400 notas
        # de crédito históricas ANTES de descartarlas -- ~22 minutos
        # perdidos en notas de 2016-2025 que igual se iban a botar.
        emision_rapida = _fecha(credit_note.get("emissionDate"))
        if emision_rapida and emision_rapida.date() < fecha_desde_dt.date():
            descartadas_por_fecha += 1
            continue

        # Solo se llega acá para notas de crédito DENTRO de la ventana (o
        # en el raro caso de que el expand no haya traído emissionDate) --
        # ahora sí vale la pena pagar el GET completo.
        doc = bsale_get_one(f"documents/{cn_id}.json", params={"expand": "[sellers,details]"})

        emision = _fecha(doc.get("emissionDate"))
        caida = _fecha(doc.get("rcofDate"))
        generacion = _fecha(doc.get("generationDate"))
        if not emision or not caida:
            continue

        # Segundo chequeo (defensivo): por si el emissionDate rápido no
        # estaba disponible antes y recién ahora se puede filtrar.
        if emision.date() < fecha_desde_dt.date():
            descartadas_por_fecha += 1
            continue

        dias_desfase = (caida.date() - emision.date()).days
        cliente = devolucion.get("client", {}).get("company") if isinstance(devolucion.get("client"), dict) else None

        sellers_obj = doc.get("sellers")
        nombres_vendedores = []
        if isinstance(sellers_obj, dict):
            for s in sellers_obj.get("items", []):
                nombre = f"{s.get('firstName', '')} {s.get('lastName', '')}".strip()
                if nombre:
                    nombres_vendedores.append(nombre)
        vendedor = ", ".join(nombres_vendedores) if nombres_vendedores else "Sin vendedor"

        details_obj = doc.get("details")
        descripciones = []
        if isinstance(details_obj, dict):
            for linea in details_obj.get("items", []):
                variant = linea.get("variant")
                desc = (variant.get("description") if isinstance(variant, dict) else None) or linea.get("note")
                if desc:
                    descripciones.append(desc)
        descripcion_producto = "; ".join(dict.fromkeys(descripciones)) if descripciones else None

        ref_doc = devolucion.get("reference_document")
        documento_referencia = _resolver_documento_referencia(ref_doc, mapa_codesii_doctype)
        if documento_referencia:
            con_referencia += 1
            if isinstance(ref_doc, dict) and _TED_TD_RE.search(ref_doc.get("ted") or ""):
                via_ted += 1
            else:
                via_doctype += 1

        filas.append((
            f"Nota de Crédito N° {doc.get('number', cn_id)}",
            documento_referencia,
            cliente or "Sin cliente",
            vendedor,
            descripcion_producto,
            # .replace(tzinfo=None): CRÍTICO (02-ago-2026, bug real
            # confirmado y reproducido) -- DuckDB convierte silenciosamente
            # cualquier datetime con tzinfo a la zona horaria DEL SISTEMA
            # OPERATIVO antes de guardarlo en una columna TIMESTAMP (que es
            # "naive"). En una máquina en Chile (UTC-4), esto resta 4 horas
            # y puede correr la fecha un día completo hacia atrás -- se
            # confirmó real: Bsale mostraba "02/07/2026" y la app guardaba
            # "2026-07-01T20:00:00". Quitar tzinfo ACÁ (dejando los valores
            # de reloj ya calculados en UTC) evita que DuckDB reinterprete
            # la hora.
            emision.replace(tzinfo=None),
            caida.replace(tzinfo=None),
            generacion.replace(tzinfo=None) if generacion else None,
            dias_desfase,
            float(doc.get("totalAmount", devolucion.get("amount", 0)) or 0),
            dias_desfase > DIAS_ALERTA,
        ))
        procesadas += 1
        if procesadas % 100 == 0:
            print(f"  {procesadas} notas de crédito procesadas...")

    print(f"[{datetime.now()}] {revisadas} devoluciones revisadas en total "
          f"({descartadas_por_fecha} descartadas por estar antes de {fecha_desde_dt.date()})")
    print(f"[{datetime.now()}] {len(filas)} notas de crédito con fecha RCOF resuelta "
          f"({con_referencia} con documento original identificado: {via_ted} vía ted, {via_doctype} vía document_type)")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        # CORREGIDO (19-ago-2026): antes era DROP TABLE + CREATE TABLE
        # completo en cada corrida (la razón original era una migración
        # de esquema puntual -- columna DOCUMENTO_REFERENCIA nueva -- que
        # ya ocurrió hace tiempo). Eso hacía que pedir una ventana chica
        # (dias_atras=30, ej. desde "Actualizar Ahora" del panel web)
        # borrara TODA la tabla y la dejara solo con notas de crédito de
        # los últimos 30 días. Ahora se crea la tabla solo si no existe, y
        # se borra/reinserta SOLO el rango [fecha_desde, hoy] que
        # realmente se volvió a consultar -- el resto del histórico queda
        # intacto sin importar qué tan chico sea dias_atras.
        con.execute("""
            CREATE TABLE IF NOT EXISTS notas_credito_desfase (
                DOCUMENTO VARCHAR, DOCUMENTO_REFERENCIA VARCHAR, CLIENTE VARCHAR,
                VENDEDOR VARCHAR, DESCRIPCION_PRODUCTO VARCHAR,
                FECHA_EMISION TIMESTAMP, FECHA_CAIDA TIMESTAMP, GENERACION_DATE TIMESTAMP,
                DIAS_DESFASE INTEGER, MONTO DOUBLE, ALERTA BOOLEAN
            )
        """)
        con.execute(
            "DELETE FROM notas_credito_desfase WHERE FECHA_EMISION >= ?",
            [fecha_desde_dt.replace(tzinfo=None)],
        )
        con.executemany(
            """INSERT INTO notas_credito_desfase
               (DOCUMENTO, DOCUMENTO_REFERENCIA, CLIENTE, VENDEDOR, DESCRIPCION_PRODUCTO,
                FECHA_EMISION, FECHA_CAIDA, GENERACION_DATE, DIAS_DESFASE, MONTO, ALERTA)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas,
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["notas_credito_desfase", datetime.now(timezone.utc)],
        )
        con.commit()
        print(f"[{datetime.now()}] ✅ notas_credito_desfase actualizada ({len(filas)} filas, ventana desde {fecha_desde_dt.date()})")
    finally:
        con.close()


if __name__ == "__main__":
    sync_notas_credito()