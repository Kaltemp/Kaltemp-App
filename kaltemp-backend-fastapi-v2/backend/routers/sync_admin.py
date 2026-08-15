# ============================================================
# ARCHIVO: sync_admin.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\sync_admin.py
# ('Actualizar Ahora' ahora sí pasa 30 días a TODAS las tablas que
#  lo soportan, no solo ventas. Respaldar: Copy-Item sync_admin.py sync_admin.py.bak)
# ============================================================

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

AGREGADO (10-ago-2026, a pedido de William):
  - POST /api/sync/historico-completo: corre TODAS las tablas del motor
    (mismo orden que sync_master.PASOS) en modo histórico -- "ventas" usa
    los días personalizados que mande el usuario, el resto usa su propia
    ventana histórica ya configurada (env vars, ya extendidas a
    2023-01-01 en la mayoría de los scripts).
  - POST /api/sync/paso/{nombre_paso}: corre UN SOLO paso a la vez (ej.
    solo "leads", solo "abandoned_checkouts"). Como cada script ya hace
    su propio DELETE+INSERT atómico por tabla, correr los pasos de a uno
    es la forma segura de hacer una carga histórica larga sin arriesgar
    perder el progreso completo si algo se corta a mitad de camino --
    cada paso que ya terminó queda guardado en DuckDB pase lo que pase
    con los siguientes.
  - GET /api/sync/pasos: lista los nombres de paso válidos, para que el
    frontend arme los botones sin hardcodear la lista dos veces.
