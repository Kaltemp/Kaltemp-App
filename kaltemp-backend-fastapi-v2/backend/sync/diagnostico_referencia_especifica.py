"""
diagnostico_referencia_especifica.py — Inspecciona el JSON crudo de
references.json para la Guía N° 57648, que confirmamos manualmente en
Bsale que SÍ referencia la Boleta N° 41660 (caso de validación real).
El sync la marcó como "sin guía" -- este script muestra el JSON exacto
para ver por qué mi comparación no la detectó.

Uso:
    python diagnostico_referencia_especifica.py
"""
import os
import sys
import json

# Fuerza UTF-8 en stdout: al redirigir con ">" en PowerShell, Windows usa
# cp1252 por defecto, que no soporta emojis (✅, ⚠️) ni siempre tildes -- eso
# cortaba el script a la primera línea con UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402

NUMERO_GUIA = 57648
CODESII_GUIA = 52


def main():
    print(f"Buscando la Guía N° {NUMERO_GUIA} (codesii={CODESII_GUIA})...")
    guia = None
    for doc in bsale_get_all("documents.json", params={"codesii": CODESII_GUIA, "number": NUMERO_GUIA}):
        guia = doc
        break

    if not guia:
        print("❌ No se encontró la guía con ese número + codesii. Probando sin filtro de codesii...")
        for doc in bsale_get_all("documents.json", params={"number": NUMERO_GUIA}):
            print("  candidato:", json.dumps(doc, indent=2, ensure_ascii=False)[:500])
        return

    print(f"✅ Guía encontrada: id={guia['id']}, number={guia.get('number')}")
    print()
    print("=" * 70)
    print("Buscando la Boleta N° 41660 (codesii=39) para comparar sus detailId...")
    print("=" * 70)
    boleta = None
    for doc in bsale_get_all("documents.json", params={"codesii": 39, "number": 41660}):
        boleta = doc
        break
    if boleta:
        print(f"✅ Boleta encontrada: id={boleta['id']}, number={boleta.get('number')}")
        print("Detalles de la boleta:")
        ids_boleta = []
        for d in bsale_get_all(f"documents/{boleta['id']}/details.json"):
            print(json.dumps(d, indent=2, ensure_ascii=False))
            ids_boleta.append(d.get("id"))
            print("-" * 40)
        print(f"IDs de detalle de la boleta: {ids_boleta}")
    else:
        print("❌ No se encontró la boleta 41660 con codesii=39")

    print()
    print("=" * 70)
    print(f"JSON completo de /v1/documents/{guia['id']}.json (todos los campos)")
    print("=" * 70)
    detalle_guia = bsale_get_one(f"documents/{guia['id']}.json", {"expand": "[details,references]"})
    print(json.dumps(detalle_guia, indent=2, ensure_ascii=False))

    print()
    print("=" * 70)
    print(f"JSON de /v1/documents/{guia['id']}/details.json (líneas de la guía)")
    print("=" * 70)
    for d in bsale_get_all(f"documents/{guia['id']}/details.json"):
        print(json.dumps(d, indent=2, ensure_ascii=False))
        print("-" * 40)

    print()
    print("=" * 70)
    print(f"JSON crudo de /v1/documents/{guia['id']}/references.json")
    print("=" * 70)

    refs = list(bsale_get_all(f"documents/{guia['id']}/references.json"))
    if not refs:
        print("⚠️ Esta guía no trae NINGUNA referencia -- el vínculo con la boleta")
        print("   vive en otro lugar (no en /references.json de la guía).")
    for r in refs:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print("-" * 40)

    print()
    print("=" * 70)
    print("Comparación: ¿aparece el número 41660 en algún campo de arriba?")
    print("=" * 70)
    crudo = json.dumps(refs, ensure_ascii=False)
    print("Contiene '41660':", "41660" in crudo)


if __name__ == "__main__":
    main()
