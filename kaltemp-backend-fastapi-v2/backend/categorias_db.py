# ============================================================
# ARCHIVO: categorias_db.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\categorias_db.py
# (Respaldar el actual antes de reemplazar: Copy-Item categorias_db.py categorias_db.py.bak
#  -- excepto peso_productos.py y PesoAlertaModal.tsx, son NUEVOS)
# ============================================================

"""
categorias_db.py — Base de datos de categorías/datos manuales asignados
a mano, separada de kaltemp_matrix.duckdb a propósito (mismo motivo que
auth_db.py: kaltemp_matrix.duckdb es de SOLO LECTURA para la API, solo
los scripts de sync la escriben).

Esta base guarda:
  - categorias_manual: SKU -> Categoría asignada a mano (por el
    importar_categorias_manual.py inicial, o desde la app vía la
    alerta de "SKU sin categoría").
  - categorias_catalogo: lista de nombres de categoría válidos (para
    poblar el selector en el modal de asignación, y evitar que se
    escriban 10 variantes del mismo nombre por typos). Compartido por
    SKUs y campañas -- misma lista de categorías reales en ambos lados.
  - campanas_categoria: nombre de campaña (Meta/Google) -> Categoría
    asignada a mano (06-ago-2026, para /api/indicadores-d2c -- antes
    se adivinaba por palabra clave en el nombre, ahora se asigna desde
    la app con la misma alerta que usamos para SKUs).
  - pesos_manual: SKU -> peso/dimensiones del paquete, asignado a mano
    (11-ago-2026, para Control Logístico -- reemplaza el 1kg fijo que
    usa actualizar_fletes_enviame.py por el peso real cuando se puede
    cruzar el envío con su documento de venta). Un SKU marcado
    'descontinuado' no necesita peso/medidas y desaparece de la alerta
    de pendientes igual que uno ya resuelto.

sync_ventas.py lee categorias_manual (solo lectura para él también,
cada quien escribe la suya) para priorizar la categoría manual por
sobre la de Bsale. channels.py lee campanas_categoria para repartir la
inversión de marketing por categoría real. actualizar_fletes_enviame.py
lee pesos_manual para calcular el peso real de un envío cuando puede
identificar su documento de venta.
"""
import os
import sqlite3
from contextlib import contextmanager

CATEGORIAS_DB_PATH = os.getenv(
    "CATEGORIAS_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaltemp_categorias.db"),
)


@contextmanager
def get_categorias_connection():
    con = sqlite3.connect(CATEGORIAS_DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def init_categorias_db():
    with get_categorias_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS categorias_manual (
                sku TEXT PRIMARY KEY,
                categoria TEXT NOT NULL,
                asignado_por TEXT,
                actualizado_en TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS categorias_catalogo (
                nombre TEXT PRIMARY KEY
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS campanas_categoria (
                campana TEXT PRIMARY KEY,
                plataforma TEXT,
                categoria TEXT NOT NULL,
                asignado_por TEXT,
                actualizado_en TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS pesos_manual (
                sku TEXT PRIMARY KEY,
                peso_kg REAL,
                largo_cm REAL,
                ancho_cm REAL,
                alto_cm REAL,
                descontinuado INTEGER NOT NULL DEFAULT 0,
                asignado_por TEXT,
                actualizado_en TEXT NOT NULL
            )
        """)
        con.commit()
