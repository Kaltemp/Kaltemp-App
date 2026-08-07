"""
routers/sync_admin.py — Permite disparar el motor de actualización desde
la propia app (botón en el modal "Conexión de Datos"), en vez de tener
que abrir PowerShell.

Corre los scripts de sync EN SEGUNDO PLANO (threading.Thread) porque una
carga histórica de años puede tardar horas -- bloquear la petición HTTP
todo ese tiempo no es viable. El frontend consulta el progreso vía
GET /api/sync/status (polling).

Estado en memoria (no en DuckDB): se pierde si el proceso de uvicorn se
reinicia mientras corre un sync. Aceptable para este caso de uso -- si
el servidor se reinicia a mitad de una corrida, se vuelve a lanzar desde
el modal, no hay corrupción de datos (cada paso hace su propio DELETE+
INSERT al final, atómico por tabla).
"""
import os
import sys
import threading
from datetime import datetime

from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/sync", tags=["sync-admin"])

_SYNC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sync")
sys.path.insert(0, os.path.abspath(_SYNC_DIR))

from sync_ventas import sync_ventas  # noqa: E402
from sync_master import PASOS  # noqa: E402  (reutiliza el mismo orden que sync_master.py)

_lock = threading.Lock()
_estado = {
    "corriendo": False,
    "modo": None,          # "incremental" | "historico"
    "paso_actual": None,
    "pct_paso": 0,
    "mensaje": "",
    "iniciado_en": None,
    "terminado_en": None,
    "resultados": {},      # {nombre_paso: "OK" | "ERROR: ..."}
}


def _reset_estado(modo: str):
    with _lock:
        _estado.update({
            "corriendo": True, "modo": modo, "paso_actual": None, "pct_paso": 0,
            "mensaje": "Iniciando...", "iniciado_en": datetime.now().isoformat(),
            "terminado_en": None, "resultados": {},
        })


def _set_progreso(paso: str, pct: int, mensaje: str):
    with _lock:
        _estado["paso_actual"] = paso
        _estado["pct_paso"] = pct
        _estado["mensaje"] = mensaje


def _set_resultado(paso: str, ok: bool, detalle: str = ""):
    with _lock:
        _estado["resultados"][paso] = "OK" if ok else f"ERROR: {detalle}"


def _finalizar():
    with _lock:
        _estado["corriendo"] = False
        _estado["terminado_en"] = datetime.now().isoformat()
        _estado["paso_actual"] = None
        _estado["pct_paso"] = 100


def _correr_incremental():
    try:
        for nombre, funcion in PASOS:
            _set_progreso(nombre, 0, f"Iniciando {nombre}...")
            try:
                if nombre == "ventas":
                    sync_ventas(dias_atras=30, progress_callback=lambda p, m: _set_progreso(nombre, p, m))
                elif nombre.startswith("enviame_despachos"):
                    # sync_enviame y ejecutar_actualizacion_costos tienen firmas
                    # distintas -- sync_enviame acepta progress_callback,
                    # ejecutar_actualizacion_costos no.
                    try:
                        funcion(progress_callback=lambda p, m: _set_progreso(nombre, p, m))
                    except TypeError:
                        funcion()
                else:
                    funcion()
                _set_resultado(nombre, True)
            except Exception as e:
                _set_resultado(nombre, False, str(e))
    finally:
        _finalizar()


def _correr_historico(dias: int):
    try:
        _set_progreso("ventas_historico", 0, "Iniciando carga histórica...")
        try:
            sync_ventas(dias_atras=dias, progress_callback=lambda p, m: _set_progreso("ventas_historico", p, m))
            _set_resultado("ventas_historico", True)
        except Exception as e:
            _set_resultado("ventas_historico", False, str(e))
    finally:
        _finalizar()


@router.get("/status")
def get_sync_status():
    with _lock:
        return dict(_estado)


@router.post("/incremental")
def iniciar_sync_incremental():
    """Corre TODO el motor (ventas 30 días + stock + pendientes + notas
    de crédito + falabella + envíame), en el mismo orden de sync_master.py."""
    with _lock:
        if _estado["corriendo"]:
            return {"iniciado": False, "error": "Ya hay una sincronización en curso."}
    _reset_estado("incremental")
    threading.Thread(target=_correr_incremental, daemon=True).start()
    return {"iniciado": True}


@router.post("/historico")
def iniciar_sync_historico(payload: dict = Body(...)):
    """Corre SOLO sync_ventas con una ventana de días personalizada --
    para la carga histórica inicial (ej. 1825 días = 5 años)."""
    dias = int(payload.get("dias", 365))
    if dias < 1 or dias > 3650:
        return {"iniciado": False, "error": "El número de días debe estar entre 1 y 3650."}
    with _lock:
        if _estado["corriendo"]:
            return {"iniciado": False, "error": "Ya hay una sincronización en curso."}
    _reset_estado("historico")
    threading.Thread(target=_correr_historico, args=(dias,), daemon=True).start()
    return {"iniciado": True, "dias": dias}
