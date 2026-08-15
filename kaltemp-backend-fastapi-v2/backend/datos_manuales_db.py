# ============================================================
# Archivo: datos_manuales_db.py
# Ruta:    backend/datos_manuales_db.py
# ============================================================

"""
datos_manuales_db.py — Base de datos de valores cargados manualmente
desde la app (metas históricas por año, presupuesto de marketing, y
cualquier otro dato de gestión que no viene de ninguna API), separada
de kaltemp_matrix.duckdb a propósito (mismo motivo que categorias_db.py
y auth_db.py: kaltemp_matrix.duckdb es de SOLO LECTURA para la API,
solo los scripts de sync la escriben).

Esta base guarda una única tabla genérica "datos_manuales" en formato
(periodo, tipo, marca) -> monto, para no tener que crear una tabla nueva
cada vez que se necesite un dato de gestión distinto:

  - periodo: string libre. Para métricas anuales usar el año ("2023",
    "2024"...). Para presupuesto de marketing mensual usar "2026-07".
  - tipo: uno de los valores en TIPOS_VALIDOS más abajo.
  - marca: una de MARCAS_VALIDAS más abajo (Kaltemp o Tom Palmer) --
    AGREGADO 09-ago-2026: antes la tabla solo tenía PRIMARY KEY
    (periodo, tipo), así que cargar un presupuesto de marketing para
    Tom Palmer sobrescribía silenciosamente el de Kaltemp del mismo
    período (mismo problema para metas/venta real, aunque en la
    práctica solo afectaba a presupuesto_marketing porque el resto de
    tipos son consolidados de toda la empresa). El resto del dashboard
    ya distingue Kaltemp/Tom Palmer en todos lados (channels.py,
    marketing.py) -- esta tabla era la única que no.
  - monto: el valor numérico (en $, mismas unidades que el resto del
    dashboard -- pesos chilenos completos, NO millones).
  - notas: texto libre opcional (ej. "estimado desde reporte Excel Q3").

cumplimiento.py lee esta tabla para el gráfico "Comparativo Histórico
de Cumplimiento" (años sin data real en `ventas` -- 2023/2024/2025 --
se completan 100% desde acá; el año en curso usa `ventas` real y solo
recurre a esta tabla para la META, que siempre es manual).
"""
import os
import sqlite3
from contextlib import contextmanager

DATOS_MANUALES_DB_PATH = os.getenv(
    "DATOS_MANUALES_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaltemp_datos_manuales.db"),
)

# Tipos de dato manual soportados hoy. Agregar acá cualquier métrica
# nueva de gestión (ej. "meta_unidades_anual") antes de usarla desde
# el endpoint, para que quede documentada y el modal la pueda listar.
TIPOS_VALIDOS = (
    "meta_venta_anual",
    "meta_contribucion_anual",
    "venta_real_manual",
    "contribucion_real_manual",
    "presupuesto_marketing",
)

# Marcas soportadas -- mismos 2 valores que ya usa el resto de la app
# (channels.py Query "Kaltemp"/"Tom Palmer", marketing.py filtro _marca).
MARCAS_VALIDAS = (
    "Kaltemp",
    "Tom Palmer",
)


@contextmanager
def get_datos_manuales_connection():
    con = sqlite3.connect(DATOS_MANUALES_DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def init_datos_manuales_db():
    with get_datos_manuales_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS datos_manuales (
                periodo TEXT NOT NULL,
                tipo TEXT NOT NULL,
                marca TEXT NOT NULL DEFAULT 'Kaltemp',
                monto REAL NOT NULL,
                notas TEXT,
                actualizado_por TEXT,
                actualizado_en TEXT NOT NULL,
                PRIMARY KEY (periodo, tipo, marca)
            )
        """)

        # Migración para instalaciones que ya tenían la tabla con el
        # esquema viejo (PRIMARY KEY periodo+tipo, sin columna marca).
        # SQLite no permite cambiar una PRIMARY KEY con ALTER TABLE, así
        # que se reconstruye la tabla completa preservando cualquier dato
        # ya cargado -- queda asignado a "Kaltemp" por default, ya que
        # antes de este cambio el presupuesto no distinguía marca.
        cols = [r["name"] for r in con.execute("PRAGMA table_info(datos_manuales)").fetchall()]
        if "marca" not in cols:
            con.execute("ALTER TABLE datos_manuales RENAME TO datos_manuales_old")
            con.execute("""
                CREATE TABLE datos_manuales (
                    periodo TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    marca TEXT NOT NULL DEFAULT 'Kaltemp',
                    monto REAL NOT NULL,
                    notas TEXT,
                    actualizado_por TEXT,
                    actualizado_en TEXT NOT NULL,
                    PRIMARY KEY (periodo, tipo, marca)
                )
            """)
            con.execute("""
                INSERT INTO datos_manuales (periodo, tipo, marca, monto, notas, actualizado_por, actualizado_en)
                SELECT periodo, tipo, 'Kaltemp', monto, notas, actualizado_por, actualizado_en
                FROM datos_manuales_old
            """)
            con.execute("DROP TABLE datos_manuales_old")

        con.commit()