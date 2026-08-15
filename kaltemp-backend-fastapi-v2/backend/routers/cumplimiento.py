# ============================================================
# Archivo: cumplimiento.py
# Ruta:    backend/routers/cumplimiento.py
# ============================================================

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
from datos_manuales_db import get_datos_manuales_connection

router = APIRouter(prefix="/api", tags=["cumplimiento"])


def _parse_csv(valor: str | None) -> list[str]:
    if not valor:
        return []
    return [v.strip() for v in valor.split(",") if v.strip()]


def _filtro_extra(vendedores: list[str], categorias: list[str], canales: list[str], bodegas: list[str]):
    """
    Arma el WHERE adicional para vendedor/categoría/canal/bodega, siguiendo
    el mismo patrón que sku.py (_filtro_extra). BODEGA se cruza contra
    ventas.SUCURSAL -- ambas columnas se pueblan desde el mismo nombre de
    oficina Bsale (ver sync_ventas.py / sync_stock_bsale.py), así que son
    comparables 1:1.
    """
    clausulas = []
    params: list = []
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


@router.get("/cumplimiento")
def get_cumplimiento(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas; vacío = todos"),
    categorias: str = Query(None, description="Lista separada por comas; vacío = todas"),
    canales: str = Query(None, description="Lista separada por comas; vacío = todos"),
    bodegas: str = Query(None, description="Lista separada por comas; vacío = todas"),
):
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    lista_bodegas = _parse_csv(bodegas)
    filtro_extra, params_extra = _filtro_extra(lista_vendedores, lista_categorias, lista_canales, lista_bodegas)

    with get_connection() as con:
        # --- Totales del período (venta real / contribución real) ---
        # CONTRIBUCION y NETO excluyen líneas de servicio técnico sin SKU
        # real (ES_GLOSA_SERVICIO) -- mismo criterio que channels.py/sku.py
        # (05-ago-2026). BRUTO_TOTAL (venta mostrada, CON IVA) no se toca,
        # pero el % MARGEN se calcula contra NETO (SIN IVA) -- mismo
        # criterio que sku.py/channels.py. Dividir margen contra BRUTO
        # subestima el % en el factor de IVA (÷1.19) -- bug detectado
        # 08-ago-2026 comparando contra "Ventas por SKU".
        sql_totales = f"""
            SELECT SUM(BRUTO_TOTAL) AS venta,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
        """
        fila = con.execute(sql_totales, [fecha_inicio, fecha_fin] + params_extra).fetchone()
        venta_real = (fila[0] or 0) / 1_000_000
        neto_real = (fila[1] or 0) / 1_000_000
        contri_real = (fila[2] or 0) / 1_000_000

        yoy_ini_totales = fecha_inicio.replace(year=fecha_inicio.year - 1)
        yoy_fin_totales = fecha_fin.replace(year=fecha_fin.year - 1)
        fila_yoy = con.execute(sql_totales, [yoy_ini_totales, yoy_fin_totales] + params_extra).fetchone()
        venta_yoy_total = (fila_yoy[0] or 0) / 1_000_000

        # --- Desglose por canal (período actual + mismo período año anterior) ---
        sql_canal = f"""
            SELECT CANAL, SUM(BRUTO_TOTAL) AS venta,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,
                   SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
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
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
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
    for canal, venta, neto, contri in cy_canal:
        venta_m = (venta or 0) / 1_000_000
        neto_m = (neto or 0) / 1_000_000
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
            "margenPct": round((contri_m / neto_m) * 100, 1) if neto_m else 0.0,
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
        "margenPct": round((contri_real / neto_real * 100), 1) if neto_real else 0.0,
        "diasTranscurridos": dias_transcurridos,
        "diasTotalCiclo": dias_totales,
        "canalBreakdown": canal_breakdown,
        "categorySales": category_sales,
    }


@router.get("/cumplimiento/recomendaciones-precio-stock")
def get_recomendaciones_precio_stock(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas; vacío = todos"),
    categorias: str = Query(None, description="Lista separada por comas; vacío = todas"),
    canales: str = Query(None, description="Lista separada por comas; vacío = todos"),
    bodegas: str = Query(None, description="Lista separada por comas; vacío = todas"),
    limite: int = Query(20, ge=1, le=100),
):
    """
    Motor de recomendación por SKU: compara unidades vendidas en el mismo
    período del año anterior (YoY) contra el stock disponible HOY, y compara
    el precio promedio del período actual vs. el precio promedio YoY.

    Dispara una recomendación de ajuste de precio cuando se cumplen AMBAS
    condiciones:
      1. Stock actual disponible >= unidades vendidas YoY (hay stock
         suficiente para al menos igualar el volumen del año pasado)
      2. El precio promedio actual subió vs. el precio promedio YoY
         (el alza de precio es la causa probable de estar por debajo
         del ritmo de venta del año anterior)

    Los "canales Z" sugeridos son los canales donde ese SKU efectivamente
    se vendió en el período YoY (dónde ya existía demanda a ese precio).
    """
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    lista_bodegas = _parse_csv(bodegas)
    filtro_extra, params_extra = _filtro_extra(lista_vendedores, lista_categorias, lista_canales, lista_bodegas)

    yoy_ini = fecha_inicio.replace(year=fecha_inicio.year - 1)
    yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

    # CONTRIBUCION/NETO_TOTAL excluyen glosas de servicio sin SKU real
    # (mismo criterio que channels.py / sku.py, 05-ago-2026). BRUTO_TOTAL
    # se usa para el precio promedio (con IVA, precio real de venta al
    # público) -- NETO_TOTAL se usa solo para el % margen (sin IVA, mismo
    # criterio que sku.py/channels.py; dividir margen contra BRUTO lo
    # subestima ÷1.19 -- bug detectado 08-ago-2026).
    sql_sku = f"""
        SELECT
            SKU_BSALE,
            ANY_VALUE(PRODUCTO) AS producto,
            ANY_VALUE(CATEGORIA) AS categoria,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) AS unidades,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE BRUTO_TOTAL END) AS venta,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND SKU_BSALE IS NOT NULL AND TRIM(SKU_BSALE) != ''
          {filtro_extra}
        GROUP BY SKU_BSALE
        HAVING SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) > 0
    """

    sql_canales_sku = f"""
        SELECT DISTINCT SKU_BSALE, CANAL
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND SKU_BSALE IS NOT NULL AND TRIM(SKU_BSALE) != ''
          AND (ES_GLOSA_SERVICIO IS NULL OR ES_GLOSA_SERVICIO = FALSE)
          {filtro_extra}
    """

    with get_connection() as con:
        actual_rows = con.execute(sql_sku, [fecha_inicio, fecha_fin] + params_extra).fetchall()
        yoy_rows = con.execute(sql_sku, [yoy_ini, yoy_fin] + params_extra).fetchall()
        canales_yoy_rows = con.execute(sql_canales_sku, [yoy_ini, yoy_fin] + params_extra).fetchall()

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

    # Mapa YoY: sku -> (unidades, venta, neto, contri)
    yoy_por_sku = {row[0]: {"unidades": row[3] or 0, "venta": row[4] or 0, "neto": row[5] or 0, "contri": row[6] or 0} for row in yoy_rows}

    # Mapa canales donde se vendió cada SKU en el período YoY
    canales_yoy_por_sku: dict[str, list[str]] = {}
    for sku_val, canal_val in canales_yoy_rows:
        if not canal_val:
            continue
        canales_yoy_por_sku.setdefault(sku_val, [])
        if canal_val not in canales_yoy_por_sku[sku_val]:
            canales_yoy_por_sku[sku_val].append(canal_val)

    recomendaciones = []
    for sku, producto, categoria, unidades_act, venta_act, neto_act, contri_act in actual_rows:
        yoy = yoy_por_sku.get(sku)
        if not yoy or yoy["unidades"] <= 0:
            continue  # sin base de comparación YoY, no se puede recomendar

        unidades_yoy = yoy["unidades"]
        precio_prom_actual = (venta_act / unidades_act) if unidades_act else 0
        precio_prom_yoy = (yoy["venta"] / unidades_yoy) if unidades_yoy else 0
        if precio_prom_yoy <= 0:
            continue

        variacion_precio_pct = round(((precio_prom_actual - precio_prom_yoy) / precio_prom_yoy) * 100, 1)
        stock_actual = stock_por_sku.get(str(sku).strip().upper(), 0)

        # --- Condición combinada: stock suficiente Y precio subió ---
        stock_suficiente = stock_actual >= unidades_yoy
        precio_subio = variacion_precio_pct > 0

        if not (stock_suficiente and precio_subio):
            continue

        canales_recomendados = canales_yoy_por_sku.get(sku, [])
        # % margen contra NETO (sin IVA) -- mismo criterio que sku.py/channels.py
        margen_pct = round((contri_act / neto_act * 100), 1) if neto_act else 0.0

        canales_str = ", ".join(canales_recomendados) if canales_recomendados else "sus canales históricos"
        mensaje = (
            f"El año pasado vendiste {unidades_yoy} unidades de {producto or sku}. "
            f"Hoy tienes {int(stock_actual)} en stock. El precio subió {variacion_precio_pct}% "
            f"vs. el año pasado. Ajusta el precio en {canales_str} para recuperar ese volumen."
        )

        recomendaciones.append({
            "sku": sku,
            "producto": producto or sku,
            "categoria": categoria or "Sin categoría",
            "unidadesYoy": int(unidades_yoy),
            "unidadesActual": int(unidades_act or 0),
            "stockActual": int(stock_actual),
            "precioPromActual": round(precio_prom_actual, 0),
            "precioPromYoy": round(precio_prom_yoy, 0),
            "variacionPrecioPct": variacion_precio_pct,
            "margenPct": margen_pct,
            "canalesRecomendados": canales_recomendados,
            "mensaje": mensaje,
        })

    # Prioriza el mayor volumen recuperable (unidades YoY) primero
    recomendaciones.sort(key=lambda r: r["unidadesYoy"], reverse=True)

    return {
        "totalRecomendaciones": len(recomendaciones),
        "recomendaciones": recomendaciones[:limite],
    }


@router.get("/cumplimiento/productos-actual")
def get_productos_actual(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas; vacío = todos"),
    categorias: str = Query(None, description="Lista separada por comas; vacío = todas"),
    canales: str = Query(None, description="Lista separada por comas; vacío = todos"),
    bodegas: str = Query(None, description="Lista separada por comas; vacío = todas"),
    top_n: int = Query(10, ge=1, le=30),
):
    """
    Top N productos por contribución en el período actual (mismos filtros
    que el resto del módulo). Base para la Matriz de Requerimiento de
    Unidades por SKU -- el frontend usa unidades/contribución de acá junto
    con la meta ($ que el usuario ingresa) para calcular cuántas unidades
    de cada producto hacen falta para alcanzar cada tramo de meta,
    repartiendo la brecha total según el share de contribución de cada
    producto en el período.
    """
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    lista_bodegas = _parse_csv(bodegas)
    filtro_extra, params_extra = _filtro_extra(lista_vendedores, lista_categorias, lista_canales, lista_bodegas)

    sql = f"""
        SELECT
            ANY_VALUE(PRODUCTO) AS producto,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) AS unidades,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contribucion
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
        GROUP BY PRODUCTO
        HAVING SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) > 0
           AND SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) > 0
        ORDER BY contribucion DESC
        LIMIT ?
    """
    with get_connection() as con:
        filas = con.execute(sql, [fecha_inicio, fecha_fin] + params_extra + [top_n]).fetchall()

    productos = [
        {
            "producto": producto,
            "unidades": int(unidades or 0),
            "contribucion": round((contribucion or 0) / 1_000_000, 3),  # en $M
        }
        for producto, unidades, contribucion in filas
    ]
    return {"productos": productos}


@router.get("/cumplimiento/sku-detalle")
def get_sku_detalle_cumplimiento(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas; vacío = todos"),
    categorias: str = Query(None, description="Lista separada por comas; vacío = todas"),
    canales: str = Query(None, description="Lista separada por comas; vacío = todos"),
    bodegas: str = Query(None, description="Lista separada por comas; vacío = todas"),
):
    """
    TODOS los SKUs vendidos en el período/filtros actuales del módulo
    Cumplimiento (sin límite de top N, a diferencia de /productos-actual
    que sí lo tiene para la Matriz). Pensado como tabla de auditoría: la
    suma de 'contribucion' de todas las filas debe calzar exactamente con
    contriReal que devuelve /api/cumplimiento con los mismos filtros,
    porque usa idéntico WHERE y la misma exclusión de ES_GLOSA_SERVICIO.
    """
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    lista_bodegas = _parse_csv(bodegas)
    filtro_extra, params_extra = _filtro_extra(lista_vendedores, lista_categorias, lista_canales, lista_bodegas)

    sql = f"""
        SELECT
            SKU_BSALE,
            ANY_VALUE(PRODUCTO) AS producto,
            ANY_VALUE(CATEGORIA) AS categoria,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) AS unidades,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE BRUTO_TOTAL END) AS venta,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contribucion
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
        GROUP BY SKU_BSALE
        HAVING SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) > 0
    """

    # Mismo grupo pero abierto por canal también -- para el desglose
    # expandible de cada SKU (un solo query extra, sin fetches perezosos
    # por fila en el frontend).
    sql_por_canal = f"""
        SELECT
            SKU_BSALE,
            CANAL,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) AS unidades,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE BRUTO_TOTAL END) AS venta,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contribucion
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {filtro_extra}
        GROUP BY SKU_BSALE, CANAL
        HAVING SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CANTIDAD END) > 0
    """

    with get_connection() as con:
        filas = con.execute(sql, [fecha_inicio, fecha_fin] + params_extra).fetchall()
        filas_canal = con.execute(sql_por_canal, [fecha_inicio, fecha_fin] + params_extra).fetchall()

    # % margen SIEMPRE contra NETO_TOTAL (sin IVA), no BRUTO_TOTAL --
    # mismo criterio que sku.py/channels.py (bug detectado 08-ago-2026:
    # dividir contra BRUTO subestima el margen en ÷1.19, el factor de IVA).
    canales_por_sku: dict[str, list[dict]] = {}
    for sku, canal, unidades_c, venta_c, neto_c, contri_c in filas_canal:
        unidades_c = unidades_c or 0
        venta_c = venta_c or 0
        neto_c = neto_c or 0
        contri_c = contri_c or 0
        canales_por_sku.setdefault(sku, []).append({
            "canal": canal or "Sin canal",
            "unidades": int(unidades_c),
            "venta": round(venta_c / 1_000_000, 3),
            "contribucion": round(contri_c / 1_000_000, 3),
            "margenPct": round((contri_c / neto_c) * 100, 1) if neto_c else 0.0,
        })
    for sku in canales_por_sku:
        canales_por_sku[sku].sort(key=lambda c: c["contribucion"], reverse=True)

    contribucion_total = sum((c or 0) for _, _, _, _, _, _, c in filas)

    skus = []
    for sku, producto, categoria, unidades, venta, neto, contribucion in filas:
        unidades = unidades or 0
        venta = venta or 0
        neto = neto or 0
        contribucion = contribucion or 0
        skus.append({
            "sku": sku or "(sin SKU)",
            "producto": producto or sku or "(sin producto)",
            "categoria": categoria or "Sin categoría",
            "unidades": int(unidades),
            "venta": round(venta / 1_000_000, 3),
            "contribucion": round(contribucion / 1_000_000, 3),
            "precioProm": round(venta / unidades, 0) if unidades else 0,
            "margenPct": round((contribucion / neto) * 100, 1) if neto else 0.0,
            "sharePct": round((contribucion / contribucion_total) * 100, 1) if contribucion_total else 0.0,
            "canales": canales_por_sku.get(sku, []),
        })

    skus.sort(key=lambda s: s["contribucion"], reverse=True)

    return {
        "skus": skus,
        "totalUnidades": sum(s["unidades"] for s in skus),
        "totalVenta": round(sum(s["venta"] for s in skus), 1),
        "totalContribucion": round(sum(s["contribucion"] for s in skus), 1),
    }


@router.get("/cumplimiento/historico-anual")
def get_historico_anual():
    """
    Comparativo de cumplimiento por año calendario completo (no por ciclo
    comercial 25-24 como el resto del módulo). Para cada año:
      - contribucionReal: si `ventas` tiene filas de ese año, se calcula
        real (SUM(CONTRIBUCION), excluyendo ES_GLOSA_SERVICIO). Si no hay
        filas para ese año (típicamente años anteriores a la sync
        histórica), se usa el valor manual 'contribucion_real_manual' si
        existe -- si tampoco existe, el año se omite del todo.
      - metaContribucion: SIEMPRE viene de datos_manuales
        ('meta_contribucion_anual') -- no existe ningún objetivo de
        negocio que se pueda calcular solo, se carga desde el modal de
        Datos Manuales.
      - cumplimientoPct: contribucionReal / metaContribucion * 100,
        solo si hay meta cargada para ese año.
    """
    with get_connection() as con:
        filas_reales = con.execute("""
            SELECT
                CAST(strftime(CAST(FECHA_OBJ AS DATE), '%Y') AS INTEGER) AS anio,
                SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contribucion,
                SUM(BRUTO_TOTAL) AS venta
            FROM ventas
            GROUP BY anio
        """).fetchall()
    contribucion_real_por_anio = {int(a): (c or 0) / 1_000_000 for a, c, v in filas_reales}
    venta_real_por_anio = {int(a): (v or 0) / 1_000_000 for a, c, v in filas_reales}

    with get_datos_manuales_connection() as con:
        filas_manual = con.execute("SELECT periodo, tipo, monto FROM datos_manuales").fetchall()

    meta_contri_por_anio: dict[int, float] = {}
    meta_venta_por_anio: dict[int, float] = {}
    contri_manual_por_anio: dict[int, float] = {}
    venta_manual_por_anio: dict[int, float] = {}
    for fila in filas_manual:
        periodo, tipo, monto = fila["periodo"], fila["tipo"], fila["monto"]
        if not periodo.isdigit():
            continue  # esta consulta es solo para métricas anuales (año exacto)
        anio = int(periodo)
        monto_m = (monto or 0) / 1_000_000
        if tipo == "meta_contribucion_anual":
            meta_contri_por_anio[anio] = monto_m
        elif tipo == "meta_venta_anual":
            meta_venta_por_anio[anio] = monto_m
        elif tipo == "contribucion_real_manual":
            contri_manual_por_anio[anio] = monto_m
        elif tipo == "venta_real_manual":
            venta_manual_por_anio[anio] = monto_m

    todos_los_anios = sorted(set(
        list(contribucion_real_por_anio.keys())
        + list(meta_contri_por_anio.keys())
        + list(contri_manual_por_anio.keys())
    ))

    resultado = []
    for anio in todos_los_anios:
        contri = contribucion_real_por_anio.get(anio)
        es_manual = False
        if contri is None or contri == 0:
            contri_manual = contri_manual_por_anio.get(anio)
            if contri_manual is not None:
                contri = contri_manual
                es_manual = True
        if contri is None:
            continue  # sin dato real ni manual -- no se puede mostrar nada de este año

        meta = meta_contri_por_anio.get(anio)
        venta = venta_real_por_anio.get(anio) or venta_manual_por_anio.get(anio)

        resultado.append({
            "anio": anio,
            "contribucionReal": round(contri, 1),
            "ventaReal": round(venta, 1) if venta else None,
            "metaContribucion": round(meta, 1) if meta else None,
            "cumplimientoPct": round((contri / meta) * 100, 1) if meta else None,
            "esManual": es_manual,
        })

    return {"anios": resultado}
