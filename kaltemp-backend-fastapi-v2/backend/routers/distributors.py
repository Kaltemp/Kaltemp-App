import duckdb
from fastapi import APIRouter, Query
from typing import Optional
import os
import pandas as pd

router = APIRouter(prefix="/api", tags=["distributors"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)

def get_db_connection():
    return duckdb.connect(DUCKDB_PATH, read_only=True)

def parse_date_safe(val, default_val):
    if not val or str(val).strip().lower() in ("null", "undefined", "none", ""):
        return default_val
    val_str = str(val).strip()
    try:
        # Formato ISO (YYYY-MM-DD) es inequívoco -- nunca debe pasar por
        # dayfirst, que puede confundir mes/día (bug confirmado 05-ago-2026:
        # "2026-08-02" se parseaba como 8 de febrero en vez de 2 de agosto).
        dt = pd.to_datetime(val_str, format="%Y-%m-%d", errors="raise")
        return dt.date()
    except (ValueError, TypeError):
        pass
    try:
        dt = pd.to_datetime(val_str, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass
    return default_val

@router.get("/distributors")
@router.get("/distribuidores")
def get_distributors(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """
    Devuelve los Indicadores B2B de DISTRIBUIDORES exclusivamente.
    """
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            
            def response_vacia():
                return {
                    "totalVentas": 0.0,
                    "ventaYoy": 0.0,
                    "variacionYoy": 0.0,
                    "totalClientes": 0,
                    "ticketPromedio": 0.0,
                    "rankingClientes": [],
                    "distribucionCategoria": [],
                    "tendenciaMensual": []
                }

            if "ventas" not in tables:
                return response_vacia()

            # Filtrar EXCLUSIVAMENTE el canal y vendedores de DISTRIBUIDORES
            query = """
                SELECT 
                    DOCUMENTO, PRODUCTO, SKU_BSALE, CANTIDAD,
                    NETO_TOTAL, BRUTO_TOTAL, CONTRIBUCION, CANAL,
                    VENDEDOR, CLIENTE, CATEGORIA, FECHA_OBJ
                FROM ventas
                WHERE UPPER(CANAL) LIKE '%DISTRIBUIDOR%'
                   OR UPPER(VENDEDOR) IN ('DANIELA VALLADARES', 'CATALINA POBLETE')
            """
            df_dist = conn.execute(query).df()
        finally:
            conn.close()

        if df_dist.empty:
            return response_vacia()

        df_dist["FECHA_OBJ"] = pd.to_datetime(df_dist["FECHA_OBJ"], errors="coerce")
        df_dist = df_dist.dropna(subset=["FECHA_OBJ"])
        df_dist["FECHA_CORTE"] = df_dist["FECHA_OBJ"].dt.date
        df_dist["AÑO"] = df_dist["FECHA_OBJ"].dt.year
        df_dist["MES_NUM"] = df_dist["FECHA_OBJ"].dt.month

        min_date = df_dist["FECHA_CORTE"].min()
        max_date = df_dist["FECHA_CORTE"].max()

        f_in = parse_date_safe(fecha_inicio, min_date)
        f_fi = parse_date_safe(fecha_fin, max_date)

        df_cy = df_dist[(df_dist["FECHA_CORTE"] >= f_in) & (df_dist["FECHA_CORTE"] <= f_fi)]

        try:
            f_in_yoy = f_in.replace(year=f_in.year - 1)
            f_fi_yoy = f_fi.replace(year=f_fi.year - 1)
            df_yoy = df_dist[(df_dist["FECHA_CORTE"] >= f_in_yoy) & (df_dist["FECHA_CORTE"] <= f_fi_yoy)]
        except Exception:
            df_yoy = pd.DataFrame()

        total_ventas = float(df_cy["BRUTO_TOTAL"].sum()) if not df_cy.empty else 0.0
        venta_yoy = float(df_yoy["BRUTO_TOTAL"].sum()) if not df_yoy.empty else 0.0
        var_yoy = round(((total_ventas - venta_yoy) / venta_yoy * 100), 1) if venta_yoy > 0 else (100.0 if total_ventas > 0 else 0.0)

        total_clientes = int(df_cy["CLIENTE"].nunique()) if not df_cy.empty else 0
        total_txs = int(df_cy["DOCUMENTO"].nunique()) if not df_cy.empty else 0
        tkp = float(total_ventas / total_txs) if total_txs > 0 else 0.0

        ranking_clientes = []
        if not df_cy.empty:
            gp_cli_cy = df_cy.groupby("CLIENTE")["BRUTO_TOTAL"].sum().reset_index()
            gp_cli_yoy = df_yoy.groupby("CLIENTE")["BRUTO_TOTAL"].sum().reset_index() if not df_yoy.empty else pd.DataFrame(columns=["CLIENTE", "BRUTO_TOTAL"])

            m_cli = pd.merge(gp_cli_cy, gp_cli_yoy, on="CLIENTE", how="left", suffixes=("_CY", "_YOY")).fillna(0)
            m_cli = m_cli.sort_values(by="BRUTO_TOTAL_CY", ascending=False).head(15)

            # Categoría dominante por cliente (la de mayor venta) -- antes no
            # existía este dato y el frontend rellenaba "Distribuidores" fijo
            # para todos, por lo que el filtro cruzado por categoría nunca
            # encontraba coincidencias reales.
            categoria_por_cliente = {}
            if "CATEGORIA" in df_cy.columns:
                gp_cli_cat = df_cy.groupby(["CLIENTE", "CATEGORIA"])["BRUTO_TOTAL"].sum().reset_index()
                idx_top_cat = gp_cli_cat.groupby("CLIENTE")["BRUTO_TOTAL"].idxmax()
                for _, row in gp_cli_cat.loc[idx_top_cat].iterrows():
                    categoria_por_cliente[row["CLIENTE"]] = str(row["CATEGORIA"]).strip()

            for _, r in m_cli.iterrows():
                cli_nom = str(r["CLIENTE"]).strip().title()
                v_cy = float(r["BRUTO_TOTAL_CY"])
                v_yy = float(r["BRUTO_TOTAL_YOY"])
                v_var = round(((v_cy - v_yy) / v_yy * 100), 1) if v_yy > 0 else (100.0 if v_cy > 0 else 0.0)

                ranking_clientes.append({
                    "cliente": cli_nom,
                    "name": cli_nom,
                    "venta": v_cy,
                    "ventaYoy": v_yy,
                    "variacion": v_var,
                    "categoria": categoria_por_cliente.get(r["CLIENTE"], "Sin Categoría Mapeada")
                })

        distribucion_categoria = []
        if not df_cy.empty and "CATEGORIA" in df_cy.columns:
            cat_counts = df_cy.groupby("CATEGORIA")["BRUTO_TOTAL"].sum().reset_index()
            cat_counts = cat_counts.sort_values(by="BRUTO_TOTAL", ascending=False)
            for _, r in cat_counts.iterrows():
                c_nom = str(r["CATEGORIA"]).strip()
                if c_nom and c_nom != "nan":
                    distribucion_categoria.append({
                        "categoria": c_nom,
                        "name": c_nom,
                        "venta": float(r["BRUTO_TOTAL"]),
                        "value": float(r["BRUTO_TOTAL"])
                    })

        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        m_cy = df_cy.groupby("MES_NUM")["BRUTO_TOTAL"].sum().to_dict() if not df_cy.empty else {}
        m_yy = df_yoy.groupby("MES_NUM")["BRUTO_TOTAL"].sum().to_dict() if not df_yoy.empty else {}

        tendencia_mensual = []
        for idx in range(1, 13):
            tendencia_mensual.append({
                "mes": meses_nombres[idx - 1],
                "venta": float(m_cy.get(idx, 0.0)),
                "ventaYoy": float(m_yy.get(idx, 0.0))
            })

        return {
            "totalVentas": total_ventas,
            "ventaYoy": venta_yoy,
            "variacionYoy": var_yoy,
            "totalClientes": total_clientes,
            "ticketPromedio": tkp,
            "rankingClientes": ranking_clientes,
            "distribucionCategoria": distribucion_categoria,
            "tendenciaMensual": tendencia_mensual
        }
    except Exception as e:
        print(f"❌ ERROR en /api/distributors: {e}")
        return response_vacia()