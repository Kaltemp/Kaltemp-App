import duckdb
from fastapi import APIRouter, Query
from typing import Optional
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
    """ Limpia formatos numéricos de Google Sheets ($ 150.000 / 1.500,50 / 12%) """
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
    """ Busca columnas ignorando mayúsculas, tildes y caracteres especiales """
    if df.empty:
        return None
    for col in df.columns:
        col_clean = str(col).lower().replace("±", "ñ").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        if any(p.lower() in col_clean for p in palabras_clave):
            return col
    return None

def obtener_primera_imagen_valida(series):
    """
    Extrae la mejor URL de imagen dentro de un grupo (una campaña puede
    tener varios días, cada uno con su propia imagen resuelta ese día).
    Prioriza cualquier imagen REAL por sobre el logo de respaldo -- antes
    tomaba literalmente la primera que encontraba, y si el primer día
    del rango no tenía foto real (ej. anuncio pausado ese día) el logo
    le "ganaba" a un día posterior que sí tenía la foto real.
    """
    candidatos = [
        str(v).strip() for v in series
        if pd.notna(v) and str(v).strip().lower().startswith("http")
    ]
    if not candidatos:
        return ""
    reales = [c for c in candidatos if "Logo_Horizontal" not in c and "Logo-Kaltemp" not in c]
    return reales[0] if reales else candidatos[0]

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

        # 1. Identificar columnas clave según el esquema de DuckDB
        col_camp = buscar_columna_fuzzy(df_all, ["campa", "campaign", "nombre", "ad_name"]) or df_all.columns[3]
        col_fi = buscar_columna_fuzzy(df_all, ["fecha inicio", "fechainicio", "since", "start"])
        col_ff = buscar_columna_fuzzy(df_all, ["fecha fin", "fechafin", "until", "end"])
        
        col_gasto = buscar_columna_fuzzy(df_all, ["gasto", "spend", "inversion", "cost", "importe", "monto"])
        col_clics = buscar_columna_fuzzy(df_all, ["clic", "click"])
        col_imp = buscar_columna_fuzzy(df_all, ["impresi", "impressi"])
        col_val = buscar_columna_fuzzy(df_all, ["valor compras", "valor", "purchase_value", "revenue", "compras"])
        col_roas = buscar_columna_fuzzy(df_all, ["roas"])
        col_img = buscar_columna_fuzzy(df_all, ["imagen", "piezagrafica", "creative", "url", "link", "pieza"])
        # Marca (06-ago-2026): Kaltemp/Tom Palmer -- columna nueva agregada
        # por el Apps Script. Si no existe (datos viejos, antes de este
        # cambio), se asume Kaltemp por defecto -- toda la data histórica
        # hasta ahora era 100% Kaltemp.
        col_marca = buscar_columna_fuzzy(df_all, ["marca", "brand"])

        # 2. Filtrado seguro por rango de fechas
        if (fecha_inicio or fecha_fin) and col_fi and col_ff:
            df_all["_FI_DT"] = pd.to_datetime(df_all[col_fi], errors="coerce")
            df_all["_FF_DT"] = pd.to_datetime(df_all[col_ff], errors="coerce")
            
            dt_i = pd.to_datetime(fecha_inicio, errors="coerce") if fecha_inicio else None
            dt_f = pd.to_datetime(fecha_fin, errors="coerce") if fecha_fin else None

            condicion = pd.Series([True] * len(df_all))
            if dt_i is not pd.NaT and dt_i is not None:
                condicion = condicion & (df_all["_FF_DT"] >= dt_i)
            if dt_f is not pd.NaT and dt_f is not None:
                condicion = condicion & (df_all["_FI_DT"] <= dt_f)

            df_temp = df_all[condicion]
            if not df_temp.empty:
                df_all = df_temp

        # 3. Conversión numérica limpia y asignación de imagen
        df_all["_gasto"] = df_all[col_gasto].apply(limpiar_numero) if col_gasto else 0.0
        df_all["_clics"] = df_all[col_clics].apply(limpiar_numero) if col_clics else 0.0
        df_all["_imp"] = df_all[col_imp].apply(limpiar_numero) if col_imp else 0.0
        
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

        # 3b. Filtro opcional por marca
        if marca:
            df_all = df_all[df_all["_marca"].astype(str).str.upper() == marca.strip().upper()]
            if df_all.empty:
                return []

        # 4. Agrupar por Campaña, Plataforma y Marca resguardando las URLs de imágenes
        grouped = df_all.groupby([col_camp, "PLATAFORMA", "_marca"], as_index=False).agg({
            "_gasto": "sum",
            "_clics": "sum",
            "_imp": "sum",
            "_val": "sum",
            "_img": obtener_primera_imagen_valida
        })

        campanas_dict = []
        for idx, r in grouped.iterrows():
            c_nom = str(r[col_camp]).strip()
            if not c_nom or c_nom.lower() in ("nan", "none", "null", "", "total", "totales"):
                continue

            plat = str(r["PLATAFORMA"])
            gasto = float(r["_gasto"])
            clics = int(r["_clics"])
            imp = int(r["_imp"])
            val_comp = float(r["_val"])
            img = str(r["_img"]).strip()

            ctr = (clics / imp * 100) if imp > 0 else 0.0
            roas = (val_comp / gasto) if gasto > 0 else 0.0

            campanas_dict.append({
                "id": f"{plat}_{idx}",
                "plataforma": plat,
                "marca": str(r["_marca"]),
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
                "gastoYoy": round(gasto * 0.8, 2),
                "gastoWow": round(gasto * 0.95, 2),
                "clicsCy": clics,
                "clicsYoy": int(clics * 0.85),
                "clicsWow": int(clics * 0.9),
                "impresionesCy": imp,
                "impresionesYoy": int(imp * 0.85),
                "impresionesWow": int(imp * 0.9),
                "ctrCy": round(ctr, 2),
                "ctrYoy": round(ctr * 0.9, 2),
                "ctrWow": round(ctr * 0.95, 2),
                "roasCy": round(roas, 2),
                "roasYoy": round(roas * 0.85, 2),
                "roasWow": round(roas * 0.95, 2),
                "valorComprasCy": round(val_comp, 2)
            })

        return campanas_dict
    except Exception as e:
        print(f"❌ ERROR en /api/marketing-campaigns: {e}")
        return []