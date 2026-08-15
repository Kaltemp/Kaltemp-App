"""
GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\marketing.py
"""
import duckdb
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import os
import pandas as pd
import re

router = APIRouter(prefix="/api", tags=["marketing"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)

def get_db_connection():
    return duckdb.connect(DUCKDB_PATH, read_only=True)

def limpiar_numero(val) -> float:
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    val_str = str(val).strip()
    val_str = re.sub(r'[^\d.,-]', '', val_str)
    if not val_str:
        return 0.0

    if "." in val_str and "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    elif "." in val_str and len(val_str.split(".")[-1]) == 3:
        val_str = val_str.replace(".", "")
    elif "," in val_str:
        val_str = val_str.replace(",", ".")

    try:
        return float(val_str)
    except Exception:
        return 0.0

def buscar_columna_fuzzy(df, palabras_clave):
    if df.empty:
        return None
    for col in df.columns:
        col_clean = str(col).lower().replace("±", "ñ").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        if any(p.lower() in col_clean for p in palabras_clave):
            return col
    return None

def obtener_primera_imagen_valida(series):
    candidatos = [
        str(v).strip() for v in series
        if pd.notna(v) and str(v).strip().lower().startswith("http")
    ]
    if not candidatos:
        return ""
    reales = [c for c in candidatos if "Logo_Horizontal" not in c and "Logo-Kaltemp" not in c]
    return reales[0] if reales else candidatos[0]

def _rango_wow_yoy(fecha_inicio: Optional[str], fecha_fin: Optional[str]):
    if not fecha_inicio or not fecha_fin:
        return None, None, None
    try:
        dt_i = pd.to_datetime(fecha_inicio)
        dt_f = pd.to_datetime(fecha_fin)
        delta_dias = (dt_f - dt_i).days + 1
        if delta_dias <= 0:
            return None, None, None

        wow_f = dt_i - pd.Timedelta(days=1)
        wow_i = wow_f - pd.Timedelta(days=delta_dias - 1)

        yoy_i = dt_i - pd.Timedelta(days=365)
        yoy_f = dt_f - pd.Timedelta(days=365)

        return (dt_i, dt_f), (wow_i, wow_f), (yoy_i, yoy_f)
    except Exception:
        return None, None, None

def _filtrar_por_rango(df: pd.DataFrame, col_fi: str, col_ff: str, dt_i, dt_f) -> pd.DataFrame:
    if df.empty or not col_fi or not col_ff or dt_i is None or dt_f is None:
        return pd.DataFrame()
    
    if "_FI_DT" not in df.columns:
        df["_FI_DT"] = pd.to_datetime(df[col_fi], errors="coerce")
    if "_FF_DT" not in df.columns:
        df["_FF_DT"] = pd.to_datetime(df[col_ff], errors="coerce")

    cond = (df["_FF_DT"] >= dt_i) & (df["_FI_DT"] <= dt_f)
    return df[cond]


@router.get("/marketing-campaigns")
@router.get("/marketing")
def get_marketing_campaigns(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    marca: Optional[str] = Query(None, description="Filtra por marca: Kaltemp o Tom Palmer")
):
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]

            df_meta = pd.DataFrame()
            if "mkt_inversion_meta" in tables:
                df_meta = conn.execute("SELECT * FROM mkt_inversion_meta").df()
                if not df_meta.empty:
                    df_meta["PLATAFORMA"] = "Meta"

            df_google = pd.DataFrame()
            if "mkt_inversion_google" in tables:
                df_google = conn.execute("SELECT * FROM mkt_inversion_google").df()
                if not df_google.empty:
                    df_google["PLATAFORMA"] = "Google"
        finally:
            conn.close()

        df_all = pd.concat([df_meta, df_google], ignore_index=True)
        if df_all.empty:
            return []

        col_camp = buscar_columna_fuzzy(df_all, ["campa", "campaign", "nombre", "ad_name"]) or df_all.columns[3]
        col_fi = buscar_columna_fuzzy(df_all, ["fecha inicio", "fechainicio", "since", "start"])
        col_ff = buscar_columna_fuzzy(df_all, ["fecha fin", "fechafin", "until", "end"])

        col_gasto = buscar_columna_fuzzy(df_all, ["gasto", "spend", "inversion", "cost", "importe", "monto"])
        col_clics = buscar_columna_fuzzy(df_all, ["clic", "click"])
        col_imp = buscar_columna_fuzzy(df_all, ["impresi", "impressi"])
        
        col_val = None
        for col in df_all.columns:
            col_lower = str(col).lower().replace("_", " ").strip()
            if "valor compras" in col_lower or "valor de conv" in col_lower or "purchase value" in col_lower:
                col_val = col
                break
        if not col_val:
            col_val = buscar_columna_fuzzy(df_all, ["valor compras", "purchase_value", "revenue"])

        col_compras = None
        for col in df_all.columns:
            col_lower = str(col).lower().replace("_", " ").strip()
            if col_lower == "compras" or col_lower == "conversiones":
                col_compras = col
                break
        if not col_compras:
            col_compras = buscar_columna_fuzzy(df_all, ["compras", "conversiones"])

        col_roas = buscar_columna_fuzzy(df_all, ["roas"])
        col_img = buscar_columna_fuzzy(df_all, ["imagen", "piezagrafica", "creative", "url", "link", "pieza"])
        col_marca = buscar_columna_fuzzy(df_all, ["marca", "brand"])

        df_all["_gasto"] = df_all[col_gasto].apply(limpiar_numero) if col_gasto else 0.0
        df_all["_clics"] = df_all[col_clics].apply(limpiar_numero) if col_clics else 0.0
        df_all["_imp"] = df_all[col_imp].apply(limpiar_numero) if col_imp else 0.0
        df_all["_compras"] = df_all[col_compras].apply(limpiar_numero) if col_compras else 0.0

        if col_val:
            df_all["_val"] = df_all[col_val].apply(limpiar_numero)
        elif col_roas:
            df_all["_roas_raw"] = df_all[col_roas].apply(limpiar_numero)
            df_all["_val"] = df_all["_gasto"] * df_all["_roas_raw"]
        else:
            df_all["_val"] = 0.0

        df_all["_img"] = df_all[col_img] if col_img else ""
        df_all["_marca"] = df_all[col_marca].fillna("Kaltemp") if col_marca else "Kaltemp"
        df_all.loc[df_all["_marca"].astype(str).str.strip() == "", "_marca"] = "Kaltemp"

        if marca:
            df_all = df_all[df_all["_marca"].astype(str).str.upper() == marca.strip().upper()]
            if df_all.empty:
                return []

        r_cy, r_wow, r_yoy = _rango_wow_yoy(fecha_inicio, fecha_fin)

        if r_cy and col_fi and col_ff:
            df_cy = _filtrar_por_rango(df_all, col_fi, col_ff, r_cy[0], r_cy[1])
            df_wow = _filtrar_por_rango(df_all, col_fi, col_ff, r_wow[0], r_wow[1])
            df_yoy = _filtrar_por_rango(df_all, col_fi, col_ff, r_yoy[0], r_yoy[1])
        else:
            df_cy = df_all
            df_wow = pd.DataFrame()
            df_yoy = pd.DataFrame()

        if df_cy.empty:
            return []

        def _agrupar_campanas(df_sub):
            if df_sub.empty:
                return {}
            grp = df_sub.groupby([col_camp, "PLATAFORMA", "_marca"], as_index=False).agg({
                "_gasto": "sum",
                "_clics": "sum",
                "_imp": "sum",
                "_val": "sum",
                "_compras": "sum",
                "_img": obtener_primera_imagen_valida
            })
            res = {}
            for _, r in grp.iterrows():
                c_nom = str(r[col_camp]).strip()
                plat = str(r["PLATAFORMA"])
                mrc = str(r["_marca"])
                key = (c_nom, plat, mrc)
                res[key] = {
                    "gasto": float(r["_gasto"]),
                    "clics": int(r["_clics"]),
                    "imp": int(r["_imp"]),
                    "val": float(r["_val"]),
                    "compras": float(r["_compras"]),
                    "img": str(r["_img"]).strip()
                }
            return res

        dict_cy = _agrupar_campanas(df_cy)
        dict_wow = _agrupar_campanas(df_wow)
        dict_yoy = _agrupar_campanas(df_yoy)

        campanas_dict = []
        for idx, (key, data_cy) in enumerate(dict_cy.items()):
            c_nom, plat, mrc = key
            if not c_nom or c_nom.lower() in ("nan", "none", "null", "", "total", "totales"):
                continue

            gasto = data_cy["gasto"]
            clics = data_cy["clics"]
            imp = data_cy["imp"]
            val_comp = data_cy["val"]
            compras = data_cy["compras"]
            img = data_cy["img"]

            ctr = (clics / imp * 100) if imp > 0 else 0.0
            cpc = (gasto / clics) if clics > 0 else 0.0
            roas = (val_comp / gasto) if gasto > 0 else 0.0
            costo_compra = (gasto / compras) if compras > 0 else 0.0

            data_wow = dict_wow.get(key, {})
            gasto_wow = data_wow.get("gasto", 0.0)
            clics_wow = data_wow.get("clics", 0)
            imp_wow = data_wow.get("imp", 0)
            val_wow = data_wow.get("val", 0.0)
            compras_wow = data_wow.get("compras", 0.0)
            ctr_wow = (clics_wow / imp_wow * 100) if imp_wow > 0 else 0.0
            roas_wow = (val_wow / gasto_wow) if gasto_wow > 0 else 0.0
            cpc_wow = (gasto_wow / clics_wow) if clics_wow > 0 else 0.0
            costo_compra_wow = (gasto_wow / compras_wow) if compras_wow > 0 else 0.0

            data_yoy = dict_yoy.get(key, {})
            gasto_yoy = data_yoy.get("gasto", 0.0)
            clics_yoy = data_yoy.get("clics", 0)
            imp_yoy = data_yoy.get("imp", 0)
            val_yoy = data_yoy.get("val", 0.0)
            compras_yoy = data_yoy.get("compras", 0.0)
            ctr_yoy = (clics_yoy / imp_yoy * 100) if imp_yoy > 0 else 0.0
            roas_yoy = (val_yoy / gasto_yoy) if gasto_yoy > 0 else 0.0
            cpc_yoy = (gasto_yoy / clics_yoy) if clics_yoy > 0 else 0.0
            costo_compra_yoy = (gasto_yoy / compras_yoy) if compras_yoy > 0 else 0.0

            campanas_dict.append({
                "id": f"{plat}_{idx}",
                "plataforma": plat,
                "marca": mrc,
                "campana": c_nom,
                "imagenUrl": img,
                "imagen_url": img,
                "imagen": img,
                "piezagrafica": img,
                "piezaGrafica": img,
                "urlAnuncio": img,
                "url": img,
                "creative": img,
                "gastoCy": round(gasto, 2),
                "gastoYoy": round(gasto_yoy, 2),
                "gastoWow": round(gasto_wow, 2),
                "clicsCy": clics,
                "clicsYoy": clics_yoy,
                "clicsWow": clics_wow,
                "impresionesCy": imp,
                "impresionesYoy": imp_yoy,
                "impresionesWow": imp_wow,
                "ctrCy": round(ctr, 2),
                "ctrYoy": round(ctr_yoy, 2),
                "ctrWow": round(ctr_wow, 2),
                "cpcCy": round(cpc, 2),
                "cpcYoy": round(cpc_yoy, 2),
                "cpcWow": round(cpc_wow, 2),
                "comprasCy": int(compras),
                "comprasYoy": int(compras_yoy),
                "comprasWow": int(compras_wow),
                "costoCompraCy": round(costo_compra, 2),
                "costoCompraYoy": round(costo_compra_yoy, 2),
                "costoCompraWow": round(costo_compra_wow, 2),
                "roasCy": round(roas, 2),
                "roasYoy": round(roas_yoy, 2),
                "roasWow": round(roas_wow, 2),
                "valorComprasCy": round(val_comp, 2)
            })

        return campanas_dict
    except Exception as e:
        print(f"❌ ERROR en /api/marketing-campaigns: {e}")
        return []


