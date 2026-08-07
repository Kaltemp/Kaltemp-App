"""
diagnostico_tipo_entrega.py — Verifica si Bsale distingue "Por Despachar"
de "Entrega Inmediata" mediante documentTypeId distintos (mismo codeSii),
igual que ya se descubrió con las Guías de Despacho (ver
diagnostico_guias_bsale.py). Si es así, basta con NO filtrar por un solo
documentTypeId -- hay que revisar el NAME de cada uno para decidir cuál
incluir/excluir.

También revisa, para una boleta real conocida (N° 37658, canal Falabella,
la misma del diagnóstico anterior), qué documentTypeId/name le tocó --
así confirmamos contra un caso real si es "Por Despachar" o "Entrega
Inmediata".

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_tipo_entrega.py
"""
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sync"))
from bsale_client import bsale_get_all  # noqa: E402

CODESII_BOLETA = 39
CODESII_FACTURA = 33


def main():
    print("=== 1) Todos los document_types con codeSii=39 (Boleta) o 33 (Factura) ===")
    tipos_relevantes = []
    for dt in bsale_get_all("document_types.json"):
        code = dt.get("codeSii")
        if code in (CODESII_BOLETA, CODESII_FACTURA):
            tipos_relevantes.append(dt)
            print(f"  id={dt.get('id'):<5} codeSii={code:<5} name={dt.get('name')!r}")

    if len({dt["id"] for dt in tipos_relevantes}) <= 2:
        print("\n  (Solo 1 documentTypeId por codeSii -- la distinción 'Por Despachar' vs "
              "'Entrega Inmediata' probablemente NO está en documentTypeId. Revisar 'attributes'.)")
    else:
        print(f"\n  ¡{len(tipos_relevantes)} documentTypeId distintos encontrados para solo 2 "
              f"codeSii! Revisa los 'name' de arriba -- probablemente ahí está la distinción.")

    print("\n=== 2) Caso real: BOLETA N° 37658 (Falabella, 2026-01-05) -- ¿qué documentTypeId le tocó? ===")
    fecha_desde = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    fecha_hasta = int(datetime(2026, 1, 15, tzinfo=timezone.utc).timestamp())
    encontrado = None
    for doc in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_BOLETA,
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
        },
    ):
        if doc.get("number") == 37658:
            encontrado = doc
            break

    if encontrado:
        doctype_obj = encontrado.get("document_type")
        doctype_id = doctype_obj.get("id") if isinstance(doctype_obj, dict) else encontrado.get("documentTypeId")
        nombre = next((dt.get("name") for dt in tipos_relevantes if str(dt.get("id")) == str(doctype_id)), "??")
        print(f"  documentTypeId={doctype_id} -> name={nombre!r}")
    else:
        print("  No se encontró la boleta en esta ventana de fecha.")

    print("\n=== 3) Muestra de 10 boletas/facturas recientes con su documentTypeId/name ===")
    print("  (para ver si realmente se reparten entre los distintos tipos, o si en la práctica")
    print("   casi todo cae en uno solo)")
    fecha_desde2 = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp())
    fecha_hasta2 = int(datetime(2026, 7, 31, tzinfo=timezone.utc).timestamp())
    contador_por_tipo = {}
    revisados = 0
    for doc in bsale_get_all(
        "documents.json",
        params={
            "codesii": CODESII_BOLETA,
            "emissiondaterange": f"[{fecha_desde2},{fecha_hasta2}]",
        },
    ):
        revisados += 1
        doctype_obj = doc.get("document_type")
        doctype_id = doctype_obj.get("id") if isinstance(doctype_obj, dict) else doc.get("documentTypeId")
        contador_por_tipo[doctype_id] = contador_por_tipo.get(doctype_id, 0) + 1
        if revisados >= 300:  # muestra representativa de julio 2026, no todo el mes
            break

    for doctype_id, cantidad in sorted(contador_por_tipo.items(), key=lambda x: -x[1]):
        nombre = next((dt.get("name") for dt in tipos_relevantes if str(dt.get("id")) == str(doctype_id)), "??")
        print(f"  documentTypeId={doctype_id} ({nombre!r}): {cantidad} boletas de {revisados} revisadas")


if __name__ == "__main__":
    main()