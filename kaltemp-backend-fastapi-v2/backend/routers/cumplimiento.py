"""
Módulo Cumplimiento Ventas — a diferencia de los demás módulos, las
METAS son objetivos de negocio definidos por la persona (no viven en
la base de datos), así que el frontend las mantiene como campos
editables. Este backend entrega todo lo que SÍ es medible desde
`ventas`: venta real, contribución real, desglose por canal con
proyección por ritmo diario (run-rate) y comparativo YoY, y unidades
vendidas por categoría vs el mismo período del año anterior.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from db import get_connection

router = APIRouter(prefix="/api", tags=["cumplimiento"])


@router.get("/cumplimiento")
def get_cumplimiento(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas; vacío = todos"),
):
    filtro_vendedor = ""
    params_extra = []
    if vendedores:
        lista = [v.strip() for v in vendedores.split(",") if v.strip()]
        if lista:
            placeholders = ", ".join(["?"] * len(lista))
            filtro_vendedor = f"AND VENDEDOR IN ({placeholders})"
            params_extra = lista

    with get_connection() as con:
        # --- Totales del período (venta real / contribución real) ---
        # CONTRIBUCION excluye líneas de servicio técnico sin SKU real
        # (ES_GLOSA_SERVICIO) -- mismo criterio que channels.py/sku.py
        # (05-ago-2026). BRUTO_TOTAL (venta) no se toca.
        sql_totales = f"""
            SELECT SUM(BRUTO_TOTAL) AS venta,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_vendedor}
        """
        fila = con.execute(sql_totales, [fecha_inicio, fecha_fin] + params_extra).fetchone()
        venta_real = (fila[0] or 0) / 1_000_000
        contri_real = (fila[1] or 0) / 1_000_000

        yoy_ini_totales = fecha_inicio.replace(year=fecha_inicio.year - 1)
        yoy_fin_totales = fecha_fin.replace(year=fecha_fin.year - 1)
        fila_yoy = con.execute(sql_totales, [yoy_ini_totales, yoy_fin_totales] + params_extra).fetchone()
        venta_yoy_total = (fila_yoy[0] or 0) / 1_000_000

        # --- Desglose por canal (período actual + mismo período año anterior) ---
        sql_canal = f"""
            SELECT CANAL, SUM(BRUTO_TOTAL) AS venta,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_vendedor}
            GROUP BY CANAL
        """
        cy_canal = con.execute(sql_canal, [fecha_inicio, fecha_fin] + params_extra).fetchall()

        yoy_ini = fecha_inicio.replace(year=fecha_inicio.year - 1)
        yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)
        yoy_canal_rows = con.execute(sql_canal, [yoy_ini, yoy_fin] + params_extra).fetchall()
        yoy_canal = {row[0]: (row[1] or 0) for row in yoy_canal_rows}

        # --- Unidades por categoría (período actual vs mismo período año anterior) ---
        sql_categoria = f"""
            SELECT CATEGORIA, SUM(CANTIDAD) AS unidades
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_vendedor}
            GROUP BY CATEGORIA
        """
        cy_cat_rows = con.execute(sql_categoria, [fecha_inicio, fecha_fin] + params_extra).fetchall()
        yoy_cat_rows = con.execute(sql_categoria, [yoy_ini, yoy_fin] + params_extra).fetchall()
        yoy_cat = {row[0]: (row[1] or 0) for row in yoy_cat_rows}

    # --- Ritmo diario / proyección por run-rate ---
    dias_totales = (fecha_fin - fecha_inicio).days + 1
    hoy = date.today()
    limite = min(fecha_fin, hoy) if hoy >= fecha_inicio else fecha_inicio
    dias_transcurridos = max(1, (limite - fecha_inicio).days + 1)
    factor_runrate = dias_totales / dias_transcurridos

    canal_breakdown = []
    for canal, venta, contri in cy_canal:
        venta_m = (venta or 0) / 1_000_000
        contri_m = (contri or 0) / 1_000_000
        venta_diaria = venta_m / dias_transcurridos if dias_transcurridos else 0
        proy = round(contri_m * factor_runrate, 1)
        yoy_val = yoy_canal.get(canal, 0) / 1_000_000
        yoy_pct = round(((venta_m - yoy_val) / yoy_val * 100), 1) if yoy_val else (100.0 if venta_m > 0 else 0.0)
        canal_breakdown.append({
            "canal": canal,
            "contri": round(contri_m, 1),
            "proy": proy,
            "ventaDiaria": round(venta_diaria, 1),
            "yoyPct": yoy_pct,
        })
    canal_breakdown.sort(key=lambda r: r["contri"], reverse=True)

    category_sales = []
    for categoria, unidades in cy_cat_rows:
        nombre = categoria or "Sin categoría"
        category_sales.append({
            "cat": nombre,
            "actual": int(unidades or 0),
            "anterior": int(yoy_cat.get(categoria, 0)),
        })
    category_sales.sort(key=lambda r: r["actual"], reverse=True)

    return {
        "ventaReal": round(venta_real, 1),
        "ventaYoyTotal": round(venta_yoy_total, 1),
        "contriReal": round(contri_real, 1),
        "diasTranscurridos": dias_transcurridos,
        "diasTotalCiclo": dias_totales,
        "canalBreakdown": canal_breakdown,
        "categorySales": category_sales,
    }
