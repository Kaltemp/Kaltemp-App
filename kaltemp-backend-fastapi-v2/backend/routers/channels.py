"""
Módulo Principal — Endpoint /api/channels e /api/indicadores-d2c

Calculado en SQL puro sobre DuckDB, respondiendo dinámicamente a todos los
filtros globales para D2C. Tendencia Semanal Anual (Semanas 01 a 52 / YTD 2026 vs 2025 YoY)
independiente de la ventana corta de fechas.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from typing import Optional
from db import get_connection
import pandas as pd
import re
import unicodedata

router = APIRouter(prefix="/api", tags=["channels"])


def limpiar_numero(val) -> float:
    """
    Convierte valores de columnas numéricas (ej. "Gasto") que pueden venir
    en formato chileno/europeo (punto = separador de miles, coma = decimal)
    a float. Es la MISMA lógica que usa marketing.py (limpiar_numero) --
    debe mantenerse igual acá para que "Inversión MKT" (Indicadores D2C)
    calce con "Inversión Total" (Campañas de Marketing). Antes esta función
    no existía en este archivo y se usaba pd.to_numeric() directo, que no
    entiende el formato con puntos como separador de miles y produce totales
    más bajos que los reales (valores mal parseados o descartados como NaN).
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
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


SKUS_TOM_PALMER = [
    "TPPK0003", "TPPK0001", "TPPK0002", "KLHT0013", "KLPB0018",
    "KLPB0019", "KLPB0020", "KLPB0022", "KLPB0023", "KLPB0029",
    "KLAP0047", "KLSU0002", "KLSU0001", "KLSU0003", "KLSU0004",
    "LOHE0001", "LOHE0002", "LOHE0003", "LOHE0004", "LOJM0001",
    "LOJM0002", "LOIE0002", "LOIE0004", "LOIE0005", "LOIE0001",
    "KLRO0002", "KLRO0005", "KLRO0004", "KLRO0006", "KLBC0095"
]


_BASE_QUERY = """
    SELECT
        CANAL AS canal,
        SUM(CASE WHEN ORIGEN = 'BSALE' THEN BRUTO_TOTAL ELSE 0 END)              AS bsale,
        SUM(CASE WHEN ORIGEN != 'BSALE' THEN BRUTO_TOTAL ELSE 0 END)             AS full,
        SUM(BRUTO_TOTAL)                                                        AS totalBruto,
        SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE CONTRIBUCION END)           AS contribucion,
        SUM(CASE WHEN ES_GLOSA_SERVICIO THEN 0 ELSE NETO_TOTAL END)             AS neto,
        COUNT(DISTINCT DOCUMENTO)                                               AS txs
    FROM ventas
    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
"""


def _fetch_period(con, fecha_inicio: date, fecha_fin: date, vendedores: list[str] | None, categorias: list[str] | None) -> dict:
    sql = _BASE_QUERY
    params: list = [fecha_inicio, fecha_fin]
    if vendedores:
        placeholders = ", ".join(["?"] * len(vendedores))
        sql += f" AND UPPER(VENDEDOR) IN ({placeholders})"
        params += [v.upper() for v in vendedores]
    if categorias:
        placeholders = ", ".join(["?"] * len(categorias))
        sql += f" AND CATEGORIA IN ({placeholders})"
        params += categorias
    sql += " GROUP BY CANAL"
    cursor = con.execute(sql, params)
    columnas = [c[0] for c in cursor.description]
    filas = cursor.fetchall()
    return {fila[0]: dict(zip(columnas, fila)) for fila in filas}


def _pct(curr: float, prev: float) -> float:
    return round(((curr - prev) / prev * 100), 1) if prev else 0.0


