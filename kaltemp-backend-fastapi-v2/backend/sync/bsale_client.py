"""
bsale_client.py — Cliente HTTP compartido para los scripts de sync.

Centraliza: autenticación (BSALE_ACCESS_TOKEN), paginación automática
(la API de Bsale limita a 50 items por página), reintentos ante HTTP 429
(rate limit) y timeouts razonables. Todos los scripts de sync_* importan
`bsale_get_all` / `bsale_get_one` desde aquí en vez de reimplementar
requests sueltos.
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Evita UnicodeEncodeError si algún script se redirige a archivo en Windows
# (cp1252 no soporta los emojis ✅/⚠️ que usan los scripts de sync).
sys.stdout.reconfigure(encoding="utf-8")

# Los scripts de sync corren sueltos (python sync_xxx.py), no a través de
# main.py, así que cargan backend/.env por su cuenta acá.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BSALE_BASE_URL = "https://api.bsale.io/v1"
_TOKEN = os.getenv("BSALE_ACCESS_TOKEN")
_PAGE_LIMIT = 50  # máximo permitido por la API de Bsale


def _headers():
    if not _TOKEN:
        raise RuntimeError(
            "Falta la variable de entorno BSALE_ACCESS_TOKEN. "
            "Expórtala antes de correr los scripts de sync."
        )
    return {"access_token": _TOKEN, "Content-Type": "application/json"}


def bsale_get_one(path: str, params: dict | None = None) -> dict:
    """GET a un endpoint que retorna un único recurso (no paginado)."""
    url = f"{BSALE_BASE_URL}/{path.lstrip('/')}"
    for intento in range(3):
        res = requests.get(url, headers=_headers(), params=params or {}, timeout=15)
        if res.status_code == 429:
            time.sleep(2 * (intento + 1))
            continue
        res.raise_for_status()
        return res.json()
    res.raise_for_status()
    return {}


def bsale_get_all(path: str, params: dict | None = None, max_items: int | None = None):
    """
    Generador que pagina automáticamente un endpoint tipo /v1/xxx.json
    (los que devuelven {"count", "items", ...}), respetando el límite de
    50 items/página de Bsale y reintentando ante HTTP 429.
    """
    params = dict(params or {})
    params["limit"] = _PAGE_LIMIT
    offset = 0
    total_yielded = 0

    while True:
        params["offset"] = offset
        url = f"{BSALE_BASE_URL}/{path.lstrip('/')}"

        for intento in range(3):
            res = requests.get(url, headers=_headers(), params=params, timeout=20)
            if res.status_code == 429:
                time.sleep(2 * (intento + 1))
                continue
            res.raise_for_status()
            break
        else:
            res.raise_for_status()

        data = res.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            yield item
            total_yielded += 1
            if max_items and total_yielded >= max_items:
                return

        offset += _PAGE_LIMIT
        if offset >= data.get("count", 0):
            break
        # Pequeña pausa para no saturar el rate limit en syncs grandes
        time.sleep(0.15)


def resolver_document_type_ids(codigos_sii: list[int]) -> dict[int, int]:
    """
    Mapea codeSii -> documentTypeId real de esta cuenta Bsale, recorriendo
    /v1/document_types.json una sola vez. Evita hardcodear IDs de tipo de
    documento (varían por cuenta/instalación).
    """
    mapa = {}
    for dt in bsale_get_all("document_types.json"):
        code = dt.get("codeSii")
        if code is not None:
            try:
                mapa[int(code)] = dt["id"]
            except (TypeError, ValueError):
                continue
    return {c: mapa[c] for c in codigos_sii if c in mapa}
