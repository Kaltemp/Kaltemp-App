"""
Módulo Principal — Endpoint /api/channels e /api/indicadores-d2c

Replica exactamente la lógica de cal_kpis() y el agrupado por CANAL
que teníamos en app.py (Streamlit), pero calculado en SQL puro sobre
DuckDB para máxima velocidad, y devuelto en el shape exacto de la
interfaz ChannelSale (src/types.ts).
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from typing import Optional
from db import get_connection
import pandas as pd
import unicodedata

router = APIRouter(prefix="/api", tags=["channels"])


# Misma agregación que usaba cal_kpis(): BSALE vs FULL (Shopify Full,
# Falabella API, etc.) se distinguen por la columna ORIGEN.
#
# MARGEN (05-ago-2026, confirmado con William): las líneas de servicio
# técnico sin SKU real (reparaciones/repuestos genéricos/despachos con
# glosa libre de Bsale, marcadas como ES_GLOSA_SERVICIO por sync_ventas.py)
# SÍ cuentan en la venta (totalBruto/bsale/full), pero se excluyen de
# contribucion/neto -- así no distorsionan el % de margen de ningún canal
# ni el Margen Frontal general, aunque su monto en $ sigue sumando.
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
    """Devuelve {canal: {bsale, full, totalBruto, contribucion, neto, txs}} para un rango."""
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
    """
    Devuelve la lista de canales con sus comparativos WOW / YOY / 2YOY,
    en el mismo formato que src/types.ts -> ChannelSale.
    """
    lista_vendedores = [v.strip() for v in vendedores.split(",") if v.strip()] if vendedores else None
    lista_categorias = [c.strip() for c in categorias.split(",") if c.strip()] if categorias else None

    dias = (fecha_fin - fecha_inicio).days + 1

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
# INDICADORES D2C (reescrito 06-ago-2026)
#
# Antes: "inversion"/"inversionYoy"/"ventaYoy"/"tkpYoy" eran
# multiplicadores inventados (venta*0.15, venta*0.12, etc.), y el
# endpoint ignoraba por completo fecha_inicio/fecha_fin (siempre traía
# el histórico completo). Además "Venta D2C" sumaba TODOS los canales,
# no solo D2C. Todo esto se corrige acá:
#   - Fecha real: se filtra ventas/GA4/marketing por fecha_inicio/
#     fecha_fin, y el "YoY" es una consulta real al mismo rango del
#     año anterior (no un multiplicador fijo).
#   - Venta D2C: filtrada a CANAL = 'D2C' (antes sumaba todo).
#   - Inversión POR CATEGORÍA: se reparte el gasto real de marketing
#     (mkt_inversion_meta + mkt_inversion_google) según a qué categoría
#     de producto corresponde cada campaña (por palabras clave en el
#     nombre, igual criterio que ya usamos para prestar imágenes entre
#     Meta y Google). Las campañas que no calzan con ninguna categoría
#     (Brand, Shopping, Catálogo) quedan fuera del reparto -- su gasto
#     sigue sumando al total general, solo no se le puede atribuir a
#     una categoría de producto específica.
# ============================================================

def _normalizar_texto(s) -> str:
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("-", " ").replace("_", " ")


# Palabra clave -> nombre de categoría REAL (debe calzar con los
# valores que existen en ventas.CATEGORIA / categorias_manual, no con
# los códigos internos que se usan para prestar imágenes en marketing).
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
    """{nombre_campana: categoria} asignado a mano desde la alerta de la
    app (prioridad sobre la adivinanza por palabra clave)."""
    from categorias_db import get_categorias_connection, init_categorias_db
    init_categorias_db()
    with get_categorias_connection() as con:
        filas = con.execute("SELECT campana, categoria FROM campanas_categoria").fetchall()
        return {row["campana"]: row["categoria"] for row in filas}


def _gasto_marketing_por_categoria(con, fecha_inicio, fecha_fin, marca: str = "Kaltemp") -> dict:
    """
    {categoria_real: gasto_total} sumando Meta + Google en el rango de
    fechas dado, repartido por categoría de producto, filtrado a UNA
    marca (columna "Marca" que ya viene en mkt_inversion_meta/google).
    Prioridad de categoría: 1) asignación manual desde la app
    (campanas_categoria) -- 2) adivinanza por palabra clave, como
    respaldo. Devuelve también "_total" con el gasto total sin
    repartir (Brand/Shopping/etc. que no calzan con ninguna categoría).

    Multi-categoría (07-ago-2026): la asignación manual puede guardar
    varias categorías separadas por coma (ej. "Mangueras, Herramientas,
    Iluminación" para una campaña de liquidación general). En ese caso
    el gasto de esa campaña se reparte en partes iguales entre todas
    las categorías listadas.
    """
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
        col_marca = next((c for c in df.columns if c.lower() == "marca"), None)
        if not (col_campana and col_gasto and col_fi):
            continue

        df["_fecha"] = pd.to_datetime(df[col_fi], errors="coerce")
        df["_gasto"] = pd.to_numeric(df[col_gasto], errors="coerce").fillna(0.0)
        df_rango = df[(df["_fecha"] >= pd.Timestamp(fecha_inicio)) & (df["_fecha"] <= pd.Timestamp(fecha_fin))]
        if col_marca:
            df_rango = df_rango[df_rango[col_marca] == marca]

        for _, fila in df_rango.iterrows():
            gasto = float(fila["_gasto"])
            resultado["_total"] += gasto
            nombre_campana = str(fila[col_campana]).strip()
            categoria_raw = mapa_manual.get(nombre_campana) or _mapear_categoria_real(nombre_campana)
            if categoria_raw:
                # Soporta 1 o varias categorías separadas por coma (ej.
                # una campaña de liquidación que promociona Mangueras,
                # Herramientas e Iluminación a la vez) -- el gasto se
                # reparte en partes iguales entre todas las que calcen,
                # ya que Meta/Google no dan el desglose interno por
                # categoría dentro de una misma campaña (07-ago-2026).
                categorias_lista = [c.strip() for c in categoria_raw.split(",") if c.strip()]
                if categorias_lista:
                    gasto_por_cat = gasto / len(categorias_lista)
                    for cat in categorias_lista:
                        resultado[cat] = resultado.get(cat, 0.0) + gasto_por_cat

    return resultado


def _ventas_d2c_periodo(con, fecha_inicio, fecha_fin, marca: str = "Kaltemp") -> dict:
    """
    Venta D2C real + desglose por categoría, para un rango de fechas Y
    una marca. Regla confirmada 06-ago-2026 con William:
      - Kaltemp: CANAL = 'D2C' específicamente.
      - Tom Palmer: TODO lo que cae bajo CANAL = 'Tom Palmer' (aún no
        tienen el mismo desglose de canales que Kaltemp -- todo su
        canal ES su D2C por ahora).
    """
    filtro_canal = "UPPER(CANAL) = 'TOM PALMER'" if marca == "Tom Palmer" else "UPPER(CANAL) = 'D2C'"

    fila_total = con.execute(f"""
        SELECT COALESCE(SUM(BRUTO_TOTAL), 0), COUNT(DISTINCT DOCUMENTO)
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? AND {filtro_canal}
    """, [fecha_inicio, fecha_fin]).fetchone()

    filas_cat = con.execute(f"""
        SELECT CATEGORIA, SUM(BRUTO_TOTAL) AS venta, COUNT(DISTINCT DOCUMENTO) AS txs
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? AND {filtro_canal}
        GROUP BY CATEGORIA
    """, [fecha_inicio, fecha_fin]).fetchall()

    por_categoria = {
        str(cat): {"venta": float(venta or 0), "txs": int(txs or 0)}
        for cat, venta, txs in filas_cat
        if cat and str(cat) not in ("nan", "None", "")
    }

    return {
        "venta_total": float(fila_total[0] or 0),
        "txs_total": int(fila_total[1] or 0),
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
    """
    Devuelve los Indicadores D2C (GA4 + Mkt Inversión + Ventas D2C + TACoS + Funnel).
    Todo real: venta D2C filtrada por canal, inversión repartida por
    categoría según campañas reales, y comparativo YoY con el mismo
    rango del año anterior (no multiplicadores inventados).

    Marca (06-ago-2026): Kaltemp usa CANAL='D2C'; Tom Palmer usa
    TODO su CANAL='Tom Palmer' (confirmado con William -- Tom Palmer
    no tiene el mismo desglose de canales todavía). GA4 -- PENDIENTE:
    ga4_metricas hoy es 100% del sitio de Kaltemp (kaltemp.cl); Tom
    Palmer (tompalmer.cl) tiene su propia propiedad de GA4 que aún no
    se sincroniza -- por eso, si marca="Tom Palmer", las métricas de
    sesiones/rebote/funnel salen en 0 en vez de mostrar por error los
    números de Kaltemp. Se activa solo cuando ga4_metricas traiga una
    columna "Marca" (mismo patrón que mkt_inversion_meta/google).
    """
    try:
        if not fecha_fin:
            fecha_fin = date.today()
        if not fecha_inicio:
            fecha_inicio = fecha_fin - timedelta(days=29)

        yoy_inicio = fecha_inicio.replace(year=fecha_inicio.year - 1)
        yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

        with get_connection() as con:
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]

            # --- GA4 (filtrado por fecha; Kaltemp y Tom Palmer viven en
            # tablas SEPARADAS -- ga4_metricas es de Kaltemp,
            # ga4_metricas_tompalmer es de Tom Palmer, 06-ago-2026) ---
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
                    df_ga4 = df_ga4_full  # sin columna de fecha reconocible -- no se puede filtrar, se usa todo
            elif marca != "Kaltemp":
                # Todavía no existe ga4_metricas_tompalmer -- no
                # inventamos números para Tom Palmer.
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

            mob = int(df_ga4[df_ga4["DISPOSITIVO"].astype(str).str.upper() == "MOBILE"]["SESIONES"].sum()) if not df_ga4.empty and "DISPOSITIVO" in df_ga4.columns else 0
            desk = int(df_ga4[df_ga4["DISPOSITIVO"].astype(str).str.upper() == "DESKTOP"]["SESIONES"].sum()) if not df_ga4.empty and "DISPOSITIVO" in df_ga4.columns else 0

            # --- Inversión de marketing (real, filtrada por fecha y marca) ---
            gasto_cat_cy = _gasto_marketing_por_categoria(con, fecha_inicio, fecha_fin, marca)
            gasto_cat_yoy = _gasto_marketing_por_categoria(con, yoy_inicio, yoy_fin, marca)
            total_mkt = gasto_cat_cy["_total"]
            total_mkt_yoy = gasto_cat_yoy["_total"]

            # --- Venta D2C real (filtrada por fecha y marca) ---
            d2c_cy = _ventas_d2c_periodo(con, fecha_inicio, fecha_fin, marca)
            d2c_yoy = _ventas_d2c_periodo(con, yoy_inicio, yoy_fin, marca)
            vta_d2c = d2c_cy["venta_total"]
            vta_d2c_yoy = d2c_yoy["venta_total"]

        tacos = (total_mkt / vta_d2c * 100) if vta_d2c > 0 else 0.0
        tacos_yoy = (total_mkt_yoy / vta_d2c_yoy * 100) if vta_d2c_yoy > 0 else 0.0
        conversion = (txs / total_sesiones * 100) if total_sesiones > 0 else 0.0

        # --- Performance por categoría: venta real + inversión real repartida ---
        # Se recorre la UNIÓN de categorías presentes en ventas Y en
        # campañas de marketing -- si no, una categoría con inversión
        # real pero sin venta categorizada todavía (típico mientras el
        # catálogo de Bsale no está 100% categorizado) desaparecía sin
        # dejar rastro (06-ago-2026, encontrado con William en Tom Palmer).
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
            "categoryPerf": cat_perf
        }
    except Exception as e:
        print(f"❌ ERROR en /api/indicadores-d2c: {e}")
        return {}