@router.get("/channels")
def get_channels(
    fecha_inicio: date = Query(..., description="Inicio del período actual (CY)"),
    fecha_fin: date = Query(..., description="Fin del período actual (CY)"),
    vendedores: str = Query(None, description="Lista separada por comas para filtrar por VENDEDOR"),
    categorias: str = Query(None, description="Lista separada por comas para filtrar por CATEGORIA"),
):
    lista_vendedores = [v.strip() for v in vendedores.split(",") if v.strip()] if vendedores else None
    lista_categorias = [c.strip() for c in categorias.split(",") if c.strip()] if categorias else None

    wow_inicio, wow_fin = fecha_inicio - timedelta(days=7), fecha_fin - timedelta(days=7)
    yoy_inicio, yoy_fin = fecha_inicio.replace(year=fecha_inicio.year - 1), fecha_fin.replace(year=fecha_fin.year - 1)
    twoyoy_inicio, twoyoy_fin = fecha_inicio.replace(year=fecha_inicio.year - 2), fecha_fin.replace(year=fecha_fin.year - 2)

    with get_connection() as con:
        cy = _fetch_period(con, fecha_inicio, fecha_fin, lista_vendedores, lista_categorias)
        wow = _fetch_period(con, wow_inicio, wow_fin, lista_vendedores, lista_categorias)
        yoy = _fetch_period(con, yoy_inicio, yoy_fin, lista_vendedores, lista_categorias)
        twoyoy = _fetch_period(con, twoyoy_inicio, twoyoy_fin, lista_vendedores, lista_categorias)

    total_bruto_general = sum(v["totalBruto"] for v in cy.values()) or 1

    resultado = []
    for canal, v in cy.items():
        w = wow.get(canal, {})
        y = yoy.get(canal, {})
        t2 = twoyoy.get(canal, {})
        v_wow = w.get("totalBruto", 0)
        v_yoy = y.get("totalBruto", 0)
        v_2yoy = t2.get("totalBruto", 0)
        neto = v["neto"] or 0
        contribucion = v["contribucion"] or 0

        resultado.append({
            "canal": canal,
            "bsale": round(v["bsale"], 0),
            "full": round(v["full"], 0),
            "totalBruto": round(v["totalBruto"], 0),
            "contribucion": round(contribucion, 0),
            "neto": round(neto, 0),
            "txs": int(v["txs"]),
            "tkp": round(v["totalBruto"] / v["txs"], 0) if v["txs"] else 0,
            "wow": round(v_wow, 0),
            "yoy": round(v_yoy, 0),
            "twoYoy": round(v_2yoy, 0),
            "wowPct": _pct(v["totalBruto"], v_wow),
            "yoyPct": _pct(v["totalBruto"], v_yoy),
            "twoYoyPct": _pct(v["totalBruto"], v_2yoy),
            "margenFrontal": round((contribucion / neto * 100), 1) if neto else 0.0,
            "share": round((v["totalBruto"] / total_bruto_general * 100), 1),
            "contribucionWow": round(w.get("contribucion", 0) or 0, 0),
            "contribucionYoy": round(y.get("contribucion", 0) or 0, 0),
            "contribucionTwoYoy": round(t2.get("contribucion", 0) or 0, 0),
            "netoWow": round(w.get("neto", 0) or 0, 0),
            "netoYoy": round(y.get("neto", 0) or 0, 0),
            "netoTwoYoy": round(t2.get("neto", 0) or 0, 0),
            "txsWow": int(w.get("txs", 0) or 0),
            "txsYoy": int(y.get("txs", 0) or 0),
            "txsTwoYoy": int(t2.get("txs", 0) or 0),
        })

    resultado.sort(key=lambda r: r["totalBruto"], reverse=True)
    return resultado


# ============================================================
# INDICADORES D2C
# ============================================================

def _normalizar_texto(s) -> str:
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("-", " ").replace("_", " ")


_MAPA_CATEGORIA_REAL = [
    ("SANITARIA", "BC Agua Sanitaria"),
    ("PISCINA", "Temperado de Piscina"),
    ("GENERADOR", "Generadores"),
    ("CALEFACTOR", "Calefacción"),
    ("CALEFACCION", "Calefacción"),
    ("PERGOLA", "Pérgolas"),
    ("TERMO", "Termos"),
    ("VENTILACION", "Ventilación"),
    ("HOT TUB", "Hot Tub"),
    ("AIRE", "Aire Acondicionado"),
    ("HERRAMIENTA", "Herramientas"),
    ("MANGUERA", "Mangueras"),
    ("ILUMINACION", "Iluminación"),
]


def _mapear_categoria_real(nombre_campana: str) -> str | None:
    n = _normalizar_texto(nombre_campana)
    for palabra, categoria in _MAPA_CATEGORIA_REAL:
        if palabra in n:
            return categoria
    return None


def _mapa_categorias_manual_campanas() -> dict:
    from categorias_db import get_categorias_connection, init_categorias_db
    init_categorias_db()
    with get_categorias_connection() as con:
        filas = con.execute("SELECT campana, categoria FROM campanas_categoria").fetchall()
        return {row["campana"]: row["categoria"] for row in filas}


