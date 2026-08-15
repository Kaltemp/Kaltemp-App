# ============================================================
# ARCHIVO: actualizar_fletes_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\actualizar_fletes_enviame.py
# ============================================================

"""
sync/actualizar_fletes_enviame.py — Rellena COSTO_ENVIO en `enviame_despachos`.

AGREGADO (11-ago-2026, a pedido de William) -- CÁLCULO CON PESO REAL:
Antes SIEMPRE se usaba un paquete genérico fijo (1 kg, 10x10x10 cm)
corregido por un factor de ajuste por courier (ver más abajo, "PLAN B").
Ahora, ANTES de recurrir a eso, se intenta un cálculo más preciso, en
DOS niveles dentro del Plan A:

  PLAN A0 (peso real, automático -- agregado 11-ago-2026, idea de
    William): N_ENVIO_REF de `enviame_despachos` YA ES el número de
    documento Bsale para Showroom/Distribuidores (confirmado real: es
    la misma clave que usa /api/enviame-shipments para mostrar la
    columna PRODUCTO). Se prueba directo contra `ventas.NUMERO_DOCUMENTO`
    -- si hay match y todos los SKUs de esa venta tienen peso cargado,
    se cotiza con el peso real sin depender de que nadie en bodega haya
    escrito nada en Envíame.

  PLAN A1 (peso real, vía texto editado a mano -- el método original):
    solo se intenta si A0 no encontró nada (típico de D2C, donde
    N_ENVIO_REF es el N° de pedido de Shopify, no de Bsale).
    1. Se llama a GET /deliveries/{id}/tracking del envío (el ID_INTERNO
       guardado por sync_enviame.py). Ese endpoint SÍ devuelve el
       historial completo de eventos -- a diferencia de GET /deliveries/
       {id} normal, que NO expone "Observaciones" NI "Descripción del
       producto" bajo ningún parámetro (confirmado real, 11-ago-2026,
       para ambos campos con varios intentos).
    2. Se busca en los comentarios de ese historial, EN ESTE ORDEN:
       a) 'Cambio de descripción: "..." a "NUEVO"' -- campo "Descripción
          del producto", el que bodega usa desde el 11-ago-2026 (cambio
          de proceso, ver más abajo).
       b) 'Cambio de texto observaciones: "..." a "NUEVO"' -- campo
          "Observaciones", usado ANTES del cambio de proceso; se deja
          como respaldo para envíos viejos que ya lo tenían cargado ahí.
       Solo aparece si alguien EDITÓ el envío después de creado para
       agregar la nota (confirmado real: la nota escrita al CREAR el
       envío no genera este mensaje, solo un cambio posterior sí).
    3. Se extraen los dígitos del texto nuevo (ej. "Boleta #41805" ->
       "41805") como candidato a NUMERO_DOCUMENTO.

  En cualquiera de los dos niveles de A: una vez que se tiene un
  NUMERO_DOCUMENTO candidato, se busca en `ventas.NUMERO_DOCUMENTO`. Si
  existe, se suma peso_manual.peso_kg × CANTIDAD de cada línea de esa
  venta. Si TODOS los SKUs de esa venta tienen peso cargado (ninguno
  falta), se cotiza con Envíame usando ese peso real -- sin aplicar el
  factor de ajuste, porque ya es una cotización real, no habría que
  corregirla.

  PLAN B (el método de siempre, sin cambios): si CUALQUIER paso de
    arriba falla (sin match en A0 ni A1, documento no encontrado, algún
    SKU sin peso cargado, error de red), se cae exactamente al mismo
    cálculo de antes: cotización teórica a 1kg fijo × factor de ajuste
    por courier (mediana real/teórico calculada en
    calcular_ajuste_flete.py).

CAMBIO DE PROCESO (11-ago-2026): a partir de ahora, bodega debe escribir
el N° de boleta/factura en el campo "Descripción del producto" al crear
el envío en Envíame, NO en "Observaciones". Motivo confirmado real: el
flujo de edición del envío (ej. "Editar bodega") puede pisar
Observaciones sin querer al tocar otro campo -- pasó con el envío
458792843, donde Observaciones tenía "Boleta #41805" pero una edición
posterior la reemplazó por el nombre del producto, perdiendo el número.
Descripción del producto no está exenta del mismo riesgo, pero al ser
el campo "oficial" desde ahora, es el que bodega debe revisar con más
cuidado antes de dar por perdido un envío sin cotización real.

Esto es un rollout GRADUAL a propósito: mientras bodega no tenga la
costumbre de escribir+editar la Observación en cada envío manual, la
gran mayoría van a seguir cayendo al Plan B -- el sistema no empeora
en ningún caso, solo mejora a medida que hay más datos reales.

Se agrega la columna ES_COSTO_REAL (booleano) para que el frontend
pueda distinguir "(real)" de "(EST.)" en vez de mostrar todo igual.

⚠️ El Plan B sigue sin ser el costo real facturado (confirmado por
correo con Raimundo Silva, soporte Envíame) -- el frontend debe seguir
mostrando esos casos como "(EST.)".

NOTAS TÉCNICAS (sin cambios):
- /v1/prices requiere el header `x-api-key`; /deliveries y /carriers
  requieren `api-key`. Se envían ambos siempre.
- Códigos de courier de /carriers no siempre son válidos como filtro
  `carrier=` en /prices -- si falla con 404 CarrierNotFoundException, se
  reintenta sin filtro y se busca por NOMBRE.
- CHILEPARCELS confirmado que NO aparece en /prices bajo ninguna
  combinación. Para esos casos, se usa el PROMEDIO de lo que sí cotizó la
  API para esa comuna como aproximación de último recurso.

Debe correr DESPUÉS de sync_enviame.py en el mismo ciclo de sync_master.py.
"""
import os
import re
import sys
import requests
import duckdb
from dotenv import load_dotenv

