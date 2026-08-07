"""
routers/auth.py — Login real contra el backend (reemplaza la validación
100% client-side que vivía en UserContext.tsx con las contraseñas de todos
los usuarios en texto plano dentro del bundle de JS).

Flujo:
  POST /api/auth/login          -> valida email+password contra el hash
                                    guardado, crea una sesión, devuelve token
  GET  /api/auth/me             -> perfil del usuario dueño del token
  POST /api/auth/logout         -> invalida el token
  GET  /api/auth/users          -> lista usuarios (SIN password), solo Admin
  POST /api/auth/users          -> crea usuario, solo Admin
  PATCH /api/auth/users/{id}    -> edita rol/nombre/módulos, solo Admin
  POST /api/auth/users/{id}/reset-password -> solo Admin
  DELETE /api/auth/users/{id}   -> solo Admin
  POST /api/auth/impersonate    -> "Simular Sesión" del UserManagementModal,
                                    solo Admin, sin necesitar la contraseña
                                    del usuario a simular

El token se manda en el header: Authorization: Bearer <token>
"""
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, HTTPException, Header, Body, UploadFile, File
from pydantic import BaseModel

from auth_db import get_users_connection, SESSION_TTL_DAYS

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ------------------------------------------------------------------
# Avatar -- foto propia (07-ago-2026)
# Se guarda en disco (backend/static/avatars/{user_id}.{ext}) y se sirve
# vía el mount de StaticFiles en main.py -- no en kaltemp_matrix.duckdb
# ni en kaltemp_users.db, para no inflar esas bases con binarios.
# ------------------------------------------------------------------
_AQUI = os.path.dirname(os.path.abspath(__file__))
AVATAR_DIR = os.path.abspath(os.path.join(_AQUI, "..", "static", "avatars"))
os.makedirs(AVATAR_DIR, exist_ok=True)

ALLOWED_AVATAR_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


# ------------------------------------------------------------------
# Modelos de entrada
# ------------------------------------------------------------------
class LoginBody(BaseModel):
    email: str
    password: str


class CreateUserBody(BaseModel):
    email: str
    nombre: str
    rol: str
    password: str
    avatarColor: Optional[str] = None
    avatarIcon: Optional[str] = None
    blockedModules: Optional[list[str]] = None
    allowedModulesOnly: Optional[list[str]] = None


