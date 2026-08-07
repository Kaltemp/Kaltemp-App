import duckdb
from fastapi import APIRouter, Query
from typing import Optional, Union, List
import os
import pandas as pd

router = APIRouter(prefix="/api", tags=["abandoned_carts"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)

def get_db_connection():
    return duckdb.connect(DUCKDB_PATH, read_only=True)

def parse_date_safe(val, default_val):
    if not val:
        return default_val
    if isinstance(val, (list, tuple)):
        val = val[0] if len(val) > 0 else None
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

def es_filtro_todos(val) -> bool:
    if val is None:
        return True
    if isinstance(val, (list, tuple)):
        if len(val) == 0:
            return True
        val = val[0]
    s = str(val).strip().upper()
    if not s or s in ("ALL", "NULL", "NONE", "UNDEFINED", "TODOS", "TODAS") or "TODO" in s or "TODAS" in s or "SELECCIONAR" in s:
        return True
    return False

def inferir_categoria(cat_orig: str, producto: str, sku: str) -> str:
    c_str = str(cat_orig or "").strip()
    if c_str and c_str not in ("Sin Tipo", "Sin Categoría Mapeada", "nan", "None", ""):
        return c_str

    p_upper = str(producto or "").strip().upper()
    s_upper = str(sku or "").strip().upper()

    if any(k in p_upper or k in s_upper for k in ("ESTUFA", "CALEFACTOR", "APOLO", "WALLY", "IR04", "CALEFACCION", "PANEL", "MISTRAL", "CLIMA", "CALOR")):
        return "Calefacción"
    elif any(k in p_upper or k in s_upper for k in ("AIRE", "ACONDICIONADO", "SPLIT", "ENFRIADOR", "VENTILADOR")):
        return "Aire Acondicionado"
    elif any(k in p_upper or k in s_upper for k in ("AGUA", "TERMO", "CALEFONT", "BOMBA DE CALOR", "SANITA")):
        return "BC Agua Sanitaria"
    elif any(k in p_upper or k in s_upper for k in ("GENERADOR", "ELECTROGENO", "BATERIA")):
        return "Generadores"
    elif any(k in p_upper or k in s_upper for k in ("FULFILLMENT", "FALABELLA", "MERCADOLIBRE")):
        return "Marketplace Fulfillment"

    return "Otros / Accesorios"

@router.get("/abandoned-checkouts")
@router.get("/abandoned-carts")
def get_abandoned_carts(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    vendedor: Optional[str] = Query(None),
    bodega: Optional[str] = Query(None)
):
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            
            def response_vacia():
                return {
                    "totalCarritos": 0, "carritosAbandonados": 0, "abandonedCount": 0, "total": 0,
                    "oportunidadPerdida": 0.0, "lostOpportunity": 0.0,
                    "carritosRecuperados": 0, "recoveredCount": 0, "recuperados": 0,
                    "tasaRecuperacion": 0.0, "recoveryRate": 0.0,
                    "distribucionCategoria": [], "distribucion_categoria": [], "categoryDistribution": [],
                    "topProductos": [], "top_productos": [], "topProducts": [],
                    "dailyTrend": [], "daily_trend": [], "comportamientoDiario": [], "comportamiento_diario": [], "trend": []
                }

            if "abandoned_checkouts" not in tables:
                return response_vacia()

            df_ac = conn.execute("SELECT * FROM abandoned_checkouts").df()
            
            df_m = pd.DataFrame()
            if "sku_maestro" in tables:
                df_m = conn.execute("SELECT SKU, CATEGORIA FROM sku_maestro").df()
                
            df_v = pd.DataFrame()
            if "ventas" in tables:
                df_v = conn.execute("SELECT SKU_BSALE, CATEGORIA FROM ventas WHERE CATEGORIA IS NOT NULL AND CATEGORIA NOT IN ('Sin Categoría Mapeada', 'Sin Tipo')").df()

            df_temp = pd.DataFrame()
            if "temperaturas" in tables:
                df_temp = conn.execute("SELECT CAST(FECHA AS DATE) AS FECHA_CORTE, TEMP_PROM FROM temperaturas").df()
        finally:
            conn.close()

        if df_ac.empty:
            return response_vacia()

        df_ac["SKU_CLEAN"] = df_ac["SKU"].astype(str).str.strip().str.upper()
        
        mapa_cat = {}
        if not df_v.empty:
            df_v["SKU_CLEAN"] = df_v["SKU_BSALE"].astype(str).str.strip().str.upper()
            for sku_val, cat_val in zip(df_v["SKU_CLEAN"], df_v["CATEGORIA"]):
                if cat_val and str(cat_val) not in ("Sin Categoría Mapeada", "Sin Tipo"):
                    mapa_cat[sku_val] = str(cat_val)

        if not df_m.empty:
            df_m["SKU_CLEAN"] = df_m["SKU"].astype(str).str.strip().str.upper()
            for sku_val, cat_val in zip(df_m["SKU_CLEAN"], df_m["CATEGORIA"]):
                if sku_val not in mapa_cat and cat_val and str(cat_val) not in ("Sin Categoría Mapeada", "Sin Tipo"):
                    mapa_cat[sku_val] = str(cat_val)

        df_ac["CATEGORIA_BASE"] = df_ac["SKU_CLEAN"].map(mapa_cat)
        df_ac["CATEGORIA"] = df_ac.apply(
            lambda r: inferir_categoria(r["CATEGORIA_BASE"], r["PRODUCTO"], r["SKU"]), axis=1
        )

        df_ac["FECHA_OBJ"] = pd.to_datetime(df_ac["FECHA_OBJ"], errors="coerce")
        df_ac = df_ac.dropna(subset=["FECHA_OBJ"])
        df_ac["FECHA_CORTE"] = df_ac["FECHA_OBJ"].dt.date

        if "CANAL" not in df_ac.columns:
            df_ac["CANAL"] = "D2C"
        if "VENDEDOR" not in df_ac.columns:
            df_ac["VENDEDOR"] = "D2C"
        if "BODEGA" not in df_ac.columns:
            df_ac["BODEGA"] = "CASA MATRIZ"

        min_date = df_ac["FECHA_CORTE"].min()
        max_date = df_ac["FECHA_CORTE"].max()

        f_in = parse_date_safe(fecha_inicio, min_date)
        f_fi = parse_date_safe(fecha_fin, max_date)

        # 1. Filtro de Fechas
        df_filt = df_ac[(df_ac["FECHA_CORTE"] >= f_in) & (df_ac["FECHA_CORTE"] <= f_fi)]

        # 2. Filtro de Categoría SKU
        if not es_filtro_todos(categoria):
            val_cat = str(categoria[0] if isinstance(categoria, (list, tuple)) else categoria).strip().upper()
            df_filt = df_filt[df_filt["CATEGORIA"].str.upper() == val_cat]

        # 3. Filtro de Canal de Venta
        if not es_filtro_todos(canal):
            val_can = str(canal[0] if isinstance(canal, (list, tuple)) else canal).strip().upper()
            df_filt = df_filt[df_filt["CANAL"].str.upper() == val_can]

        # 4. Filtro de Vendedor
        if not es_filtro_todos(vendedor):
            val_vend = str(vendedor[0] if isinstance(vendedor, (list, tuple)) else vendedor).strip().upper()
            df_filt = df_filt[df_filt["VENDEDOR"].str.upper() == val_vend]

        # 5. Filtro de Bodega
        if not es_filtro_todos(bodega):
            val_bod = str(bodega[0] if isinstance(bodega, (list, tuple)) else bodega).strip().upper()
            df_filt = df_filt[df_filt["BODEGA"].str.upper() == val_bod]

        if df_filt.empty:
            return response_vacia()

        checkouts_unicos = df_filt.drop_duplicates(subset=["ID_CHECKOUT"])
        total_carritos = len(checkouts_unicos)

        abandonados = checkouts_unicos[checkouts_unicos["ESTADO"] == "ABANDONADO"]
        s_op = pd.to_numeric(abandonados["TOTAL_PRICE"], errors="coerce").sum()
        oportunidad_perdida = float(s_op) if pd.notna(s_op) else 0.0

        recuperados = checkouts_unicos[checkouts_unicos["ESTADO"] == "RECUPERADO"]
        num_recuperados = len(recuperados)
        tasa_recuperacion = round((num_recuperados / total_carritos * 100), 1) if total_carritos > 0 else 0.0

        cat_counts = df_filt.groupby("CATEGORIA")["ID_CHECKOUT"].nunique().reset_index()
        cat_counts.columns = ["categoria", "count"]
        cat_counts = cat_counts.sort_values(by="count", ascending=False)

        distribucion_categoria = []
        for _, r in cat_counts.iterrows():
            c_nom = str(r["categoria"])
            if c_nom and c_nom != "nan":
                distribucion_categoria.append({
                    "categoria": c_nom,
                    "name": c_nom,
                    "count": int(r["count"]),
                    "value": int(r["count"])
                })

        prod_counts = df_filt.groupby("PRODUCTO").agg(
            carritos=("ID_CHECKOUT", "nunique"),
            precio_ref=("PRECIO_UNITARIO", "mean")
        ).reset_index().sort_values(by="carritos", ascending=False).head(5)

        top_productos = []
        for _, r in prod_counts.iterrows():
            p_nom = str(r["PRODUCTO"])
            p_pref = float(r["precio_ref"]) if pd.notna(r["precio_ref"]) else 0.0
            top_productos.append({
                "producto": p_nom,
                "name": p_nom,
                "carritos": int(r["carritos"]),
                "count": int(r["carritos"]),
                "precioRef": p_pref,
                "precio_ref": p_pref
            })

        daily_counts = checkouts_unicos.groupby("FECHA_CORTE").agg(
            carritos=("ID_CHECKOUT", "nunique")
        ).reset_index().sort_values(by="FECHA_CORTE")

        if not df_temp.empty:
            daily_counts = pd.merge(daily_counts, df_temp, on="FECHA_CORTE", how="left")
            daily_counts["TEMP_PROM"] = daily_counts["TEMP_PROM"].fillna(12.0)
        else:
            daily_counts["TEMP_PROM"] = 12.0

        daily_trend = []
        for idx, r in daily_counts.iterrows():
            d_str = r["FECHA_CORTE"].strftime("%d/%m")
            c_num = int(r["carritos"])
            t_real = round(float(r["TEMP_PROM"]), 1)
            daily_trend.append({
                "fecha": d_str,
                "date": d_str,
                "carritos": c_num,
                "count": c_num,
                "carts": c_num,
                "temperatura": t_real,
                "temp": t_real,
                "temp_c": t_real
            })

        return {
            "totalCarritos": total_carritos,
            "carritosAbandonados": total_carritos,
            "abandonedCount": total_carritos,
            "total": total_carritos,

            "oportunidadPerdida": oportunidad_perdida,
            "lostOpportunity": oportunidad_perdida,

            "carritosRecuperados": num_recuperados,
            "recoveredCount": num_recuperados,
            "recuperados": num_recuperados,

            "tasaRecuperacion": tasa_recuperacion,
            "recoveryRate": tasa_recuperacion,

            "distribucionCategoria": distribucion_categoria,
            "distribucion_categoria": distribucion_categoria,
            "categoryDistribution": distribucion_categoria,

            "topProductos": top_productos,
            "top_productos": top_productos,
            "topProducts": top_productos,

            "dailyTrend": daily_trend,
            "daily_trend": daily_trend,
            "comportamientoDiario": daily_trend,
            "comportamiento_diario": daily_trend,
            "trend": daily_trend
        }
    except Exception as e:
        print(f"❌ ERROR en /api/abandoned-checkouts: {e}")
        return response_vacia()