# categorias_db.py vive en backend/ (un nivel arriba de backend/sync/, donde
# corre este script) -- sin esto, Python no lo encuentra al correr
# `python actualizar_fletes_enviame.py` parado en la carpeta sync/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from categorias_db import get_categorias_connection

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

if not API_KEY or not COMPANY_ID:
    raise RuntimeError("Faltan ENVIAME_API_KEY / ENVIAME_COMPANY_ID en el .env de la raíz.")

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}

CARRIER_MAP = {
    "STARKEN": "SKN", "BLUEXPRESS": "BLX", "CHILEXPRESS": "CHX",
    "CORREOSCHILE": "CCH", "CHILEPARCELS": "CPS", "99MINUTOS": "99M",
    "FEDEX": "FDX", "RECIBELO": "RBL", "SENBY": "SNBY", "HELPCOURIER": "HPC",
}

_couriers_sin_mapear_avisados = set()
_codigos_invalidos_en_prices = set()


def mostrar_carriers_reales():
    url = f"https://api.enviame.io/api/s1/v1/companies/{COMPANY_ID}/carriers"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            print("\n📋 Couriers activos reales en la cuenta Envíame:")
            for c in res.json().get("data", []):
                print(f"   '{c.get('name', '').upper()}': '{c.get('code', '')}',")
        else:
            print(f"⚠️ No se pudo obtener el listado de carriers ({res.status_code}): {res.text[:300]}")
    except Exception as e:
        print(f"⚠️ Error consultando carriers: {e}")


def cargar_factores_ajuste():
    con = duckdb.connect(DB_FILE, read_only=True)
    tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    if "enviame_factor_ajuste" not in tablas:
        con.close()
        print("ℹ️ Tabla enviame_factor_ajuste no existe todavía -- se usa factor 1.0 (sin ajuste).")
        return {}, 1.0

    df = con.execute("SELECT CARRIER, FACTOR FROM enviame_factor_ajuste").df()
    con.close()
    factores = dict(zip(df["CARRIER"], df["FACTOR"]))
    factor_global = factores.pop("__GLOBAL__", 1.0)
    print(f"📐 Factores de ajuste cargados: {factores} (respaldo global: {factor_global:.3f})")
    return factores, factor_global


