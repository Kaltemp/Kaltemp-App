"""
sync/sync_master.py — Motor de actualización maestro único.
Orquesta todos los scripts de sync en el orden correcto, con manejo de
errores por paso y resumen final.
"""
import sys
import os
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync_temperaturas import sync_temperaturas  # noqa: E402
from sync_sku_maestro import sync_sku_maestro  # noqa: E402
from sync_ventas import sync_ventas  # noqa: E402
from sync_leads import sync_leads  # noqa: E402
from sync_abandoned_carts import sync_abandoned_carts  # noqa: E402
from sync_marketing import sync_marketing  # noqa: E402
from sync_stock_bsale import sync_stock  # noqa: E402
from sync_pendientes_documentos import sync_pendientes_documentos  # noqa: E402
from sync_notas_credito import sync_notas_credito  # noqa: E402
from sync_falabella_estados import sync_falabella_estados  # noqa: E402
from sync_enviame import sync_enviame  # noqa: E402
from actualizar_fletes_enviame import ejecutar_actualizacion_costos  # noqa: E402

PASOS = [
    ("temperaturas", sync_temperaturas),
    ("sku_maestro", sync_sku_maestro),
    ("ventas", lambda: sync_ventas(dias_atras=30)),
    ("leads", sync_leads),
    ("abandoned_checkouts", sync_abandoned_carts),
    ("marketing", sync_marketing),
    ("stock_bsale", sync_stock),
    ("pendientes_despacho_docs", sync_pendientes_documentos),
    ("notas_credito_desfase", sync_notas_credito),
    ("falabella_estados_pedido", sync_falabella_estados),
    ("enviame_despachos", sync_enviame),
    ("enviame_despachos.COSTO_ENVIO", ejecutar_actualizacion_costos),
]


def main():
    print(f"\n{'='*70}\n[{datetime.now()}] Iniciando motor de actualización maestro Kaltemp\n{'='*70}")
    resultados = {}
    for nombre, funcion in PASOS:
        print(f"\n--- Ejecutando: {nombre} ---")
        try:
            funcion()
            resultados[nombre] = "OK"
        except Exception as e:
            print(f"❌ Error en paso {nombre}: {e}")
            traceback.print_exc()
            resultados[nombre] = f"ERROR: {e}"

    print(f"\n{'='*70}\nResumen de Sincronización [{datetime.now()}]:")
    for nombre, estado in resultados.items():
        icono = "✅" if estado == "OK" else "❌"
        print(f"  {icono} {nombre}: {estado}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()