# ============================================================
# ARCHIVO: peso_productos.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\peso_productos.py
# ============================================================
"""
routers/peso_productos.py — Alerta de "SKU vendido sin peso/medidas" +
asignación manual desde la app. Mismo patrón que routers/categorias.py.

Flujo:
  GET  /api/peso-productos/pendientes -> SKUs que aparecen en `ventas`
                                          sin peso/medidas asignado y
                                          que NO están marcados como
                                          descontinuados
  POST /api/peso-productos/asignar    -> guarda peso/medidas (o marca
                                          descontinuado) para un SKU

Un SKU marcado 'descontinuado' se guarda con peso/medidas en NULL --
sale de la lista de pendientes igual que uno con datos reales, porque
ya no importa para el cálculo de fletes (no se va a seguir vendiendo).
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel

from db import get_connection
from categorias_db import get_categorias_connection, init_categorias_db
from routers.auth import get_current_user

router = APIRouter(prefix="/api/peso-productos", tags=["peso-productos"])


class AsignarPesoBody(BaseModel):
    sku: str
    pesoKg: Optional[float] = None
    largoCm: Optional[float] = None
    anchoCm: Optional[float] = None
    altoCm: Optional[float] = None
    descontinuado: bool = False


@router.get("/pendientes")
def get_pendientes(authorization: Optional[str] = Header(None)):
    get_current_user(authorization)  # requiere sesión válida, cualquier rol

    init_categorias_db()

    # SKUs ya resueltos (con peso real O marcados descontinuados) --
    # no se muestran de nuevo en la alerta.
    with get_categorias_connection() as con_p:
        ya_resueltos = {row["sku"] for row in con_p.execute("SELECT sku FROM pesos_manual").fetchall()}

    with get_connection() as con:
        filas = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(PRODUCTO) AS producto,
                   SUM(BRUTO_TOTAL) AS venta_total, COUNT(*) AS lineas
            FROM ventas
            WHERE (ES_GLOSA_SERVICIO IS NULL OR ES_GLOSA_SERVICIO = FALSE)
              AND SKU_BSALE IS NOT NULL AND SKU_BSALE != ''
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
        if f[0] not in ya_resueltos
    ]
    return {"total": len(pendientes), "items": pendientes}


@router.post("/asignar")
def asignar_peso(body: AsignarPesoBody, authorization: Optional[str] = Header(None)):
    current = get_current_user(authorization)

    sku = body.sku.strip().upper()
    if not sku:
        raise HTTPException(status_code=400, detail="SKU es obligatorio.")

    if not body.descontinuado:
        if not body.pesoKg or body.pesoKg <= 0:
            raise HTTPException(status_code=400, detail="Peso (kg) es obligatorio y debe ser mayor a 0 (o marca el producto como descontinuado).")

    init_categorias_db()
    with get_categorias_connection() as con:
        con.execute("""
            INSERT INTO pesos_manual (sku, peso_kg, largo_cm, ancho_cm, alto_cm, descontinuado, asignado_por, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                peso_kg = excluded.peso_kg,
                largo_cm = excluded.largo_cm,
                ancho_cm = excluded.ancho_cm,
                alto_cm = excluded.alto_cm,
                descontinuado = excluded.descontinuado,
                asignado_por = excluded.asignado_por,
                actualizado_en = excluded.actualizado_en
        """, [
            sku,
            None if body.descontinuado else body.pesoKg,
            None if body.descontinuado else body.largoCm,
            None if body.descontinuado else body.anchoCm,
            None if body.descontinuado else body.altoCm,
            1 if body.descontinuado else 0,
            current.get("email", ""),
            datetime.now(timezone.utc).isoformat(),
        ])
        con.commit()

    mensaje = f"'{sku}' marcado como descontinuado." if body.descontinuado else f"Peso/medidas guardados para '{sku}'."
    return {"success": True, "message": mensaje}
