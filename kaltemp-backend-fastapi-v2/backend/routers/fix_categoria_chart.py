# ============================================================
# ARCHIVO: fix_categoria_chart.py
# QUE HACE: actualiza el endpoint /api/sku/categoria-resumen en
# backend/routers/sku.py para que también devuelva el año anterior
# y el YoY% por categoría (antes solo devolvía el año actual).
# Esto es lo que necesita el nuevo gráfico "Venta Total por Categoría"
# con barras agrupadas por año (como el de Power BI).
#
# COMO USARLO:
#   1. Copia este archivo DENTRO de la carpeta:
#      C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers
#      (la misma carpeta donde está sku.py)
#   2. Abre PowerShell en esa carpeta (con el venv activado)
#   3. Corre:
#      python fix_categoria_chart.py
#   4. Reinicia uvicorn (si no tiene --reload activo) y recarga el frontend.
# ============================================================
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sku.py")

TEXTO_VIEJO = '''@router.get("/categoria-resumen")
def get_categoria_resumen(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None),
    canales: str = Query(None),
):
    """
    Venta total agrupada por CATEGORIA para el rango de fechas -- reemplaza
    el `categoryChartData` fijo del gráfico de barras horizontal.
    Se filtra por Vendedor/Canal (no por Categoría: sería redundante, ya
    que este mismo endpoint es el que arma el desglose por categoría).
    """
    extra_sql, extra_params = _filtro_extra(_parse_csv(vendedores), None, _parse_csv(canales))
    with get_connection() as con:
        filas = con.execute(f"""
            SELECT CATEGORIA, SUM(BRUTO_TOTAL) AS venta
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
              AND CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
              AND NOT ES_GLOSA_SERVICIO
              {extra_sql}
            GROUP BY CATEGORIA
            ORDER BY venta DESC
        """, [fecha_inicio, fecha_fin, *extra_params]).fetchall()

    return [{"name": f[0], "value": round((f[1] or 0) / 1_000_000, 1)} for f in filas]'''

TEXTO_NUEVO = '''@router.get("/categoria-resumen")
def get_categoria_resumen(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None),
    canales: str = Query(None),
):
    """
    Venta total agrupada por CATEGORIA para el rango de fechas, con
    comparativo YoY (mismo patron que /canal-resumen) -- alimenta el
    grafico de barras agrupadas por año (año anterior vs año actual)
    con etiquetas de monto + var% YoY en la barra del año actual.
    Se filtra por Vendedor/Canal (no por Categoría: sería redundante, ya
    que este mismo endpoint es el que arma el desglose por categoría).
    """
    extra_sql, extra_params = _filtro_extra(_parse_csv(vendedores), None, _parse_csv(canales))

    yoy_inicio = fecha_inicio.replace(year=fecha_inicio.year - 1)
    yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

    with get_connection() as con:
        cy = dict(con.execute(f"""
            SELECT CATEGORIA, SUM(BRUTO_TOTAL) AS venta
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
              AND CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
              AND NOT ES_GLOSA_SERVICIO
              {extra_sql}
            GROUP BY CATEGORIA
        """, [fecha_inicio, fecha_fin, *extra_params]).fetchall())

        yoy = dict(con.execute(f"""
            SELECT CATEGORIA, SUM(BRUTO_TOTAL) AS venta
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
              AND CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
              AND NOT ES_GLOSA_SERVICIO
              {extra_sql}
            GROUP BY CATEGORIA
        """, [yoy_inicio, yoy_fin, *extra_params]).fetchall())

    categorias_todas = set(cy.keys()) | set(yoy.keys())
    resultado = []
    for cat in categorias_todas:
        venta_cy = cy.get(cat, 0) or 0
        venta_yoy = yoy.get(cat, 0) or 0
        pct = round(((venta_cy - venta_yoy) / venta_yoy * 100), 1) if venta_yoy else None
        resultado.append({
            "name": cat,
            "value": round(venta_cy / 1_000_000, 1),
            "valueAnterior": round(venta_yoy / 1_000_000, 1),
            "yoyPct": pct,
        })
    resultado.sort(key=lambda r: r["value"], reverse=True)

    return {
        "anioActual": fecha_fin.year,
        "anioAnterior": fecha_fin.year - 1,
        "categorias": resultado,
    }'''


def main():
    if not os.path.exists(ARCHIVO):
        print(f"❌ No encontré el archivo en: {ARCHIVO}")
        print("   Asegúrate de haber copiado fix_categoria_chart.py DENTRO de la carpeta backend/routers.")
        return

    with open(ARCHIVO, "r", encoding="utf-8") as f:
        contenido = f.read()

    if TEXTO_NUEVO in contenido:
        print("✅ El archivo ya tiene el arreglo aplicado. No hay nada que hacer.")
        return

    if TEXTO_VIEJO not in contenido:
        print("⚠️ No encontré el bloque de código esperado en sku.py.")
        print("   Puede que el archivo ya haya sido editado a mano y quedó distinto.")
        print("   No se modificó nada -- avísale a Claude para revisar el archivo actual.")
        return

    backup = ARCHIVO + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"💾 Respaldo guardado en: {backup}")

    contenido_nuevo = contenido.replace(TEXTO_VIEJO, TEXTO_NUEVO)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido_nuevo)

    print("✅ sku.py arreglado con éxito -- /api/sku/categoria-resumen ahora devuelve")
    print("   año actual, año anterior y YoY% por categoría.")
    print("   Si tu uvicorn no está corriendo con --reload, reinícialo.")


if __name__ == "__main__":
    main()