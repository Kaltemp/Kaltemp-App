"""
routers/categorias.py — Alerta de "SKU sin categoría" + asignación
manual desde la app.

Flujo:
  GET  /api/categorias/pendientes  -> SKUs que aparecen en `ventas` sin
                                       categoría resuelta y que TAMPOCO
                                       tienen una categoría manual
                                       asignada todavía (para la alerta)
  GET  /api/categorias/catalogo    -> nombres de categoría existentes
                                       (para el selector del modal)
  POST /api/categorias/asignar     -> guarda SKU -> categoría en
                                       categorias_manual

IMPORTANTE: asignar una categoría acá NO actualiza retroactivamente
`ventas.CATEGORIA` al instante -- esa tabla vive en kaltemp_matrix.duckdb,
que es de solo lectura para esta API (por diseño, ver db.py). La
categoría queda guardada y se aplica automáticamente en la PRÓXIMA
corrida de sync_ventas.py (que ya prioriza categorias_manual sobre
Bsale). El frontend debe dejar eso claro en la confirmación.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel

from db import get_connection
from categorias_db import get_categorias_connection, init_categorias_db
from routers.auth import get_current_user

router = APIRouter(prefix="/api/categorias", tags=["categorias"])


class AsignarCategoriaBody(BaseModel):
    sku: str
    categoria: str


@router.get("/pendientes")
def get_pendientes(authorization: Optional[str] = Header(None)):
    get_current_user(authorization)  # requiere sesión válida, cualquier rol

    init_categorias_db()

    # SKUs ya resueltos manualmente (aunque el próximo sync no haya corrido
    # todavía) -- no los mostramos de nuevo en la alerta.
    with get_categorias_connection() as con_cat:
        ya_asignados = {row["sku"] for row in con_cat.execute("SELECT sku FROM categorias_manual").fetchall()}

    with get_connection() as con:
        filas = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(PRODUCTO) AS producto,
                   SUM(BRUTO_TOTAL) AS venta_total, COUNT(*) AS lineas
            FROM ventas
            WHERE CATEGORIA IN ('Sin Categoría Mapeada', 'Sin Tipo')
              AND (ES_GLOSA_SERVICIO IS NULL OR ES_GLOSA_SERVICIO = FALSE)
            GROUP BY SKU_BSALE
            ORDER BY venta_total DESC
        """).fetchall()

    pendientes = [
        {
            "sku": f[0],
            "producto": f[1],
            "ventaTotal": round(f[2] or 0, 0),
            "lineas": f[3],
        }
        for f in filas
        if f[0] not in ya_asignados
    ]
    return {"total": len(pendientes), "items": pendientes}


@router.get("/catalogo")
def get_catalogo(authorization: Optional[str] = Header(None)):
    get_current_user(authorization)
    init_categorias_db()
    with get_categorias_connection() as con:
        filas = con.execute("SELECT nombre FROM categorias_catalogo ORDER BY nombre").fetchall()
    return [row["nombre"] for row in filas]


@router.post("/asignar")
def asignar_categoria(body: AsignarCategoriaBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)

    sku = body.sku.strip().upper()
    categoria = body.categoria.strip()
    if not sku or not categoria:
        raise HTTPException(status_code=400, detail="SKU y categoría son obligatorios.")

    init_categorias_db()
    with get_categorias_connection() as con:
        con.execute("""
            INSERT INTO categorias_manual (sku, categoria, asignado_por, actualizado_en)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                categoria = excluded.categoria,
                asignado_por = excluded.asignado_por,
                actualizado_en = excluded.actualizado_en
        """, [sku, categoria, current.get("email", ""), datetime.now(timezone.utc).isoformat()])
        con.execute("INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)", [categoria])
        con.commit()

    return {
        "success": True,
        "message": f"Categoría '{categoria}' guardada para {sku}. Se aplicará en la próxima sincronización de ventas.",
    }


# ============================================================
# ALERTA DE "CAMPAÑA SIN CATEGORÍA" (06-ago-2026) -- mismo patrón que
# la de SKUs de arriba, pero para campañas de Meta/Google. La usa
# /api/indicadores-d2c para repartir la inversión de marketing por
# categoría real de producto, en vez de adivinar por palabra clave.
# ============================================================

class AsignarCampanaCategoriaBody(BaseModel):
    campana: str
    plataforma: str
    categoria: str


@router.get("/campanas-pendientes")
def get_campanas_pendientes(authorization: Optional[str] = Header(None)):
    get_current_user(authorization)
    init_categorias_db()

    with get_categorias_connection() as con_cat:
        ya_asignadas = {row["campana"] for row in con_cat.execute("SELECT campana FROM campanas_categoria").fetchall()}

    pendientes = []
    with get_connection() as con:
        tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        for tabla, plataforma in (("mkt_inversion_meta", "Meta"), ("mkt_inversion_google", "Google")):
            if tabla not in tables:
                continue
            df = con.execute(f"SELECT * FROM {tabla}").df()
            if df.empty:
                continue
            col_campana = next((c for c in df.columns if "campa" in c.lower()), None)
            col_gasto = next((c for c in df.columns if "gasto" in c.lower()), None)
            col_marca = next((c for c in df.columns if c.lower() == "marca"), None)
            if not (col_campana and col_gasto):
                continue

            import pandas as pd
            df["_gasto"] = pd.to_numeric(df[col_gasto], errors="coerce").fillna(0.0)
            agg = df.groupby(col_campana).agg(
                gasto=("_gasto", "sum"),
                marca=(col_marca, "first") if col_marca else (col_campana, "first"),
            ).reset_index()

            for _, fila in agg.iterrows():
                nombre = str(fila[col_campana]).strip()
                if not nombre or nombre in ya_asignadas:
                    continue
                pendientes.append({
                    "campana": nombre,
                    "plataforma": plataforma,
                    "marca": str(fila["marca"]) if col_marca else "Kaltemp",
                    "gastoTotal": round(float(fila["gasto"]), 0),
                })

    pendientes.sort(key=lambda p: p["gastoTotal"], reverse=True)
    return {"total": len(pendientes), "items": pendientes}


@router.post("/campanas-asignar")
def asignar_campana_categoria(body: AsignarCampanaCategoriaBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)

    campana = body.campana.strip()
    plataforma = body.plataforma.strip()
    categoria = body.categoria.strip()
    if not campana or not categoria:
        raise HTTPException(status_code=400, detail="Campaña y categoría son obligatorias.")

    init_categorias_db()
    with get_categorias_connection() as con:
        con.execute("""
            INSERT INTO campanas_categoria (campana, plataforma, categoria, asignado_por, actualizado_en)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(campana) DO UPDATE SET
                plataforma = excluded.plataforma,
                categoria = excluded.categoria,
                asignado_por = excluded.asignado_por,
                actualizado_en = excluded.actualizado_en
        """, [campana, plataforma, categoria, current.get("email", ""), datetime.now(timezone.utc).isoformat()])
        # Soporta 1 o varias categorías separadas por coma (ej. una
        # campaña de liquidación que promociona varias categorías a la
        # vez) -- cada una se agrega individualmente al catálogo/selector,
        # no la cadena completa (07-ago-2026).
        for cat_individual in [c.strip() for c in categoria.split(",") if c.strip()]:
            con.execute("INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)", [cat_individual])
        con.commit()

    return {
        "success": True,
        "message": f"Categoría(s) '{categoria}' guardada(s) para la campaña '{campana}'. Se reflejará de inmediato en Indicadores D2C.",
    }