# ============================================================
# ARCHIVO: diagnostico_descripcion_producto_enviame.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_descripcion_producto_enviame.py
# ============================================================
"""
diagnostico_descripcion_producto_enviame.py — El listado /deliveries NO
trae el campo "Descripción del producto" (confirmado: no apareció en el
dump completo de diagnostico_fecha_entrega_enviame.py). Este script
llama al DETALLE de un envío puntual (GET /deliveries/{id}, el link
"self" que sí viene en el listado) para buscar dónde vive ese campo.

Uso:
    cd backend
    python diagnostico_descripcion_producto_enviame.py --identifier 458868350
    python diagnostico_descripcion_producto_enviame.py --imported-id 19695 --fecha 2026-08-13

Si pasas --imported-id, hay que pasar también --fecha (YYYY-MM-DD, el día
aproximado en que se creó ESE envío puntual) -- imported_id se reutiliza
en el tiempo (confirmado real: "19695" existe tanto en dic-2025 como en
ago-2026 para envíos completamente distintos), así que sin la fecha no
hay forma de saber a cuál te refieres.

Si no pasas nada, toma el envío más reciente que tenga
"Boleta"/"Factura"/"Guía" en CUALQUIER campo de texto visible del
listado, o si no encuentra ninguno, el más reciente a secas.
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
COMPANY_ID = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    print("❌ No se pudo cargar ENVIAME_API_KEY / COMPANY_ID.")
    raise SystemExit(1)

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}


def _buscar_por_imported_id_y_fecha(imported_id: str, fecha_str: str):
    """
    Busca en el LISTADO, usando date_from (el único parámetro de fecha
    confirmado que soporta la API, según sync_enviame.py -- date_to no
    está confirmado y podría estar siendo ignorado silenciosamente),
    el/los envío(s) cuyo imported_id calce. Muestra TODOS los
    candidatos con su fecha real para que se elija a mano cuál es --
    evita repetir el problema de agarrar el candidato equivocado
    (confirmado real: imported_id se reutiliza en fechas lejanas).
    """
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    desde = (fecha - timedelta(days=5)).isoformat()

    url = f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries"
    candidatos = []
    page = 1
    while page <= 10:  # tope de seguridad, no debería necesitar tantas
        res = requests.get(url, headers=HEADERS, params={"date_from": desde, "page": page, "limit": 100}, timeout=30)
        if res.status_code != 200:
            print(f"❌ Error ({res.status_code}) buscando en el listado: {res.text[:300]}")
            return None
        items = res.json().get("data", [])
        if not items:
            break
        for e in items:
            if str(e.get("imported_id")) == str(imported_id):
                candidatos.append(e)
        page += 1

    if not candidatos:
        print(f"❌ No encontré ningún envío con imported_id={imported_id!r} desde {desde} en adelante.")
        print("   Prueba con una fecha más antigua, o usa --identifier si tienes el número largo.")
        return None

    print(f"\nEncontré {len(candidatos)} candidato(s) con imported_id={imported_id!r}:\n")
    for c in candidatos:
        print(f"  identifier={c['identifier']:<12} created_at={c.get('created_at')!r:<25} "
              f"cliente={((c.get('customer') or {}).get('full_name'))!r} "
              f"comuna={((c.get('shipping_address') or {}).get('place'))!r}")

    if len(candidatos) == 1:
        return candidatos[0]["identifier"]

    print(f"\n⚠️ Hay más de uno -- vuelve a correr con --identifier <el correcto de la lista de arriba>.")
    return None


def _buscar_candidato():
    url = f"https://api.enviame.io/api/s2/v2/companies/{COMPANY_ID}/deliveries"
    res = requests.get(url, headers=HEADERS, params={"limit": 50}, timeout=30)
    res.raise_for_status()
    items = res.json().get("data", [])

    for e in items:
        texto_plano = json.dumps(e, ensure_ascii=False).upper()
        if "BOLETA" in texto_plano or "FACTURA" in texto_plano or "GUÍA" in texto_plano or "GUIA" in texto_plano:
            print(f"✅ Encontrado candidato con referencia de documento en el listado: identifier={e['identifier']}")
            return e["identifier"]

    if items:
        print("⚠️ Ninguno de los últimos 50 trae 'Boleta/Factura/Guía' visible en el listado -- "
              "uso el más reciente para revisar su detalle igual.")
        return items[0]["identifier"]

    print("❌ El listado vino vacío.")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--identifier", help="El número largo (9 dígitos) del envío, si lo tienes.")
    parser.add_argument("--imported-id", help="El 'N. de envío' que ves en la lista de Envíame (ej. 19695).")
    parser.add_argument("--fecha", help="Fecha aproximada (YYYY-MM-DD) en que se creó ESE envío -- obligatorio junto con --imported-id.")
    args = parser.parse_args()

    if args.identifier:
        identifier = args.identifier
    elif args.imported_id:
        if not args.fecha:
            print("❌ Si usas --imported-id, también necesitas --fecha (YYYY-MM-DD).")
            return
        identifier = _buscar_por_imported_id_y_fecha(args.imported_id, args.fecha)
        if identifier is None:
            return
    else:
        identifier = _buscar_candidato()
        if identifier is None:
            return

    url = f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}"
    res = requests.get(url, headers=HEADERS, timeout=30)
    if res.status_code != 200:
        print(f"❌ Error ({res.status_code}) al pedir el detalle: {res.text[:300]}")
        return

    detalle = res.json()

    print(f"\n{'=' * 80}\nDETALLE COMPLETO -- identifier={identifier}\n{'=' * 80}")
    print(json.dumps(detalle, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 80}\nBÚSQUEDA de campos con 'descrip', 'observ', 'product', 'reference', 'nota'\n{'=' * 80}")

    def _buscar_claves(obj, ruta=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ruta_actual = f"{ruta}.{k}" if ruta else k
                if any(p in k.lower() for p in ("descrip", "observ", "product", "reference", "nota", "referencia")):
                    print(f"  {ruta_actual} = {v!r}")
                _buscar_claves(v, ruta_actual)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _buscar_claves(v, f"{ruta}[{i}]")

    _buscar_claves(detalle)

    # Búsqueda de texto crudo -- sin depender del nombre de la clave,
    # busca directamente "BOLETA"/"FACTURA"/"GUIA"/"GUÍA" en cualquier
    # valor string del JSON (recursivo), que es justo lo que William
    # confirmó que bodega escribe en el campo "Descripción del producto".
    print(f"\n{'=' * 80}\nBúsqueda de texto crudo: BOLETA / FACTURA / GUIA / GUÍA\n{'=' * 80}")
    palabras = ("BOLETA", "FACTURA", "GUIA", "GUÍA")

    def _buscar_texto(obj, ruta=""):
        encontrados = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                encontrados += _buscar_texto(v, f"{ruta}.{k}" if ruta else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                encontrados += _buscar_texto(v, f"{ruta}[{i}]")
        elif isinstance(obj, str):
            if any(p in obj.upper() for p in palabras):
                encontrados.append((ruta, obj))
        return encontrados

    hallazgos = _buscar_texto(detalle)
    if hallazgos:
        for ruta, valor in hallazgos:
            print(f"  ✅ {ruta} = {valor!r}")
    else:
        print("  (nada encontrado en el detalle -- probando sub-endpoints)")

    # Ni el listado ni el detalle trajeron el campo -- prueba de
    # sub-endpoints candidatos donde suele vivir la info de "paquete"
    # en APIs de logística (packages/items), y también la versión s1
    # de la API por si expone algo distinto que s2.
    print(f"\n{'=' * 80}\nProbando sub-endpoints candidatos\n{'=' * 80}")
    candidatos = [
        f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}/packages",
        f"https://api.enviame.io/api/s2/v2/deliveries/{identifier}/items",
        f"https://api.enviame.io/api/s1/v1/deliveries/{identifier}",
        f"https://api.enviame.io/api/s1/v1/companies/{COMPANY_ID}/deliveries/{identifier}",
    ]
    for url_candidato in candidatos:
        try:
            r = requests.get(url_candidato, headers=HEADERS, timeout=15)
            print(f"\nGET {url_candidato}\n  Status: {r.status_code}")
            if r.status_code == 200:
                cuerpo = r.json()
                print(f"  {json.dumps(cuerpo, indent=2, ensure_ascii=False)[:1500]}")
                hallazgos_sub = _buscar_texto(cuerpo)
                for ruta, valor in hallazgos_sub:
                    print(f"  ✅ TEXTO ENCONTRADO: {ruta} = {valor!r}")
            else:
                print(f"  {r.text[:200]}")
        except Exception as e:
            print(f"\nGET {url_candidato}\n  ERROR: {e}")

    # Intento con expand=/fields= -- mismo patrón que ya usa el proyecto
    # para pedir campos extra en la API de Bsale (expand=[client,details]).
    # No confirmado que Envíame lo soporte, pero es barato probarlo.
    print(f"\n{'=' * 80}\nProbando parámetros expand=/fields= sobre el detalle\n{'=' * 80}")
    intentos_params = [
        {"expand": "all"},
        {"expand": "package,description,observations"},
        {"fields": "description,observations,product_description"},
        {"include": "package"},
    ]
    for params in intentos_params:
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            print(f"\nGET {url} params={params}\n  Status: {r.status_code}")
            if r.status_code == 200:
                cuerpo = r.json()
                hallazgos_sub = _buscar_texto(cuerpo)
                if hallazgos_sub:
                    for ruta, valor in hallazgos_sub:
                        print(f"  ✅ TEXTO ENCONTRADO: {ruta} = {valor!r}")
                elif json.dumps(cuerpo, ensure_ascii=False, sort_keys=True) != json.dumps(detalle, ensure_ascii=False, sort_keys=True):
                    print(f"  ℹ️ La respuesta CAMBIÓ con este parámetro (pero sin BOLETA/FACTURA/GUIA) -- revisar a mano:")
                    print(f"  {json.dumps(cuerpo, indent=2, ensure_ascii=False)[:800]}")
                else:
                    print(f"  (respuesta idéntica a la del detalle sin parámetros -- este parámetro no hizo nada)")
            else:
                print(f"  {r.text[:150]}")
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()