"""
import os
import sys
import threading
from datetime import datetime

from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/sync", tags=["sync-admin"])

_SYNC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sync")
sys.path.insert(0, os.path.abspath(_SYNC_DIR))

from sync_ventas import sync_ventas, sync_ventas_historico_resumible, reiniciar_checkpoint_ventas  # noqa: E402
from sync_enviame import sync_enviame  # noqa: E402
from sync_master import PASOS  # noqa: E402  (reutiliza el mismo orden que sync_master.py)

PASOS_DICT = dict(PASOS)
NOMBRES_PASOS = [nombre for nombre, _ in PASOS]

# EXCLUIDAS del reproceso por ventana corta (POST /api/sync/historico,
# agregado 15-ago-2026 a pedido de William). Estas 2 tablas representan
# "estado actual" (documentos que siguen pendientes, estado de pedidos
# Falabella) y no tienen todavía un reproceso seguro por rango de fechas
# como el resto -- limitarlas a los últimos N días podría hacer
# desaparecer de la lista un documento que sigue pendiente pero fue
# emitido hace más de N días. Quedan fuera de este botón; se actualizan
# con "Carga Histórica Completa" o con su botón individual.
TABLAS_EXCLUIDAS_VENTANA = {"pendientes_despacho_docs", "falabella_estados_pedido"}

_lock = threading.Lock()
_estado = {
    "corriendo": False,
    "modo": None,          # "incremental" | "historico" | "historico_completo" | "paso:<nombre>"
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


def _ejecutar_un_paso(nombre: str, funcion, dias_ventas: int = None, dias_enviame: int = None, modo: str = None, forzar_reproceso: bool = False):
    """Corre un paso individual. 'dias_ventas' es el número que el
    usuario puso en el campo de días del motor -- pese al nombre
    (histórico, se mantiene por compatibilidad), aplica a CUALQUIER
    tabla que acepte un parámetro dias_atras, no solo a ventas. ventas
    y enviame_despachos tienen manejo especial (checkpoint resumible /
    su propio parámetro dias_enviame); el resto pasa por la rama
    genérica de abajo.

    forzar_reproceso (agregado 15-ago-2026, modo "ventana"): cuando
    ventas usa la versión resumible por checkpoint (ventanas >60 días),
    por defecto un rango ya marcado como "cubierto" no se vuelve a
    descargar. forzar_reproceso=True lo re-descarga igual, para capturar
    cambios que hayan pasado en Bsale después de la carga original."""
    _set_progreso(nombre, 0, f"Iniciando {nombre}...")
    try:
        if nombre == "ventas":
            dias = dias_ventas if dias_ventas is not None else 30
            # Ventanas grandes (carga histórica real) usan la versión
            # resumible por checkpoint; una actualización corta de 30
            # días (Actualizar Ahora, o el botón individual sin días
            # explícitos) sigue usando la versión simple -- no vale la
            # pena la complejidad de ventanas para un rango tan chico.
            # La versión simple (sync_ventas) ya hace DELETE+INSERT de
            # toda su ventana en cada corrida, así que siempre reprocesa
            # sola -- no necesita el flag forzar_reproceso.
            if dias_ventas is not None and dias > 60:
                sync_ventas_historico_resumible(
                    dias_atras=dias,
                    progress_callback=lambda p, m: _set_progreso(nombre, p, m),
                    forzar_reproceso=forzar_reproceso,
                )
            else:
                sync_ventas(dias_atras=dias, progress_callback=lambda p, m: _set_progreso(nombre, p, m))
        elif nombre == "enviame_despachos":
            sync_enviame(
                progress_callback=lambda p, m: _set_progreso(nombre, p, m),
                dias_atras=dias_enviame,
            )
        elif nombre == "enviame_despachos.COSTO_ENVIO":
            # CORREGIDO (11-ago-2026): antes esta rama siempre llamaba a
            # funcion() sin nada, así que el campo de días del motor no
            # tenía ningún efecto acá -- a diferencia de las demás tablas.
            # ejecutar_actualizacion_costos no tiene un concepto de
            # "ventana de días" real (recorre TODO enviame_despachos, no
            # filtra por fecha) -- lo que sí tiene es un modo "recalcular
            # todo" vs "solo lo pendiente". Se mapea: forzar_todo=True
            # SOLO para Carga Histórica Completa o el botón individual
            # con un valor de días puesto a mano -- NUNCA para "Actualizar
            # Ahora", que manda dias_ventas=30 fijo (no es una elección
            # real del usuario para esta tabla) y debe seguir siendo
            # rápido, solo tocando lo pendiente.
            forzar = modo in ("historico_completo", "paso_individual", "ventana") and dias_ventas is not None
            funcion(forzar_todo=forzar)
        else:
            # Genérico: intenta con dias_atras (si el usuario puso algo
            # en el campo de días) + progress_callback, y va cayendo a
            # firmas más simples si la función no los acepta -- así el
            # mismo campo de días del motor aplica a CUALQUIER tabla que
            # ya soporte dias_atras (notas_credito, temperaturas,
            # abandoned_checkouts, falabella_estados_pedido,
            # pendientes_despacho_docs, ver sync_*.py, 11-ago-2026),
            # sin tener que hardcodear cada nombre acá.
            intentos = []
            if dias_ventas is not None:
                intentos.append(lambda: funcion(progress_callback=lambda p, m: _set_progreso(nombre, p, m), dias_atras=dias_ventas))
                intentos.append(lambda: funcion(dias_atras=dias_ventas))
            intentos.append(lambda: funcion(progress_callback=lambda p, m: _set_progreso(nombre, p, m)))
            intentos.append(lambda: funcion())

            ultimo_error = None
            for intento in intentos:
                try:
                    intento()
                    ultimo_error = None
                    break
                except TypeError as e:
                    ultimo_error = e
                    continue
            if ultimo_error:
                raise ultimo_error
        _set_resultado(nombre, True)
    except Exception as e:
        _set_resultado(nombre, False, str(e))


def _correr_incremental():
    """'Actualizar Ahora' -- ahora sí les pasa 30 días a TODAS las
    tablas que lo soportan (antes solo ventas realmente usaba 30; el
    resto traía su histórico completo cada vez). Las que no aceptan
    dias_atras (sku_maestro, stock_bsale, marketing) lo ignoran
    automáticamente vía el fallback de _ejecutar_un_paso -- sin efecto
    para ellas, siguen igual que siempre."""
    try:
        for nombre, funcion in PASOS:
            _ejecutar_un_paso(nombre, funcion, dias_ventas=30, dias_enviame=30, modo="incremental")
    finally:
        _finalizar()


def _correr_historico(dias: int):
    """REESCRITO (15-ago-2026, a pedido de William): antes este botón
    corría SOLO sync_ventas. Ahora reprocesa los últimos `dias` días en
    TODAS las tablas del motor que soportan una ventana de fecha segura
    (mismo orden que sync_master.PASOS), con forzar_reproceso=True para
    que capture cambios que hayan pasado en el origen después de la
    carga original (NC aplicada más tarde, campaña de marketing
    corregida, sesión GA4 recalculada, etc.) -- sin esto, si un rango ya
    estaba marcado como "cubierto" (caso de ventas con checkpoint), el
    botón no volvía a tocarlo.

    TABLAS_EXCLUIDAS_VENTANA (pendientes_despacho_docs,
    falabella_estados_pedido) se omiten acá: son "estado actual", no
    historial por fecha -- ver el comentario en su definición más
    arriba. Quedan disponibles vía "Carga Histórica Completa" o su
    botón individual.

    Las tablas sin concepto de ventana de fecha (sku_maestro,
    stock_bsale, marketing, enviame_cruce_ventas, planilla_despachos)
    igual corren -- siempre traen su snapshot/histórico completo, así
    que "reprocesar los últimos N días" no les cambia nada, pero no
    está de más dejarlas al día también."""
    try:
        for nombre, funcion in PASOS:
            if nombre in TABLAS_EXCLUIDAS_VENTANA:
                _set_resultado(nombre, True, "omitido -- no soporta ventana corta todavía, usa Carga Histórica Completa")
                continue
            _ejecutar_un_paso(nombre, funcion, dias_ventas=dias, dias_enviame=dias, modo="ventana", forzar_reproceso=True)
    finally:
        _finalizar()


def _correr_historico_completo(dias_ventas: int, dias_enviame: int = None):
    """Corre TODAS las tablas en modo histórico, en el mismo orden que
    sync_master.PASOS. 'ventas' usa dias_ventas; 'enviame_despachos' usa
    dias_enviame si se especifica (por defecto usa ENVIAME_DIAS_ATRAS del
    .env, o 60 si tampoco está seteado); el resto usa su propia ventana
    histórica ya configurada por variable de entorno (la mayoría parte en
    2023-01-01). Si un paso falla, se registra el error y se SIGUE con el
    siguiente -- no se detiene toda la corrida por un solo paso caído.
    """
    try:
        for nombre, funcion in PASOS:
            _ejecutar_un_paso(nombre, funcion, dias_ventas=dias_ventas, dias_enviame=dias_enviame, modo="historico_completo")
    finally:
        _finalizar()


def _correr_paso_individual(nombre: str, dias_ventas: int = None, dias_enviame: int = None):
    try:
        funcion = PASOS_DICT[nombre]
        _ejecutar_un_paso(nombre, funcion, dias_ventas=dias_ventas, dias_enviame=dias_enviame, modo="paso_individual")
    finally:
        _finalizar()


@router.get("/status")
def get_sync_status():
    with _lock:
        return dict(_estado)


@router.get("/pasos")
def listar_pasos():
    """Lista los nombres de paso válidos y el orden en que corren --
    para que el frontend arme los botones individuales sin hardcodear la
    lista aparte."""
    return {"pasos": NOMBRES_PASOS}


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
    """Reprocesa los últimos 'dias' días en TODAS las tablas que
    soportan una ventana de fecha segura (todo el motor excepto
    TABLAS_EXCLUIDAS_VENTANA), forzando reproceso para capturar cambios
    posteriores en el origen. Pensado para refrescos puntuales cortos
    (ej. 5-7 días) -- para una carga histórica inicial grande (años),
    usa "Carga Histórica Completa"."""
    dias = int(payload.get("dias", 365))
    if dias < 1 or dias > 3650:
        return {"iniciado": False, "error": "El número de días debe estar entre 1 y 3650."}
    with _lock:
        if _estado["corriendo"]:
            return {"iniciado": False, "error": "Ya hay una sincronización en curso."}
    _reset_estado("historico")
    threading.Thread(target=_correr_historico, args=(dias,), daemon=True).start()
    return {"iniciado": True, "dias": dias, "pasos": [n for n in NOMBRES_PASOS if n not in TABLAS_EXCLUIDAS_VENTANA]}


@router.post("/historico-completo")
def iniciar_sync_historico_completo(payload: dict = Body(...)):
    """Corre TODAS las tablas del motor en modo histórico (mismo orden
    que sync_master.PASOS). 'ventas' usa el parámetro 'dias'; el resto
    usa su propia ventana histórica ya configurada. Opcionalmente se
    puede pasar 'dias_enviame' para pedirle a Envíame más de sus 60 días
    por defecto (requiere el fix de ENVIAME_DIAS_ATRAS)."""
    dias = int(payload.get("dias", 1825))
    if dias < 1 or dias > 3650:
        return {"iniciado": False, "error": "El número de días debe estar entre 1 y 3650."}
    dias_enviame = payload.get("dias_enviame")
    dias_enviame = int(dias_enviame) if dias_enviame else None

    with _lock:
        if _estado["corriendo"]:
            return {"iniciado": False, "error": "Ya hay una sincronización en curso."}
    _reset_estado("historico_completo")
    threading.Thread(target=_correr_historico_completo, args=(dias, dias_enviame), daemon=True).start()
    return {"iniciado": True, "dias": dias, "dias_enviame": dias_enviame, "pasos": NOMBRES_PASOS}


@router.post("/paso/{nombre_paso}")
def iniciar_sync_paso(nombre_paso: str, payload: dict = Body(default={})):
    """Corre UN SOLO paso del motor por nombre (ej. 'leads',
    'abandoned_checkouts', 'ventas'). Pensado para cargas históricas por
    partes: si se corta a mitad de camino, solo se pierde el paso que
    estaba corriendo en ese momento -- los anteriores ya quedaron
    guardados en DuckDB (cada script hace su propio DELETE+INSERT
    atómico), y se puede re-lanzar solo el paso que faltó."""
    if nombre_paso not in PASOS_DICT:
        return {
            "iniciado": False,
            "error": f"Paso desconocido: '{nombre_paso}'. Válidos: {NOMBRES_PASOS}",
        }
    with _lock:
        if _estado["corriendo"]:
            return {"iniciado": False, "error": "Ya hay una sincronización en curso."}

    dias_ventas = payload.get("dias")
    dias_ventas = int(dias_ventas) if dias_ventas else None
    dias_enviame = payload.get("dias_enviame")
    dias_enviame = int(dias_enviame) if dias_enviame else None

    _reset_estado(f"paso:{nombre_paso}")
    threading.Thread(
        target=_correr_paso_individual,
        args=(nombre_paso, dias_ventas, dias_enviame),
        daemon=True,
    ).start()
    return {"iniciado": True, "paso": nombre_paso}