def _extraer_precio(item):
    services = item.get("services", [])
    if not services:
        return None
    precio = services[0].get("price", 0.0)
    for srv in services:
        if srv.get("code") in ("ecommerce", "priority", "normal", "estandar"):
            precio = srv.get("price", precio)
            break
    return float(precio) if precio else None


def _llamar_prices(comuna_destino, carrier_code=None):
    url = "https://api.enviame.io/api/v1/prices"
    params = {
        "from_place": "Santiago",
        "to_place": comuna_destino,
        "weight": 1.0, "length": 10, "width": 10, "height": 10,
    }
    if carrier_code:
        params["carrier"] = carrier_code
    return requests.get(url, headers=HEADERS, params=params, timeout=10)


def consultar_tarifa_tarificador(comuna_destino, carrier_nombre, cache_tarifas, factores, factor_global):
    carrier_norm = str(carrier_nombre).upper().strip()
    carrier_code = CARRIER_MAP.get(carrier_norm, "")
    key_cache = f"{comuna_destino}_{carrier_norm}"

    if key_cache in cache_tarifas:
        return cache_tarifas[key_cache]

    if not comuna_destino or comuna_destino.strip().lower() in ("", "sin comuna"):
        cache_tarifas[key_cache] = 0.0
        return 0.0

    if not carrier_code and carrier_norm not in _couriers_sin_mapear_avisados:
        _couriers_sin_mapear_avisados.add(carrier_norm)
        print(f"⚠️ Courier '{carrier_nombre}' no está en CARRIER_MAP -- se cotiza sin filtrar por courier.")

    precio_base = None
    precios_disponibles_ruta = []
    usar_codigo = bool(carrier_code) and carrier_code not in _codigos_invalidos_en_prices

    try:
        if usar_codigo:
            res = _llamar_prices(comuna_destino, carrier_code)
            if res.status_code == 404 and "CARRIER_NOT_FOUND" in res.text:
                _codigos_invalidos_en_prices.add(carrier_code)
                usar_codigo = False
            elif res.status_code == 200:
                for item in res.json().get("data", []):
                    p = _extraer_precio(item)
                    if p:
                        precio_base = p
                        break
            else:
                print(f"⚠️ {res.status_code} cotizando {comuna_destino}/{carrier_nombre}: {res.text[:200]}")

        if precio_base is None and not usar_codigo:
            res = _llamar_prices(comuna_destino, carrier_code=None)
            if res.status_code == 200:
                data = res.json().get("data", [])
                for item in data:
                    p = _extraer_precio(item)
                    if p:
                        precios_disponibles_ruta.append(p)
                        nombre_item = str(item.get("name", "")).upper().strip()
                        if nombre_item == carrier_norm or carrier_norm in nombre_item:
                            precio_base = p
            else:
                print(f"⚠️ {res.status_code} cotizando {comuna_destino}/{carrier_nombre} (sin filtro): {res.text[:200]}")

    except Exception as e:
        print(f"⚠️ Error cotizando {comuna_destino} / {carrier_nombre}: {e}")

    if precio_base is None and precios_disponibles_ruta:
        precio_base = sum(precios_disponibles_ruta) / len(precios_disponibles_ruta)
        if carrier_norm not in _couriers_sin_cobertura_avisados:
            _couriers_sin_cobertura_avisados.add(carrier_norm)
            print(f"ℹ️ '{carrier_nombre}' no está cotizable en /prices -- se usa el promedio de otros "
                  f"couriers en esa ruta como aproximación (${precio_base:,.0f}).")

    if not precio_base:
        cache_tarifas[key_cache] = 0.0
        return 0.0

    factor = factores.get(carrier_norm, factor_global)
    precio_ajustado = round(precio_base * factor, 0)
    cache_tarifas[key_cache] = precio_ajustado
    return precio_ajustado


