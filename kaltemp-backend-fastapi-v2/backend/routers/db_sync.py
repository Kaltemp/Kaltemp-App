"""
db_sync.py — Endpoints para el botón "DuckDB / Drive" del Header:
  GET  /api/db/status            -> tamaño, última modificación, tablas + conteo
  POST /api/db/upload            -> subir kaltemp_matrix.duckdb directo desde el navegador
  GET  /api/db/service-account   -> estado de la Cuenta de Servicio GCP configurada
  POST /api/db/service-account   -> guardar la clave JSON de la Cuenta de Servicio
  POST /api/db/sync-drive        -> descargar kaltemp_matrix.duckdb desde Google Drive

Es un port directo (misma lógica, mismo shape de respuesta) del server.ts
de Express que ya tenías funcionando en el proyecto anterior -- no es una
reimplementación desde cero, para no arriesgar comportamiento distinto.

IMPORTANTE - Concurrencia: este router escribe directo sobre el archivo en
DUCKDB_PATH. Como el resto del backend (`db.py`) abre y cierra una conexión
read_only por request (nunca mantiene una conexión abierta entre llamadas),
sobrescribir el archivo acá es seguro -- no hay riesgo de corromper una
conexión activa, mismo principio que ya usan los scripts de sync por cron.
"""
import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import APIRouter, UploadFile, File, Body
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from db import get_connection, DB_PATH

router = APIRouter(prefix="/api/db", tags=["db-sync"])

_BACKEND_DIR = Path(__file__).resolve().parent
_SERVICE_ACCOUNT_PATH = _BACKEND_DIR / "data" / "service_account.json"
_SERVICE_ACCOUNT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _db_path() -> Path:
    return Path(DB_PATH)


@router.get("/status")
def get_db_status():
    db_path = _db_path()
    if not db_path.exists():
        return {
            "exists": False,
            "message": "No hay base de datos todavía. Sube kaltemp_matrix.duckdb o sincroniza desde Google Drive.",
            "tables": [],
            "lastUpdated": None,
        }

    stats = db_path.stat()
    tabla_info = []
    error_tablas = None
    try:
        with get_connection() as con:
            tablas = con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
            for (nombre,) in tablas:
                try:
                    count = con.execute(f'SELECT COUNT(*) FROM "{nombre}"').fetchone()[0]
                except Exception:
                    count = 0
                tabla_info.append({"name": nombre, "count": count})
    except Exception as e:
        error_tablas = str(e)

    resultado = {
        "exists": True,
        "sizeBytes": stats.st_size,
        "sizeMb": f"{stats.st_size / (1024 * 1024):.2f}",
        "lastUpdated": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat(),
        "tables": tabla_info,
    }
    if error_tablas:
        resultado["error"] = error_tablas
    return resultado


@router.post("/upload")
async def upload_db(database: UploadFile = File(...)):
    try:
        db_path = _db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        contenido = await database.read()
        with open(db_path, "wb") as f:
            f.write(contenido)

        stats = db_path.stat()
        return {
            "success": True,
            "message": "¡Base de datos kaltemp_matrix.duckdb subida y guardada con éxito!",
            "sizeMb": f"{stats.st_size / (1024 * 1024):.2f}",
            "lastUpdated": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e) or "Error al subir el archivo"}


@router.get("/service-account")
def get_service_account_status():
    if not _SERVICE_ACCOUNT_PATH.exists():
        return {"configured": False}
    try:
        data = json.loads(_SERVICE_ACCOUNT_PATH.read_text(encoding="utf-8"))
        return {
            "configured": True,
            "clientEmail": data.get("client_email", "Cuenta de Servicio configurada"),
            "projectId": data.get("project_id"),
        }
    except Exception as e:
        return {"configured": False, "error": str(e)}


@router.post("/service-account")
def save_service_account(payload: dict = Body(...)):
    json_key = payload.get("jsonKey")
    try:
        parsed = json_key if isinstance(json_key, dict) else json.loads(json_key)
    except Exception:
        return {"success": False, "error": "Formato JSON inválido. Revisa el contenido de la clave de Cuenta de Servicio."}

    if not parsed.get("client_email") or not parsed.get("private_key"):
        return {
            "success": False,
            "error": "El archivo JSON ingresado no es una clave válida de Cuenta de Servicio de Google "
                     "(falta client_email o private_key).",
        }

    _SERVICE_ACCOUNT_PATH.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    return {
        "success": True,
        "clientEmail": parsed["client_email"],
        "projectId": parsed.get("project_id"),
        "message": f"Cuenta de Servicio {parsed['client_email']} guardada con éxito.",
    }


def _extraer_file_id(drive_url: str | None, file_id: str | None) -> str | None:
    if file_id:
        return file_id
    if not drive_url:
        return None
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", drive_url)
    if m:
        return m.group(1)
    m = re.search(r"id=([a-zA-Z0-9_-]+)", drive_url)
    return m.group(1) if m else None


@router.post("/sync-drive")
def sync_from_drive(payload: dict = Body(...)):
    file_id = _extraer_file_id(payload.get("driveUrl"), payload.get("fileId"))
    if not file_id:
        return {"success": False, "error": "Enlace o ID de Google Drive inválido."}

    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Camino 1: Cuenta de Servicio configurada (recomendado, sin límites de Workspace) ---
    if _SERVICE_ACCOUNT_PATH.exists():
        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(_SERVICE_ACCOUNT_PATH),
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
            drive = build("drive", "v3", credentials=credentials)
            request = drive.files().get_media(fileId=file_id)

            buffer = io.FileIO(str(db_path), "wb")
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            buffer.close()

            stats = db_path.stat()
            client_email = json.loads(_SERVICE_ACCOUNT_PATH.read_text(encoding="utf-8")).get("client_email")
            return {
                "success": True,
                "message": f"¡Base de datos sincronizada exitosamente con la Cuenta de Servicio ({client_email})!",
                "fileId": file_id,
                "sizeMb": f"{stats.st_size / (1024 * 1024):.2f}",
                "lastUpdated": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            client_email = None
            try:
                client_email = json.loads(_SERVICE_ACCOUNT_PATH.read_text(encoding="utf-8")).get("client_email")
            except Exception:
                pass
            return {
                "success": False,
                "error": (
                    f"Error al descargar desde Google Drive API con la cuenta {client_email}: {e}. "
                    "Asegúrate de haber compartido el archivo con este correo en Google Drive."
                ),
            }

    # --- Camino 2: descarga pública sin autenticación (fallback) ---
    try:
        url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(db_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Verifica que no haya descargado una página HTML de error/login de Google
        with open(db_path, "rb") as f:
            muestra = f.read(200).decode("utf-8", errors="ignore").lower()
        if "<!doctype html" in muestra or "<html" in muestra:
            return {
                "success": False,
                "error": (
                    "Google Drive requiere autenticación. Para solucionar esto en tu cuenta empresa:\n"
                    "1) Configura la clave JSON de tu Cuenta de Servicio en la sección inferior,\n"
                    "2) O usa la Opción 2 (Carga Directa) para subir el archivo .duckdb manualmente."
                ),
            }

        stats = db_path.stat()
        return {
            "success": True,
            "message": "¡Base de datos sincronizada desde Google Drive con éxito!",
            "fileId": file_id,
            "sizeMb": f"{stats.st_size / (1024 * 1024):.2f}",
            "lastUpdated": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e) or "Falló la sincronización con Google Drive"}