def _gasto_marketing_por_categoria(
    con,
    fecha_inicio,
    fecha_fin,
    marca: str = "Kaltemp",
    categorias: list[str] | None = None
) -> dict:
    resultado: dict = {"_total": 0.0}
    mapa_manual = _mapa_categorias_manual_campanas()
    tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]

    for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
        if tabla not in tables:
            continue
        df = con.execute(f"SELECT * FROM {tabla}").df()
        if df.empty:
            continue

        col_campana = next((c for c in df.columns if "campa" in c.lower()), None)
        col_gasto = next((c for c in df.columns if "gasto" in c.lower()), None)
        col_fi = next((c for c in df.columns if "fecha inicio" in c.lower().replace("ó", "o")), None)
        col_ff = next((c for c in df.columns if "fecha fin" in c.lower().replace("ó", "o")), None)
        col_marca = next((c for c in df.columns if c.lower() == "marca"), None)
        if not (col_campana and col_gasto and col_fi):
            continue

        df["_fecha"] = pd.to_datetime(df[col_fi], errors="coerce")
        # Si no hay columna de fecha fin, se asume que la campaña dura un solo día
        # (fecha_fin = fecha_inicio), igual que hace /api/marketing-campaigns.
        df["_fecha_fin"] = pd.to_datetime(df[col_ff], errors="coerce") if col_ff else df["_fecha"]
        df["_gasto"] = df[col_gasto].apply(limpiar_numero)
        # IMPORTANTE: se usa el mismo criterio de "traslape de rango" que
        # /api/marketing-campaigns (_filtrar_por_rango en marketing.py) --
        # una campaña cuenta si [fecha_inicio, fecha_fin] se superpone con el
        # rango consultado, no solo si "empieza" dentro de él. Antes esta
        # función filtraba únicamente por fecha_inicio, lo que hacía que
        # "Inversión MKT" en Indicadores D2C no calzara con "Inversión Total"
        # en Campañas de Marketing para el mismo rango de fechas.
        df_rango = df[(df["_fecha_fin"] >= pd.Timestamp(fecha_inicio)) & (df["_fecha"] <= pd.Timestamp(fecha_fin))]
        if col_marca and col_marca in df_rango.columns:
            df_rango = df_rango[df_rango[col_marca] == marca]

        for _, fila in df_rango.iterrows():
            gasto = float(fila["_gasto"])
            nombre_campana = str(fila[col_campana]).strip()
            cat_camp = mapa_manual.get(nombre_campana) or _mapear_categoria_real(nombre_campana)
            # Toda campaña que no matchea ninguna categoría conocida (ni por
            # mapeo manual ni por palabra clave en el nombre) cae en
            # "Sin Categoría" -- el mismo nombre que ya usa _ventas_d2c_periodo
            # para ventas sin categoría, así se fusionan en una sola fila de
            # la tabla en vez de perderse. Antes esas campañas SÍ sumaban al
            # "_total" (la tarjeta INVERSIÓN MKT) pero no a ninguna categoría,
            # por lo que el total de la tabla "Performance por Categoría"
            # (TOTAL GENERAL) quedaba por debajo de la tarjeta.
            cat_bucket = cat_camp or "Sin Categoría"

            if categorias and not any(c.lower() == cat_bucket.lower() for c in categorias):
                continue

            resultado["_total"] += gasto
            resultado[cat_bucket] = resultado.get(cat_bucket, 0.0) + gasto

    return resultado


