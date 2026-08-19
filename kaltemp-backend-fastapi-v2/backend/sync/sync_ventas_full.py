# ============================================================
# ARCHIVO: sync_ventas_full.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_ventas_full.py
# ============================================================

"""
sync/sync_ventas_full.py — Puebla `ventas` con las ventas de fulfillment
de marketplaces que NO son Falabella (Mercado Libre, Paris, Ripley), leyendo
los consumos de stock de la bodega "Full MKP" en Bsale
(GET /v1/stocks/consumptions.json, officeid de esa bodega).

Es la pieza que sync_ventas.py dejó explícitamente OMITIDA el 03-ago-2026
("Consumos Fulfillment... tarea aparte" -- ver docstring de sync_ventas.py),
ahora que SÍ hay una fuente de precio confiable: el campo `note` de cada
consumo, con formato:

    "Consumo por pedido {Canal} #{numero_pedido} precio unitario ${precio}"

Confirmado con William (18-ago-2026) revisando datos reales de la bodega
"Full MKP" (id=2): SOLO cuentan como venta los consumos que traen el
paquete completo (fecha, canal, precio, número de pedido, SKU) -- un
consumo sin "precio unitario $X" en el note es un ajuste manual de
inventario (hecho por un usuario), no una venta, y se ignora.

FALABELLA -- excluido a propósito: también aparecen consumos de Falabella
en esta misma bodega (con el mismo formato de note), pero Falabella ya
se sincroniza completo y en tiempo real vía FALABELLA_API (Seller Center,
ver sync_ventas.py::obtener_ventas_falabella_api). Si este script también
escribiera esos consumos, cada venta de Falabella quedaría contada DOS
VECES en `ventas`. Por eso cualquier consumo cuyo canal (extraído del
note) sea "Falabella" se ignora acá.

ORIGEN escrito: 'BSALE_FULL' -- exactamente el que ya espera
routers/fulfillment.py (_ORIGENES_FULL = ("BSALE_FULL", "FALABELLA_API")),
así que ese módulo empieza a mostrar datos reales sin tocarlo.

Nota sobre paginación: la API de Bsale ignora silenciosamente el parámetro
de rango de fecha para este endpoint (confirmado empíricamente) y limita
a 50 resultados por página -- así que este script trae TODOS los consumos
de la bodega en cada corrida (son ~400-1000, liviano) y filtra la fecha
del lado del cliente. Si el volumen crece mucho en el futuro y esto se
vuelve lento, se puede optimizar recordando el último id ya procesado.

REVISADO (19-ago-2026, William + Claude, auditoría del panel web "Motor
de Actualización"/sync_admin.py): a diferencia de ga4_kaltemp/
ga4_tompalmer/notas_credito/falabella_estados_pedido/
pendientes_despacho_docs/abandoned_checkouts (todos corregidos ese mismo
día por el mismo motivo), este script YA escribía de forma segura desde
el principio: el DELETE de _escribir_en_duckdb() está acotado por
ORIGEN='BSALE_FULL' + rango de fecha, nunca toca el resto de `ventas`
(BSALE, FALABELLA_API, etc.) ni borra fuera de la ventana consultada. No
requirió ningún cambio.
"""
import os
import re
import sys
import datetime
import requests
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_AQUI))  # para poder importar categorias_db
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE_URL = "https://api.bsale.cl/v1"
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

ORIGEN_TAG = "BSALE_FULL"
NOMBRE_BODEGA_FULL = "FULL MKP"  # nombre exacto confirmado via API (offices.json, id=2)

# Canales de marketplace que este sync SÍ procesa. "Falabella" se excluye
# a propósito -- ver docstring arriba.
CANAL_MAP = {
    "MERCADO LIBRE": "MERCADOLIBRE",
    "MERCADOLIBRE": "MERCADOLIBRE",
    "PARIS": "PARIS",
    "RIPLEY": "RIPLEY",
}

PATRON_NOTE = re.compile(
    r"Consumo por pedido\s+(.+?)\s+#(\S+)\s+precio unitario\s*\$\s*([\d.,]+)", re.IGNORECASE
)


def _bsale_headers():
    return HEADERS


