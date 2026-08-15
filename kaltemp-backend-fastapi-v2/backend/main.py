# ============================================================
# ARCHIVO: main.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\main.py
# ============================================================

"""
Backend Kaltemp Dashboard — API para el frontend React (AI Studio export).

Corre como servicio independiente dentro de la misma VM (e2-small),
sin puertos públicos: solo accesible vía Tailscale (o localhost si el
frontend se sirve desde el mismo host con Nginx como reverse proxy).
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import channels, sku, tendencia, abandoned_carts, marketing, leads, cumplimiento
from routers import fulfillment, distributors, real_estate, temperatura_ventas, sync_dependent, filtros, db_sync, sync_admin
from routers import auth, categorias, resumen, peso_productos, datos_manuales
from auth_db import init_users_db
from categorias_db import init_categorias_db

app = FastAPI(title="Kaltemp Dashboard API", version="0.1.0")

init_users_db()
init_categorias_db()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(channels.router)
app.include_router(sku.router)
app.include_router(tendencia.router)
app.include_router(abandoned_carts.router)
app.include_router(marketing.router)
app.include_router(leads.router)
app.include_router(cumplimiento.router)
app.include_router(fulfillment.router)
app.include_router(distributors.router)
app.include_router(real_estate.router)
app.include_router(temperatura_ventas.router)
app.include_router(sync_dependent.router)
app.include_router(filtros.router)
app.include_router(db_sync.router)
app.include_router(sync_admin.router)
app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(resumen.router)
app.include_router(peso_productos.router)
app.include_router(datos_manuales.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}