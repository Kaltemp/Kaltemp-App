"""
sync_master_nuevas_tablas.py — Corre los 3 scripts nuevos en orden.

No reemplaza tu sync_master.py existente (que ya sincroniza ventas,
leads, envíame, etc.) — este es solo para las 3 tablas nuevas. Una vez
que confirmes que los resultados se ven bien, puedes copiar estas 3
llamadas dentro de tu sync_master.py real.

Uso manual:    python sync_master_nuevas_tablas.py
Uso en cron:   */20 * * * * cd /ruta/backend/sync && /ruta/venv/bin/python sync_master_nuevas_tablas.py >> /var/log/kaltemp_sync_nuevas.log 2>&1
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from sync_stock_bsale import sync_stock  # noqa: E402
from sync_notas_credito import sync_notas_credito  # noqa: E402

# ⚠️ sync_pendientes_despacho.py está OBSOLETO y ya no se corre acá.
# El módulo "Pendientes por Despachar" ahora se deriva de RESERVADO en
# `stock_bsale` (misma tabla y sync que Stock) -- sync_stock_bsale.py de
# abajo alimenta a los 2 módulos a la vez, sin necesitar un sync aparte.

PASOS = [
    ("stock_bsale", sync_stock),
    ("notas_credito_desfase", sync_notas_credito),
]


def main():
    print(f"\n{'='*70}\n[{datetime.now()}] Iniciando sync de tablas nuevas\n{'='*70}")
    resultados = {}
    for nombre, funcion in PASOS:
        try:
            funcion()
            resultados[nombre] = "OK"
        except Exception as e:
            print(f"❌ Error sincronizando {nombre}: {e}")
            resultados[nombre] = f"ERROR: {e}"

    print(f"\n{'='*70}\nResumen:")
    for nombre, estado in resultados.items():
        print(f"  {nombre}: {estado}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
