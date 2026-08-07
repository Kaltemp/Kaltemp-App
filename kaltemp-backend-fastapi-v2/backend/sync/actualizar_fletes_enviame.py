"""
sync/actualizar_fletes_enviame.py — Rellena COSTO_ENVIO en `enviame_despachos`
con una ESTIMACIÓN vía el tarificador de Envíame (/api/v1/prices), corregida
por un factor de ajuste real calculado por courier.

⚠️ NO es el costo real facturado (confirmado por correo con Raimundo Silva,
soporte Envíame). Es una cotización con paquete genérico fijo (1 kg,
10x10x10 cm) MULTIPLICADA por un factor de corrección (enviame_factor_ajuste).
El frontend debe seguir mostrando esta columna como "(EST.)".

NOTAS TÉCNICAS:
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
import requests
import duckdb
from dotenv import load_dotenv

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


def ejecutar_actualizacion_costos():
    print("🔄 Conectando a DuckDB...")
    factores, factor_global = cargar_factores_ajuste()
    con = duckdb.connect(DB_FILE)

    df_despachos = con.execute("""
        SELECT ID_ENVIO_PK, COMUNA, COURIER
        FROM enviame_despachos
        WHERE COSTO_ENVIO IS NULL OR COSTO_ENVIO = 0.0
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

    for _, row in df_despachos.iterrows():
        costo = consultar_tarifa_tarificador(row["COMUNA"], row["COURIER"], cache_tarifas, factores, factor_global)
        if costo > 0:
            con_costo_real += 1

        con.execute(
            "UPDATE enviame_despachos SET COSTO_ENVIO = ? WHERE ID_ENVIO_PK = ?",
            [costo, row["ID_ENVIO_PK"]],
        )
        actualizados += 1
        if actualizados % 50 == 0 or actualizados == total:
            print(f"   ⏳ {actualizados}/{total} ({con_costo_real} con estimación > $0)")

    con.close()
    print(f"\n🎉 Listo: {con_costo_real}/{total} despachos con estimación (ajustada) > $0.")


if __name__ == "__main__":
    mostrar_carriers_reales()
    ejecutar_actualizacion_costos()