_couriers_sin_cobertura_avisados = set()


# ============================================================
# PLAN A -- peso real (agregado 11-ago-2026)
# ============================================================
# ACTUALIZADO (11-ago-2026, cambio de proceso a pedido de William): de
# ahora en adelante bodega escribe el N° de documento en "Descripción
# del producto" en vez de "Observaciones" (Observaciones se estaba
# pisando sin querer al editar otros campos del envío -- confirmado
# real con el envío 458792843: a las 10:26 Observaciones tenía "Boleta
# #41805", pero a las 11:12 un segundo editor cambió Descripción Y
# Observaciones a la vez, dejando ambas en "APOLO 1500 INVERTER" y
# perdiendo el número).
#
# Se prueban los DOS patrones (Descripción primero, Observaciones como
# respaldo para envíos viejos ya creados antes de este cambio de
# proceso), sobre los mismos eventos de /tracking -- confirmado real
# que "Descripción del producto" tampoco aparece en GET /deliveries/{id}
# normal, necesita el mismo hack de leer el historial de ediciones.
#
# El texto del evento es distinto entre los dos campos:
#   Descripción:   'Cambio de descripción: "..." a "NUEVO"'
#   Observaciones: 'Cambio de texto observaciones: "..." a "NUEVO"'
_PATRON_DESCRIPCION = re.compile(r'[Cc]ambio de descripci[oó]n:\s*"[^"]*"\s*a\s*"([^"]*)"')
_PATRON_OBSERVACIONES = re.compile(r'[Cc]ambio de texto observaciones:\s*"[^"]*"\s*a\s*"([^"]*)"')


def _obtener_numero_documento_desde_tracking(identifier):
    """Llama a /deliveries/{id}/tracking y busca, en cada evento (del
    más reciente al más viejo), primero el patrón de Descripción del
    producto y luego el de Observaciones. Devuelve solo los dígitos del
    primer texto que matchee (ej. "Boleta #41805" -> "41805"), o None si
    ningún evento trae ninguno de los dos."""
    if not identifier:
        return None
    url = f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}/tracking"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return None
        data = res.json()
        contenido = data.get("data", data) if isinstance(data, dict) else {}
        eventos = contenido.get("tracking", []) if isinstance(contenido, dict) else []

        for evento in eventos:
            comentario = evento.get("comment") or ""
            for patron in (_PATRON_DESCRIPCION, _PATRON_OBSERVACIONES):
                m = patron.search(comentario)
                if m:
                    digitos = re.search(r"\d+", m.group(1))
                    if digitos:
                        return digitos.group(0)
        return None
    except Exception:
        return None


def _cargar_pesos_manual():
    """SKU -> peso_kg desde la base de pesos manuales (categorias_db.py).
    SKUs marcados descontinuado, o sin peso cargado, no cuentan."""
    pesos = {}
    with get_categorias_connection() as con:
        for row in con.execute(
            "SELECT sku, peso_kg FROM pesos_manual WHERE descontinuado = 0 AND peso_kg IS NOT NULL"
        ).fetchall():
            pesos[row["sku"]] = row["peso_kg"]
    return pesos


def _calcular_peso_real_envio(numero_documento, con_duckdb, pesos_por_sku):
    """Busca las líneas de venta de ese NUMERO_DOCUMENTO y suma peso_kg
    × CANTIDAD. Devuelve None si el documento no existe en `ventas`, o
    si ALGÚN SKU de esa venta no tiene peso cargado -- mejor no cotizar
    con un peso parcial que sabemos que está incompleto."""
    filas = con_duckdb.execute(
        "SELECT SKU_BSALE, CANTIDAD FROM ventas WHERE NUMERO_DOCUMENTO = ?",
        [numero_documento],
    ).fetchall()
    if not filas:
        return None

    peso_total = 0.0
    for sku, cantidad in filas:
        sku_norm = str(sku or "").strip().upper()
        if sku_norm not in pesos_por_sku:
            return None
        peso_total += pesos_por_sku[sku_norm] * float(cantidad or 1)

    return peso_total if peso_total > 0 else None