def _calcular_tendencia_semanal_d2c(
    df_ga4_full,
    con,
    marca: str = "Kaltemp",
    categorias: list[str] | None = None
) -> list:
    """
    Calcula la tendencia semanal anual (Sem 01 a semana actual YTD)
    para el año actual (2026) y su comparativo YoY (2025).
    """
    today = date.today()
    anio_actual = today.year
    anio_yoy = anio_actual - 1

    tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
    filas_gasto = []
    mapa_manual = _mapa_categorias_manual_campanas()

    for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
        if tabla not in tables:
            continue
        df_mkt = con.execute(f"SELECT * FROM {tabla}").df()
        if df_mkt.empty:
            continue

        col_campana = next((c for c in df_mkt.columns if "campa" in c.lower()), None)
        col_gasto = next((c for c in df_mkt.columns if "gasto" in c.lower()), None)
        col_fi = next((c for c in df_mkt.columns if "fecha inicio" in c.lower().replace("ó", "o")), None)
        col_marca = next((c for c in df_mkt.columns if c.lower() == "marca"), None)
        if not (col_gasto and col_fi):
            continue

        df_mkt["_fecha"] = pd.to_datetime(df_mkt[col_fi], errors="coerce")
        df_mkt["_gasto"] = df_mkt[col_gasto].apply(limpiar_numero)

        if col_marca and col_marca in df_mkt.columns:
            df_mkt = df_mkt[df_mkt[col_marca] == marca]

        for _, fila in df_mkt.iterrows():
            if pd.notnull(fila["_fecha"]):
                dt = fila["_fecha"]
                if dt.year in (anio_actual, anio_yoy):
                    nombre_campana = str(fila[col_campana]).strip() if col_campana else ""
                    cat_camp = mapa_manual.get(nombre_campana) or _mapear_categoria_real(nombre_campana)
                    cat_bucket = cat_camp or "Sin Categoría"
                    if categorias and not any(c.lower() == cat_bucket.lower() for c in categorias):
                        continue
                    filas_gasto.append({"fecha": dt, "gasto": float(fila["_gasto"]), "anio": dt.year})

    df_spend = pd.DataFrame(filas_gasto)

    semana_actual_num = today.isocalendar().week
    semanas_lista = [f"Sem {w:02d}" for w in range(1, semana_actual_num + 1)]

    res_dict = {
        w: {"sessions": 0, "sessionsYoy": 0, "spend": 0.0, "spendYoy": 0.0}
        for w in semanas_lista
    }

    # Sesiones GA4 (2026 vs 2025)
    if not df_ga4_full.empty and "_fecha" in df_ga4_full.columns and "SESIONES" in df_ga4_full.columns:
        df_valid = df_ga4_full[df_ga4_full["_fecha"].notnull()].copy()
        df_valid["_anio"] = df_valid["_fecha"].dt.year
        df_valid["_semana"] = df_valid["_fecha"].apply(lambda d: f"Sem {d.isocalendar().week:02d}")

        for _, row in df_valid.iterrows():
            sem = row["_semana"]
            anio = row["_anio"]
            ses = int(row["SESIONES"])

            if sem in res_dict:
                if anio == anio_actual:
                    res_dict[sem]["sessions"] += ses
                elif anio == anio_yoy:
                    res_dict[sem]["sessionsYoy"] += ses

    # Gasto MKT (2026 vs 2025)
    if not df_spend.empty:
        df_spend["_semana"] = df_spend["fecha"].apply(lambda d: f"Sem {d.isocalendar().week:02d}")
        for _, row in df_spend.iterrows():
            sem = row["_semana"]
            anio = row["anio"]
            gasto = float(row["gasto"])

            if sem in res_dict:
                if anio == anio_actual:
                    res_dict[sem]["spend"] += gasto
                elif anio == anio_yoy:
                    res_dict[sem]["spendYoy"] += gasto

    weekly_list = []
    for sem in semanas_lista:
        weekly_list.append({
            "week": sem,
            "sessions": res_dict[sem]["sessions"],
            "sessionsYoy": res_dict[sem]["sessionsYoy"],
            "spend": round(res_dict[sem]["spend"], 2),
            "spendYoy": round(res_dict[sem]["spendYoy"], 2)
        })

    return weekly_list