def _limpiar_precio(precio_raw: str) -> float:
    """El note trae el precio como entero plano (ej. '89990'), pero por si
    algún día viene con separador de miles, se limpia igual que el resto
    del sistema: punto = miles, coma = decimal."""
    s = str(precio_raw).strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    else:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _obtener_office_id_full_mkp(headers) -> int | None:
    try:
        resp = requests.get(f"{BASE_URL}/offices.json", headers=headers, params={"limit": 50}, timeout=20)
        if resp.status_code != 200:
            return None
        for o in resp.json().get("items", []):
            if str(o.get("name", "")).strip().upper() == NOMBRE_BODEGA_FULL:
                return o.get("id")
    except Exception:
        pass
    return None


def _traer_todos_los_consumos(office_id, headers):
    """Trae TODOS los consumos de la bodega (la API no soporta filtrar por
    fecha de forma confiable para este endpoint -- confirmado 18-ago-2026).
    Limit real de Bsale: 50 por página, aunque se pida más."""
    todos = []
    limit, offset = 50, 0
    while True:
        resp = requests.get(
            f"{BASE_URL}/stocks/consumptions.json",
            params={"officeid": office_id, "limit": limit, "offset": offset},
            headers=headers, timeout=30,
        )
        if resp.status_code != 200:
            break
        items = resp.json().get("items", [])
        if not items:
            break
        todos.extend(items)
        offset += limit
        if len(items) < limit:
            break
        if offset > 20000:  # freno de seguridad
            break
    return todos


def _obtener_detalle_consumo(consumo, headers):
    href = (consumo.get("details") or {}).get("href")
    if not href:
        href = f"{BASE_URL}/stocks/consumptions/{consumo['id']}/details.json"
    try:
        resp = requests.get(href, headers=headers, params={"expand": "[variant]"}, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("items", [])
    except Exception:
        pass
    return []


def _cargar_mapa_categorias_sku() -> dict:
    """Mismo mecanismo que sync_ventas.py -- categorias_manual gana sobre
    sku_maestro."""
    mapa: dict = {}
    try:
        with duckdb.connect(DB_FILE, read_only=True) as con:
            existe = con.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'sku_maestro'"
            ).fetchone()
            if existe:
                filas = con.execute("SELECT SKU, CATEGORIA FROM sku_maestro").fetchall()
                mapa.update({str(sku).strip().upper(): cat for sku, cat in filas if sku})
    except Exception as e:
        print(f"⚠️ No se pudo cargar sku_maestro: {e}")

    try:
        from categorias_db import get_categorias_connection, init_categorias_db
        init_categorias_db()
        with get_categorias_connection() as con:
            filas = con.execute("SELECT sku, categoria FROM categorias_manual").fetchall()
            for row in filas:
                sku = str(row["sku"]).strip().upper()
                if sku:
                    mapa[sku] = row["categoria"]
    except Exception as e:
        print(f"⚠️ No se pudo cargar categorias_manual: {e}")

    return mapa


