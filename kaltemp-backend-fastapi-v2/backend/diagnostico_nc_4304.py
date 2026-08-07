"""
diagnostico_nc_4304.py — Busca la devolución específica que generó la
Nota de Crédito N° 4304 (la de la Boleta N° 37573) y dumpea su
reference_document crudo, para ver por qué _resolver_documento_referencia
no pudo resolverlo (falta 'number'? falta 'ted'? el 'ted' no tiene <TD>?).

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_nc_4304.py
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sync"))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402


def _con_reintento(generador_fn, intentos=3):
    """
    Envuelve un generador (como bsale_get_all) con reintento simple ante
    cortes de red transitorios (timeouts) -- bsale_get_all solo reintenta
    ante HTTP 429, no ante timeouts de conexión.
    """
    for intento in range(intentos):
        try:
            yield from generador_fn()
            return
        except Exception as e:
            print(f"  [aviso] corte de red en intento {intento + 1}/{intentos}: {e}")
            if intento == intentos - 1:
                raise
            time.sleep(3)


def main():
    print("Buscando devolución con credit_note.number == 4304 ...")
    encontrada = None
    revisadas = 0
    generador = lambda: bsale_get_all(
        "returns.json", params={"expand": "[credit_note,reference_document,office]"}
    )
    for devolucion in _con_reintento(generador):
        revisadas += 1
        credit_note = devolucion.get("credit_note")
        if credit_note and str(credit_note.get("number")) == "4304":
            encontrada = devolucion
            break
        if revisadas % 500 == 0:
            print(f"  {revisadas} devoluciones revisadas...")

    if not encontrada:
        print(f"No se encontró (revisadas {revisadas} devoluciones en total).")
        return

    print(f"\n=== Encontrada tras revisar {revisadas} devoluciones ===")
    print("\n--- reference_document (tal como viene del expand) ---")
    ref_doc = encontrada.get("reference_document")
    print(json.dumps(ref_doc, indent=2, ensure_ascii=False))

    if isinstance(ref_doc, dict):
        print(f"\n¿Tiene 'number'? {'number' in ref_doc} -> {ref_doc.get('number')}")
        print(f"¿Tiene 'ted'? {'ted' in ref_doc}")
        if "ted" in ref_doc:
            print(f"Contenido de 'ted' (primeros 200 chars): {str(ref_doc.get('ted'))[:200]}")

        print("\n--- Reforzando con GET puntual a /documents/{id}.json ---")
        detalle = bsale_get_one(f"documents/{ref_doc['id']}.json")
        print(json.dumps(detalle, indent=2, ensure_ascii=False)[:2000])
        print(f"\n¿El GET puntual trae 'ted'? {'ted' in detalle}")
        print(f"¿El GET puntual trae 'number'? {'number' in detalle} -> {detalle.get('number')}")
    else:
        print("reference_document no es un dict o es None -- eso ya explica el fallo.")


if __name__ == "__main__":
    main()