def _ventas_d2c_periodo(
    con,
    fecha_inicio,
    fecha_fin,
    marca: str = "Kaltemp",
    categorias: list[str] | None = None,
    vendedores: list[str] | None = None,
    bodegas: list[str] | None = None
) -> dict:
    filtro_canal = """(
        UPPER(CANAL) IN ('D2C', 'SHOWROOM')
        OR UPPER(VENDEDOR) LIKE '%ANDES%GEAR%'
        OR UPPER(VENDEDOR) LIKE '%ANDESGEAR%'
    )"""

    placeholders_sku = ", ".join(["?"] * len(SKUS_TOM_PALMER))
    if marca == "Tom Palmer":
        filtro_marca = f"UPPER(SKU_BSALE) IN ({placeholders_sku})"
    else:
        filtro_marca = f"(SKU_BSALE IS NULL OR UPPER(SKU_BSALE) NOT IN ({placeholders_sku}))"

    sql_where = f"WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? AND {filtro_canal} AND {filtro_marca}"
    params = [fecha_inicio, fecha_fin] + SKUS_TOM_PALMER

    if categorias:
        placeholders = ", ".join(["?"] * len(categorias))
        sql_where += f" AND CATEGORIA IN ({placeholders})"
        params += categorias

    if vendedores:
        placeholders = ", ".join(["?"] * len(vendedores))
        sql_where += f" AND UPPER(VENDEDOR) IN ({placeholders})"
        params += [v.upper() for v in vendedores]

    if bodegas:
        placeholders = ", ".join(["?"] * len(bodegas))
        sql_where += f" AND BODEGA IN ({placeholders})"
        params += bodegas

    filas_cat = con.execute(f"""
        SELECT 
            CASE 
                WHEN ES_GLOSA_SERVICIO THEN 'Despachos y Servicios'
                WHEN CATEGORIA IS NULL OR TRIM(CATEGORIA) = '' THEN 'Sin Categoría'
                ELSE CATEGORIA 
            END AS cat_nombre,
            SUM(BRUTO_TOTAL) AS venta, 
            COUNT(DISTINCT DOCUMENTO) AS txs
        FROM ventas
        {sql_where}
        GROUP BY cat_nombre
    """, params).fetchall()

    por_categoria = {}
    venta_acumulada = 0.0
    txs_acumuladas = 0

    for cat_nombre, venta, txs in filas_cat:
        v = float(venta or 0)
        t = int(txs or 0)
        por_categoria[str(cat_nombre)] = {"venta": v, "txs": t}
        venta_acumulada += v
        txs_acumuladas += t

    return {
        "venta_total": venta_acumulada,
        "txs_total": txs_acumuladas,
        "por_categoria": por_categoria,
    }


