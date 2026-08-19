"""
Carga historica de ventas de fulfillment (Mercado Libre, Paris, Ripley,
y Falabella SOLO antes del 2025-01-03) desde tu archivo VENTAS_FULL.xlsx
(exportado de tu Power BI antiguo) hacia la tabla `ventas`.

Por que es seguro (confirmado con diagnosticos previos, todos de solo
lectura, corridos por William):
  - CANAL='MERCADOLIBRE'/'PARIS'/'RIPLEY'/'FALABELLA' + ORIGEN='BSALE' que
    ya existe en `ventas` es venta DIRECTA con documento real (boleta/
    factura), no fulfillment -- no se solapa con este archivo.
  - ORIGEN='BSALE_FULL' (el que deberia traer fulfillment via consumo)
    tiene 0 filas hoy en `ventas` -- nunca se cargo nada de esto.
  - Falabella desde el 2025-01-03 en adelante ya esta 100% cubierto por
    ORIGEN='FALABELLA_API' (Seller Center, tiempo real) -- por eso este
    script EXCLUYE esas filas del Excel, para no duplicar.

Este script:
  1) Lee full_historico_a_cargar.csv (ya filtrado -- 6972 filas: 1365
     Falabella pre-2025-01-03, 5107 Mercado Libre, 333 Paris, 167 Ripley).
  2) Para cada uno de los 51 SKU distintos, resuelve el costo actual real
     desde Bsale (mismo mecanismo que ya usa sync_ventas.py para las
     lineas de Falabella que no tienen documento propio) y la categoria
     (categorias_manual -> sku_maestro, misma prioridad que sync_ventas.py).
  3) Arma las filas finales con el mismo esquema de `ventas`, con
     ORIGEN='FULL_HISTORICO_MANUAL' (asi queda 100% trazable y distinto
     de cualquier sync automatico presente o futuro).
  4) Imprime un RESUMEN (filas y monto por canal+mes, mas 10 filas de
     muestra ya calculadas) y pide confirmacion explícita ANTES de
     escribir nada en la base.
  5) Si confirmas, borra cualquier carga anterior con este mismo ORIGEN
     (para que el script se pueda re-correr sin duplicar) e inserta todo.

IMPORTANTE -- supuesto a confirmar: la columna "Monto" del Excel se trata
como MONTO BRUTO (con IVA incluido) de la linea completa (no unitario) --
consistente con el formato "precio unitario $X" visto en los consumos
reales de Bsale. NETO_TOTAL = MONTO / 1.19. Si tu Excel en realidad
guardaba el monto SIN IVA, avisame antes de confirmar la carga.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    python cargar_ventas_full_historico.py
    (full_historico_a_cargar.csv debe estar en la misma carpeta)
"""
import os
import csv
import sys
import datetime
import requests
import duckdb
from dotenv import load_dotenv
from collections import defaultdict

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

BSALE_TOKEN = os.getenv("BSALE_TOKEN") or os.getenv("BSALE_ACCESS_TOKEN")
HEADERS = {"access_token": BSALE_TOKEN, "Content-Type": "application/json"}
BASE = "https://api.bsale.cl/v1"

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
CSV_PATH = os.path.join(_AQUI, "full_historico_a_cargar.csv")
print(f"Base de datos que se va a modificar: {DB_FILE}")
ORIGEN_TAG = "FULL_HISTORICO_MANUAL"

if not BSALE_TOKEN:
    print("❌ Falta BSALE_TOKEN (o BSALE_ACCESS_TOKEN) en el .env")
    raise SystemExit(1)

if not os.path.exists(CSV_PATH):
    print(f"❌ No se encuentra {CSV_PATH} -- debe estar en la misma carpeta que este script.")
    raise SystemExit(1)


