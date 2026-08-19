# ============================================================
# ARCHIVO: sync_ventas.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_ventas.py
# (Respaldar el archivo actual antes de reemplazar: Copy-Item sync_ventas.py sync_ventas.py.bak)
# ============================================================

"""
sync/sync_ventas.py — Puebla la tabla `ventas`, base de la que dependen
el Módulo Principal (/api/channels, /api/tendencia-mensual,
/api/acumulado-ytd), Stock (categoría/producto por SKU) y KPIs de
Logística ("Cobro Real Bsale").

Port de actualizacion_incremental_automatica() / cargar_datos_bsale_dinamico()
/ aplicar_matriz_financiera() del Código_V1.txt (Streamlit), con 2 cambios
de alcance confirmados con William (03-ago-2026):

  1. SIN dependencia de CSV (Precios.csv / "SKU _ COSTO - Costo.csv") --
     ya no se usan. El costo sale directo de Bsale (costo real de
     despacho si el documento ya tiene guía, o costo actual de la
     variante como respaldo).

  2. OMITIDA la sección de "Consumos Fulfillment" (Mercado Libre / Paris
     / Ripley / D2C vía bodega FULL) -- esa sección dependía 100% de
     Precios.csv para valorizar cada línea (los consumos de bodega no
     traen precio de venta). Sin CSV no hay forma de valorizarlos hoy.
     Si esos canales siguen activos, hace falta definir una fuente de
     precio nueva antes de poder reincorporarlos -- tarea aparte.

CATEGORÍA (corregido 05-ago-2026, confirmado con William): el campo
`category` del detalle de cada línea de venta en Bsale casi nunca viene
poblado (~96% de las ventas caían en "Sin Categoría Mapeada"). Ahora la
categoría se resuelve SIEMPRE cruzando SKU_BSALE contra la tabla
`sku_maestro` (que sync_sku_maestro.py llena desde el catálogo real de
productos de Bsale: /v1/product_types.json + /v1/products.json). Por
eso sync_sku_maestro DEBE correr antes que este script en sync_master.py
(ya estaba así, no requirió cambio de orden).

Fuentes que SÍ quedan activas:
  - Ventas directas de Bsale (documents.json, expand sellers/details/client)
  - Venta real de Falabella Fulfillment (Seller Center API, GetOrders +
    GetOrderItems) -- ya reemplazaba a los consumos Bsale para ese canal
    en el código original, sin depender de CSV.

Debe correr PRIMERO en sync_master.py (stock_bsale y otros módulos
heredan categoría/producto desde `ventas`), pero DESPUÉS de sync_sku_maestro.
"""
import os
import sys
import time
import datetime
import hashlib
import hmac
import urllib.parse
import requests
import pandas as pd
import duckdb
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
# categorias_db.py vive en backend/ (un nivel arriba de backend/sync/) --
# hay que agregarlo a sys.path para poder importarlo sin importar desde
# qué carpeta se invoque `python sync/sync_ventas.py`.
sys.path.insert(0, os.path.dirname(_AQUI))
# .env raíz: credenciales (Bsale, Falabella, Envíame, Cliengo, Shopify).
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
# backend/.env: config específica del backend (DUCKDB_PATH, ALLOWED_ORIGINS).
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN")
FALABELLA_API_KEY = os.getenv("FALABELLA_API_KEY")
FALABELLA_USER = os.getenv("FALABELLA_USER")

# Misma variable que usa db.py -- así todos los scripts escriben al mismo
# archivo que la app realmente lee.
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
TZ_CHILE = ZoneInfo("America/Santiago")

