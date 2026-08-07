import os
import io
import duckdb
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional

router = APIRouter(prefix="/api", tags=["export"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)


@router.get("/export/ventas-excel")
def export_ventas_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None)
):
    """
    06-ago-2026: reescrito -- el archivo original apuntaba a columnas
    que no existen en la tabla real `ventas` (FECHA_DOCUMENTO, SKU,
    RUT_CLIENTE, PRECIO_NETO_UNITARIO, MARGEN, COMUNA, EMAIL, etc.).
    Con filtro de fecha la consulta fallaba directo (columna
    inexistente); sin filtro, generaba el Excel igual pero con casi
    todas las columnas vacías/en cero sin avisar. Se usa el esquema
    real (ver sync_ventas.py): DOCUMENTO, PRODUCTO, SKU_BSALE,
    CANTIDAD, NETO_TOTAL, BRUTO_TOTAL, COSTO_TOTAL, CONTRIBUCION,
    CANAL, VENDEDOR, CLIENTE, CATEGORIA, FECHA_OBJ, ORIGEN,
    TIPO_DOCUMENTO, NUMERO_DOCUMENTO, SUCURSAL, ES_GLOSA_SERVICIO.
    Bsale no trae datos de contacto del cliente (RUT/comuna/ciudad/
    email) a este nivel -- esas columnas no se pueden incluir porque
    el dato simplemente no existe en la fuente.
    """
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)

        query = "SELECT * FROM ventas WHERE 1=1"
        params = []

        if start_date:
            query += " AND CAST(FECHA_OBJ AS DATE) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND CAST(FECHA_OBJ AS DATE) <= ?"
            params.append(end_date)
        if canal and canal != "Todos":
            query += " AND CANAL = ?"
            params.append(canal)
        if categoria and categoria != "Todas":
            query += " AND CATEGORIA = ?"
            params.append(categoria)

        query += " ORDER BY FECHA_OBJ DESC"

        df = conn.execute(query, params).df()
        conn.close()

        # Columnas reales de `ventas` -- ver docstring arriba.
        df_export = pd.DataFrame()

        df_export["Documento"] = df.get("DOCUMENTO", "")
        df_export["Tipo de Documento"] = df.get("TIPO_DOCUMENTO", "")
        df_export["N° Documento"] = df.get("NUMERO_DOCUMENTO", "")
        df_export["Fecha"] = pd.to_datetime(df.get("FECHA_OBJ"), errors="coerce").dt.strftime("%d/%m/%Y") if "FECHA_OBJ" in df.columns else ""
        df_export["Canal"] = df.get("CANAL", "")
        df_export["Origen"] = df.get("ORIGEN", "")
        df_export["Sucursal"] = df.get("SUCURSAL", "")
        df_export["Vendedor"] = df.get("VENDEDOR", "")
        df_export["Cliente"] = df.get("CLIENTE", "")
        df_export["Categoría"] = df.get("CATEGORIA", "")
        df_export["SKU"] = df.get("SKU_BSALE", "")
        df_export["Producto"] = df.get("PRODUCTO", "")
        df_export["Cantidad"] = df.get("CANTIDAD", 0)
        df_export["Neto Total"] = df.get("NETO_TOTAL", 0)
        df_export["Bruto Total"] = df.get("BRUTO_TOTAL", 0)
        df_export["Costo Total"] = df.get("COSTO_TOTAL", 0)
        df_export["Contribución"] = df.get("CONTRIBUCION", 0)
        df_export["Es Glosa Servicio (sin margen)"] = df.get("ES_GLOSA_SERVICIO", False)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Ventas Consolidadas")

        output.seek(0)

        filename = f"Ventas_Consolidadas_Kaltemp_{start_date or 'inicio'}_a_{end_date or 'hoy'}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        return {"error": f"Error al generar Excel: {str(e)}"}