def _llamar_prices_peso_real(comuna_destino, carrier_code, peso_kg):
    """Igual que _llamar_prices, pero con el peso real en vez del 1kg
    fijo. Envíame también exige dimensiones -- se aproxima un cubo
    escalado al peso (mejor que 10x10x10 fijo para paquetes pesados,
    aunque no es la medida real del paquete)."""
    url = "https://api.enviame.io/api/v1/prices"
    lado_cm = max(10, round((peso_kg ** (1 / 3)) * 12))
    params = {
        "from_place": "Santiago", "to_place": comuna_destino,
        "weight": peso_kg, "length": lado_cm, "width": lado_cm, "height": lado_cm,
    }
    if carrier_code:
        params["carrier"] = carrier_code
    return requests.get(url, headers=HEADERS, params=params, timeout=10)


def _intentar_costo_real(comuna, courier, id_interno, n_envio_ref, con_duckdb, pesos_por_sku):
    """Orquesta el Plan A completo, en dos niveles:

    A0) N_ENVIO_REF directo como NUMERO_DOCUMENTO (agregado 11-ago-2026, a
        idea de William): para Showroom/Distribuidores, N_ENVIO_REF YA ES
        el número de documento Bsale (confirmado real -- es la misma
        clave que ya usa /api/enviame-shipments para mostrar la columna
        PRODUCTO). Funciona 100% automático, sin depender de que bodega
        escriba nada en Envíame.
    A1) Si A0 no encuentra nada (típico de D2C, donde N_ENVIO_REF es el
        N° de pedido de Shopify, no de Bsale), cae al método anterior:
        leer el historial de /tracking buscando Descripción del producto
        u Observaciones editadas a mano.

    Devuelve (costo, True) si logró un precio con peso real en cualquiera
    de los dos niveles, o (None, False) si ambos fallaron -- en ese caso
    el llamador debe caer al Plan B."""
    numero_doc = str(n_envio_ref) if n_envio_ref else None
    peso_real = _calcular_peso_real_envio(numero_doc, con_duckdb, pesos_por_sku) if numero_doc else None
    nivel = "A0" if peso_real else None

    if not peso_real:
        numero_doc = _obtener_numero_documento_desde_tracking(id_interno)
        if numero_doc:
            peso_real = _calcular_peso_real_envio(numero_doc, con_duckdb, pesos_por_sku)
            nivel = "A1" if peso_real else None

    if not peso_real:
        return None, False, None

    carrier_norm = str(courier or "").upper().strip()
    carrier_code = CARRIER_MAP.get(carrier_norm, "")
    try:
        res = _llamar_prices_peso_real(comuna, carrier_code, peso_real)
        if res.status_code == 200:
            for item in res.json().get("data", []):
                p = _extraer_precio(item)
                if p:
                    return round(p, 0), True, nivel
    except Exception as e:
        print(f"⚠️ Error cotizando con peso real (doc {numero_doc}): {e}")

    return None, False, None