MAPEO_CANALES = {
    "ALEJANDRO ALARCON": "OFICINA", "ALEXIS CORNEJO": "SHOWROOM", "CAROLINA MALDONADO": "OFICINA",
    "CORNERSHOP": "OTROS", "D2C": "D2C", "ESTEBAN CARRASCO": "SERVICIO TÉCNICO", "FALABELLA": "FALABELLA",
    "FRANCISCO GRANESE": "SHOWROOM", "GUSTAVO BOETSCH": "OFICINA", "ITAU": "OTROS", "JAIME CASES": "SHOWROOM",
    "KAROLINA VASQUEZ": "OFICINA", "LINIO": "OTROS", "LUKAS MONTALDO": "SHOWROOM", "MANUEL EYZAGUIRRE": "OFICINA",
    "MAXIMILIANO DIAZ": "INMOBILIARIAS", "MERCADOLIBRE": "MERCADOLIBRE", "PARIS": "PARIS", "RAFAEL ESCOBAR": "INMOBILIARIAS",
    "RIPLEY": "RIPLEY", "SANDRA AVENDAÑO": "SHOWROOM", "SEBASTIÁN ESPINOSA": "OFICINA", "SEBASTIAN ESPINOSA": "OFICINA",
    "SODIMAC": "OTROS", "TOMPALMER": "D2C", "WILLIAM GARRIDO": "D2C", "ANDESGEAR": "OTROS", "WALMART MKP": "WALMART MKP",
    "STEFANY ROSALES": "D2C", "KALTEMP HITES": "HITES", "BARBARA CABELLO": "OTROS", "LUIS BAEZA": "INMOBILIARIAS",
    "SOLEDAD PASCUAL": "SHOWROOM", "DANIELA VALLADARES": "DISTRIBUIDORES", "MANUEL ERRAZURIZ": "TOM PALMER",
    "MAXIMILIANO DIAZ - INMOBILIARIA": "INMOBILIARIAS", "DIANA LEON": "SHOWROOM", "PABLO OPAZO": "DISTRIBUIDORES",
    "CATALINA POBLETE": "DISTRIBUIDORES", "DAVID LEON": "SERVICIO TÉCNICO", "KALTEMP FALABELLA": "FALABELLA",
    "KALTEMP FALABELLA 2": "FALABELLA", "KALTEMP MERCADOLIBRE": "MERCADOLIBRE", "KALTEMP PARIS": "PARIS", "KALTEMP RIPLEY": "RIPLEY",
    # FIX (17-ago-2026, a pedido de William): estos 3 vendedores existen
    # tal cual en Bsale (confirmado contra la base real) pero no tenían
    # una entrada EXACTA en este diccionario, así que el .get(..., "OTROS")
    # de más abajo los mandaba todos a "OTROS" en silencio -- ninguno era
    # un error de tipeo en Bsale, era que acá faltaba la clave.
    "KALTEMP ANDESGEAR": "OTROS",  # CORREGIDO (17-ago-2026, a pedido de William): va a OTROS, no a D2C -- el módulo D2C ya lo cuenta aparte por VENDEDOR, independiente de este CANAL
    "PARIS FULLFILMENT": "PARIS",  # fulfillment de Paris, mismo canal que "KALTEMP PARIS"
    "KALTEMP ITAU": "OTROS",  # ya cae en OTROS por defecto, se deja explícito para que no dependa del fallback
    "KALTEMP SODIMAC": "OTROS",  # ídem
}


def _bsale_headers():
    return {"Content-Type": "application/json", "access_token": BSALE_TOKEN}


