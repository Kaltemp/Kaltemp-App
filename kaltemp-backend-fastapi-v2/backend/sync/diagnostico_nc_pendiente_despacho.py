# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_nc_pendiente_despacho.py
"""
diagnostico_nc_pendiente_despacho.py

Objetivo: confirmar, con el caso real que reportó William (Factura
Electrónica N° 17303 / Nota de Crédito N° 3563), que el módulo de
Pendientes por Despachar puede detectar documentos que en realidad NO
están pendientes porque ya tienen una Nota de Crédito asociada (aunque
nunca hayan tenido guía de despacho).

Qué hace:
1. Busca en returns.json (expand=[credit_note,reference_document]) la
   devolución cuyo reference_document.number == 17303, y también la que
   tiene credit_note.number == 3563 (por si el cruce por número de
   factura fallara, para comparar).
2. Imprime el reference_document y credit_note crudos.
3. Muestra la fecha de emisión de la NC, para decidir si el cruce se
   puede apoyar en `notas_credito_desfase` (ventana NC_FECHA_DESDE) o si
   hay que escanear returns.json completo dentro de
   sync_pendientes_despacho.py.
4. Cuenta cuántas devoluciones totales trae la cuenta (para estimar el
   costo de tiempo de escanear returns.json completo en cada corrida).

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python diagnostico_nc_pendiente_despacho.py
(usa las credenciales del .env raíz, igual que los demás scripts de sync)
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402

NUMERO_FACTURA_BUSCADA = "17303"
NUMERO_NC_BUSCADA = "3563"


def _con_reintento(generador_fn, intentos=3):
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
    print(f"Buscando en returns.json: reference_document.number == {NUMERO_FACTURA_BUSCADA} "
          f"o credit_note.number == {NUMERO_NC_BUSCADA} ...")
    encontrada_por_factura = None
    encontrada_por_nc = None
    revisadas = 0

    generador = lambda: bsale_get_all(
        "returns.json", params={"expand": "[credit_note,reference_document]"}
    )
    for devolucion in _con_reintento(generador):
        revisadas += 1
        ref_doc = devolucion.get("reference_document")
        credit_note = devolucion.get("credit_note")

        if isinstance(ref_doc, dict) and str(ref_doc.get("number")) == NUMERO_FACTURA_BUSCADA:
            encontrada_por_factura = devolucion

        if isinstance(credit_note, dict) and str(credit_note.get("number")) == NUMERO_NC_BUSCADA:
            encontrada_por_nc = devolucion

        if revisadas % 500 == 0:
            print(f"  {revisadas} devoluciones revisadas...")

        # Una vez que tenemos ambas (o hemos revisado bastante), no hace
        # falta seguir pagando la paginación completa para este diagnóstico.
        if encontrada_por_factura and encontrada_por_nc:
            break

    print(f"\n=== Total revisadas hasta encontrar (o agotar búsqueda): {revisadas} ===")

    print("\n--- Resultado búsqueda por N° de Factura (17303) ---")
    if encontrada_por_factura:
        print(json.dumps(encontrada_por_factura, indent=2, ensure_ascii=False)[:3000])
    else:
        print("NO encontrada por número de factura en el reference_document.")

    print("\n--- Resultado búsqueda por N° de Nota de Crédito (3563) ---")
    if encontrada_por_nc:
        print(json.dumps(encontrada_por_nc, indent=2, ensure_ascii=False)[:3000])
        cn = encontrada_por_nc.get("credit_note", {})
        print(f"\nFecha emisión NC (emissionDate crudo, epoch): {cn.get('emissionDate')}")
    else:
        print("NO encontrada por número de nota de crédito.")

    if not encontrada_por_factura and not encontrada_por_nc:
        print("\n[!] No se encontró ninguna de las dos en las primeras "
              f"{revisadas} devoluciones revisadas. Puede que returns.json "
              "no esté ordenado de forma que la encontremos rápido -- "
              "avisar a Claude con este resultado antes de seguir.")

    # --- Conteo total de devoluciones (para estimar costo de escanear
    #     returns.json completo sin filtro de fecha) ---
    print("\n\nContando el total de devoluciones en la cuenta (puede demorar)...")
    total = 0
    t0 = time.time()
    for _ in _con_reintento(lambda: bsale_get_all("returns.json", params={"expand": "[credit_note]"})):
        total += 1
        if total % 1000 == 0:
            print(f"  {total} devoluciones contadas... ({time.time() - t0:.0f}s transcurridos)")
    print(f"\n=== TOTAL devoluciones en la cuenta: {total} (tardó {time.time() - t0:.0f}s) ===")


if __name__ == "__main__":
    main()