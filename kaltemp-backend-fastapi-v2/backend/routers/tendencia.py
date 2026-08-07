"""
Tendencia Mensual + Acumulado YTD — Módulo Principal.

Ambos widgets usan exclusivamente la tabla `ventas` (ya conocida),
así que se conectan sin riesgo de columnas inexistentes.

El rango de fechas del sidebar NO aplica acá a propósito (son vistas de
histórico anual: los 12 meses del año, o el acumulado desde el 1 de enero),
pero Categoría/Canal/Vendedor SÍ se filtran, para poder ver el
comportamiento mensual/acumulado de un segmento específico.
"""
from datetime import date
from fastapi import APIRouter, Query
from typing import Optional
from db import get_connection
import pandas as pd

router = APIRouter(prefix="/api", tags=["tendencia"])

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _parse_fecha(fecha_fin_param, fecha_param, fecha_inicio_param) -> date:
    """Convierte cualquier variante de parámetro de fecha a un objeto date válido"""
    raw = fecha_fin_param or fecha_param or fecha_inicio_param
    if not raw or str(raw).strip().lower() in ("null", "undefined", "none", ""):
        return date.today()
    if isinstance(raw, date):
        return raw
    raw_str = str(raw).strip()
    try:
        # Formato ISO (YYYY-MM-DD) es inequívoco -- nunca debe pasar por
        # dayfirst, que puede confundir mes/día (bug confirmado 05-ago-2026:
        # "2026-08-02" se parseaba como 8 de febrero en vez de 2 de agosto,
        # dejando /api/acumulado-ytd en $0 porque el rango de fechas
        # resultante no calzaba con ninguna venta real).
        dt = pd.to_datetime(raw_str, format="%Y-%m-%d", errors="raise")
        return dt.date()
    except (ValueError, TypeError):
        pass
    try:
        dt = pd.to_datetime(raw_str, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return date.today()


def _filtro_extra(vendedores: list[str] | None, categorias: list[str] | None, canales: list[str] | None):
    """Arma el WHERE adicional + params comunes a ambos endpoints."""
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


def _parse_csv(valor: str | None) -> list[str] | None:
    return [v.strip() for v in valor.split(",") if v.strip()] if valor else None


@router.get("/tendencia-mensual")
def get_tendencia_mensual(
    fecha_fin: Optional[str] = Query(None),
    fecha: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    vendedores: Optional[str] = Query(None),
    categorias: Optional[str] = Query(None),
    canales: Optional[str] = Query(None),
):
    """
    Venta bruta mes a mes del año de fecha_fin, comparado contra el
    mismo mes del año anterior. Montos en millones (para que calcen
    directo con el gráfico, que ya formatea "$ X M").
    """
    f_corte = _parse_fecha(fecha_fin, fecha, fecha_inicio)
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    extra_sql, extra_params = _filtro_extra(lista_vendedores, lista_categorias, lista_canales)

    anio_actual = f_corte.year
    anio_anterior = anio_actual - 1

    sql = f"""
        SELECT
            EXTRACT(YEAR FROM CAST(FECHA_OBJ AS DATE))::INTEGER  AS anio,
            EXTRACT(MONTH FROM CAST(FECHA_OBJ AS DATE))::INTEGER AS mes,
            SUM(BRUTO_TOTAL) AS venta
        FROM ventas
        WHERE EXTRACT(YEAR FROM CAST(FECHA_OBJ AS DATE)) IN (?, ?)
        {extra_sql}
        GROUP BY anio, mes
    """
    with get_connection() as con:
        cursor = con.execute(sql, [anio_actual, anio_anterior, *extra_params])
        filas = cursor.fetchall()

    ventas_cy = [0.0] * 12
    ventas_ly = [0.0] * 12
    for anio, mes, venta in filas:
        valor_millones = round((venta or 0) / 1_000_000, 1)
        if anio == anio_actual:
            ventas_cy[mes - 1] = valor_millones
        elif anio == anio_anterior:
            ventas_ly[mes - 1] = valor_millones

    resultado = []
    for i, nombre_mes in enumerate(_MESES):
        cy, ly = ventas_cy[i], ventas_ly[i]
        yoy = round(((cy - ly) / ly * 100), 1) if ly else 0.0
        resultado.append({"month": nombre_mes, "cy": cy, "ly": ly, "yoy": yoy})

    return resultado


@router.get("/acumulado-ytd")
def get_acumulado_ytd(
    fecha_fin: Optional[str] = Query(None),
    fecha: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    vendedores: Optional[str] = Query(None),
    categorias: Optional[str] = Query(None),
    canales: Optional[str] = Query(None),
):
    """
    Venta bruta acumulada desde el 1 de enero hasta fecha_fin,
    comparada contra el mismo período del año anterior, más una
    proyección simple de cierre de año por "run-rate" (venta diaria
    promedio del período extrapolada a 365 días).
    """
    f_corte = _parse_fecha(fecha_fin, fecha, fecha_inicio)
    lista_vendedores = _parse_csv(vendedores)
    lista_categorias = _parse_csv(categorias)
    lista_canales = _parse_csv(canales)
    extra_sql, extra_params = _filtro_extra(lista_vendedores, lista_categorias, lista_canales)

    anio_actual = f_corte.year
    inicio_actual = date(anio_actual, 1, 1)
    inicio_anterior = date(anio_actual - 1, 1, 1)
    
    try:
        fin_anterior = f_corte.replace(year=anio_actual - 1)
    except Exception:
        fin_anterior = date(anio_actual - 1, 12, 31)

    sql = f"SELECT SUM(BRUTO_TOTAL) FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? {extra_sql}"
    with get_connection() as con:
        actual = (con.execute(sql, [inicio_actual, f_corte, *extra_params]).fetchone() or [0])[0] or 0
        anterior = (con.execute(sql, [inicio_anterior, fin_anterior, *extra_params]).fetchone() or [0])[0] or 0

    dias_transcurridos = (f_corte - inicio_actual).days + 1
    proyeccion = (actual / dias_transcurridos * 365) if dias_transcurridos > 0 else 0

    return {
        "actual": round(actual / 1_000_000, 1),
        "yoy": round(anterior / 1_000_000, 1),
        "proyeccion": round(proyeccion / 1_000_000, 1),
        "yoyPct": round(((actual - anterior) / anterior * 100), 1) if anterior else 0.0,
    }