class UpdateUserBody(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    avatarColor: Optional[str] = None
    # OJO: avatarIcon usa un sentinel (string vacío "") para poder distinguir
    # "no lo mandaron" (None -- no tocar) de "el usuario eligió quitar el
    # ícono y volver a solo iniciales" (avatarIcon=None explícito no se
    # puede distinguir de "campo ausente" en un PATCH parcial de Pydantic,
    # por eso el frontend manda "" para "sin ícono").
    avatarIcon: Optional[str] = None
    blockedModules: Optional[list[str]] = None
    allowedModulesOnly: Optional[list[str]] = None


class ResetPasswordBody(BaseModel):
    newPassword: str


class ImpersonateBody(BaseModel):
    targetUserId: str


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _row_to_user_dict(row) -> dict:
    """Nunca incluye password_hash -- este es el único shape que sale hacia el frontend."""
    return {
        "id": row["id"],
        "email": row["email"],
        "nombre": row["nombre"],
        "rol": row["rol"],
        "avatarColor": row["avatar_color"],
        "avatarIcon": row["avatar_icon"],
        "avatarImageUrl": row["avatar_image_url"],
        "blockedModules": json.loads(row["blocked_modules"] or "[]"),
        "allowedModulesOnly": json.loads(row["allowed_modules_only"] or "[]") or None,
    }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_session(con, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_TTL_DAYS)
    con.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        [token, user_id, now.isoformat(), expires.isoformat()],
    )
    con.commit()
    return token


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependencia FastAPI: extrae y valida el Bearer token, devuelve el usuario."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado. Falta el header Authorization.")
    token = authorization.removeprefix("Bearer ").strip()

    with get_users_connection() as con:
        session_row = con.execute(
            "SELECT * FROM sessions WHERE token = ?", [token]
        ).fetchone()
        if not session_row:
            raise HTTPException(status_code=401, detail="Sesión inválida. Inicia sesión nuevamente.")

        expires_at = datetime.fromisoformat(session_row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            con.execute("DELETE FROM sessions WHERE token = ?", [token])
            con.commit()
            raise HTTPException(status_code=401, detail="Sesión expirada. Inicia sesión nuevamente.")

        user_row = con.execute(
            "SELECT * FROM users WHERE id = ?", [session_row["user_id"]]
        ).fetchone()
        if not user_row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado.")

        return _row_to_user_dict(user_row)


def require_admin(user: dict) -> None:
    if user.get("rol") != "Administrador":
        raise HTTPException(status_code=403, detail="Requiere rol de Administrador.")


# ------------------------------------------------------------------
# Login / sesión
# ------------------------------------------------------------------
@router.post("/login")
def login(body: LoginBody):
    email = body.email.strip().lower()
    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", [email]).fetchone()
        if not row or not _verify_password(body.password, row["password_hash"]):
            # Mensaje genérico a propósito: no revelar si el email existe o no.
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")

        token = _create_session(con, row["id"])
        return {"token": token, "user": _row_to_user_dict(row)}


@router.post("/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        with get_users_connection() as con:
            con.execute("DELETE FROM sessions WHERE token = ?", [token])
            con.commit()
    return {"success": True}


@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    user = get_current_user(authorization)
    return user


# ------------------------------------------------------------------
# Gestión de usuarios (RBAC) -- todo requiere rol Administrador
# ------------------------------------------------------------------
@router.get("/users")
def list_users(authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)
    require_admin(current)
    with get_users_connection() as con:
        rows = con.execute("SELECT * FROM users ORDER BY created_at").fetchall()
        return [_row_to_user_dict(r) for r in rows]


@router.post("/users")
def create_user(body: CreateUserBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)
    require_admin(current)

    email = body.email.strip().lower()
    avatar_color = body.avatarColor or "#" + secrets.token_hex(3)

    with get_users_connection() as con:
        existente = con.execute("SELECT 1 FROM users WHERE email = ?", [email]).fetchone()
        if existente:
            raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo.")

        user_id = f"u-{uuid.uuid4().hex[:12]}"
        con.execute(
            """INSERT INTO users
               (id, email, nombre, rol, avatar_color, avatar_icon, password_hash, blocked_modules, allowed_modules_only, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                user_id, email, body.nombre.strip(), body.rol, avatar_color, body.avatarIcon,
                _hash_password(body.password),
                json.dumps(body.blockedModules or []),
                json.dumps(body.allowedModulesOnly or []),
                datetime.now(timezone.utc).isoformat(),
            ],
        )
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        return _row_to_user_dict(row)


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UpdateUserBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)

    # Self-service de avatar (07-ago-2026): cualquier usuario puede cambiar
    # SU PROPIO avatar (color/ícono) sin ser Administrador -- pero si viene
    # cualquier otro campo (nombre, rol, módulos), o si es sobre OTRO
    # usuario, sigue exigiendo Administrador como antes.
    es_uno_mismo = user_id == current["id"]
    solo_toca_avatar = body.nombre is None and body.rol is None and body.blockedModules is None and body.allowedModulesOnly is None
    if not (es_uno_mismo and solo_toca_avatar):
        require_admin(current)

    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        nombre = body.nombre if body.nombre is not None else row["nombre"]
        rol = body.rol if body.rol is not None else row["rol"]
        avatar_color = body.avatarColor if body.avatarColor is not None else row["avatar_color"]
        # avatarIcon: None = no lo mandaron (no tocar) -- "" = el usuario
        # eligió quitar el ícono y volver a solo iniciales (se guarda NULL).
        if body.avatarIcon is None:
            avatar_icon = row["avatar_icon"]
        elif body.avatarIcon == "":
            avatar_icon = None
        else:
            avatar_icon = body.avatarIcon
        # Elegir color o ícono del catálogo es una elección explícita --
        # si tenía una foto propia subida, esa elección la reemplaza (son
        # mutuamente excluyentes, ver AvatarBadge.tsx: foto > ícono > inicial).
        avatar_image_url = row["avatar_image_url"]
        if body.avatarColor is not None or body.avatarIcon is not None:
            avatar_image_url = None
        blocked = json.dumps(body.blockedModules) if body.blockedModules is not None else row["blocked_modules"]
        allowed = json.dumps(body.allowedModulesOnly) if body.allowedModulesOnly is not None else row["allowed_modules_only"]

        con.execute(
            """UPDATE users SET nombre=?, rol=?, avatar_color=?, avatar_icon=?, avatar_image_url=?, blocked_modules=?, allowed_modules_only=?
               WHERE id=?""",
            [nombre, rol, avatar_color, avatar_icon, avatar_image_url, blocked, allowed, user_id],
        )
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        return _row_to_user_dict(row)


@router.post("/users/{user_id}/avatar-image")
async def upload_avatar_image(user_id: str, file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    """Sube una foto propia de avatar. Cualquier usuario puede subir la
    SUYA; un Administrador puede subir la de cualquiera."""
    current = get_current_user(authorization)
    if user_id != current["id"]:
        require_admin(current)

    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes JPG, PNG o WEBP.")

    contenido = await file.read()
    if len(contenido) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="La imagen no puede pesar más de 2MB.")

    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        # Si el usuario ya tenía una foto con otra extensión, la borramos
        # para no dejar archivos huérfanos acumulándose en el disco.
        for ext_previa in ALLOWED_AVATAR_TYPES.values():
            ruta_previa = os.path.join(AVATAR_DIR, f"{user_id}.{ext_previa}")
            if os.path.exists(ruta_previa):
                os.remove(ruta_previa)

        ext = ALLOWED_AVATAR_TYPES[file.content_type]
        filename = f"{user_id}.{ext}"
        with open(os.path.join(AVATAR_DIR, filename), "wb") as f:
            f.write(contenido)

        # Cache-busting: si sube una foto nueva con el mismo nombre de
        # archivo, el navegador no debe seguir mostrando la vieja cacheada.
        version = int(datetime.now(timezone.utc).timestamp())
        avatar_image_url = f"/static/avatars/{filename}?v={version}"

        # Subir una foto propia reemplaza cualquier ícono del catálogo
        # elegido antes (mutuamente excluyentes).
        con.execute(
            "UPDATE users SET avatar_image_url = ?, avatar_icon = NULL WHERE id = ?",
            [avatar_image_url, user_id],
        )
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        return _row_to_user_dict(row)


@router.delete("/users/{user_id}/avatar-image")
def delete_avatar_image(user_id: str, authorization: Optional[str] = Header(None)):
    """Quita la foto propia y vuelve al catálogo de íconos / iniciales."""
    current = get_current_user(authorization)
    if user_id != current["id"]:
        require_admin(current)

    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        for ext_previa in ALLOWED_AVATAR_TYPES.values():
            ruta_previa = os.path.join(AVATAR_DIR, f"{user_id}.{ext_previa}")
            if os.path.exists(ruta_previa):
                os.remove(ruta_previa)

        con.execute("UPDATE users SET avatar_image_url = NULL WHERE id = ?", [user_id])
        con.commit()
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        return _row_to_user_dict(row)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, body: ResetPasswordBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)
    require_admin(current)

    if len(body.newPassword) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres.")

    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", [user_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        con.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            [_hash_password(body.newPassword), user_id],
        )
        # Cierra todas las sesiones activas de ese usuario -- si le cambiaron
        # la contraseña, no debería seguir con una sesión abierta indefinida.
        con.execute("DELETE FROM sessions WHERE user_id = ?", [user_id])
        con.commit()
    return {"success": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)
    require_admin(current)

    if user_id == current["id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario.")

    with get_users_connection() as con:
        con.execute("DELETE FROM sessions WHERE user_id = ?", [user_id])
        cur = con.execute("DELETE FROM users WHERE id = ?", [user_id])
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {"success": True}


# ------------------------------------------------------------------
# "Simular Sesión" del UserManagementModal -- un Admin puede pasar a ver
# la app como otro usuario, SIN necesitar su contraseña. Genera una sesión
# nueva para el usuario destino (no reutiliza el token del admin).
# ------------------------------------------------------------------
@router.post("/impersonate")
def impersonate(body: ImpersonateBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)
    require_admin(current)

    with get_users_connection() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", [body.targetUserId]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        token = _create_session(con, row["id"])
        return {"token": token, "user": _row_to_user_dict(row)}
