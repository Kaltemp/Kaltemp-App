"""
diagnostico_commercial_state.py — Solo lectura contra la API de Bsale (no
escribe nada en DuckDB). Investiga 2 cosas antes de confiar en el campo
`commercialState` (no documentado oficialmente, visto en respuestas reales
de documents.json) para clasificar Pendiente/Despachado:

  1) Qué valores toma `commercialState` en un caso 100% conocido: la boleta
     41660 (ya confirmaste manualmente que despachó vía guía 57648).
  2) Si `commercialState` correlaciona con nuestra clasificación actual
     (relatedDetailId) en una muestra de documentos recientes -- si NO
     correlaciona bien, es señal de que uno de los 2 métodos está mal.

También trae /v1/stocks.json (quantityReserved agregado) como número de
control independiente: si el total pendiente reconstruido (1499 docs) está
muy lejos de lo que Bsale reporta como "reservado por despachar" a nivel de
stock, es una alerta adicional de que el 96% de "críticos" no es real.

Uso:
    export BSALE_ACCESS_TOKEN=...
    cd backend/sync
    python diagnostico_commercial_state.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402


def _epoch(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


print("=" * 70)
print("1) Caso conocido: boleta N° 41660 (codesii=39) -- ya confirmado que")
print("   SÍ despachó, vía guía 57648. Buscamos su commercialState real.")
print("=" * 70)
encontrada = False
for doc in bsale_get_all("documents.json", params={"codesii": 39, "number": 41660}):
    encontrada = True
    print(f"  id={doc.get('id')} number={doc.get('number')} "
          f"state={doc.get('state')} commercialState={doc.get('commercialState')} "
          f"totalAmount={doc.get('totalAmount')}")
if not encontrada:
    print("  No se encontró (¿folio distinto o fuera de rango por defecto?). "
          "Prueba ajustar el filtro si hace falta.")

print()
print("=" * 70)
print("2) Muestra de 30 boletas recientes: comparamos commercialState vs")
print("   nuestra clasificación actual (relatedDetailId contra guías)")
print("=" * 70)
fecha_desde = _epoch(datetime.now(timezone.utc) - timedelta(days=30))
fecha_hasta = _epoch(datetime.now(timezone.utc))

# Reconstruye el mismo mapa relatedDetailId -> monto_guia que usa el sync,
# pero solo para los últimos 30 días (más rápido para este diagnóstico).
mapa_detail_id_a_monto_guia = {}
for guia in bsale_get_all(
    "documents.json",
    params={"codesii": 52, "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]", "expand": "[details]"},
):
    monto_guia = float(guia.get("totalAmount", 0) or 0)
    details = guia.get("details")
    items = details.get("items", []) if isinstance(details, dict) else []
    for linea in items:
        rid = linea.get("relatedDetailId")
        if rid:
            mapa_detail_id_a_monto_guia[rid] = monto_guia

contador_valores_commercial_state = {}
coincidencias = 0
total_muestra = 0
for doc in bsale_get_all(
    "documents.json",
    params={"codesii": 39, "emissiondaterange": f"[{fecha_desde},{fecha_hasta}]", "expand": "[details]"},
    max_items=30,
):
    total_muestra += 1
    cs = doc.get("commercialState")
    contador_valores_commercial_state[cs] = contador_valores_commercial_state.get(cs, 0) + 1

    details = doc.get("details")
    items = details.get("items", []) if isinstance(details, dict) else []
    ids_propios = {d.get("id") for d in items if d.get("id")}
    tiene_guia_reconstruido = bool(ids_propios & mapa_detail_id_a_monto_guia.keys())

    # Hipótesis a validar: commercialState == 1 (o != 0) equivale a "tiene guía"
    hipotesis_despachado = cs not in (0, None)
    coincide = hipotesis_despachado == tiene_guia_reconstruido
    coincidencias += coincide
    print(f"  Doc {doc.get('number')}: commercialState={cs!r}  "
          f"reconstruido_tiene_guia={tiene_guia_reconstruido}  "
          f"{'✅ coincide' if coincide else '❌ DISCREPANCIA'}")

print()
print(f"  Distribución de commercialState en la muestra: {contador_valores_commercial_state}")
print(f"  Coincidencias hipótesis vs reconstrucción actual: {coincidencias}/{total_muestra}")

print()
print("=" * 70)
print("3) Número de control: stocks.json -> suma de quantityReserved")
print("   ('cantidad reservada... en documentos pendientes de despachar')")
print("=" * 70)
total_reservado = 0.0
n_variantes_con_reserva = 0
for stock in bsale_get_all("stocks.json"):
    qr = float(stock.get("quantityReserved", 0) or 0)
    if qr > 0:
        total_reservado += qr
        n_variantes_con_reserva += 1
print(f"  Suma total quantityReserved (todas las sucursales): {total_reservado}")
print(f"  Variantes con reserva > 0: {n_variantes_con_reserva}")
print("  (Compara este total de UNIDADES contra las ~1499 DOCUMENTOS que hoy")
print("   muestra el módulo -- no son la misma unidad de medida, pero si el")
print("   orden de magnitud es muy distinto, es otra señal de alerta.)")