@router.get("/indicadores-d2c")
@router.get("/d2c")
def get_d2c_performance(
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    categoria: Optional[str] = Query(None),
    canal: Optional[str] = Query(None),
    vendedor: Optional[str] = Query(None),
    bodega: Optional[str] = Query(None),
    marca: str = Query("Kaltemp", description="Kaltemp o Tom Palmer")
):
    try:
        if not fecha_fin:
            fecha_fin = date.today()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=29)

        lista_categorias = [c.strip() for c in categoria.split(",") if c.strip()] if categoria else None
        lista_vendedores = [v.strip() for v in vendedor.split(",") if v.strip()] if vendedor else None
        lista_bodegas = [b.strip() for b in bodega.split(",") if b.strip()] if bodega else None

        yoy_inicio = fecha_inicio.replace(year=fecha_inicio.year - 1)
        yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

        with get_connection() as con:
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]

            df_ga4_full = pd.DataFrame()
            df_ga4 = pd.DataFrame()
            df_ga4_yoy = pd.DataFrame()
            ga4_disponible_para_marca = True

            tabla_ga4 = "ga4_metricas_tompalmer" if marca == "Tom Palmer" else "ga4_metricas"
            if tabla_ga4 in tables:
                df_ga4_full = con.execute(f"SELECT * FROM {tabla_ga4}").df()
                col_fecha_ga4 = next((c for c in df_ga4_full.columns if "fecha" in c.lower()), None)

                if col_fecha_ga4:
                    df_ga4_full["_fecha"] = pd.to_datetime(df_ga4_full[col_fecha_ga4], errors="coerce")
                    df_ga4 = df_ga4_full[(df_ga4_full["_fecha"] >= pd.Timestamp(fecha_inicio)) & (df_ga4_full["_fecha"] <= pd.Timestamp(fecha_fin))]
                    df_ga4_yoy = df_ga4_full[(df_ga4_full["_fecha"] >= pd.Timestamp(yoy_inicio)) & (df_ga4_full["_fecha"] <= pd.Timestamp(yoy_fin))]
                else:
                    df_ga4 = df_ga4_full
            elif marca != "Kaltemp":
                ga4_disponible_para_marca = False

            def _sesiones(df):
                return int(df["SESIONES"].sum()) if not df.empty and "SESIONES" in df.columns else 0

            def _txs_ga4(df):
                return int(df["TRANSACCIONES"].sum()) if not df.empty and "TRANSACCIONES" in df.columns else 0

            total_sesiones = _sesiones(df_ga4)
            sesiones_yoy = _sesiones(df_ga4_yoy)
            tasa_rebote = float(df_ga4["TASA_REBOTE"].mean() * 100) if not df_ga4.empty and "TASA_REBOTE" in df_ga4.columns else 0.0
            atc = int(df_ga4["ADD_TO_CART"].sum()) if not df_ga4.empty and "ADD_TO_CART" in df_ga4.columns else 0
            checkouts = int(df_ga4["CHECKOUTS"].sum()) if not df_ga4.empty and "CHECKOUTS" in df_ga4.columns else 0
            txs = _txs_ga4(df_ga4)

            # Clasificación de Dispositivos
            if not df_ga4.empty and "DISPOSITIVO" in df_ga4.columns and "SESIONES" in df_ga4.columns:
                disp_clean = df_ga4["DISPOSITIVO"].astype(str).str.strip().str.upper()
                mob = int(df_ga4[disp_clean.str.contains("MOB")]["SESIONES"].sum())
                desk = int(df_ga4[~disp_clean.str.contains("MOB")]["SESIONES"].sum())
            else:
                mob = 0
                desk = 0

            # --- Inversión de marketing ---
            gasto_cat_cy = _gasto_marketing_por_categoria(con, fecha_inicio, fecha_fin, marca, lista_categorias)
            gasto_cat_yoy = _gasto_marketing_por_categoria(con, yoy_inicio, yoy_fin, marca, lista_categorias)
            total_mkt = gasto_cat_cy["_total"]
            total_mkt_yoy = gasto_cat_yoy["_total"]

            # --- Tendencia Semanal Anual (2026 vs 2025 YoY) ---
            weekly_data = _calcular_tendencia_semanal_d2c(df_ga4_full, con, marca, lista_categorias)

            # --- Venta D2C real ---
            d2c_cy = _ventas_d2c_periodo(con, fecha_inicio, fecha_fin, marca, lista_categorias, lista_vendedores, lista_bodegas)
            d2c_yoy = _ventas_d2c_periodo(con, yoy_inicio, yoy_fin, marca, lista_categorias, lista_vendedores, lista_bodegas)
            vta_d2c = d2c_cy["venta_total"]
            vta_d2c_yoy = d2c_yoy["venta_total"]

        tacos = (total_mkt / vta_d2c * 100) if vta_d2c > 0 else 0.0
        tacos_yoy = (total_mkt_yoy / vta_d2c_yoy * 100) if vta_d2c_yoy > 0 else 0.0
        conversion = (txs / total_sesiones * 100) if total_sesiones > 0 else 0.0

        # --- Performance por categoría ---
        categorias_ventas = set(d2c_cy["por_categoria"].keys())
        categorias_marketing = {k for k in gasto_cat_cy.keys() if k != "_total"}
        categorias_marketing |= {k for k in gasto_cat_yoy.keys() if k != "_total"}
        todas_las_categorias = categorias_ventas | categorias_marketing

        cat_perf = []
        for cat_nombre in todas_las_categorias:
            datos = d2c_cy["por_categoria"].get(cat_nombre, {"venta": 0.0, "txs": 0})
            venta = datos["venta"]
            txs_cat = datos["txs"]
            datos_yoy = d2c_yoy["por_categoria"].get(cat_nombre, {"venta": 0.0, "txs": 0})

            cat_perf.append({
                "categoria": cat_nombre,
                "inversion": round(gasto_cat_cy.get(cat_nombre, 0.0), 2),
                "inversionYoy": round(gasto_cat_yoy.get(cat_nombre, 0.0), 2),
                "venta": round(venta, 2),
                "ventaYoy": round(datos_yoy["venta"], 2),
                "tkp": round(venta / txs_cat, 0) if txs_cat else 0.0,
                "tkpYoy": round(datos_yoy["venta"] / datos_yoy["txs"], 0) if datos_yoy["txs"] else 0.0,
            })

        cat_perf.sort(key=lambda c: (c["venta"], c["inversion"]), reverse=True)

        return {
            "marca": marca,
            "ga4Disponible": ga4_disponible_para_marca,
            "totalSessions": total_sesiones,
            "totalMktSpend": total_mkt,
            "totalD2CSales": vta_d2c,
            "tacosGlobal": tacos,
            "conversionRate": conversion,
            "bounceRate": tasa_rebote,
            "sessionsYoy": sesiones_yoy,
            "mktSpendYoy": total_mkt_yoy,
            "d2cSalesYoy": vta_d2c_yoy,
            "tacosYoy": tacos_yoy,
            "mobileSessions": mob,
            "desktopSessions": desk,
            "addToCart": atc,
            "checkouts": checkouts,
            "transactions": txs,
            "weeklyData": weekly_data,
            "categoryPerf": cat_perf
        }
    except Exception as e:
        print(f"❌ ERROR en /api/indicadores-d2c: {e}")
        return {}