# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\diagnostico_falabella_retencion.py
"""
diagnostico_falabella_retencion.py

1. Prueba GetOrders directo contra enero 2025 -- ¿la API devuelve algo,
   o confirma que no retiene pedidos tan viejos?
2. Si devuelve algo, busca si los OrderNumber del ejemplo real
   (3501007626, 3501013134, 3501011179, 3501011250) están entre ellos.
3. Dumpea el JSON CRUDO de un pedido reciente (últimos 30 días) para ver
   TODOS los campos que trae GetOrders -- buscamos algo tipo
   "FulfillmentBy"/"IsFulfillmentByFalabella"/similar que explique si hay
   pedidos que la cuenta simplemente no puede ver.

Uso (desde backend/sync/, con venv activo):
    python diagnostico_falabella_retencion.py
"""
import sys
import os
import json
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from falabella_client import get_orders  # noqa: E402

PEDIDOS_BUSCADOS = {"3501007626", "3501013134", "3501011179", "3501011250"}


def main():
    print("=" * 70)
    print("PRUEBA 1: GetOrders para enero 2025 (¿retiene la API algo tan viejo?)")
    print("=" * 70)
    pedidos_2025 = get_orders(date(2025, 1, 1), date(2025, 1, 31))
    print(f"Pedidos devueltos por la API para enero 2025: {len(pedidos_2025)}")

    if pedidos_2025:
        encontrados = [
            p for p in pedidos_2025
            if str(p.get("OrderNumber", p.get("OrderId"))) in PEDIDOS_BUSCADOS
        ]
        print(f"¿Están los 4 pedidos buscados entre ellos? {len(encontrados)} encontrados de 4")
        print("\nPrimeros 3 pedidos devueltos (para ver el formato real):")
        for p in pedidos_2025[:3]:
            print(json.dumps(p, indent=2, ensure_ascii=False)[:1000])
            print("---")
    else:
        print("La API no devolvió NADA para enero 2025 -- confirma que no hay retención")
        print("tan atrás en el tiempo (o que esos pedidos específicos no existen para")
        print("esta cuenta). Con esto ya sabemos que ampliar FALABELLA_FECHA_DESDE no")
        print("va a traer estos 4 pedidos puntuales.")

    print("\n" + "=" * 70)
    print("PRUEBA 2: JSON crudo de pedidos recientes (buscamos campo de Fulfillment)")
    print("=" * 70)
    hoy = date.today()
    pedidos_recientes = get_orders(hoy - timedelta(days=30), hoy)
    print(f"Pedidos últimos 30 días: {len(pedidos_recientes)}")
    if pedidos_recientes:
        print("\nJSON completo del primer pedido (todos los campos disponibles):")
        print(json.dumps(pedidos_recientes[0], indent=2, ensure_ascii=False))

        print("\n--- Buscando keys que mencionen 'fulfil' o 'warehouse' en cualquier pedido ---")
        keys_relevantes = set()
        for p in pedidos_recientes:
            for k in p.keys():
                if "fulfil" in k.lower() or "warehouse" in k.lower():
                    keys_relevantes.add(k)
        print(f"Keys encontradas: {keys_relevantes if keys_relevantes else 'ninguna'}")
    else:
        print("No hay pedidos en los últimos 30 días -- raro, revisar credenciales/cuenta.")


if __name__ == "__main__":
    main()