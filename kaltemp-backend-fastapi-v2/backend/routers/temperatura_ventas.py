"""
Módulo Ventas vs. Temperatura — replica app.py: ventas diarias desde
`ventas` (BRUTO_TOTAL agrupado por FECHA_OBJ) + clima real de Open-Meteo
para Santiago (mismo endpoint y fallback forecast que usaba Streamlit).
"""
from datetime import date
from fastapi import APIRouter, Query
from db import get_connection
import requests

router = APIRouter(prefix="/api", tags=["temperature"])

_LAT, _LON = "-33.45", "-70.66"


def _obtener_clima(fecha_inicio: str, fecha_fin: str) -> dict:
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?latitude={_LAT}&longitude={_LON}"
        f"&start_date={fecha_inicio}&end_date={fecha_fin}"
        f"&daily=temperature_2m_max,temperature_2m_min&timezone=America%2FSantiago"
    )
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            # Fallback a forecast (igual que Streamlit) para rangos muy recientes
            url = url.replace("archive-api.open-meteo.com/v1/archive", "api.open-meteo.com/v1/forecast")
            res = requests.get(url, timeout=5)
        if res.status_code == 200:
            daily = res.json().get("daily", {})
            fechas = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            return {f: {"max": ma, "min": mi} for f, ma, mi in zip(fechas, maxs, mins)}
    except Exception:
        pass
    return {}


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

    clima = _obtener_clima(fecha_inicio.isoformat(), fecha_fin.isoformat())

    resultado = []
    for fecha, venta in filas:
        fecha_str = fecha.isoformat()
        c = clima.get(fecha_str, {})
        resultado.append({
            "fechaStr": fecha_str,
            "fechaDisp": fecha.strftime("%d-%m"),
            "brutoTotal": round(venta or 0, 0),
            "tempMax": c.get("max", 0) or 0,
            "tempMin": c.get("min", 0) or 0,
        })
    return resultado
