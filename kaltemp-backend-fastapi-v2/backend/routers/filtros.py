"""
Módulo Filtros Globales — expone los valores REALES que existen hoy en
`ventas` para poblar los selectores de Categoría SKU y Vendedor, y en
`stock_bsale` para el selector de Bodega. No se usa una lista fija en el
frontend: viene directo de lo que Bsale ya sincronizó, así nunca se
desactualiza ni requiere mapeos manuales.

Canal de Venta NO se incluye acá a propósito: esa lista se define en el
código matriz (ALL_CHANNELS en FilterContext.tsx), no en Bsale.
"""
from fastapi import APIRouter
from db import get_connection

router = APIRouter(prefix="/api", tags=["filtros"])


def _tabla_existe(con, nombre: str) -> bool:
    return con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [nombre]
    ).fetchone() is not None


@router.get("/filtros")
def get_filtros():
    with get_connection() as con:
        categorias = [
            r[0] for r in con.execute("""
                SELECT DISTINCT CATEGORIA FROM ventas
                WHERE CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
                ORDER BY CATEGORIA
            """).fetchall()
        ]
        vendedores = [
            r[0] for r in con.execute("""
                SELECT DISTINCT VENDEDOR FROM ventas
                WHERE VENDEDOR IS NOT NULL AND TRIM(VENDEDOR) != ''
                ORDER BY VENDEDOR
            """).fetchall()
        ]
        bodegas = []
        if _tabla_existe(con, "stock_bsale"):
            bodegas = [
                r[0] for r in con.execute("""
                    SELECT DISTINCT BODEGA FROM stock_bsale
                    WHERE BODEGA IS NOT NULL AND TRIM(BODEGA) != ''
                    ORDER BY BODEGA
                """).fetchall()
            ]
    return {"categorias": categorias, "vendedores": vendedores, "bodegas": bodegas}
