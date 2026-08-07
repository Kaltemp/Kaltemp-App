"""
auth_db.py — Base de datos de usuarios/sesiones, separada de kaltemp_matrix.duckdb
a propósito.

kaltemp_matrix.duckdb es de SOLO LECTURA para esta API (solo los scripts de
sync la escriben, por diseño -- ver db.py). Usuarios y contraseñas necesitan
un lugar que la API SÍ pueda escribir libremente (crear usuarios, resetear
contraseñas, etc. desde UserManagementModal), sin tocar ese patrón ni
competir por locks con el proceso de sync.

Se usa SQLite (stdlib, sin dependencias nuevas) en un archivo aparte:
kaltemp_users.db. Para ~10 usuarios el volumen es trivial, así que no hay
impacto de rendimiento sobre el resto de la app.

Contraseñas: NUNCA se guardan en texto plano -- se hashean con bcrypt antes
de insertarse (ver routers/auth.py). Esta base solo guarda el hash.
"""
import os
import sqlite3
from contextlib import contextmanager

USERS_DB_PATH = os.getenv(
    "USERS_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaltemp_users.db"),
)

SESSION_TTL_DAYS = 30


@contextmanager
def get_users_connection():
    con = sqlite3.connect(USERS_DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
    finally:
        con.close()


def _migrar_avatar_icon(con):
    """Agrega columnas si la base ya existía de antes de estos cambios
    (07-ago-2026, catálogo de avatares + foto propia) -- CREATE TABLE IF
    NOT EXISTS no altera tablas ya creadas, así que hay que migrar a mano."""
    columnas = [row[1] for row in con.execute("PRAGMA table_info(users)").fetchall()]
    if "avatar_icon" not in columnas:
        con.execute("ALTER TABLE users ADD COLUMN avatar_icon TEXT")
    if "avatar_image_url" not in columnas:
        con.execute("ALTER TABLE users ADD COLUMN avatar_image_url TEXT")
    con.commit()


def init_users_db():
    """Crea las tablas si no existen. Se llama al arrancar la app (main.py)."""
    with get_users_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL,
                avatar_color TEXT NOT NULL,
                avatar_icon TEXT,
                avatar_image_url TEXT,
                password_hash TEXT NOT NULL,
                blocked_modules TEXT NOT NULL DEFAULT '[]',
                allowed_modules_only TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        con.commit()
        _migrar_avatar_icon(con)