@router.get("/marketing/weekly-trend")
def get_marketing_weekly_trend(
    marca: Optional[str] = Query(None, description="Filtra por marca: Kaltemp o Tom Palmer")
):
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            df_meta = pd.DataFrame()
            if "mkt_inversion_meta" in tables:
                df_meta = conn.execute("SELECT * FROM mkt_inversion_meta").df()
            df_google = pd.DataFrame()
            if "mkt_inversion_google" in tables:
                df_google = conn.execute("SELECT * FROM mkt_inversion_google").df()
        finally:
            conn.close()

        df_all = pd.concat([df_meta, df_google], ignore_index=True)
        if df_all.empty:
            return []

        col_fi = buscar_columna_fuzzy(df_all, ["fecha inicio", "fechainicio", "since", "start"])
        col_gasto = buscar_columna_fuzzy(df_all, ["gasto", "spend", "inversion", "cost", "importe", "monto"])
        col_marca = buscar_columna_fuzzy(df_all, ["marca", "brand"])

        if not col_fi or not col_gasto:
            return []

        df_all["_marca"] = df_all[col_marca].fillna("Kaltemp") if col_marca else "Kaltemp"
        if marca:
            df_all = df_all[df_all["_marca"].astype(str).str.upper() == marca.strip().upper()]
            if df_all.empty:
                return []

        df_all["_FI_DT"] = pd.to_datetime(df_all[col_fi], errors="coerce")
        df_all["_gasto"] = df_all[col_gasto].apply(limpiar_numero)

        df_all = df_all[df_all["_FI_DT"].notna()]
        df_all["_year"] = df_all["_FI_DT"].dt.year
        df_all["_week"] = df_all["_FI_DT"].dt.isocalendar().week

        df_all = df_all[df_all["_year"].isin([2024, 2025, 2026])]

        grp = df_all.groupby(["_week", "_year"])["_gasto"].sum().unstack(level=1)

        now_dt = pd.Timestamp.now()
        current_week_2026 = now_dt.isocalendar().week if now_dt.year == 2026 else 52

        weekly_list = []
        for w in range(1, 53):
            v_2026 = float(grp.loc[w, 2026]) if (2026 in grp.columns and w in grp.index and pd.notna(grp.loc[w, 2026])) else 0.0
            v_2025 = float(grp.loc[w, 2025]) if (2025 in grp.columns and w in grp.index and pd.notna(grp.loc[w, 2025])) else 0.0
            v_2024 = float(grp.loc[w, 2024]) if (2024 in grp.columns and w in grp.index and pd.notna(grp.loc[w, 2024])) else 0.0

            v_2026_val = v_2026 if w <= current_week_2026 else None

            weekly_list.append({
                "semana": f"S{w}",
                "numSemana": w,
                "actual2026": v_2026_val,
                "yoy2025": round(v_2025, 2),
                "yoy2024": round(v_2024, 2)
            })

        return weekly_list
    except Exception as e:
        print(f"❌ ERROR en /api/marketing/weekly-trend: {e}")
        return []