# ---------------------------------------------------------------------
# 1) Leer el CSV
# ---------------------------------------------------------------------
filas_csv = []
with open(CSV_PATH, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        filas_csv.append(row)
print(f"Filas leidas del CSV: {len(filas_csv)}")


# ---------------------------------------------------------------------
# 2) Resolver costo actual por SKU (mismo mecanismo que sync_ventas.py)
# ---------------------------------------------------------------------
def resolver_variant_id_por_sku(sku, cache):
    sku_norm = str(sku).strip().upper()
    if sku_norm in cache:
        return cache[sku_norm]
    variant_id = None
    try:
        resp = requests.get(f"{BASE}/variants.json", headers=HEADERS,
                             params={"code": sku_norm, "limit": 1}, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                variant_id = items[0].get("id")
    except Exception:
        pass
    cache[sku_norm] = variant_id
    return variant_id


def obtener_costo_actual_variante(variant_id, cache):
    if variant_id in cache:
        return cache[variant_id]
    costo = 0.0
    try:
        resp = requests.get(f"{BASE}/variants/{variant_id}/costs.json", headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            historial = data.get("history") or []
            if historial:
                ultima = max(historial, key=lambda h: h.get("admissionDate", 0))
                costo = float(ultima.get("cost", 0) or 0)
            else:
                costo = float(data.get("averageCost", 0) or 0)
    except Exception:
        pass
    cache[variant_id] = costo
    return costo


skus_distintos = sorted(set(r["SKU"].strip().upper() for r in filas_csv if r["SKU"]))
print(f"SKUs distintos a resolver: {len(skus_distintos)}")

cache_variant_id = {}
cache_costo = {}
costo_por_sku = {}
for i, sku in enumerate(skus_distintos, 1):
    v_id = resolver_variant_id_por_sku(sku, cache_variant_id)
    costo = obtener_costo_actual_variante(v_id, cache_costo) if v_id else 0.0
    costo_por_sku[sku] = costo
    print(f"  [{i}/{len(skus_distintos)}] SKU={sku}  variant_id={v_id}  costo_actual={costo:,.0f}")

skus_sin_costo = [s for s, c in costo_por_sku.items() if c == 0]
if skus_sin_costo:
    print(f"\n⚠️ {len(skus_sin_costo)} SKU sin costo resuelto (quedaran con COSTO_TOTAL=0, "
          f"CONTRIBUCION=NETO completo): {skus_sin_costo}")


# ---------------------------------------------------------------------
# 3) Resolver categoria por SKU (categorias_manual gana, sku_maestro respaldo)
# ---------------------------------------------------------------------
def cargar_mapa_categorias_sku():
    mapa = {}
    try:
        with duckdb.connect(DB_FILE, read_only=True) as con:
            existe = con.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'sku_maestro'"
            ).fetchone()
            if existe:
                filas = con.execute("SELECT SKU, CATEGORIA FROM sku_maestro").fetchall()
                mapa.update({str(sku).strip().upper(): cat for sku, cat in filas if sku})
    except Exception as e:
        print(f"⚠️ No se pudo leer sku_maestro: {e}")

    try:
        from categorias_db import get_categorias_connection, init_categorias_db
        init_categorias_db()
        with get_categorias_connection() as con:
            filas = con.execute("SELECT sku, categoria FROM categorias_manual").fetchall()
            for row in filas:
                sku = str(row["sku"]).strip().upper()
                if sku:
                    mapa[sku] = row["categoria"]
    except Exception as e:
        print(f"⚠️ No se pudo leer categorias_manual (¿estas corriendo esto desde backend\\?): {e}")

    return mapa


mapa_categorias = cargar_mapa_categorias_sku()
print(f"\nCategorias resueltas para {sum(1 for s in skus_distintos if s in mapa_categorias)} "
      f"de {len(skus_distintos)} SKUs.")


# ---------------------------------------------------------------------
# 4) Armar filas finales
# ---------------------------------------------------------------------
filas_finales = []
filas_saltadas = []
for r in filas_csv:
    canal = r["CANAL"].strip().upper()
    sku = r["SKU"].strip().upper()
    cantidad = int(float(r["CANTIDAD"]))

    # El Excel original trae al menos 1 fila con "Monto" vacío (dato faltante
    # de origen, no un error de este script) -- se salta con aviso en vez de
    # reventar toda la carga por 1 fila.
    if not r["MONTO"].strip():
        filas_saltadas.append(r)
        continue
    monto_bruto = float(r["MONTO"])
    neto = monto_bruto / 1.19
    costo_unit = costo_por_sku.get(sku, 0.0)
    costo_total = costo_unit * cantidad
    contribucion = neto - costo_total
    fecha_obj = datetime.datetime.strptime(r["FECHA"], "%Y-%m-%d")
    categoria = mapa_categorias.get(sku, "Sin Categoría Mapeada")

    filas_finales.append({
        "DOCUMENTO": f"{canal} HISTÓRICO N° {r['ORDEN']}",
        "PRODUCTO": str(r["TITULO_MKT"]).upper(),
        "SKU_BSALE": sku,
        "CANTIDAD": cantidad,
        "NETO_TOTAL": neto,
        "BRUTO_TOTAL": monto_bruto,
        "COSTO_TOTAL": costo_total,
        "CONTRIBUCION": contribucion,
        "CANAL": canal,
        "VENDEDOR": f"KALTEMP {canal}",
        "CLIENTE": "CLIENTE FULFILLMENT",
        "CATEGORIA": categoria,
        "FECHA_OBJ": fecha_obj,
        "ORIGEN": ORIGEN_TAG,
        "TIPO_DOCUMENTO": "PEDIDO FULFILLMENT HISTÓRICO",
        "NUMERO_DOCUMENTO": r["ORDEN"],
        "SUCURSAL": canal,
        "ES_GLOSA_SERVICIO": False,
    })

print(f"\nFilas finales armadas: {len(filas_finales)}")
if filas_saltadas:
    print(f"⚠️ {len(filas_saltadas)} fila(s) del CSV saltadas por venir con 'Monto' vacío en el Excel original "
          f"(no se cargan, no se pueden calcular sin un monto):")
    for r in filas_saltadas:
        print(f"   CANAL={r['CANAL']} ORDEN={r['ORDEN']} SKU={r['SKU']} FECHA={r['FECHA']}")


# ---------------------------------------------------------------------
# 5) Resumen por canal + mes, y muestra de 10 filas -- ANTES de escribir nada
# ---------------------------------------------------------------------
resumen = defaultdict(lambda: {"filas": 0, "bruto": 0.0})
for f in filas_finales:
    ym = f["FECHA_OBJ"].strftime("%Y-%m")
    key = (f["CANAL"], ym)
    resumen[key]["filas"] += 1
    resumen[key]["bruto"] += f["BRUTO_TOTAL"]

print("\n" + "=" * 100)
print("RESUMEN POR CANAL + MES (lo que se va a insertar)")
print("=" * 100)
for (canal, ym), d in sorted(resumen.items()):
    print(f"  {canal:15s} {ym}  filas={d['filas']:4d}  bruto=${d['bruto']:,.0f}")

print("\n" + "=" * 100)
print("MUESTRA -- 10 filas ya calculadas")
print("=" * 100)
for f in filas_finales[:10]:
    print(f"\n  DOCUMENTO: {f['DOCUMENTO']}")
    print(f"  PRODUCTO: {f['PRODUCTO']}  SKU: {f['SKU_BSALE']}  CATEGORIA: {f['CATEGORIA']}")
    print(f"  CANTIDAD: {f['CANTIDAD']}  BRUTO: {f['BRUTO_TOTAL']:,.0f}  NETO: {f['NETO_TOTAL']:,.0f}  "
          f"COSTO: {f['COSTO_TOTAL']:,.0f}  CONTRIBUCION: {f['CONTRIBUCION']:,.0f}")
    print(f"  FECHA: {f['FECHA_OBJ'].date()}  ORIGEN: {f['ORIGEN']}")

total_bruto = sum(f["BRUTO_TOTAL"] for f in filas_finales)
print(f"\nTOTAL BRUTO a insertar (todas las filas, todos los canales/meses): ${total_bruto:,.0f}")


# ---------------------------------------------------------------------
# 6) Confirmacion explicita antes de escribir
# ---------------------------------------------------------------------
print("\n" + "=" * 100)
print(f"Esto va a: 1) BORRAR cualquier fila existente en `ventas` con ORIGEN='{ORIGEN_TAG}' "
      f"(por si ya corriste esto antes), y 2) INSERTAR las {len(filas_finales)} filas de arriba.")
print("No toca ninguna otra fila de la tabla (ORIGEN='BSALE', 'FALABELLA_API', etc. quedan intactas).")
respuesta = input("\nEscribe CARGAR (en mayúsculas) para confirmar, cualquier otra cosa cancela: ").strip()

if respuesta != "CARGAR":
    print("Cancelado -- no se escribió nada en la base.")
    sys.exit(0)


# ---------------------------------------------------------------------
# 7) Escribir
# ---------------------------------------------------------------------
with duckdb.connect(DB_FILE) as con:
    antes = con.execute("SELECT COUNT(*) FROM ventas WHERE ORIGEN = ?", [ORIGEN_TAG]).fetchone()[0]
    con.execute("DELETE FROM ventas WHERE ORIGEN = ?", [ORIGEN_TAG])
    print(f"Filas previas con ORIGEN='{ORIGEN_TAG}' borradas: {antes}")

    con.execute("""
        CREATE TABLE tmp_carga_full_historico (
            DOCUMENTO VARCHAR, PRODUCTO VARCHAR, SKU_BSALE VARCHAR, CANTIDAD INTEGER,
            NETO_TOTAL DOUBLE, BRUTO_TOTAL DOUBLE, COSTO_TOTAL DOUBLE, CONTRIBUCION DOUBLE,
            CANAL VARCHAR, VENDEDOR VARCHAR, CLIENTE VARCHAR, CATEGORIA VARCHAR, FECHA_OBJ TIMESTAMP,
            ORIGEN VARCHAR, TIPO_DOCUMENTO VARCHAR, NUMERO_DOCUMENTO VARCHAR, SUCURSAL VARCHAR,
            ES_GLOSA_SERVICIO BOOLEAN
        )
    """)
    cols = ["DOCUMENTO", "PRODUCTO", "SKU_BSALE", "CANTIDAD", "NETO_TOTAL", "BRUTO_TOTAL",
            "COSTO_TOTAL", "CONTRIBUCION", "CANAL", "VENDEDOR", "CLIENTE", "CATEGORIA",
            "FECHA_OBJ", "ORIGEN", "TIPO_DOCUMENTO", "NUMERO_DOCUMENTO", "SUCURSAL", "ES_GLOSA_SERVICIO"]
    valores = [[f[c] for c in cols] for f in filas_finales]
    placeholders = ", ".join(["?"] * len(cols))
    con.executemany(f"INSERT INTO tmp_carga_full_historico VALUES ({placeholders})", valores)

    columnas_explicitas = ", ".join(cols)
    con.execute(
        f"INSERT INTO ventas ({columnas_explicitas}) "
        f"SELECT {columnas_explicitas} FROM tmp_carga_full_historico"
    )
    con.execute("DROP TABLE tmp_carga_full_historico")

    despues = con.execute("SELECT COUNT(*) FROM ventas WHERE ORIGEN = ?", [ORIGEN_TAG]).fetchone()[0]

print(f"\n✅ Listo. Filas insertadas con ORIGEN='{ORIGEN_TAG}': {despues}")