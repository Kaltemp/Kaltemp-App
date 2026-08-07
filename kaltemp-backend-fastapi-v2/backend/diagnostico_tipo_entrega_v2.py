"""
diagnostico_tipo_entrega_v2.py — Compara el JSON COMPLETO de dos
documentos reales conocidos (uno "Por Despachar", otro "Entrega
Inmediata") para encontrar el campo exacto que los distingue en la API
de Bsale. También dumpea /documents/{id}/attributes.json de ambos --
los atributos personalizados de Bsale son el candidato más probable.

CONFIGURA ABAJO los 2 números de documento antes de correr: uno que
sepas con certeza que fue emitido como "Por Despachar" y otro como
"Entrega Inmediata" (mismo codeSii, para comparar manzanas con manzanas
-- ideal si son ambos Boleta).

Uso:
    export BSALE_ACCESS_TOKEN=...
    python diagnostico_tipo_entrega_v2.py
"""
import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sync"))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402

CODESII_BOLETA = 39
CODESII_FACTURA = 33

# --- 3 casos reales confirmados por William (02-ago-2026) ---
CASO_A = (CODESII_BOLETA, 37658, "POR DESPACHAR -- Boleta, Falabella marketplace")
CASO_B = (CODESII_BOLETA, 41266, "ENTREGA INMEDIATA -- Boleta, showroom")
CASO_C = (CODESII_FACTURA, 20677, "YA DESPACHADO -- Factura, Casa Matriz")
# ------------------------------------------------

# Ventana amplia por si los documentos son de fechas distintas.
FECHA_DESDE = datetime(2025, 1, 1, tzinfo=timezone.utc)
FECHA_HASTA = datetime(2026, 7, 31, tzinfo=timezone.utc)


def _buscar_documento(codesii: int, numero: int):
    fecha_desde = int(FECHA_DESDE.timestamp())
    fecha_hasta = int(FECHA_HASTA.timestamp())
    revisados = 0
    for doc in bsale_get_all(
        "documents.json",
        params={
            "codesii": codesii,
            "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]",
            "expand": "[client,details,sellers,office]",
        },
    ):
        revisados += 1
        if revisados % 1000 == 0:
            print(f"    {revisados} revisados buscando N° {numero}...")
        if doc.get("number") == numero:
            return doc
    return None


def _dump_documento(codesii: int, numero: int, etiqueta: str):
    print(f"\n{'=' * 70}\n{etiqueta} -- N° {numero} (codesii={codesii})\n{'=' * 70}")
    doc = _buscar_documento(codesii, numero)
    if not doc:
        print(f"  NO ENCONTRADA en la ventana {FECHA_DESDE.date()} a {FECHA_HASTA.date()}.")
        return None

    doc_id = doc["id"]
    print(f"\n--- Documento completo (id={doc_id}) ---")
    print(json.dumps(doc, indent=2, ensure_ascii=False))

    print(f"\n--- /documents/{doc_id}/attributes.json ---")
    try:
        attrs = list(bsale_get_all(f"documents/{doc_id}/attributes.json"))
        print(json.dumps(attrs, indent=2, ensure_ascii=False))
        if not attrs:
            print("  (vacío -- sin atributos personalizados)")
    except Exception as e:
        print(f"  ERROR: {e}")

    return doc


def main():
    doc_a = _dump_documento(*CASO_A)
    doc_b = _dump_documento(*CASO_B)
    doc_c = _dump_documento(*CASO_C)

    if doc_a and doc_b:
        print(f"\n\n{'=' * 70}\nCOMPARACIÓN A vs B (mismo codeSii=Boleta): campos que DIFIEREN\n{'=' * 70}")
        claves = set(doc_a.keys()) | set(doc_b.keys())
        for k in sorted(claves):
            va, vb = doc_a.get(k), doc_b.get(k)
            if va != vb:
                print(f"  {k}:\n    A (por despachar)     = {va!r}\n    B (entrega inmediata) = {vb!r}")

    if doc_a and doc_c:
        print(f"\n\n{'=' * 70}\nCOMPARACIÓN A vs C (distinto codeSii, ambos 'con despacho'): campos comunes iguales\n{'=' * 70}")
        print("(Menos preciso por ser Boleta vs Factura, pero sirve como referencia extra)")
        claves = set(doc_a.keys()) & set(doc_c.keys())
        for k in sorted(claves):
            va, vc = doc_a.get(k), doc_c.get(k)
            marca = "≈ igual" if va == vc else "≠ distinto"
            print(f"  {k}: A={va!r} | C={vc!r}  [{marca}]")


if __name__ == "__main__":
    main()