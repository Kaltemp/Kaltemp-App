"""
diagnostico_reference_document.py — Inspecciona la estructura REAL que
devuelve /v1/returns.json de Bsale, para encontrar el campo correcto del
documento original (boleta/factura) detrás de cada nota de crédito.

CONTEXTO: sync_notas_credito.py corrió completo (4.427 notas de crédito
procesadas) pero 0 con documento original identificado -- eso significa
que `devolucion.get("reference_document")` está devolviendo None/vacío
para las 4.427, algo estructural, no un caso raro. Este script dumpea el
JSON crudo de un par de devoluciones para ver qué campo trae realmente
el documento original.

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_reference_document.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sync"))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402


def main():
    print("=== 1) Primeras 3 devoluciones CON expand=[credit_note,reference_document,office] ===")
    count = 0
    primeros_ids = []
    for devolucion in bsale_get_all(
        "returns.json",
        params={"expand": "[credit_note,reference_document,office]"},
        max_items=200,  # buscamos entre las primeras 200 hasta encontrar 3 con credit_note
    ):
        if not devolucion.get("credit_note"):
            continue
        count += 1
        primeros_ids.append(devolucion.get("id"))
        print(f"\n--- Devolución id={devolucion.get('id')} (con credit_note) ---")
        print(json.dumps(devolucion, indent=2, ensure_ascii=False)[:3000])
        if count >= 3:
            break

    if not primeros_ids:
        print("No se encontraron devoluciones con credit_note en las primeras 200. Revisa el token/permisos.")
        return

    print("\n\n=== 2) Mismo id, pero SIN expand (para ver campos por default) ===")
    for devolucion in bsale_get_all("returns.json", max_items=500):
        if devolucion.get("id") == primeros_ids[0]:
            print(json.dumps(devolucion, indent=2, ensure_ascii=False)[:3000])
            break

    print("\n\n=== 3) GET puntual a /v1/returns/{id}.json (recurso único, sin expand) ===")
    detalle = bsale_get_one(f"returns/{primeros_ids[0]}.json")
    print(json.dumps(detalle, indent=2, ensure_ascii=False)[:3000])

    print("\n\n=== 4) Probar variantes de expand por separado ===")
    for variante in ["[reference_document]", "[referenceDocument]", "[document]", "[details]"]:
        print(f"\n--- expand={variante} ---")
        try:
            for devolucion in bsale_get_all(
                "returns.json", params={"expand": variante}, max_items=5
            ):
                if devolucion.get("id") == primeros_ids[0]:
                    print(json.dumps(devolucion, indent=2, ensure_ascii=False)[:2000])
                    break
            else:
                print("(el id de referencia no salió en los primeros 5 con esta variante -- normal, "
                      "el orden puede variar; igual mira si aparecen campos nuevos arriba)")
        except Exception as e:
            print(f"ERROR con esta variante: {e}")


if __name__ == "__main__":
    main()