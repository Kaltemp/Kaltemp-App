"""
diagnostico_recomendaciones_precio_stock.py — Replica la lógica exacta de
/api/cumplimiento/recomendaciones-precio-stock PERO sin el filtro final
(stock_suficiente AND precio_subio), para ver los valores reales de cada
SKU candidato y entender por qué el endpoint devuelve 0 resultados.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_recomendaciones_precio_stock.py
"""
import os
import duckdb
from datetime import date
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

# ============================================================
# AJUSTA ESTOS VALORES para que calcen con lo que tenías
# seleccionado en el screenshot (ciclo 25-jul a 24-ago 2026,
# 5 canales: D2C, FALABELLA, OTROS, PARIS, MERCADOLIBRE)
# ============================================================
FECHA_INICIO = date(2026, 7, 25)
FECHA_FIN = date(2026, 8, 24)
CANALES_FILTRO = ["D2C", "FALABELLA", "OTROS", "PARIS", "MERCADOLIBRE"]
CATEGORIAS_FILTRO = []   # vacío = todas
VENDEDORES_FILTRO = []   # vacío = todos
BODEGAS_FILTRO = []      # vacío = todas
# ============================================================

print("=" * 80)
print("DIAGNÓSTICO — RECOMENDACIONES DE PRECIO & STOCK (YoY)")
print("=" * 80)
print(f"📁 DUCKDB_PATH: {DB_FILE}")
print(f"📅 Período actual: {FECHA_INICIO} → {FECHA_FIN}")

yoy_ini = FECHA_INICIO.replace(year=FECHA_INICIO.year - 1)
yoy_fin = FECHA_FIN.replace(year=FECHA_FIN.year - 1)
print(f"📅 Período YoY:    {yoy_ini} → {yoy_fin}")
print(f"🔎 Canales filtro: {CANALES_FILTRO or 'TODOS'}")
print(f"🔎 Categorías filtro: {CATEGORIAS_FILTRO or 'TODAS'}")
print(f"🔎 Vendedores filtro: {VENDEDORES_FILTRO or 'TODOS'}")
print()

if not os.path.exists(DB_FILE):
    print("❌ El archivo .duckdb no existe en esa ruta.")
    exit(1)


def filtro_extra(vendedores, categorias, canales, bodegas):
    clausulas = []
    params = []
    if vendedores:
        clausulas.append(f"VENDEDOR IN ({', '.join(['?'] * len(vendedores))})")
        params += vendedores
    if categorias:
        clausulas.append(f"CATEGORIA IN ({', '.join(['?'] * len(categorias))})")
        params += categorias
    if canales:
        clausulas.append(f"UPPER(CANAL) IN ({', '.join(['?'] * len(canales))})")
        params += [c.upper() for c in canales]
    if bodegas:
        clausulas.append(f"UPPER(SUCURSAL) IN ({', '.join(['?'] * len(bodegas))})")
        params += [b.upper() for b in bodegas]
    sql = ("AND " + " AND ".join(clausulas)) if clausulas else ""
    return sql, params


filtro_sql, filtro_params = filtro_extra(VENDEDORES_FILTRO, CATEGORIAS_FILTRO, CANALES_FILTRO, BODEGAS_FILTRO)

con = duckdb.connect(DB_FILE, read_only=True)

sql_sku = f"""
    SELECT
        SKU_BSALE,
        ANY_VALUE(PRODUCTO) AS producto,
        ANY_VALUE(CATEGORIA) AS categoria,
        SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) AS unidades,
        SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE BRUTO_TOTAL END) AS venta,
        SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
      AND SKU_BSALE IS NOT NULL AND TRIM(SKU_BSALE) != ''
      {filtro_sql}
    GROUP BY SKU_BSALE
    HAVING SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) > 0
"""

actual_rows = con.execute(sql_sku, [FECHA_INICIO, FECHA_FIN] + filtro_params).fetchall()
yoy_rows = con.execute(sql_sku, [yoy_ini, yoy_fin] + filtro_params).fetchall()

print(f"📦 SKUs con venta en el período ACTUAL (con filtros aplicados): {len(actual_rows)}")
print(f"📦 SKUs con venta en el período YoY (con filtros aplicados):    {len(yoy_rows)}")
print()