@router.get("/marketing-campaigns/anuncios")
def get_marketing_campaign_anuncios(
    campana: str = Query(..., description="Nombre exacto de la campaña (columna 'Campaña')"),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    marca: Optional[str] = Query(None, description="Filtra por marca: Kaltemp o Tom Palmer")
):
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if "mkt_inversion_meta_anuncios" not in tables:
                return []
            df = conn.execute("SELECT * FROM mkt_inversion_meta_anuncios").df()
        finally:
            conn.close()

        if df.empty:
            return []

        col_camp = None
        for col in df.columns:
            c_l = str(col).lower().strip()
            if c_l in ["campaña", "campana", "campaign"]:
                col_camp = col
                break
        if not col_camp:
            col_camp = df.columns[3]

        df = df[df[col_camp].astype(str).str.strip().str.lower() == campana.strip().lower()]
        if df.empty:
            return []

        col_ad_id = None
        for col in df.columns:
            c_l = str(col).lower().replace("_", " ").strip()
            if c_l in ["ad id", "id anuncio", "id_anuncio", "adid"]:
                col_ad_id = col
                break
        if not col_ad_id:
            col_ad_id = df.columns[5] if len(df.columns) > 5 else df.columns[0]

        col_ad_name = None
        for col in df.columns:
            c_l = str(col).lower().replace("_", " ").strip()
            if c_l in ["anuncio", "nombre anuncio", "ad name", "ad_name"]:
                col_ad_name = col
                break
        if not col_ad_name:
            col_ad_name = df.columns[4] if len(df.columns) > 4 else df.columns[0]

        col_gasto = buscar_columna_fuzzy(df, ["gasto", "spend", "inversion", "cost"])
        col_clics = buscar_columna_fuzzy(df, ["clic", "click"])
        col_imp = buscar_columna_fuzzy(df, ["impresi", "impressi"])

        col_val = None
        for col in df.columns:
            col_lower = str(col).lower().replace("_", " ").strip()
            if "valor compras" in col_lower or "valor de conv" in col_lower or "purchase value" in col_lower:
                col_val = col
                break
        if not col_val:
            col_val = buscar_columna_fuzzy(df, ["valor compras", "purchase_value", "revenue"])

        col_compras = None
        for col in df.columns:
            col_lower = str(col).lower().replace("_", " ").strip()
            if col_lower == "compras" or col_lower == "conversiones":
                col_compras = col
                break
        if not col_compras:
            col_compras = buscar_columna_fuzzy(df, ["compras", "conversiones"])

        col_img = None
        for col in df.columns:
            c_l = str(col).lower().strip()
            if c_l in ["imagen", "piezagrafica", "creative", "url", "link"]:
                col_img = col
                break
        if not col_img:
            col_img = buscar_columna_fuzzy(df, ["imagen", "piezagrafica", "creative", "url", "link"])

        col_fi = buscar_columna_fuzzy(df, ["fecha inicio", "fechainicio", "since", "start"])
        col_ff = buscar_columna_fuzzy(df, ["fecha fin", "fechafin", "until", "end"])
        col_marca = buscar_columna_fuzzy(df, ["marca", "brand"])

        df["_gasto"] = df[col_gasto].apply(limpiar_numero) if col_gasto else 0.0
        df["_clics"] = df[col_clics].apply(limpiar_numero) if col_clics else 0.0
        df["_imp"] = df[col_imp].apply(limpiar_numero) if col_imp else 0.0
        df["_val"] = df[col_val].apply(limpiar_numero) if col_val else 0.0
        df["_compras"] = df[col_compras].apply(limpiar_numero) if col_compras else 0.0
        df["_img"] = df[col_img] if col_img else ""

        df["_marca"] = df[col_marca].fillna("Kaltemp") if col_marca else "Kaltemp"
        df.loc[df["_marca"].astype(str).str.strip() == "", "_marca"] = "Kaltemp"

        if marca:
            df = df[df["_marca"].astype(str).str.upper() == marca.strip().upper()]
            if df.empty:
                return []

        r_cy, r_wow, r_yoy = _rango_wow_yoy(fecha_inicio, fecha_fin)

        if r_cy and col_fi and col_ff:
            df_cy = _filtrar_por_rango(df, col_fi, col_ff, r_cy[0], r_cy[1])
            df_wow = _filtrar_por_rango(df, col_fi, col_ff, r_wow[0], r_wow[1])
            df_yoy = _filtrar_por_rango(df, col_fi, col_ff, r_yoy[0], r_yoy[1])
        else:
            df_cy = df
            df_wow = pd.DataFrame()
            df_yoy = pd.DataFrame()

        if df_cy.empty:
            return []

        def _agrupar_anuncios(df_sub):
            if df_sub.empty:
                return {}
            grp = df_sub.groupby([col_ad_id, col_ad_name], as_index=False).agg({
                "_gasto": "sum",
                "_clics": "sum",
                "_imp": "sum",
                "_val": "sum",
                "_compras": "sum",
                "_img": obtener_primera_imagen_valida
            })
            res = {}
            for _, r in grp.iterrows():
                a_id = str(r[col_ad_id]).strip()
                a_nom = str(r[col_ad_name]).strip()
                key = (a_id, a_nom)
                res[key] = {
                    "gasto": float(r["_gasto"]),
                    "clics": int(r["_clics"]),
                    "imp": int(r["_imp"]),
                    "val": float(r["_val"]),
                    "compras": float(r["_compras"]),
                    "img": str(r["_img"]).strip()
                }
            return res

        dict_cy = _agrupar_anuncios(df_cy)
        dict_wow = _agrupar_anuncios(df_wow)
        dict_yoy = _agrupar_anuncios(df_yoy)

        anuncios_list = []
        for idx, (key, data_cy) in enumerate(dict_cy.items()):
            a_id, a_nom = key
            gasto = data_cy["gasto"]
            clics = data_cy["clics"]
            imp = data_cy["imp"]
            val_comp = data_cy["val"]
            compras = data_cy["compras"]
            img = data_cy["img"]

            ctr = (clics / imp * 100) if imp > 0 else 0.0
            cpc = (gasto / clics) if clics > 0 else 0.0
            roas = (val_comp / gasto) if gasto > 0 else 0.0
            costo_compra = (gasto / compras) if compras > 0 else 0.0

            data_wow = dict_wow.get(key, {})
            gasto_wow = data_wow.get("gasto", 0.0)
            clics_wow = data_wow.get("clics", 0)
            imp_wow = data_wow.get("imp", 0)
            val_wow = data_wow.get("val", 0.0)
            compras_wow = data_wow.get("compras", 0.0)
            ctr_wow = (clics_wow / imp_wow * 100) if imp_wow > 0 else 0.0
            roas_wow = (val_wow / gasto_wow) if gasto_wow > 0 else 0.0
            cpc_wow = (gasto_wow / clics_wow) if clics_wow > 0 else 0.0
            costo_compra_wow = (gasto_wow / compras_wow) if compras_wow > 0 else 0.0

            data_yoy = dict_yoy.get(key, {})
            gasto_yoy = data_yoy.get("gasto", 0.0)
            clics_yoy = data_yoy.get("clics", 0)
            imp_yoy = data_yoy.get("imp", 0)
            val_yoy = data_yoy.get("val", 0.0)
            compras_yoy = data_yoy.get("compras", 0.0)
            ctr_yoy = (clics_yoy / imp_yoy * 100) if imp_yoy > 0 else 0.0
            roas_yoy = (val_yoy / gasto_yoy) if gasto_yoy > 0 else 0.0
            cpc_yoy = (gasto_yoy / clics_yoy) if clics_yoy > 0 else 0.0
            costo_compra_yoy = (gasto_yoy / compras_yoy) if compras_yoy > 0 else 0.0

            anuncios_list.append({
                "id": f"ad_{idx}_{a_id}",
                "ad_id": a_id,
                "adId": a_id,
                "ad_name": a_nom,
                "anuncio": a_nom,
                "campana": campana,
                "imagenUrl": img,
                "imagen_url": img,
                "imagen": img,
                "piezagrafica": img,
                "piezaGrafica": img,
                "urlAnuncio": img,
                "url": img,
                "creative": img,
                "gastoCy": round(gasto, 2),
                "gastoYoy": round(gasto_yoy, 2),
                "gastoWow": round(gasto_wow, 2),
                "clicsCy": clics,
                "clicsYoy": clics_yoy,
                "clicsWow": clics_wow,
                "impresionesCy": imp,
                "impresionesYoy": imp_yoy,
                "impresionesWow": imp_wow,
                "ctrCy": round(ctr, 2),
                "ctrYoy": round(ctr_yoy, 2),
                "ctrWow": round(ctr_wow, 2),
                "cpcCy": round(cpc, 2),
                "cpcYoy": round(cpc_yoy, 2),
                "cpcWow": round(cpc_wow, 2),
                "comprasCy": int(compras),
                "comprasYoy": int(compras_yoy),
                "comprasWow": int(compras_wow),
                "costoCompraCy": round(costo_compra, 2),
                "costoCompraYoy": round(costo_compra_yoy, 2),
                "costoCompraWow": round(costo_compra_wow, 2),
                "roasCy": round(roas, 2),
                "roasYoy": round(roas_yoy, 2),
                "roasWow": round(roas_wow, 2),
                "valorComprasCy": round(val_comp, 2)
            })

        anuncios_list.sort(key=lambda x: x["gastoCy"], reverse=True)
        return anuncios_list
    except Exception as e:
        print(f"❌ ERROR en /api/marketing-campaigns/anuncios: {e}")
        return []