# ---------------------------------------------------------------------
# COSTO -- directo de Bsale, sin CSV. Documento ya despachado -> costo
# real de esa guía. No despachado todavía -> costo actual de la variante.
# ---------------------------------------------------------------------
def obtener_costo_real_documento(document_id, headers):
    """Costo real de despacho por SKU para un documento (boleta/factura)
    de Bsale. Solo existe si el documento YA fue despachado (tiene guía)."""
    try:
        resp = requests.get(
            "https://api.bsale.cl/v1/documents/costs.json",
            headers=headers, params={"documentid": document_id}, timeout=15,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        costos = {}
        for item in (data.get("cost_detail") or []):
            variante = item.get("variant") or {}
            shipping = item.get("shipping_detail") or {}
            sku = str(variante.get("code", "")).strip().upper()
            if sku:
                costos[sku] = costos.get(sku, 0) + (shipping.get("variantTotalCost") or 0)
        return costos
    except Exception:
        return {}


def obtener_costo_actual_variante(variant_id, headers, cache_costo_actual):
    """Último costo INGRESADO de una variante en Bsale (no promedio) --
    respaldo cuando el documento aún no tiene guía / costo real asignado.
    Cacheado por variant_id para no repetir la llamada en la misma corrida."""
    if variant_id in cache_costo_actual:
        return cache_costo_actual[variant_id]
    costo = 0.0
    try:
        resp = requests.get(
            f"https://api.bsale.cl/v1/variants/{variant_id}/costs.json",
            headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            historial = data.get("history") or []
            if historial:
                ultima_recepcion = max(historial, key=lambda h: h.get("admissionDate", 0))
                costo = float(ultima_recepcion.get("cost", 0) or 0)
            else:
                costo = float(data.get("averageCost", 0) or 0)
    except Exception:
        pass
    cache_costo_actual[variant_id] = costo
    return costo


def resolver_variant_id_por_sku(sku, headers, cache_variant_id):
    """NUEVO (03-ago-2026): Falabella entrega el SKU pero no el variant_id
    de Bsale -- necesario para poder consultar obtener_costo_actual_variante()
    y así tener costo 'directo de Bsale' también en las líneas de Falabella
    (que no tienen documento Bsale asociado, por lo tanto tampoco costo real
    de despacho vía obtener_costo_real_documento)."""
    sku_norm = str(sku).strip().upper()
    if not sku_norm:
        return None
    if sku_norm in cache_variant_id:
        return cache_variant_id[sku_norm]
    variant_id = None
    try:
        resp = requests.get(
            "https://api.bsale.cl/v1/variants.json",
            headers=headers, params={"code": sku_norm, "limit": 1}, timeout=10,
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                variant_id = items[0].get("id")
    except Exception:
        pass
    cache_variant_id[sku_norm] = variant_id
    return variant_id


# ---------------------------------------------------------------------
# FALABELLA SELLER CENTER: venta real de fulfillment (fuente de verdad,
# reemplaza los consumos de bodega -- Bsale nunca se entera de una
# cancelación/devolución hecha en el marketplace).
# ---------------------------------------------------------------------
def _falabella_timestamp():
    ts = datetime.datetime.now(TZ_CHILE)
    t = ts.strftime("%Y-%m-%dT%H:%M:%S%z")
    return f"{t[:-2]}:{t[-2:]}"


def _falabella_firmar(api_key, params):
    concatenated = urllib.parse.urlencode(sorted(params.items()))
    return hmac.new(api_key.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha256).hexdigest()


def obtener_ventas_falabella_api(f_inicio, f_fin, headers_bsale, cache_variant_id, cache_costo_actual):
    """
    ⚠️ Limitación conocida (heredada del código original): solo revisa
    pedidos CREADOS en [f_inicio, f_fin]. Un pedido creado antes que se
    cancela recién ahora no se detecta acá.
    """
    if not FALABELLA_API_KEY or not FALABELLA_USER:
        return pd.DataFrame(), {}

    ESTADOS_NO_VALIDOS = {"canceled", "cancelled", "returned"}
    diag = {
        "pedidos_totales": 0, "items_totales": 0, "excl_shipping_type": 0,
        "excl_estado": 0, "incluidos": 0,
    }

    pedidos = []
    limit, offset = 100, 0
    while True:
        params = {
            "Action": "GetOrders", "Format": "JSON", "Timestamp": _falabella_timestamp(),
            "UserID": FALABELLA_USER, "Version": "1.0",
            "CreatedAfter": f_inicio.strftime("%Y-%m-%dT00:00:00-04:00"),
            "CreatedBefore": f_fin.strftime("%Y-%m-%dT23:59:59-04:00"),
            "Limit": str(limit), "Offset": str(offset),
        }
        params["Signature"] = _falabella_firmar(FALABELLA_API_KEY, params)
        try:
            resp = requests.get("https://sellercenter-api.falabella.com", params=params, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
            orders = data.get("SuccessResponse", {}).get("Body", {}).get("Orders", {}).get("Order", [])
            if isinstance(orders, dict):
                orders = [orders]
            if not orders:
                break
            pedidos.extend(orders)
            if len(orders) < limit:
                break
            offset += limit
        except Exception:
            break

    diag["pedidos_totales"] = len(pedidos)
    if not pedidos:
        return pd.DataFrame(), diag

    all_rows = []
    for pedido in pedidos:
        order_id = pedido.get("OrderId")
        order_number = pedido.get("OrderNumber", order_id)
        cliente_nombre = f"{pedido.get('CustomerFirstName', '')} {pedido.get('CustomerLastName', '')}".strip().upper() or "CLIENTE FALABELLA"
        if not order_id:
            continue

        params = {
            "Action": "GetOrderItems", "Format": "JSON", "Timestamp": _falabella_timestamp(),
            "UserID": FALABELLA_USER, "Version": "1.0", "OrderId": str(order_id),
        }
        params["Signature"] = _falabella_firmar(FALABELLA_API_KEY, params)

        try:
            resp = requests.get("https://sellercenter-api.falabella.com", params=params, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("SuccessResponse", {}).get("Body", {}).get("OrderItems", {}).get("OrderItem", [])
            if isinstance(items, dict):
                items = [items]

            for it in items:
                diag["items_totales"] += 1
                tipo_envio = str(it.get("ShippingType", "")).lower().strip()
                if tipo_envio != "fulfillment":
                    diag["excl_shipping_type"] += 1
                    continue

                estado_item = str(it.get("Status", "")).lower().strip()
                if estado_item in ESTADOS_NO_VALIDOS:
                    diag["excl_estado"] += 1
                    continue

                try:
                    pagado = float(it.get("PaidPrice", 0) or 0)
                except Exception:
                    pagado = 0.0
                bruto = pagado  # NMV Falabella no incluye envío
                neto = bruto / 1.19

                try:
                    f_obj = datetime.datetime.strptime(it.get("CreatedAt", ""), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    f_obj = datetime.datetime.now()

                nombre_producto = str(it.get("Name", "PRODUCTO FALABELLA"))
                nombre_producto = (
                    nombre_producto.replace("&eacute;", "é").replace("&aacute;", "á")
                    .replace("&iacute;", "í").replace("&oacute;", "ó").replace("&uacute;", "ú")
                    .replace("&ntilde;", "ñ").replace("&Ntilde;", "Ñ").upper()
                )
                sku_item = str(it.get("Sku", "")).strip().upper()

                # Costo directo de Bsale por SKU (Falabella no trae costo).
                costo_total_linea = 0.0
                v_id = resolver_variant_id_por_sku(sku_item, headers_bsale, cache_variant_id)
                if v_id:
                    costo_total_linea = obtener_costo_actual_variante(v_id, headers_bsale, cache_costo_actual)

                diag["incluidos"] += 1
                all_rows.append({
                    "DOCUMENTO": f"FALABELLA N° {order_number}",
                    "PRODUCTO": nombre_producto, "SKU_BSALE": sku_item, "CANTIDAD": 1,
                    "NETO_TOTAL": neto, "BRUTO_TOTAL": bruto, "CANAL": "FALABELLA",
                    "VENDEDOR": "KALTEMP FALABELLA", "CLIENTE": cliente_nombre,
                    "CATEGORIA_BSALE": "Marketplace Fulfillment", "FECHA_OBJ": f_obj,
                    "ORIGEN": "FALABELLA_API", "COSTO_TOTAL_BSALE": costo_total_linea,
                    "TIPO_DOCUMENTO": "PEDIDO FALABELLA FULFILLMENT", "NUMERO_DOCUMENTO": order_number,
                    "SUCURSAL": "FALABELLA",
                })
            time.sleep(0.15)  # límite Falabella: 30 requests / 3 segundos
        except Exception:
            continue

    return pd.DataFrame(all_rows), diag


# ---------------------------------------------------------------------
# VENTAS DIRECTAS DE BSALE
# ---------------------------------------------------------------------
def cargar_datos_bsale_dinamico(f_inicio, f_fin, progress_callback=None):
    if not BSALE_TOKEN:
        raise RuntimeError("Falta BSALE_TOKEN en el .env de la raíz del proyecto")

    headers = _bsale_headers()
    api_inicio = f_inicio - datetime.timedelta(days=1)
    api_fin = f_fin + datetime.timedelta(days=1)
    start_dt = datetime.datetime.combine(api_inicio, datetime.time.min).replace(tzinfo=TZ_CHILE)
    end_dt = datetime.datetime.combine(api_fin, datetime.time.max).replace(tzinfo=TZ_CHILE)
    start_ts, end_ts = int(start_dt.timestamp()), int(end_dt.timestamp())

    all_rows = []
    limit, offset = 50, 0
    pagina_actual = 1
    cache_costo_actual_bsale = {}
    cache_variant_id = {}

    def _report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    # === 1. Ventas normales de Bsale ===
    while True:
        _report(min(2 + pagina_actual * 2, 40), f"🛒 Descargando Bsale (lote {pagina_actual})...")
        pagina_actual += 1

        url = f"https://api.bsale.cl/v1/documents.json?emissiondaterange=[{start_ts},{end_ts}]&limit={limit}&offset={offset}&expand=[document_type,details,client,sellers]"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            for doc in items:
                try:
                    n_tipo_node = doc.get("document_type") or {}
                    n_tipo = str(n_tipo_node.get("name", "")).upper()
                    if any(f in n_tipo for f in ("PROFORMA", "COMPRA", "GUIA", "GUÍA", "COTIZACION", "COTIZACIÓN", "NULA", "ORDEN", "PEDIDO", "ANTICIPO")):
                        continue

                    mult = -1 if "NOTA DE CR" in n_tipo else 1
                    f_obj = datetime.datetime.fromtimestamp(doc.get("emissionDate", 0), tz=datetime.timezone.utc).replace(tzinfo=None)
                    if not (f_inicio <= f_obj.date() <= f_fin):
                        continue

                    doc_nro = f"{n_tipo} N° {doc.get('number','')}"
                    numero_documento_raw = doc.get("number", "")
                    office_node_doc = doc.get("office") or {}
                    sucursal_doc = str(office_node_doc.get("description") or office_node_doc.get("name") or "").strip()

                    c_obj = doc.get("client") or {}
                    cliente_clean = f"{str(c_obj.get('firstName', '')).strip()} {str(c_obj.get('lastName', '')).strip()}".strip() or str(c_obj.get('company', '')).strip() or "CLIENTE GENERAL"

                    sellers_obj = doc.get("sellers") or {}
                    sellers_items = sellers_obj.get("items") or []
                    nombres = [f"{str(u.get('firstName', '')).strip()} {str(u.get('lastName', '')).strip()}".strip().upper() for u in sellers_items if u]
                    vendedor_upper = " ".join((", ".join(nombres) if nombres else "SIN VENDEDOR").upper().split())
                    canal = MAPEO_CANALES.get(vendedor_upper, "OTROS")

                    doc_total_real = float(doc.get("totalAmount", 0)) * mult
                    details_obj = doc.get("details") or {}
                    details_items = details_obj.get("items") or []
                    sum_details_bruto = sum(float(item.get("totalAmount", 0)) * mult for item in details_items if item)
                    factor = doc_total_real / sum_details_bruto if sum_details_bruto != 0 and doc_total_real != 0 else (0.0 if doc_total_real == 0 else 1.0)

                    costos_reales_doc = obtener_costo_real_documento(doc.get("id"), headers)
                    time.sleep(0.08)

                    for item in details_items:
                        if not item:
                            continue
                        cantidad = int(item.get("quantity", 1)) * mult
                        bruto_linea_base = float(item.get("totalAmount", 0)) * mult
                        if bruto_linea_base == 0 and float(item.get("netUnitValue", 0)) > 0:
                            bruto_linea_base = float(item.get("netUnitValue", 0)) * cantidad * 1.19
                        bruto_linea_final = bruto_linea_base * factor
                        neto_linea_final = bruto_linea_final / 1.19

                        cat_obj = item.get("category") or {}
                        cat = cat_obj.get("name", "Sin Categoría Mapeada") if isinstance(cat_obj, dict) else "Sin Categoría Mapeada"

                        variant_node = item.get("variant") or {}
                        sku_item = str(variant_node.get("code", "")).strip().upper()
                        v_id_item = str(variant_node.get("id", ""))

                        if sku_item and sku_item in costos_reales_doc:
                            costo_total_linea = costos_reales_doc[sku_item]
                        elif v_id_item:
                            costo_total_linea = obtener_costo_actual_variante(v_id_item, headers, cache_costo_actual_bsale) * abs(cantidad)
                        else:
                            costo_total_linea = 0.0

                        all_rows.append({
                            "DOCUMENTO": doc_nro,
                            "PRODUCTO": str(variant_node.get("description", item.get("comment", "PRODUCTO"))).upper(),
                            "SKU_BSALE": sku_item, "CANTIDAD": cantidad,
                            "NETO_TOTAL": neto_linea_final, "BRUTO_TOTAL": bruto_linea_final, "CANAL": canal,
                            "VENDEDOR": vendedor_upper, "CLIENTE": cliente_clean.upper(), "CATEGORIA_BSALE": cat,
                            "FECHA_OBJ": f_obj, "ORIGEN": "BSALE", "COSTO_TOTAL_BSALE": costo_total_linea,
                            "TIPO_DOCUMENTO": n_tipo, "NUMERO_DOCUMENTO": numero_documento_raw, "SUCURSAL": sucursal_doc,
                        })
                except Exception:
                    continue

            offset += limit
            time.sleep(0.15)
        except Exception:
            break

    # === 2. Venta real de Falabella Fulfillment ===
    _report(45, "📦 Descargando ventas Falabella (Seller Center)...")
    df_falabella, diag_falabella = obtener_ventas_falabella_api(f_inicio, f_fin, headers, cache_variant_id, cache_costo_actual_bsale)
    if not df_falabella.empty:
        all_rows.extend(df_falabella.to_dict("records"))
    _report(55, f"📦 Falabella: {diag_falabella.get('incluidos', 0)} líneas incluidas.")

    return pd.DataFrame(all_rows)


def _cargar_mapa_categorias_sku() -> dict:
    """
    Carga {SKU: CATEGORIA}, combinando dos fuentes con prioridad:

    1. categorias_manual (kaltemp_categorias.db) -- la clasificación real
       del negocio, cargada por importar_categorias_manual.py o asignada
       desde la alerta "SKU sin categoría" en la app. Esta GANA siempre
       que exista, porque Bsale no tiene categorización útil hoy (casi
       todo el catálogo está en "Sin Tipo").
    2. sku_maestro (kaltemp_matrix.duckdb) -- lo que trae Bsale, usado
       solo como respaldo para los SKUs que categorias_manual no cubre.

    Confirmado con William (05-ago-2026).
    """
    mapa: dict = {}

    # 1. sku_maestro primero (respaldo, se sobrescribe con la manual después)
    try:
        with duckdb.connect(DB_FILE, read_only=True) as con:
            existe = con.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'sku_maestro'"
            ).fetchone()
            if not existe:
                print("⚠️ Tabla sku_maestro no existe todavía -- corre sync_sku_maestro.py primero.")
            else:
                filas = con.execute("SELECT SKU, CATEGORIA FROM sku_maestro").fetchall()
                mapa.update({str(sku).strip().upper(): cat for sku, cat in filas if sku})
    except Exception as e:
        print(f"⚠️ No se pudo cargar sku_maestro para mapear categorías: {e}")

    # 2. categorias_manual (gana por sobre sku_maestro)
    try:
        from categorias_db import get_categorias_connection, init_categorias_db
        init_categorias_db()
        with get_categorias_connection() as con:
            filas = con.execute("SELECT sku, categoria FROM categorias_manual").fetchall()
            n_manual = 0
            for row in filas:
                sku = str(row["sku"]).strip().upper()
                if sku:
                    mapa[sku] = row["categoria"]
                    n_manual += 1
            if n_manual:
                print(f"ℹ️ {n_manual} categorías manuales cargadas (tienen prioridad sobre Bsale).")
    except Exception as e:
        print(f"⚠️ No se pudo cargar categorias_manual: {e}")

    return mapa


def _es_glosa_no_producto(sku: str, producto: str) -> bool:
    """
    Detecta líneas de venta que NO son productos reales del catálogo:
    boletas/facturas de Servicio Técnico emitidas con glosa libre en Bsale
    (reparaciones, repuestos genéricos, despachos) en vez de un SKU real.

    Confirmado con William (05-ago-2026): estas SÍ deben contar en la
    VENTA (monto en $), pero NO en el margen/contribución de NINGÚN
    módulo -- se marcan acá con ES_GLOSA_SERVICIO=True en vez de
    eliminarse, para que cada router pueda excluirlas solo del cálculo
    de margen (CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END),
    sin perder el monto de venta.

    Se marca si:
      - El SKU es puramente numérico (glosa auto-generada por Bsale, ej.
        "1785188194192870" -- no es un SKU real del catálogo Kaltemp,
        que siempre usa prefijo de letras: KLGE, KLES, KLBC, KLST...), o
      - El SKU o el nombre del producto contiene "REPARACIÓN", "REPUESTO"
        o "DESPACHO" (ej. SKU_BSALE="DESPACHOCENTRY" sin nombre asociado,
        o un SKU real cuyo nombre sí trae esas palabras).

    Repuestos con SKU real del catálogo (prefijo KLST, ej. "ANODO DE
    SACRIFICIO", "RESISTENCIA 1500W", "FILTROS IR04") NO se marcan --
    son inventario real con costo real, y ni su SKU ni su nombre llevan
    esas palabras.
    """
    sku_limpio = str(sku or "").strip()
    if sku_limpio.isdigit() and len(sku_limpio) >= 5:
        return True
    texto_a_revisar = f"{sku_limpio} {str(producto or '').strip()}".upper()
    palabras_excluidas = ("REPARACION", "REPARACIÓN", "REPUESTO", "DESPACHO")
    return any(p in texto_a_revisar for p in palabras_excluidas)


def aplicar_matriz_financiera(df_origen, mapa_categorias_sku: dict = None):
    """
    Simplificado (03-ago-2026): SIN merge contra CSV de costos/categoría.
    COSTO_TOTAL_BSALE ya viene resuelto directo de Bsale desde
    cargar_datos_bsale_dinamico() -- acá solo se consolida a los nombres
    finales de columna y se calcula CONTRIBUCION.

    CATEGORIA (05-ago-2026): se resuelve SIEMPRE cruzando SKU_BSALE contra
    `sku_maestro` (mapa_categorias_sku), no contra el campo `category` del
    detalle de venta de Bsale -- ese campo casi nunca viene poblado.

    ES_GLOSA_SERVICIO (05-ago-2026): ver _es_glosa_no_producto() -- estas
    líneas SÍ quedan en `ventas` (para no perder el monto de venta), pero
    marcadas para que cada router las excluya del cálculo de margen.
    """
    if df_origen.empty:
        return df_origen

    mapa_categorias_sku = mapa_categorias_sku or {}

    df = df_origen.copy()
    df["SKU_BSALE"] = df["SKU_BSALE"].astype(str).str.strip().str.upper()

    df["ES_GLOSA_SERVICIO"] = df.apply(
        lambda r: _es_glosa_no_producto(r["SKU_BSALE"], r.get("PRODUCTO", "")), axis=1
    )
    n_marcadas = int(df["ES_GLOSA_SERVICIO"].sum())
    if n_marcadas:
        print(f"ℹ️ {n_marcadas} líneas marcadas como servicio técnico sin SKU real "
              f"(reparación/repuesto genérico/despacho) -- cuentan en venta, excluidas del margen.")

    costo_bsale = pd.to_numeric(df.get("COSTO_TOTAL_BSALE", 0.0), errors="coerce").fillna(0.0)
    cantidad = df["CANTIDAD"]
    neto_t = df["NETO_TOTAL"]
    signo = neto_t.apply(lambda x: -1 if x < 0 else 1)
    df["COSTO_TOTAL"] = costo_bsale * signo
    df["CONTRIBUCION"] = df["NETO_TOTAL"] - df["COSTO_TOTAL"]
    df["CATEGORIA"] = df["SKU_BSALE"].map(mapa_categorias_sku).fillna("Sin Categoría Mapeada")

    cols_finales = [
        "DOCUMENTO", "PRODUCTO", "SKU_BSALE", "CANTIDAD",
        "NETO_TOTAL", "BRUTO_TOTAL", "COSTO_TOTAL", "CONTRIBUCION",
        "CANAL", "VENDEDOR", "CLIENTE", "CATEGORIA", "FECHA_OBJ", "ORIGEN",
        "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO", "SUCURSAL", "ES_GLOSA_SERVICIO",
    ]
    for c in cols_finales:
        if c not in df.columns:
            if c in ("CANTIDAD", "NETO_TOTAL", "BRUTO_TOTAL", "COSTO_TOTAL", "CONTRIBUCION"):
                df[c] = 0.0
            elif c == "ES_GLOSA_SERVICIO":
                df[c] = False
            else:
                df[c] = ""

    return df[cols_finales]


def sync_ventas(dias_atras: int = 3, progress_callback=None):
    """
    Punto de entrada para sync_master.py. dias_atras=3 por defecto (igual
    de espíritu al "ayer/hoy" original, con un día extra de margen para
    correcciones tardías) -- para la PRIMERA carga histórica completa,
    usar sync_ventas_historico_resumible() en vez de esta, que escribe
    todo en un solo golpe al final y puede perder horas de descarga si
    se corta a mitad de camino.
    """
    def _report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    hoy = datetime.date.today()
    f_inicio = hoy - datetime.timedelta(days=dias_atras)
    f_fin = hoy

    _report(1, f"🚀 Sincronizando ventas ({f_inicio} → {f_fin})...")
    df_raw = cargar_datos_bsale_dinamico(f_inicio, f_fin, progress_callback)
    if df_raw.empty:
        _report(100, "⚠️ No se encontraron ventas en el rango.")
        return

    mapa_categorias_sku = _cargar_mapa_categorias_sku()
    df_proc = aplicar_matriz_financiera(df_raw, mapa_categorias_sku)
    _report(90, f"💾 Escribiendo {len(df_proc)} líneas en 'ventas'...")

    _escribir_ventas_en_duckdb(df_proc, f_inicio, f_fin)

    _report(100, f"✨ Listo: {len(df_proc)} líneas de venta sincronizadas.")


def _escribir_ventas_en_duckdb(df_proc, f_inicio, f_fin):
    """Extraído de sync_ventas() para reutilizarlo también desde la
    versión por ventanas -- misma lógica de CREATE TABLE/ALTER/DELETE+
    INSERT de siempre, sin cambios."""
    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                DOCUMENTO VARCHAR, PRODUCTO VARCHAR, SKU_BSALE VARCHAR, CANTIDAD INTEGER,
                NETO_TOTAL DOUBLE, BRUTO_TOTAL DOUBLE, COSTO_TOTAL DOUBLE, CONTRIBUCION DOUBLE,
                CANAL VARCHAR, VENDEDOR VARCHAR, CLIENTE VARCHAR, CATEGORIA VARCHAR, FECHA_OBJ TIMESTAMP,
                ORIGEN VARCHAR, TIPO_DOCUMENTO VARCHAR, NUMERO_DOCUMENTO VARCHAR, SUCURSAL VARCHAR,
                ES_GLOSA_SERVICIO BOOLEAN
            )
        """)
        columnas_existentes = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'ventas'"
            ).fetchall()
        }
        if "ES_GLOSA_SERVICIO" not in columnas_existentes:
            con.execute("ALTER TABLE ventas ADD COLUMN ES_GLOSA_SERVICIO BOOLEAN DEFAULT FALSE")

        con.execute("DELETE FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?", [f_inicio, f_fin])
        con.register("df_proc_tmp", df_proc)
        con.execute("""
            INSERT INTO ventas (DOCUMENTO, PRODUCTO, SKU_BSALE, CANTIDAD, NETO_TOTAL, BRUTO_TOTAL,
                                 COSTO_TOTAL, CONTRIBUCION, CANAL, VENDEDOR, CLIENTE, CATEGORIA,
                                 FECHA_OBJ, ORIGEN, TIPO_DOCUMENTO, NUMERO_DOCUMENTO, SUCURSAL,
                                 ES_GLOSA_SERVICIO)
            SELECT DOCUMENTO, PRODUCTO, SKU_BSALE, CANTIDAD, NETO_TOTAL, BRUTO_TOTAL,
                   COSTO_TOTAL, CONTRIBUCION, CANAL, VENDEDOR, CLIENTE, CATEGORIA,
                   FECHA_OBJ, ORIGEN, TIPO_DOCUMENTO, NUMERO_DOCUMENTO, SUCURSAL,
                   ES_GLOSA_SERVICIO
            FROM df_proc_tmp
        """)


# ---------------------------------------------------------------------
# CARGA HISTÓRICA RESUMIBLE (agregado 10-ago-2026, a pedido de William)
# ---------------------------------------------------------------------
# sync_ventas() de arriba descarga TODO el rango pedido en memoria y
# recién escribe a DuckDB al final (90%) -- si se corta antes de eso
# (ej. uvicorn se reinicia por --reload al guardar un archivo), se
# pierde la descarga completa, sin importar si iba en el lote 300.
#
# Esta versión parte el rango en VENTANAS chicas (30 días por defecto).
# Cada ventana se descarga, procesa y ESCRIBE a DuckDB por separado --
# si se corta a mitad de una ventana, las ventanas anteriores ya están
# guardadas. Además guarda un CHECKPOINT (tabla sync_checkpoint) con la
# última ventana completada -- si se vuelve a lanzar, arranca desde ahí
# en vez de repetir desde el día 1.
def _leer_checkpoint(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS sync_checkpoint (
            proceso VARCHAR PRIMARY KEY,
            checkpoint_fecha DATE,
            actualizado_en TIMESTAMP
        )
    """)
    row = con.execute(
        "SELECT checkpoint_fecha FROM sync_checkpoint WHERE proceso = 'ventas_historico'"
    ).fetchone()
    return row[0] if row else None


def _guardar_checkpoint(con, fecha):
    con.execute("""
        CREATE TABLE IF NOT EXISTS sync_checkpoint (
            proceso VARCHAR PRIMARY KEY,
            checkpoint_fecha DATE,
            actualizado_en TIMESTAMP
        )
    """)
    con.execute(
        "INSERT OR REPLACE INTO sync_checkpoint (proceso, checkpoint_fecha, actualizado_en) VALUES (?, ?, ?)",
        ["ventas_historico", fecha, datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)],
    )


def reiniciar_checkpoint_ventas():
    """Borra el checkpoint -- usar si se quiere forzar que la próxima
    corrida arranque desde el día 1 otra vez (ej. si cambiaste el
    número total de días pedidos a uno mayor al ya cubierto)."""
    with duckdb.connect(DB_FILE) as con:
        con.execute("CREATE TABLE IF NOT EXISTS sync_checkpoint (proceso VARCHAR PRIMARY KEY, checkpoint_fecha DATE, actualizado_en TIMESTAMP)")
        con.execute("DELETE FROM sync_checkpoint WHERE proceso = 'ventas_historico'")


def sync_ventas_historico_resumible(dias_atras: int = 1825, ventana_dias: int = 30, progress_callback=None,
                                      forzar_reproceso: bool = False):
    """Versión por ventanas + checkpoint de la carga histórica de ventas.
    Reintentable: si se corta a mitad de camino, la próxima llamada con
    los mismos (o más) dias_atras retoma justo después del checkpoint.

    forzar_reproceso (agregado 11-ago-2026, a pedido de William): por
    default (False) el checkpoint puede hacer que un rango ya cubierto
    se salte por completo ("Ya estaba al día") -- útil para NO repetir
    una carga histórica gigante ya terminada, pero un problema real si
    lo que buscás es capturar cambios que pasaron en Bsale DESPUÉS de
    la primera carga (una NC aplicada más tarde, un precio corregido,
    etc.) -- esos cambios nunca se reflejarían porque el rango se salta
    entero. Con forzar_reproceso=True se IGNORA el checkpoint para
    decidir si arrancar o no -- el rango pedido (los últimos
    `dias_atras` días) siempre se vuelve a descargar y reemplazar desde
    cero. El checkpoint se sigue guardando igual mientras corre, así que
    si esta corrida se corta a mitad de camino, una llamada posterior
    SIN forzar_reproceso todavía puede retomar desde ahí."""
    def _report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    hoy = datetime.date.today()
    rango_inicio = hoy - datetime.timedelta(days=dias_atras)
    rango_fin = hoy

    if forzar_reproceso:
        ventana_inicio = rango_inicio
        _report(1, f"🔁 forzar_reproceso=True -- reprocesando {rango_inicio} → {rango_fin} desde cero, "
                    f"sin importar qué diga el checkpoint.")
    else:
        with duckdb.connect(DB_FILE) as con:
            checkpoint = _leer_checkpoint(con)

        if checkpoint and checkpoint >= rango_inicio:
            ventana_inicio = checkpoint + datetime.timedelta(days=1)
            _report(1, f"↩️ Retomando desde checkpoint: {ventana_inicio} (ya cubierto hasta {checkpoint})")
        else:
            ventana_inicio = rango_inicio
            _report(1, f"🚀 Carga histórica de ventas desde cero: {rango_inicio} → {rango_fin}")

    if ventana_inicio > rango_fin:
        _report(100, "✅ Ya estaba al día -- nada nuevo que cargar en este rango.")
        return

    total_dias = (rango_fin - rango_inicio).days or 1
    mapa_categorias_sku = _cargar_mapa_categorias_sku()

    while ventana_inicio <= rango_fin:
        ventana_fin = min(ventana_inicio + datetime.timedelta(days=ventana_dias - 1), rango_fin)

        avance_dias = (ventana_inicio - rango_inicio).days
        pct = min(2 + int((avance_dias / total_dias) * 95), 97)
        _report(pct, f"📅 Ventana {ventana_inicio} → {ventana_fin}...")

        try:
            df_raw = cargar_datos_bsale_dinamico(ventana_inicio, ventana_fin, None)
            if not df_raw.empty:
                df_proc = aplicar_matriz_financiera(df_raw, mapa_categorias_sku)
                _escribir_ventas_en_duckdb(df_proc, ventana_inicio, ventana_fin)
                _report(pct, f"💾 Ventana {ventana_inicio} → {ventana_fin}: {len(df_proc)} líneas guardadas.")
            else:
                _report(pct, f"ℹ️ Ventana {ventana_inicio} → {ventana_fin}: sin ventas.")

            with duckdb.connect(DB_FILE) as con:
                _guardar_checkpoint(con, ventana_fin)

        except Exception as e:
            _report(pct, f"⚠️ Error en ventana {ventana_inicio}→{ventana_fin}: {e} -- se detiene acá, el checkpoint quedó en la última ventana OK.")
            raise

        ventana_inicio = ventana_fin + datetime.timedelta(days=1)

    _report(100, f"✨ Carga histórica de ventas completa: {rango_inicio} → {rango_fin}.")


if __name__ == "__main__":
    import sys
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    sync_ventas(dias_atras=dias)