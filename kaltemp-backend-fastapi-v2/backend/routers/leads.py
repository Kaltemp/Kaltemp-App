import duckdb
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, date, timedelta
import os
import pandas as pd

router = APIRouter(prefix="/api", tags=["leads"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)

def get_db_connection():
    return duckdb.connect(DUCKDB_PATH, read_only=True)

@router.get("/leads")
def get_leads(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    try:
        conn = get_db_connection()
        try:
            df_all = conn.execute("SELECT * FROM leads").df()
        finally:
            conn.close()

        if df_all.empty:
            return {
                "totalLeads": 0, "totalLeadsWow": 0, "totalLeadsYoy": 0, "totalLeads2Yoy": 0,
                "convertidos": 0, "tasaConversion": 0,
                "canalPrincipal": {"nombre": "—", "pct": 0},
                "topVendedor": {"nombre": "—", "pct": 0},
                "topProducto": {"nombre": "—", "pct": 0},
                "pipelineStatuses": [], "weeklyTrend": [], "monthlyData": [],
                "sourcesData": [], "salesReps": [], "comunas": [], "productosData": [],
                "aniosDisponibles": []
            }

        df_all["FECHA_OBJ"] = pd.to_datetime(df_all["FECHA_OBJ"], errors="coerce")
        df_all = df_all.dropna(subset=["FECHA_OBJ"])

        if df_all.empty:
            return {
                "totalLeads": 0, "totalLeadsWow": 0, "totalLeadsYoy": 0, "totalLeads2Yoy": 0,
                "convertidos": 0, "tasaConversion": 0,
                "canalPrincipal": {"nombre": "—", "pct": 0},
                "topVendedor": {"nombre": "—", "pct": 0},
                "topProducto": {"nombre": "—", "pct": 0},
                "pipelineStatuses": [], "weeklyTrend": [], "monthlyData": [],
                "sourcesData": [], "salesReps": [], "comunas": [], "productosData": [],
                "aniosDisponibles": []
            }

        df_all["FECHA_CORTE"] = df_all["FECHA_OBJ"].dt.date
        df_all["AÑO"] = df_all["FECHA_OBJ"].dt.year
        df_all["MES_NUM"] = df_all["FECHA_OBJ"].dt.month
        df_all["SEMANA"] = df_all["FECHA_OBJ"].dt.isocalendar().week.astype(int)

        def normalizar_canal(val):
            if pd.isna(val): return "Chat Web"
            s = str(val).strip().upper()
            return "WhatsApp" if ("WHATSAPP" in s or "WSP" in s or s == "WA") else "Chat Web"

        def normalizar_estado(st_val):
            if pd.isna(st_val): return "NUEVO"
            s = str(st_val).upper().strip()
            if s == "CLIENT" or "CON_VENTA" in s or "WON" in s: return "CON_VENTA"
            elif s == "LONG_TERM" or "SIN_VENTA" in s or "LOST" in s or "DISCARDED" in s: return "SIN_VENTA"
            elif s == "ACTIVE" or "PROGRESO" in s or "CONTACTED" in s: return "EN_PROGRESO"
            return "NUEVO"

        def limpiar_fuente(val):
            if pd.isna(val) or not str(val).strip(): return "kaltemp.cl"
            s = str(val).strip().lower()
            if "google" in s: return "Google"
            elif "facebook" in s or "fb" in s: return "Facebook"
            elif "instagram" in s or "ig" in s: return "Instagram"
            elif "kaltemp" in s: return "kaltemp.cl"
            return s.capitalize()

        df_all["CANAL_DISP"] = df_all["CANAL"].apply(normalizar_canal)
        df_all["ESTADO_DISP"] = df_all["ESTADO"].apply(normalizar_estado)
        df_all["FUENTE_DISP"] = df_all["FUENTE"].apply(limpiar_fuente)

        if "PRODUCTO" not in df_all.columns:
            df_all["PRODUCTO"] = "General / Consulta Web"
        else:
            df_all["PRODUCTO"] = df_all["PRODUCTO"].fillna("General / Consulta Web")

        min_date = df_all["FECHA_CORTE"].min()
        max_date = df_all["FECHA_CORTE"].max()

        try:
            f_in = pd.to_datetime(fecha_inicio).date() if fecha_inicio else min_date
        except Exception:
            f_in = min_date

        try:
            f_fi = pd.to_datetime(fecha_fin).date() if fecha_fin else max_date
        except Exception:
            f_fi = max_date

        df_filt = df_all[(df_all["FECHA_CORTE"] >= f_in) & (df_all["FECHA_CORTE"] <= f_fi)]
        total_leads = len(df_filt)

        # WoW (agregado 19-ago-2026, a pedido de William: la tarjeta TOTAL LEADS
        # solo tenía YoY). Mismo criterio que ya usan channels.py/fulfillment.py
        # para WoW en el resto de la app: la misma cantidad de días del rango
        # seleccionado, corrida 7 días atrás -- no depende de reemplazar el año,
        # así que no tiene el borde de Feb-29 que sí tiene el cálculo YoY/2YoY.
        try:
            f_in_wow = f_in - timedelta(days=7)
            f_fi_wow = f_fi - timedelta(days=7)
            total_wow = len(df_all[(df_all["FECHA_CORTE"] >= f_in_wow) & (df_all["FECHA_CORTE"] <= f_fi_wow)])
        except Exception:
            total_wow = 0

        # YoY
        try:
            f_in_yoy = f_in.replace(year=f_in.year - 1)
            f_fi_yoy = f_fi.replace(year=f_fi.year - 1)
            total_yoy = len(df_all[(df_all["FECHA_CORTE"] >= f_in_yoy) & (df_all["FECHA_CORTE"] <= f_fi_yoy)])
        except Exception:
            total_yoy = 0

        try:
            f_in_2yoy = f_in.replace(year=f_in.year - 2)
            f_fi_2yoy = f_fi.replace(year=f_fi.year - 2)
            total_2yoy = len(df_all[(df_all["FECHA_CORTE"] >= f_in_2yoy) & (df_all["FECHA_CORTE"] <= f_fi_2yoy)])
        except Exception:
            total_2yoy = 0

        convertidos = len(df_filt[df_filt["ESTADO_DISP"] == "CON_VENTA"])
        tasa_conv = round((convertidos / total_leads * 100), 1) if total_leads > 0 else 0

        # Pipeline
        st_counts = df_filt["ESTADO_DISP"].value_counts().to_dict()
        labels_map = {"NUEVO": "Nuevo", "EN_PROGRESO": "En Progreso", "CON_VENTA": "Con Venta", "SIN_VENTA": "Sin Venta"}
        pipeline_statuses = []
        for st_key, st_label in labels_map.items():
            cnt = int(st_counts.get(st_key, 0))
            pct = round((cnt / total_leads * 100), 1) if total_leads > 0 else 0
            pipeline_statuses.append({"id": st_key, "label": st_label, "count": cnt, "pct": pct})

        # Líderes
        canal_counts = df_filt["CANAL_DISP"].value_counts()
        top_canal_nombre = canal_counts.index[0] if not canal_counts.empty else "—"
        top_canal_pct = round((canal_counts.iloc[0] / total_leads * 100), 1) if not canal_counts.empty and total_leads > 0 else 0

        vend_counts = df_filt["VENDEDOR"].value_counts()
        top_vend_nombre = vend_counts.index[0] if not vend_counts.empty else "—"
        top_vend_pct = round((vend_counts.iloc[0] / total_leads * 100), 1) if not vend_counts.empty and total_leads > 0 else 0

        # Métrica de Productos / Categorías de Interés
        prod_counts = df_filt["PRODUCTO"].value_counts()
        top_prod_nombre = prod_counts.index[0] if not prod_counts.empty else "—"
        top_prod_pct = round((prod_counts.iloc[0] / total_leads * 100), 1) if not prod_counts.empty and total_leads > 0 else 0

        productos_data = []
        for prod_name, cnt in prod_counts.items():
            if pd.isna(prod_name) or not str(prod_name).strip(): continue
            productos_data.append({
                "producto": str(prod_name),
                "count": int(cnt),
                "pct": round((cnt / total_leads * 100), 1) if total_leads > 0 else 0
            })

        sales_reps = []
        for v_name, cnt in vend_counts.items():
            if pd.isna(v_name) or not str(v_name).strip(): continue
            sales_reps.append({
                "name": str(v_name).title(),
                "leads": int(cnt),
                "pct": round((cnt / total_leads * 100), 1) if total_leads > 0 else 0
            })

        src_counts = df_filt["FUENTE_DISP"].value_counts()
        sources_data = []
        for src_name, cnt in src_counts.items():
            sources_data.append({
                "name": str(src_name),
                "count": int(cnt),
                "share": round((cnt / total_leads * 100), 1) if total_leads > 0 else 0
            })

        com_counts = df_filt["COMUNA"].value_counts().head(5)
        comunas = []
        for com_name, cnt in com_counts.items():
            if pd.isna(com_name) or not str(com_name).strip(): continue
            comunas.append({
                "comuna": str(com_name).title(),
                "count": int(cnt),
                "pct": round((cnt / total_leads * 100), 1) if total_leads > 0 else 0
            })

        anio_act = f_fi.year if f_fi else max_date.year
        anio_ant = anio_act - 1
        anio_2ant = anio_act - 2

        sem_act = df_all[df_all["AÑO"] == anio_act].groupby("SEMANA")["ID_LEAD"].count().to_dict()
        sem_ant = df_all[df_all["AÑO"] == anio_ant].groupby("SEMANA")["ID_LEAD"].count().to_dict()
        sem_2ant = df_all[df_all["AÑO"] == anio_2ant].groupby("SEMANA")["ID_LEAD"].count().to_dict()

        weekly_trend = []
        for w in range(1, 53):
            weekly_trend.append({
                "week": f"S{w}",
                "yActual": int(sem_act.get(w, 0)),
                "yAnterior": int(sem_ant.get(w, 0)),
                "y2Anterior": int(sem_2ant.get(w, 0))
            })

        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        mes_act = df_all[df_all["AÑO"] == anio_act].groupby("MES_NUM")["ID_LEAD"].count().to_dict()
        mes_ant = df_all[df_all["AÑO"] == anio_ant].groupby("MES_NUM")["ID_LEAD"].count().to_dict()
        mes_2ant = df_all[df_all["AÑO"] == anio_2ant].groupby("MES_NUM")["ID_LEAD"].count().to_dict()

        monthly_data = []
        for m_num in range(1, 13):
            monthly_data.append({
                "mes": meses_nombres[m_num - 1],
                "yActual": int(mes_act.get(m_num, 0)),
                "yAnterior": int(mes_ant.get(m_num, 0)),
                "y2Anterior": int(mes_2ant.get(m_num, 0))
            })

        return {
            "totalLeads": total_leads,
            "totalLeadsWow": total_wow,
            "totalLeadsYoy": total_yoy,
            "totalLeads2Yoy": total_2yoy,
            "convertidos": convertidos,
            "tasaConversion": tasa_conv,
            "canalPrincipal": {"nombre": top_canal_nombre, "pct": top_canal_pct},
            "topVendedor": {"nombre": top_vend_nombre, "pct": top_vend_pct},
            "topProducto": {"nombre": top_prod_nombre, "pct": top_prod_pct},
            "pipelineStatuses": pipeline_statuses,
            "weeklyTrend": weekly_trend,
            "monthlyData": monthly_data,
            "sourcesData": sources_data,
            "salesReps": sales_reps,
            "comunas": comunas,
            "productosData": productos_data,
            "aniosDisponibles": [anio_act, anio_ant, anio_2ant]
        }
    except Exception as e:
        return {"error": str(e)}