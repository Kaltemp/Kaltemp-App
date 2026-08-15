"""
Módulo Detalle Fulfillment — replica EXACTA de la lógica de app.py (Streamlit):
ventas de fulfillment = ORIGEN in ('BSALE_FULL', 'FALABELLA_API'), sobre la
misma tabla `ventas` (no existe ni hace falta una tabla separada).

AGREGADO (02-ago-2026): endpoint /api/fulfillment-por-producto -- desglose
real por producto y canal (antes esto era 100% mock en el frontend, con
productos que ni siquiera existen en el catálogo real). Se arma agrupando
`ventas` por PRODUCTO + CANAL (mismas columnas que ya usa el resto de la
app, sin depender de una lista fija de canales -- confirmado que "RIPLEY"
ni siquiera está en ALL_CHANNELS, así que no se asume una grilla fija
FBF/FBM/FBP/FBR; se devuelve una fila por combinación producto+canal
realmente presente en los datos).

NOTA IMPORTANTE (confirmado con William, 02-ago-2026): el propio origen de
los datos de `ventas.ORIGEN IN ('BSALE_FULL','FALABELLA_API')` es externo a
este backend -- Falabella se trae directo de Falabella Seller Center, el
resto de los marketplaces (Mercado Libre, Paris, etc.) se traen de Bsale
vía consumos de stock en la bodega "Full MKP" (GET /v1/stocks/consumptions.json,
con el precio de venta embebido en el campo `note`/observación de cada
consumo -- confirmado real, endpoint documentado en
https://apichile.bsalelab.com/lista-de-endpoints/productos-y-servicios/stocks).
Ese proceso de sync ya puebla `ventas` correctamente (es el mismo que usa
el módulo Principal) -- este router NO lo reimplementa, solo lo consulta.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from db import get_connection

router = APIRouter(prefix="/api", tags=["fulfillment"])

_ORIGENES_FULL = ("BSALE_FULL", "FALABELLA_API")


def _totales_periodo(con, fecha_inicio: date, fecha_fin: date) -> dict:
    placeholders = ", ".join(["?"] * len(_ORIGENES_FULL))
    sql = f"""
        SELECT
            SUM(BRUTO_TOTAL) AS venta,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END) AS contribucion,
            SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END) AS neto
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND ORIGEN IN ({placeholders})
    """
    fila = con.execute(sql, [fecha_inicio, fecha_fin, *_ORIGENES_FULL]).fetchone()
    venta, contribucion, neto = (fila or (0, 0, 0))
    return {"venta": venta or 0, "contribucion": contribucion or 0, "neto": neto or 0}


def _venta_directa_periodo(con, fecha_inicio: date, fecha_fin: date) -> float:
    """
    Venta directa (Bsale/sitio propio) = todo lo que NO es fulfillment --
    para la comparativa real "Directa vs Fulfillment" (antes esos 2 números
    estaban escritos a mano en el frontend).
    """
    placeholders = ", ".join(["?"] * len(_ORIGENES_FULL))
    sql = f"""
        SELECT SUM(BRUTO_TOTAL)
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND ORIGEN NOT IN ({placeholders})
    """
    fila = con.execute(sql, [fecha_inicio, fecha_fin, *_ORIGENES_FULL]).fetchone()
    return (fila[0] if fila else 0) or 0


def _por_canal(con, fecha_inicio: date, fecha_fin: date):
    placeholders = ", ".join(["?"] * len(_ORIGENES_FULL))
    sql = f"""
        SELECT CANAL, ORIGEN, SUM(BRUTO_TOTAL) AS venta
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND ORIGEN IN ({placeholders})
        GROUP BY CANAL, ORIGEN
        ORDER BY venta DESC
    """
    filas = con.execute(sql, [fecha_inicio, fecha_fin, *_ORIGENES_FULL]).fetchall()
    return [{"canal": r[0], "origen": r[1], "venta": round(r[2] or 0, 0)} for r in filas]


@router.get("/fulfillment")
def get_fulfillment(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    wow_ini, wow_fin = fecha_inicio - timedelta(days=7), fecha_fin - timedelta(days=7)
    yoy_ini, yoy_fin = fecha_inicio.replace(year=fecha_inicio.year - 1), fecha_fin.replace(year=fecha_fin.year - 1)

    with get_connection() as con:
        cy = _totales_periodo(con, fecha_inicio, fecha_fin)
        wow = _totales_periodo(con, wow_ini, wow_fin)
        yoy = _totales_periodo(con, yoy_ini, yoy_fin)
        programas = _por_canal(con, fecha_inicio, fecha_fin)
        venta_directa_cy = _venta_directa_periodo(con, fecha_inicio, fecha_fin)
        venta_directa_yoy = _venta_directa_periodo(con, yoy_ini, yoy_fin)

    margen_frontal = (cy["contribucion"] / cy["neto"] * 100) if cy["neto"] else 0.0
    total_consolidado = cy["venta"] + venta_directa_cy
    share_fulfillment = (cy["venta"] / total_consolidado * 100) if total_consolidado else 0.0
    total_consolidado_yoy = yoy["venta"] + venta_directa_yoy
    share_fulfillment_yoy = (yoy["venta"] / total_consolidado_yoy * 100) if total_consolidado_yoy else 0.0

    return {
        "ventaCy": round(cy["venta"], 0),
        "ventaWow": round(wow["venta"], 0),
        "ventaYoy": round(yoy["venta"], 0),
        "contribucionCy": round(cy["contribucion"], 0),
        "contribucionWow": round(wow["contribucion"], 0),
        "contribucionYoy": round(yoy["contribucion"], 0),
        "margenFrontalCy": round(margen_frontal, 1),
        "programas": programas,
        "ventaDirectaCy": round(venta_directa_cy, 0),
        "ventaDirectaYoy": round(venta_directa_yoy, 0),
        "totalConsolidadoCy": round(total_consolidado, 0),
        "shareFulfillmentCy": round(share_fulfillment, 1),
        "shareFulfillmentYoy": round(share_fulfillment_yoy, 1),
    }


def _por_producto_canal(con, fecha_inicio: date, fecha_fin: date) -> dict:
    """
    (PRODUCTO, CANAL) -> {unidades, venta}. Misma tabla `ventas` real, sin
    inventar columnas: se usa CANTIDAD (unidades) y BRUTO_TOTAL (venta),
    exactamente igual a como ya se usan en el resto de la app.

    DESPACHO (07-ago-2026): se excluye ES_GLOSA_SERVICIO -- esta es una
    tabla "por producto", así que una línea de despacho no debe poder
    aparecer como si fuera un producto vendido.
    """
    placeholders = ", ".join(["?"] * len(_ORIGENES_FULL))
    sql = f"""
        SELECT PRODUCTO, CANAL, SUM(CANTIDAD) AS unidades, SUM(BRUTO_TOTAL) AS venta
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND ORIGEN IN ({placeholders})
          AND PRODUCTO IS NOT NULL AND TRIM(PRODUCTO) != ''
          AND NOT ES_GLOSA_SERVICIO
        GROUP BY PRODUCTO, CANAL
    """
    filas = con.execute(sql, [fecha_inicio, fecha_fin, *_ORIGENES_FULL]).fetchall()
    return {(f[0], f[1]): {"unidades": f[2] or 0, "venta": f[3] or 0} for f in filas}


@router.get("/fulfillment-por-producto")
def get_fulfillment_por_producto(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    """
    Desglose real por PRODUCTO + CANAL (reemplaza la tabla que antes era
    100% mock en el frontend). Una fila por combinación producto+canal
    realmente presente en `ventas` -- no se asume una grilla fija de
    canales (FBF/FBM/FBP/FBR), porque no todos esos canales están
    necesariamente activos en la cuenta real (ej. Ripley no aparece en
    ALL_CHANNELS hoy).
    """
    yoy_ini = fecha_inicio.replace(year=fecha_inicio.year - 1)
    yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

    with get_connection() as con:
        actual = _por_producto_canal(con, fecha_inicio, fecha_fin)
        anterior = _por_producto_canal(con, yoy_ini, yoy_fin)

    claves = set(actual.keys()) | set(anterior.keys())
    filas = []
    for producto, canal in claves:
        cy = actual.get((producto, canal), {"unidades": 0, "venta": 0})
        yoy = anterior.get((producto, canal), {"unidades": 0, "venta": 0})
        unidades_yoy = yoy["unidades"]
        var_pct = (
            ((cy["unidades"] - unidades_yoy) / unidades_yoy * 100)
            if unidades_yoy else (100.0 if cy["unidades"] else 0.0)
        )
        venta_yoy = yoy["venta"]
        venta_var_pct = (
            ((cy["venta"] - venta_yoy) / venta_yoy * 100)
            if venta_yoy else (100.0 if cy["venta"] else 0.0)
        )
        filas.append({
            "id": f"{producto}|{canal}",
            "producto": producto,
            "canal": canal or "Sin canal",
            "unidades": cy["unidades"],
            "unidadesYoy": unidades_yoy,
            "varPct": round(var_pct, 1),
            "venta": round(cy["venta"], 0),
            "ventaYoy": round(venta_yoy, 0),
            "ventaVarPct": round(venta_var_pct, 1),
        })

    filas.sort(key=lambda r: r["venta"], reverse=True)
    return {"items": filas}