# ============================================================
# TOP / BOTTOM ANUNCIOS DE TODA LA CUENTA (13-ago-2026, para Resumen)
# Mismo detector de columnas fuzzy que /marketing-campaigns/anuncios,
# pero SIN filtrar por una campaña puntual -- agrupa por anuncio sobre
# toda la tabla mkt_inversion_meta_anuncios en el rango de fechas dado.
# Se descartan anuncios con gastoCy <= 0 (sin inversión real, no aportan
# información de "mejor/peor" -- solo ensuciarían el ranking con 0/0).
# ============================================================
@router.get("/marketing-campaigns/top-anuncios")
def get_marketing_top_anuncios(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    marca: Optional[str] = Query(None, description="Filtra por marca: Kaltemp o Tom Palmer"),
    limite: int = Query(3, ge=1, le=10),
):
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if "mkt_inversion_meta_anuncios" not in tables:
                return {"mejores": [], "peores": []}
            df = conn.execute("SELECT * FROM mkt_inversion_meta_anuncios").df()
        finally:
            conn.close()

        if df.empty:
            return {"mejores": [], "peores": []}

        col_ad_id = None
        for col in df.columns:
            c_l = str(col).lower().replace("_", " ").strip()
            if c_l in ["ad id", "id anuncio", "id_anuncio", "adid"]:
                col_ad_id = col
                break
        if not col_ad_id:
            col_ad_id = df.columns[5] if len(df.columns) > 5 else df.columns[0]

        col_ad_name = None
        for col in df.columns:
            c_l = str(col).lower().replace("_", " ").strip()
            if c_l in ["anuncio", "nombre anuncio", "ad name", "ad_name"]:
                col_ad_name = col
                break
        if not col_ad_name:
            col_ad_name = df.columns[4] if len(df.columns) > 4 else df.columns[0]

        col_gasto = buscar_columna_fuzzy(df, ["gasto", "spend", "inversion", "cost"])
        col_clics = buscar_columna_fuzzy(df, ["clic", "click"])
        col_imp = buscar_columna_fuzzy(df, ["impresi", "impressi"])

        col_val = None
        for col in df.columns:
            col_lower = str(col).lower().replace("_", " ").strip()
            if "valor compras" in col_lower or "valor de conv" in col_lower or "purchase value" in col_lower:
                col_val = col
                break
        if not col_val:
            col_val = buscar_columna_fuzzy(df, ["valor compras", "purchase_value", "revenue"])

        col_img = None
        for col in df.columns:
            c_l = str(col).lower().strip()
            if c_l in ["imagen", "piezagrafica", "creative", "url", "link"]:
                col_img = col
                break
        if not col_img:
            col_img = buscar_columna_fuzzy(df, ["imagen", "piezagrafica", "creative", "url", "link"])

        col_fi = buscar_columna_fuzzy(df, ["fecha inicio", "fechainicio", "since", "start"])
        col_marca = buscar_columna_fuzzy(df, ["marca", "brand"])

        df["_gasto"] = df[col_gasto].apply(limpiar_numero) if col_gasto else 0.0
        df["_clics"] = df[col_clics].apply(limpiar_numero) if col_clics else 0.0
        df["_imp"] = df[col_imp].apply(limpiar_numero) if col_imp else 0.0
        df["_val"] = df[col_val].apply(limpiar_numero) if col_val else 0.0
        df["_img"] = df[col_img] if col_img else ""
        df["_marca"] = df[col_marca].fillna("Kaltemp") if col_marca else "Kaltemp"
        df.loc[df["_marca"].astype(str).str.strip() == "", "_marca"] = "Kaltemp"

        if marca:
            df = df[df["_marca"].astype(str).str.upper() == marca.strip().upper()]

        if fecha_inicio and fecha_fin and col_fi:
            df[col_fi] = pd.to_datetime(df[col_fi], errors="coerce")
            f_ini_dt = pd.Timestamp(fecha_inicio)
            f_fin_dt = pd.Timestamp(fecha_fin)
            df = df[(df[col_fi] >= f_ini_dt) & (df[col_fi] <= f_fin_dt)]

        if df.empty:
            return {"mejores": [], "peores": []}

        grp = df.groupby([col_ad_id, col_ad_name], as_index=False).agg({
            "_gasto": "sum", "_clics": "sum", "_imp": "sum", "_val": "sum",
            "_img": obtener_primera_imagen_valida,
        })

        anuncios = []
        for _, r in grp.iterrows():
            gasto = float(r["_gasto"])
            if gasto <= 0:
                continue
            clics = float(r["_clics"])
            imp = float(r["_imp"])
            val = float(r["_val"])
            roas = (val / gasto) if gasto else 0.0
            ctr = (clics / imp * 100) if imp else 0.0
            anuncios.append({
                "adId": str(r[col_ad_id]).strip(),
                "anuncio": str(r[col_ad_name]).strip(),
                "imagen": str(r["_img"]).strip(),
                "gastoCy": round(gasto, 0),
                "clicsCy": int(clics),
                "impresionesCy": int(imp),
                "ctrCy": round(ctr, 2),
                "roasCy": round(roas, 2),
            })

        anuncios.sort(key=lambda a: a["roasCy"], reverse=True)
        peores = anuncios[-limite:] if len(anuncios) > limite else anuncios[:]
        peores = list(reversed(peores))
        return {
            "mejores": anuncios[:limite],
            "peores": peores,
        }
    except Exception as e:
        print(f"❌ ERROR en /api/marketing-campaigns/top-anuncios: {e}")
        return {"mejores": [], "peores": []}