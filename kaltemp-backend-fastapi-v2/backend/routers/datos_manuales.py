# ============================================================
# Archivo: datos_manuales.py
# Ruta:    backend/routers/datos_manuales.py
# ============================================================

"""
routers/datos_manuales.py — CRUD de datos cargados manualmente desde la
app (metas históricas anuales, presupuesto de marketing, etc.). Ver
datos_manuales_db.py para el diseño de la tabla y los tipos válidos.

Solo usa GET y POST (igual que categorias.py) -- el CORSMiddleware en
main.py solo permite esos dos métodos.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datos_manuales_db import get_datos_manuales_connection, TIPOS_VALIDOS, MARCAS_VALIDAS

router = APIRouter(prefix="/api/datos-manuales", tags=["datos_manuales"])


class DatoManualIn(BaseModel):
    periodo: str
    tipo: str
    marca: str = "Kaltemp"
    monto: float
    notas: str | None = None
    actualizado_por: str | None = None


class DatoManualEliminar(BaseModel):
    periodo: str
    tipo: str
    marca: str = "Kaltemp"


@router.get("/tipos")
def get_tipos_validos():
    """Catálogo de tipos de dato manual soportados, para poblar el selector del modal."""
    etiquetas = {
        "meta_venta_anual": "Meta de Venta (anual)",
        "meta_contribucion_anual": "Meta de Contribución (anual)",
        "venta_real_manual": "Venta Real histórica (manual)",
        "contribucion_real_manual": "Contribución Real histórica (manual)",
        "presupuesto_marketing": "Presupuesto de Marketing",
    }
    return [{"tipo": t, "etiqueta": etiquetas.get(t, t)} for t in TIPOS_VALIDOS]


@router.get("/marcas")
def get_marcas_validas():
    """Catálogo de marcas soportadas, para poblar el selector del modal."""
    return list(MARCAS_VALIDAS)


@router.get("/metas")
def get_datos_manuales():
    with get_datos_manuales_connection() as con:
        filas = con.execute("""
            SELECT periodo, tipo, marca, monto, notas, actualizado_por, actualizado_en
            FROM datos_manuales
            ORDER BY periodo DESC, tipo, marca
        """).fetchall()
        return [dict(f) for f in filas]


@router.post("/metas")
def upsert_dato_manual(dato: DatoManualIn):
    if dato.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Debe ser uno de: {', '.join(TIPOS_VALIDOS)}")
    if dato.marca not in MARCAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Marca inválida. Debe ser una de: {', '.join(MARCAS_VALIDAS)}")
    if not dato.periodo.strip():
        raise HTTPException(status_code=400, detail="El período no puede estar vacío.")

    ahora = datetime.now(timezone.utc).isoformat()
    with get_datos_manuales_connection() as con:
        con.execute("""
            INSERT INTO datos_manuales (periodo, tipo, marca, monto, notas, actualizado_por, actualizado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(periodo, tipo, marca) DO UPDATE SET
                monto = excluded.monto,
                notas = excluded.notas,
                actualizado_por = excluded.actualizado_por,
                actualizado_en = excluded.actualizado_en
        """, [dato.periodo.strip(), dato.tipo, dato.marca, dato.monto, dato.notas, dato.actualizado_por, ahora])
        con.commit()
    return {"success": True, "message": "Dato guardado correctamente."}


@router.post("/metas/eliminar")
def eliminar_dato_manual(dato: DatoManualEliminar):
    with get_datos_manuales_connection() as con:
        con.execute(
            "DELETE FROM datos_manuales WHERE periodo = ? AND tipo = ? AND marca = ?",
            [dato.periodo.strip(), dato.tipo, dato.marca],
        )
        con.commit()
    return {"success": True, "message": "Dato eliminado."}