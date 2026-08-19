"""
Módulo Ventas por SKU — Carga perezosa (lazy load) de 4 niveles.

En vez de devolver el árbol completo Producto -> Vendedor -> Documento
-> Cliente de una sola vez (lento y pesado con datos reales), cada
nivel se pide por separado, solo cuando el usuario expande esa fila
en el frontend. Replica exactamente las agregaciones de app.py
(Streamlit) para el módulo "📦 Ventas por SKU".
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from db import get_connection

router = APIRouter(prefix="/api/sku", tags=["sku"])


def _rango_wow_yoy(fecha_inicio: date, fecha_fin: date):
    wow = (fecha_inicio - timedelta(days=7), fecha_fin - timedelta(days=7))
    yoy = (fecha_inicio.replace(year=fecha_inicio.year - 1), fecha_fin.replace(year=fecha_fin.year - 1))
    return wow, yoy


def _query(con, group_cols: list[str], where_extra: str, params_extra: list, fecha_inicio: date, fecha_fin: date):
    """
    Ejecuta la agregación CY/WOW/YOY para el nivel pedido (group_cols),
    con filtros adicionales opcionales (where_extra) para acotar a un
    producto/vendedor/documento específico en niveles más profundos.
    """
    (wow_ini, wow_fin), (yoy_ini, yoy_fin) = _rango_wow_yoy(fecha_inicio, fecha_fin)
    cols = ", ".join(group_cols)

    def _fetch(f_ini: date, f_fin: date, incluir_neto_contri: bool):
        # MARGEN (05-ago-2026): igual que en channels.py -- las líneas de
        # servicio técnico sin SKU real (ES_GLOSA_SERVICIO) cuentan en
        # venta/cantidad, pero se excluyen de neto/contribución para no
        # distorsionar el % de margen por producto.
        #
        # DESPACHO (07-ago-2026, confirmado con William): en ESTE módulo
        # (Ventas por SKU, 100% centrado en producto) se excluyen del TODO
        # -- unidades y venta también, no solo neto/contribución -- porque
        # un despacho no es un producto y no debe poder aparecer como fila
        # en el Top 15 ni en ningún nivel del árbol (vendedor/documento/
        # cliente). Esto es distinto del resto de la app (KPIs de venta
        # total SÍ incluyen despacho) porque acá cada fila ES un producto.
        extra_select = (
            ", SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto,"
            " SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contri"
        ) if incluir_neto_contri else ""
        sql = f"""
            SELECT {cols},
                SUM(CANTIDAD) AS cant,
                SUM(BRUTO_TOTAL) AS venta
                {extra_select}
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
              AND NOT ES_GLOSA_SERVICIO
            {where_extra}
            GROUP BY {cols}
        """
        cursor = con.execute(sql, [f_ini, f_fin] + params_extra)
        columnas = [c[0] for c in cursor.description]
        filas = cursor.fetchall()
        return {
            tuple(dict(zip(columnas, f))[g] for g in group_cols): dict(zip(columnas, f))
            for f in filas
        }

    cy = _fetch(fecha_inicio, fecha_fin, incluir_neto_contri=True)
    wow = _fetch(wow_ini, wow_fin, incluir_neto_contri=False)
    yoy = _fetch(yoy_ini, yoy_fin, incluir_neto_contri=False)
    return cy, wow, yoy


def _armar_nodo(clave, cy_row: dict, wow_row: dict | None, yoy_row: dict | None, incluir_extras: bool):
    cant_cy = cy_row["cant"] or 0
    venta_cy = cy_row["venta"] or 0
    cant_wow = (wow_row or {}).get("cant", 0) or 0
    venta_wow = (wow_row or {}).get("venta", 0) or 0
    cant_yoy = (yoy_row or {}).get("cant", 0) or 0
    venta_yoy = (yoy_row or {}).get("venta", 0) or 0
    neto_cy = cy_row.get("neto", 0) or 0
    contri_cy = cy_row.get("contri", 0) or 0

    nodo = {
        "id": "_".join(str(c) for c in clave),
        "nombre": clave[0],
        "cantCy": cant_cy,
        "cantWow": cant_wow,
        "cantYoy": cant_yoy,
        "ventaCy": round(venta_cy, 0),
        "ventaWow": round(venta_wow, 0),
        "ventaYoy": round(venta_yoy, 0),
        "netoCy": round(neto_cy, 0),
        "contriCy": round(contri_cy, 0),
        "pPromCy": round(venta_cy / cant_cy, 0) if cant_cy else 0,
        "pPromWow": round(venta_wow / cant_wow, 0) if cant_wow else 0,
        "pPromYoy": round(venta_yoy / cant_yoy, 0) if cant_yoy else 0,
        "margenCy": round((contri_cy / neto_cy * 100), 1) if neto_cy else 0.0,
        "margenYoy": 0.0,
    }
    if incluir_extras:
        nodo["sku"] = clave[1] if len(clave) > 1 else ""
        nodo["categoria"] = clave[2] if len(clave) > 2 else ""
    return nodo


@router.get("/productos")
def get_productos(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None, description="Lista separada por comas -- filtro cruzado de vendedor"),
    canales: str = Query(None, description="Lista separada por comas -- filtro cruzado de canal"),
):
    """Nivel 1: Top 15 productos por venta actual (igual que app.py)."""
    where_extra, params_extra = _filtro_extra(_parse_csv(vendedores), None, _parse_csv(canales))
    with get_connection() as con:
        cy, wow, yoy = _query(
            con,
            group_cols=["PRODUCTO", "SKU_BSALE", "CATEGORIA"],
            where_extra=where_extra,
            params_extra=params_extra,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

    nodos = []
    for clave, cy_row in cy.items():
        nodos.append(_armar_nodo(clave, cy_row, wow.get(clave), yoy.get(clave), incluir_extras=True))

    nodos.sort(key=lambda n: n["ventaCy"], reverse=True)
    return nodos[:15]


@router.get("/vendedores")
def get_vendedores(
    producto: str = Query(...),
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    """Nivel 2: Vendedores para un producto específico."""
    with get_connection() as con:
        cy, wow, yoy = _query(
            con,
            group_cols=["VENDEDOR"],
            where_extra="AND PRODUCTO = ?",
            params_extra=[producto],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
    nodos = [_armar_nodo(clave, cy_row, wow.get(clave), yoy.get(clave), incluir_extras=False) for clave, cy_row in cy.items()]
    nodos.sort(key=lambda n: n["ventaCy"], reverse=True)
    return nodos


@router.get("/documentos")
def get_documentos(
    producto: str = Query(...),
    vendedor: str = Query(...),
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    """Nivel 3: Documentos (boletas/facturas) para un producto+vendedor."""
    with get_connection() as con:
        cy, wow, yoy = _query(
            con,
            group_cols=["DOCUMENTO"],
            where_extra="AND PRODUCTO = ? AND VENDEDOR = ?",
            params_extra=[producto, vendedor],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
    nodos = [_armar_nodo(clave, cy_row, wow.get(clave), yoy.get(clave), incluir_extras=False) for clave, cy_row in cy.items()]
    nodos.sort(key=lambda n: n["ventaCy"], reverse=True)
    return nodos


@router.get("/clientes")
def get_clientes(
    producto: str = Query(...),
    vendedor: str = Query(...),
    documento: str = Query(...),
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    """Nivel 4: Clientes para un producto+vendedor+documento específico."""
    with get_connection() as con:
        cy, wow, yoy = _query(
            con,
            group_cols=["CLIENTE"],
            where_extra="AND PRODUCTO = ? AND VENDEDOR = ? AND DOCUMENTO = ?",
            params_extra=[producto, vendedor, documento],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
    nodos = [_armar_nodo(clave, cy_row, wow.get(clave), yoy.get(clave), incluir_extras=False) for clave, cy_row in cy.items()]
    nodos.sort(key=lambda n: n["ventaCy"], reverse=True)
    return nodos


def _parse_csv(valor: str | None) -> list[str] | None:
    return [v.strip() for v in valor.split(",") if v.strip()] if valor else None


def _filtro_extra(vendedores: list[str] | None, categorias: list[str] | None, canales: list[str] | None):
    clausulas = []
    params: list = []
    if vendedores:
        clausulas.append(f"UPPER(VENDEDOR) IN ({', '.join(['?'] * len(vendedores))})")
        params += [v.upper() for v in vendedores]
    if categorias:
        clausulas.append(f"CATEGORIA IN ({', '.join(['?'] * len(categorias))})")
        params += categorias
    if canales:
        clausulas.append(f"UPPER(CANAL) IN ({', '.join(['?'] * len(canales))})")
        params += [c.upper() for c in canales]
    return (" AND " + " AND ".join(clausulas)) if clausulas else "", params


@router.get("/categoria-resumen")
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
    }


@router.get("/canal-resumen")
def get_canal_resumen(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    vendedores: str = Query(None),
    categorias: str = Query(None),
):
    """
    Venta total agrupada por CANAL con comparativo YoY -- reemplaza el
    `channelsData` fijo de la tabla "Venta por Canal".
    Se filtra por Vendedor/Categoría (no por Canal: sería redundante, ya
    que este endpoint es el que arma el desglose por canal).
    """
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    extra_sql, extra_params = _filtro_extra(lista_vendedores, lista_categorias, None)

    yoy_inicio = fecha_inicio.replace(year=fecha_inicio.year - 1)
    yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

    with get_connection() as con:
        cy = dict(con.execute(f"""
            SELECT CANAL, SUM(BRUTO_TOTAL) FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {extra_sql}
            GROUP BY CANAL
        """, [fecha_inicio, fecha_fin, *extra_params]).fetchall())
        yoy = dict(con.execute(f"""
            SELECT CANAL, SUM(BRUTO_TOTAL) FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {extra_sql}
            GROUP BY CANAL
        """, [yoy_inicio, yoy_fin, *extra_params]).fetchall())

    resultado = []
    for canal, venta in cy.items():
        venta_yoy = yoy.get(canal, 0) or 0
        venta = venta or 0
        pct = round(((venta - venta_yoy) / venta_yoy * 100), 1) if venta_yoy else None
        resultado.append({
            "canal": canal,
            "venta": round(venta / 1_000_000, 1),
            "yoy": round(venta_yoy / 1_000_000, 1) if venta_yoy else None,
            "yoyPct": pct,
        })
    resultado.sort(key=lambda r: r["venta"], reverse=True)
    return resultado