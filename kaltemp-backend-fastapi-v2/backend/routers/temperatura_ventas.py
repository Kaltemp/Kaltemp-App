"""
Módulo Ventas vs. Temperatura — replica app.py: ventas diarias desde
`ventas` (BRUTO_TOTAL agrupado por FECHA_OBJ) + clima real de Open-Meteo
/ DuckDB (tabla `temperaturas`) incluyendo comparativo YoY.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from db import get_connection
import requests

router = APIRouter(prefix="/api", tags=["temperature"])

_LAT, _LON = "-33.45", "-70.66"


def _get_yoy_date(dt: date) -> date:
    """Retorna la misma fecha pero del año anterior (YoY)."""
    try:
        return dt.replace(year=dt.year - 1)
    except ValueError:
        # Manejo de años bisiestos (29 feb -> 28 feb)
        return dt.replace(year=dt.year - 1, day=28)


def _obtener_clima_api(fecha_inicio_str: str, fecha_fin_str: str) -> dict:
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?latitude={_LAT}&longitude={_LON}"
        f"&start_date={fecha_inicio_str}&end_date={fecha_fin_str}"
        f"&daily=temperature_2m_max,temperature_2m_min&timezone=America%2FSantiago"
    )
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            # Fallback a forecast para rangos muy recientes
            url = url.replace("archive-api.open-meteo.com/v1/archive", "api.open-meteo.com/v1/forecast")
            res = requests.get(url, timeout=5)
        if res.status_code == 200:
            daily = res.json().get("daily", {})
            fechas = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            return {
                f: {
                    "max": float(ma) if ma is not None else 0.0,
                    "min": float(mi) if mi is not None else 0.0
                }
                for f, ma, mi in zip(fechas, maxs, mins)
            }
    except Exception:
        pass
    return {}


def _obtener_clima_rango(con, fecha_inicio: date, fecha_fin: date) -> dict:
    """Consulta la tabla DuckDB `temperaturas` y complementa con Open-Meteo API si faltan días."""
    clima = {}
    try:
        sql = """
            SELECT CAST(FECHA AS DATE) AS fecha, TEMP_MAX, TEMP_MIN
            FROM temperaturas
            WHERE CAST(FECHA AS DATE) BETWEEN ? AND ?
        """
        rows = con.execute(sql, [fecha_inicio, fecha_fin]).fetchall()
        for f, tmax, tmin in rows:
            if f is not None:
                clima[f.isoformat()] = {
                    "max": float(tmax) if tmax is not None else 0.0,
                    "min": float(tmin) if tmin is not None else 0.0
                }
    except Exception:
        pass

    # Verificar si faltan fechas en el rango
    cur = fecha_inicio
    faltan = False
    while cur <= fecha_fin:
        if cur.isoformat() not in clima:
            faltan = True
            break
        cur += timedelta(days=1)

    # Si faltan fechas en DuckDB, llamar a la API
    if faltan:
        api_data = _obtener_clima_api(fecha_inicio.isoformat(), fecha_fin.isoformat())
        for f_str, vals in api_data.items():
            if f_str not in clima or clima[f_str]["max"] == 0:
                clima[f_str] = vals

    return clima


@router.get("/ventas-temperatura")
def get_ventas_temperatura(fecha_inicio: date = Query(...), fecha_fin: date = Query(...)):
    sql = """
        SELECT CAST(FECHA_OBJ AS DATE) AS fecha, SUM(BRUTO_TOTAL) AS venta
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
        GROUP BY fecha
        ORDER BY fecha ASC
    """
    with get_connection() as con:
        filas = con.execute(sql, [fecha_inicio, fecha_fin]).fetchall()

        # Rangos para período actual y período YoY (año anterior)
        fecha_inicio_yoy = _get_yoy_date(fecha_inicio)
        fecha_fin_yoy = _get_yoy_date(fecha_fin)

        clima_act = _obtener_clima_rango(con, fecha_inicio, fecha_fin)
        clima_yoy = _obtener_clima_rango(con, fecha_inicio_yoy, fecha_fin_yoy)

    resultado = []
    for fecha, venta in filas:
        fecha_str = fecha.isoformat()
        fecha_yoy_str = _get_yoy_date(fecha).isoformat()

        c_act = clima_act.get(fecha_str, {})
        c_yoy = clima_yoy.get(fecha_yoy_str, {})

        resultado.append({
            "fechaStr": fecha_str,
            "fechaDisp": fecha.strftime("%d-%m"),
            "brutoTotal": round(float(venta or 0), 0),
            "tempMax": round(float(c_act.get("max", 0) or 0), 1),
            "tempMin": round(float(c_act.get("min", 0) or 0), 1),
            "tempMaxYoY": round(float(c_yoy.get("max", 0) or 0), 1),
            "tempMinYoY": round(float(c_yoy.get("min", 0) or 0), 1),
        })
    return resultado