# --- Sin filtro de canal, para comparar ---
filtro_sql_sin_canal, params_sin_canal = filtro_extra(VENDEDORES_FILTRO, CATEGORIAS_FILTRO, [], BODEGAS_FILTRO)
sql_sku_sin_canal = sql_sku.replace(filtro_sql, filtro_sql_sin_canal)
actual_sin_canal = con.execute(sql_sku_sin_canal, [FECHA_INICIO, FECHA_FIN] + params_sin_canal).fetchall()
yoy_sin_canal = con.execute(sql_sku_sin_canal, [yoy_ini, yoy_fin] + params_sin_canal).fetchall()
print(f"🔓 (Sin filtro de canal) SKUs período actual: {len(actual_sin_canal)}")
print(f"🔓 (Sin filtro de canal) SKUs período YoY:    {len(yoy_sin_canal)}")
print()

yoy_por_sku = {row[0]: {"unidades": row[3] or 0, "venta": row[4] or 0, "contri": row[5] or 0} for row in yoy_rows}

tablas = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
stock_por_sku = {}
if "stock_bsale" in tablas:
    stock_rows = con.execute("""
        SELECT UPPER(TRIM(SKU)) AS sku_norm, SUM(DISPONIBLE) AS disponible
        FROM stock_bsale
        WHERE UPPER(BODEGA) NOT IN ('ÑUÑOA', 'CONCEPCION SOLARSUR', 'CONCEPCIÓN SOLARSUR')
        GROUP BY UPPER(TRIM(SKU))
    """).fetchall()
    stock_por_sku = {row[0]: (row[1] or 0) for row in stock_rows}

print(f"📊 SKUs con stock_bsale cargado: {len(stock_por_sku)}")
print()

print("=" * 80)
print("DETALLE POR SKU (sin aplicar el filtro final, para inspección)")
print("=" * 80)

candidatos = []
for sku, producto, categoria, unidades_act, venta_act, contri_act in actual_rows:
    yoy = yoy_por_sku.get(sku)
    if not yoy or yoy["unidades"] <= 0:
        continue  # sin base YoY

    unidades_yoy = yoy["unidades"]
    precio_prom_actual = (venta_act / unidades_act) if unidades_act else 0
    precio_prom_yoy = (yoy["venta"] / unidades_yoy) if unidades_yoy else 0
    if precio_prom_yoy <= 0:
        continue

    variacion_precio_pct = round(((precio_prom_actual - precio_prom_yoy) / precio_prom_yoy) * 100, 1)
    stock_actual = stock_por_sku.get(str(sku).strip().upper(), 0)

    stock_suficiente = stock_actual >= unidades_yoy
    precio_subio = variacion_precio_pct > 0
    cumple_ambas = stock_suficiente and precio_subio

    candidatos.append({
        "sku": sku,
        "producto": (producto or "")[:40],
        "unidades_yoy": unidades_yoy,
        "stock_actual": stock_actual,
        "stock_ok": stock_suficiente,
        "variacion_pct": variacion_precio_pct,
        "precio_ok": precio_subio,
        "cumple": cumple_ambas,
    })

print(f"\n🔍 Total de SKUs con base YoY válida (candidatos evaluados): {len(candidatos)}\n")

if not candidatos:
    print("⚠️  No hay NINGÚN SKU con datos YoY comparables bajo estos filtros.")
    print("    Esto sugiere que el filtro de canal es demasiado restrictivo para")
    print("    el período YoY, o que estos canales no tenían actividad hace un año.")
else:
    candidatos.sort(key=lambda c: (c["cumple"], c["stock_ok"], c["precio_ok"]), reverse=True)
    print(f"{'SKU':<15} {'PRODUCTO':<42} {'UN.YOY':>7} {'STOCK':>7} {'STOCK_OK':>9} {'VAR%':>7} {'PRECIO_OK':>10} {'CUMPLE':>7}")
    print("-" * 110)
    for c in candidatos[:30]:
        print(f"{c['sku']:<15} {c['producto']:<42} {c['unidades_yoy']:>7} {c['stock_actual']:>7} "
              f"{str(c['stock_ok']):>9} {c['variacion_pct']:>6.1f}% {str(c['precio_ok']):>10} {str(c['cumple']):>7}")

    n_cumple = sum(1 for c in candidatos if c["cumple"])
    n_solo_stock = sum(1 for c in candidatos if c["stock_ok"] and not c["precio_ok"])
    n_solo_precio = sum(1 for c in candidatos if c["precio_ok"] and not c["stock_ok"])
    print()
    print(f"✅ Cumplen AMBAS condiciones: {n_cumple}")
    print(f"📦 Cumplen SOLO stock suficiente (precio no subió): {n_solo_stock}")
    print(f"💰 Cumplen SOLO precio al alza (stock insuficiente): {n_solo_precio}")

con.close()
print()
print("=" * 80)
print("✅ Diagnóstico completo. Copia y pega este output completo.")
print("=" * 80)