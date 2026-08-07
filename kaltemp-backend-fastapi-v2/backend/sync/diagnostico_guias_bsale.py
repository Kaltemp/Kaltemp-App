"""
diagnostico_guias_bsale.py — Confirma si esta cuenta Bsale emite Guías de
Despacho Electrónicas (codeSii=52) y bajo qué documentTypeId(s), antes de
corregir sync_pendientes_despacho.py a ciegas.

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_guias_bsale.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402


def main():
    print("=" * 70)
    print("1) Todos los tipos de documento configurados en esta cuenta")
    print("=" * 70)
    tipos_guia = []
    for dt in bsale_get_all("document_types.json"):
        code = dt.get("codeSii")
        print(f"  id={dt.get('id'):<5} codeSii={str(code):<5} name={dt.get('name')}")
        if str(code) == "52":
            tipos_guia.append(dt["id"])

    print()
    print(f"-> document_types con codeSii=52 (Guía Despacho Electrónica): {tipos_guia}")
    print()

    print("=" * 70)
    print("2) Conteo real de documentos con codeSii=52 (filtro directo, sin pasar por documenttypeid)")
    print("=" * 70)
    total = 0
    primeros = []
    for doc in bsale_get_all("documents.json", params={"codesii": 52}, max_items=5):
        total += 1
        primeros.append(doc)
    # bsale_get_all corta en max_items=5, así que para el conteo real
    # pedimos también el count crudo de la primera página:
    import requests
    from bsale_client import BSALE_BASE_URL, _headers  # type: ignore
    res = requests.get(f"{BSALE_BASE_URL}/documents.json", headers=_headers(), params={"codesii": 52, "limit": 1})
    count_real = res.json().get("count", "desconocido")

    print(f"-> count real reportado por Bsale (codesii=52): {count_real}")
    print(f"-> primeros {len(primeros)} documentos de ejemplo:")
    for d in primeros:
        print(f"     id={d.get('id')} number={d.get('number')} document_type={d.get('document_type', {}).get('id')} emissionDate={d.get('emissionDate')}")

    print()
    print("=" * 70)
    print("3) Si documenttypeid=X (uno de los ids de arriba) da 0 pero codesii=52 SÍ trae documentos,")
    print("   confirma que el bug era filtrar por un solo documentTypeId en vez de por codeSii.")
    print("=" * 70)
    for tid in tipos_guia:
        res2 = requests.get(f"{BSALE_BASE_URL}/documents.json", headers=_headers(), params={"documenttypeid": tid, "limit": 1})
        c = res2.json().get("count", "desconocido")
        print(f"  documenttypeid={tid} -> count={c}")


if __name__ == "__main__":
    main()
