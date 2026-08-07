"""
diagnostico_numero_pedido.py — Busca dónde vive el N° de Pedido (marketplace)
dentro de un documento Bsale real, para una boleta de canal Falabella/
Mercadolibre. Revisa 3 lugares posibles:
  1) El campo 'note' de cada línea de detalle (¿lo trae el pedido ahí?)
  2) El sub-recurso /documents/{id}/references.json (documentos relacionados)
  3) Cualquier campo de texto libre en el documento mismo (observations, etc.)

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_numero_pedido.py
"""
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sync"))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402

# Boleta real de canal "Kaltemp Falabella" (vendedor), confirmada en
# pendientes_despacho_docs: BOLETA N° 37658, Carlo Veragua, emitida
# 2026-01-05. Se acota la búsqueda a una ventana de fecha estrecha --
# SIN esto, el script recorre TODA la historia de boletas de la cuenta
# (decenas de miles) una por una, lo que puede tardar minutos u horas sin
# mostrar ningún avance (justo lo que pasó en el primer intento).
NUMERO_BUSCADO = 37658
CODESII_BOLETA = 39
FECHA_DESDE = datetime(2026, 1, 1, tzinfo=timezone.utc)
FECHA_HASTA = datetime(2026, 1, 15, tzinfo=timezone.utc)


def main():
    fecha_desde_epoch = int(FECHA_DESDE.timestamp())
    fecha_hasta_epoch = int(FECHA_HASTA.timestamp())
    print(f"Buscando BOLETA N° {NUMERO_BUSCADO} (codesii={CODESII_BOLETA}), "
          f"ventana {FECHA_DESDE.date()} a {FECHA_HASTA.date()}...")
    encontrado = None
    revisados = 0
    for doc in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_BOLETA,
            "emissiondaterange": f"[{fecha_desde_epoch},{fecha_hasta_epoch}]",
            "expand": "[client,details,sellers,office]",
        },
    ):
        revisados += 1
        if revisados % 50 == 0:
            print(f"  {revisados} documentos revisados en la ventana...")
        if doc.get("number") == NUMERO_BUSCADO:
            encontrado = doc
            break

    if not encontrado:
        print(f"No se encontró tras revisar {revisados} documentos en la ventana. "
              "Puede que la fecha real sea otra -- amplía FECHA_DESDE/FECHA_HASTA.")
        return

    doc_id = encontrado["id"]
    print(f"\n=== Documento encontrado, id={doc_id} ===")

    print("\n--- 1) Campo 'note' de cada línea de detalle ---")
    details = encontrado.get("details")
    lineas = details.get("items", []) if isinstance(details, dict) else details
    if not lineas:
        lineas = list(bsale_get_all(f"documents/{doc_id}/details.json"))
    for linea in lineas:
        print(json.dumps({
            "id": linea.get("id"),
            "note": linea.get("note"),
            "variant_code": (linea.get("variant") or {}).get("code"),
            "variant_description": (linea.get("variant") or {}).get("description"),
        }, indent=2, ensure_ascii=False))

    print("\n--- 2) /documents/{id}/references.json (documentos relacionados) ---")
    try:
        referencias = list(bsale_get_all(f"documents/{doc_id}/references.json"))
        print(json.dumps(referencias, indent=2, ensure_ascii=False)[:3000])
        if not referencias:
            print("(vacío -- sin documentos relacionados registrados)")
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n--- 3) Todos los campos de texto del documento (buscando algo tipo pedido/orden) ---")
    for k, v in encontrado.items():
        if isinstance(v, str) and len(v) < 200:
            print(f"  {k}: {v!r}")


if __name__ == "__main__":
    main()