def ejecutar_actualizacion_costos(forzar_todo: bool = None):
    """
    forzar_todo (agregado 11-ago-2026, para conectar el campo de 'días'
    del modal a este paso): si se pasa explícito (True/False), manda por
    sobre la variable de entorno FORZAR_RECALCULO -- así sync_admin.py
    puede disparar el recálculo completo desde la UI sin depender de que
    alguien setee la variable a mano en una terminal. Si no se pasa nada
    (None, el caso de correrlo suelto por consola), se sigue respetando
    FORZAR_RECALCULO=1 como antes.
    """
    print("🔄 Conectando a DuckDB...")
    factores, factor_global = cargar_factores_ajuste()
    pesos_por_sku = _cargar_pesos_manual()
    print(f"⚖️ {len(pesos_por_sku)} SKUs con peso real cargado (para el Plan A).")
    con = duckdb.connect(DB_FILE)

    try:
        con.execute("ALTER TABLE enviame_despachos ADD COLUMN ES_COSTO_REAL BOOLEAN DEFAULT FALSE")
    except duckdb.Error:
        pass  # ya existe -- normal en corridas posteriores a la primera

    # FORZAR_RECALCULO=1 (agregado 11-ago-2026): por default el script solo
    # toca despachos con COSTO_ENVIO en NULL/0 -- así que un despacho ya
    # calculado con el método viejo (antes de que existiera el Plan A0/A1)
    # NUNCA se vuelve a tocar solo. Con esta variable se recalculan TODOS,
    # para que las mejoras de peso real alcancen también al histórico ya
    # procesado. Tarda bastante más (llama a la API por cada despacho, no
    # solo por los nuevos) -- usarla a propósito, no en cada corrida normal.
    forzar_todo = forzar_todo if forzar_todo is not None else (os.getenv("FORZAR_RECALCULO", "0") == "1")
    where_sql = "" if forzar_todo else "WHERE COSTO_ENVIO IS NULL OR COSTO_ENVIO = 0.0"
    if forzar_todo:
        print("🔁 FORZAR_RECALCULO=1 -- recalculando TODOS los despachos, no solo los pendientes.")

    df_despachos = con.execute(f"""
        SELECT ID_ENVIO_PK, COMUNA, COURIER, ID_INTERNO, N_ENVIO_REF
        FROM enviame_despachos
        {where_sql}
    """).df()

    total = len(df_despachos)
    print(f"📦 {total} despachos sin costo estimado.")
    if total == 0:
        print("✅ Todos los despachos ya tienen costo estimado.")
        con.close()
        return

    cache_tarifas = {}
    actualizados = 0
    con_costo_real = 0
    con_peso_real_a0 = 0
    con_peso_real_a1 = 0

    for _, row in df_despachos.iterrows():
        costo, uso_peso_real, nivel = _intentar_costo_real(
            row["COMUNA"], row["COURIER"], row["ID_INTERNO"], row["N_ENVIO_REF"], con, pesos_por_sku
        )

        if costo is None:
            # Plan B -- método de siempre
            costo = consultar_tarifa_tarificador(row["COMUNA"], row["COURIER"], cache_tarifas, factores, factor_global)
            uso_peso_real = False

        if costo and costo > 0:
            con_costo_real += 1
        if nivel == "A0":
            con_peso_real_a0 += 1
        elif nivel == "A1":
            con_peso_real_a1 += 1

        con.execute(
            "UPDATE enviame_despachos SET COSTO_ENVIO = ?, ES_COSTO_REAL = ? WHERE ID_ENVIO_PK = ?",
            [costo or 0.0, uso_peso_real, row["ID_ENVIO_PK"]],
        )
        actualizados += 1
        if actualizados % 50 == 0 or actualizados == total:
            con_peso_real = con_peso_real_a0 + con_peso_real_a1
            print(f"   ⏳ {actualizados}/{total} ({con_costo_real} con estimación > $0, {con_peso_real} con PESO REAL: "
                  f"{con_peso_real_a0} directo/N_ENVIO_REF, {con_peso_real_a1} vía texto editado)")

    con.close()
    con_peso_real = con_peso_real_a0 + con_peso_real_a1
    print(f"\n🎉 Listo: {con_costo_real}/{total} con estimación, de los cuales {con_peso_real} usaron peso real "
          f"({con_peso_real_a0} vía Plan A0 -- N_ENVIO_REF directo, sin depender de bodega -- "
          f"y {con_peso_real_a1} vía Plan A1 -- Descripción/Observaciones editadas a mano) "
          f"en vez del 1kg genérico (Plan B).")


if __name__ == "__main__":
    mostrar_carriers_reales()
    ejecutar_actualizacion_costos()