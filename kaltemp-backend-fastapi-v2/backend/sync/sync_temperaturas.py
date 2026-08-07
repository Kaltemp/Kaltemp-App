"""
sync/sync_temperaturas.py — Descarga las temperaturas históricas reales de
Santiago de Chile desde Open-Meteo (API Gratuita) y puebla la tabla `temperaturas`
en kaltemp_matrix.duckdb.
"""
import os
import sys
import requests
import duckdb
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

# Coordenadas de Santiago de Chile
LATITUD = "-33.45"
LONGITUD = "-70.66"


def descargar_clima_santiago(f_inicio_str, f_fin_str):
    """Consulta la API de Open-Meteo para Santiago"""
    url_archive = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={LATITUD}&longitude={LONGITUD}&start_date={f_inicio_str}&end_date={f_fin_str}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean&timezone=America%2FSantiago"
    )
    
    try:
        res = requests.get(url_archive, timeout=20)
        if res.status_code != 200:
            # Fallback a Forecast API para los días más recientes
            url_forecast = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={LATITUD}&longitude={LONGITUD}&start_date={f_inicio_str}&end_date={f_fin_str}"
                f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean&timezone=America%2FSantiago"
            )
            res = requests.get(url_forecast, timeout=20)

        if res.status_code == 200:
            daily = res.json().get("daily", {})
            times = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            means = daily.get("temperature_2m_mean", [])

            filas = []
            for t, t_max, t_min, t_mean in zip(times, maxs, mins, means):
                dt_obj = datetime.strptime(t, "%Y-%m-%d")
                v_max = float(t_max) if t_max is not None else 0.0
                v_min = float(t_min) if t_min is not None else 0.0
                v_prom = float(t_mean) if t_mean is not None else (v_max + v_min) / 2.0
                
                filas.append((dt_obj, v_max, v_min, v_prom))
            return filas
    except Exception as e:
        print(f"⚠️ Error consultando API de Clima Open-Meteo: {e}")

    return []


def sync_temperaturas():
    hoy = date.today()
    fecha_inicio_str = "2021-01-01"
    fecha_fin_str = hoy.strftime("%Y-%m-%d")

    print(f"[{datetime.now()}] 🌡️ Descargando clima de Santiago desde {fecha_inicio_str} hasta {fecha_fin_str}...")
    filas = descargar_clima_santiago(fecha_inicio_str, fecha_fin_str)

    print(f"[{datetime.now()}] 💾 Escribiendo {len(filas)} días de temperatura en DuckDB...")

    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS temperaturas (
                FECHA TIMESTAMP PRIMARY KEY,
                TEMP_MAX DOUBLE,
                TEMP_MIN DOUBLE,
                TEMP_PROM DOUBLE
            )
        """)
        con.execute("DELETE FROM temperaturas")
        con.executemany(
            "INSERT OR REPLACE INTO temperaturas (FECHA, TEMP_MAX, TEMP_MIN, TEMP_PROM) VALUES (?, ?, ?, ?)",
            filas
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["temperaturas", datetime.now(timezone.utc).replace(tzinfo=None)]
        )
        print(f"[{datetime.now()}] ✅ Tabla 'temperaturas' actualizada ({len(filas)} días guardados).")


if __name__ == "__main__":
    sync_temperaturas()