def _obtener_costo_actual_variante(variant_id, headers, cache):
    if variant_id in cache:
        return cache[variant_id]
    costo = 0.0
    try:
        resp = requests.get(f"{BASE_URL}/variants/{variant_id}/costs.json", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            historial = data.get("history") or []
            if historial:
                ultima = max(historial, key=lambda h: h.get("admissionDate", 0))
                costo = float(ultima.get("cost", 0) or 0)
            else:
                costo = float(data.get("averageCost", 0) or 0)
    except Exception:
        pass
    cache[variant_id] = costo
    return costo


def _procesar_consumos(consumos, headers, mapa_categorias, f_inicio, f_fin, progress_callback=None):
    """Filtra por fecha + patrón de note, excluye Falabella, agrupa el
    detalle por SKU (un consumo puede traer varias líneas con el MISMO
    SKU repetido -- se suman), y arma las filas finales para `ventas`."""
    filas = []
    cache_costo = {}
    ignorados_falabella = 0
    ignorados_sin_precio = 0
    ignorados_multi_sku = 0
    ignorados_fuera_rango = 0

    for i, consumo in enumerate(consumos):
        note = (consumo.get("note", "") or "").strip()
        m = PATRON_NOTE.search(note)
        if not m:
            ignorados_sin_precio += 1
            continue

        canal_raw = m.group(1).strip().upper()
        pedido = m.group(2).strip()
        precio_unitario = _limpiar_precio(m.group(3))

        if canal_raw == "FALABELLA":
            ignorados_falabella += 1
            continue

        canal = CANAL_MAP.get(canal_raw)
        if not canal:
            # Canal nuevo que no conocemos todavia -- no lo perdemos,
            # pero avisamos para agregarlo a CANAL_MAP.
            print(f"⚠️ Canal no reconocido en note (consumo id={consumo.get('id')}): {canal_raw!r} -- se ignora, agregar a CANAL_MAP si corresponde.")
            continue

        fecha_unix = consumo.get("consumptionDate")
        if not fecha_unix:
            continue
        fecha_obj = datetime.datetime.fromtimestamp(fecha_unix, tz=datetime.timezone.utc).replace(tzinfo=None)
        if not (f_inicio <= fecha_obj.date() <= f_fin):
            ignorados_fuera_rango += 1
            continue

        detalle = _obtener_detalle_consumo(consumo, headers)
        if not detalle:
            continue

        # Agrupar por SKU -- si el consumo trae mas de un SKU DISTINTO no
        # podemos atribuir el precio_unitario del note a cada uno con
        # confianza, asi que se ignora y se avisa (no debería pasar según
        # los datos vistos hasta ahora, pero mejor no asumir).
        skus_en_detalle = {}
        for d in detalle:
            variant = d.get("variant") or {}
            sku = str(variant.get("code", "")).strip().upper()
            if not sku:
                continue
            cant = float(d.get("quantity", 0) or 0)
            if sku not in skus_en_detalle:
                skus_en_detalle[sku] = {"cantidad": 0.0, "variant_id": variant.get("id"),
                                         "producto": variant.get("description", "PRODUCTO")}
            skus_en_detalle[sku]["cantidad"] += cant

        if len(skus_en_detalle) > 1:
            print(f"⚠️ Consumo id={consumo.get('id')} (pedido {pedido}) trae {len(skus_en_detalle)} "
                  f"SKUs distintos -- no se puede atribuir 1 solo precio_unitario con confianza, se ignora.")
            ignorados_multi_sku += 1
            continue

        for sku, info in skus_en_detalle.items():
            cantidad = int(info["cantidad"])
            if cantidad <= 0:
                continue
            bruto_total = precio_unitario * cantidad
            neto_total = bruto_total / 1.19
            costo_unit = _obtener_costo_actual_variante(info["variant_id"], headers, cache_costo) if info["variant_id"] else 0.0
            costo_total = costo_unit * cantidad
            contribucion = neto_total - costo_total
            categoria = mapa_categorias.get(sku, "Sin Categoría Mapeada")

            filas.append({
                "DOCUMENTO": f"{canal} N° {pedido}",
                "PRODUCTO": str(info["producto"]).upper(),
                "SKU_BSALE": sku,
                "CANTIDAD": cantidad,
                "NETO_TOTAL": neto_total,
                "BRUTO_TOTAL": bruto_total,
                "COSTO_TOTAL": costo_total,
                "CONTRIBUCION": contribucion,
                "CANAL": canal,
                "VENDEDOR": f"KALTEMP {canal}",
                "CLIENTE": "CLIENTE FULFILLMENT",
                "CATEGORIA": categoria,
                "FECHA_OBJ": fecha_obj,
                "ORIGEN": ORIGEN_TAG,
                "TIPO_DOCUMENTO": "CONSUMO FULFILLMENT BSALE",
                "NUMERO_DOCUMENTO": pedido,
                "SUCURSAL": canal,
                "ES_GLOSA_SERVICIO": False,
            })

        if progress_callback and i % 20 == 0:
            progress_callback(min(10 + int(i / max(len(consumos), 1) * 80), 90),
                               f"📦 Procesando consumos Full MKP ({i}/{len(consumos)})...")

    print(f"ℹ️ Consumos ignorados -- Falabella (ya cubierto por FALABELLA_API): {ignorados_falabella}, "
          f"sin precio en note (ajuste manual, no es venta): {ignorados_sin_precio}, "
          f"multi-SKU sin poder atribuir precio: {ignorados_multi_sku}, "
          f"fuera del rango de fecha pedido: {ignorados_fuera_rango}")
    return filas


def _escribir_en_duckdb(filas, f_inicio, f_fin):
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
        # Mismo patron DELETE+INSERT por rango de fecha que sync_ventas.py,
        # pero acotado a ORIGEN='BSALE_FULL' -- no toca BSALE, FALABELLA_API
        # ni FULL_HISTORICO_MANUAL (la carga historica manual).
        con.execute(
            "DELETE FROM ventas WHERE ORIGEN = ? AND CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?",
            [ORIGEN_TAG, f_inicio, f_fin],
        )
        if not filas:
            return
        cols = ["DOCUMENTO", "PRODUCTO", "SKU_BSALE", "CANTIDAD", "NETO_TOTAL", "BRUTO_TOTAL",
                "COSTO_TOTAL", "CONTRIBUCION", "CANAL", "VENDEDOR", "CLIENTE", "CATEGORIA",
                "FECHA_OBJ", "ORIGEN", "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO", "SUCURSAL", "ES_GLOSA_SERVICIO"]
        con.execute("""
            CREATE TABLE tmp_ventas_full (
                DOCUMENTO VARCHAR, PRODUCTO VARCHAR, SKU_BSALE VARCHAR, CANTIDAD INTEGER,
                NETO_TOTAL DOUBLE, BRUTO_TOTAL DOUBLE, COSTO_TOTAL DOUBLE, CONTRIBUCION DOUBLE,
                CANAL VARCHAR, VENDEDOR VARCHAR, CLIENTE VARCHAR, CATEGORIA VARCHAR, FECHA_OBJ TIMESTAMP,
                ORIGEN VARCHAR, TIPO_DOCUMENTO VARCHAR, NUMERO_DOCUMENTO VARCHAR, SUCURSAL VARCHAR,
                ES_GLOSA_SERVICIO BOOLEAN
            )
        """)
        placeholders = ", ".join(["?"] * len(cols))
        con.executemany(
            f"INSERT INTO tmp_ventas_full VALUES ({placeholders})",
            [[f[c] for c in cols] for f in filas],
        )
        con.execute("INSERT INTO ventas SELECT * FROM tmp_ventas_full")
        con.execute("DROP TABLE tmp_ventas_full")


def sync_ventas_full(dias_atras: int = 10, progress_callback=None):
    """Punto de entrada para sync_master.py. dias_atras=10 por defecto --
    más margen que sync_ventas() (3 días) porque un pedido de fulfillment
    puede tardar unos días en despacharse y recién ahí generarse el
    consumo en Bsale."""
    def _report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    if not BSALE_TOKEN:
        _report(100, "❌ Falta BSALE_TOKEN en el .env -- no se puede sincronizar.")
        return

    hoy = datetime.date.today()
    f_inicio = hoy - datetime.timedelta(days=dias_atras)
    f_fin = hoy

    headers = _bsale_headers()
    _report(1, "🔎 Buscando bodega 'FULL MKP' en Bsale...")
    office_id = _obtener_office_id_full_mkp(headers)
    if not office_id:
        _report(100, f"❌ No se encontró la bodega '{NOMBRE_BODEGA_FULL}' en Bsale -- revisar nombre.")
        return

    _report(5, f"📥 Descargando consumos de la bodega Full MKP (id={office_id})...")
    consumos = _traer_todos_los_consumos(office_id, headers)
    _report(10, f"📥 {len(consumos)} consumos totales traídos, filtrando y procesando...")

    mapa_categorias = _cargar_mapa_categorias_sku()
    filas = _procesar_consumos(consumos, headers, mapa_categorias, f_inicio, f_fin, progress_callback)

    _report(92, f"💾 Escribiendo {len(filas)} líneas de venta fulfillment (Mercado Libre/Paris/Ripley)...")
    _escribir_en_duckdb(filas, f_inicio, f_fin)

    _report(100, f"✨ Listo: {len(filas)} líneas sincronizadas ({f_inicio} → {f_fin}).")


if __name__ == "__main__":
    dias = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    sync_ventas_full(dias_atras=dias)