# ============================================================
# ARCHIVO: resumen.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\resumen.py
# (Respaldar antes: Copy-Item resumen.py resumen.py.bak)
#
# CAMBIOS vs la versión anterior (ver auditoría en el chat):
# Se mantienen TAL CUAL las secciones que ya usaban datos reales:
#   A. kpis_hero, B. tendencia_mensual, C. channels, D. rankings_sku,
#   E. distribuidores/inmobiliaria, I. pendientes_despacho / leads.
# Se REEMPLAZAN por consultas reales (antes tenían números fijos o
# fórmulas inventadas) -- mismo shape de respuesta, misma forma en que
# ResumenView.tsx los consume, así que el diseño no cambia:
#   F. logistica       -> antes: despachos*13887 inventado + fallback
#                          665/9.235.411/3.440.054 fijo si algo fallaba.
#                          Ahora: mismas columnas/criterio que ya usa
#                          /api/logistica real (sync_dependent.py):
#                          COSTO_ENVIO real de enviame_despachos, cobro
#                          real de ventas (PRODUCTO='Despacho' o
#                          SKU_BSALE='DespachoCentry'). Si no hay datos,
#                          disponible=False (el frontend ya lo maneja).
#   G. marketing/d2c    -> antes: sesiones, inversión, impresiones, CTR
#                          y venta D2C fijos (ej. 53255 sesiones,
#                          $6.000.000 inversión, siempre los mismos
#                          números pasara lo que pasara). Ahora: sesiones
#                          reales de ga4_metricas / ga4_metricas_tompalmer,
#                          inversión/impresiones/clics reales de
#                          mkt_inversion_meta + mkt_inversion_google (mismo
#                          fuzzy-match de columnas que ya usa marketing.py),
#                          y venta D2C real con el mismo criterio que usa
#                          /api/indicadores-d2c (CANAL D2C/SHOWROOM +
#                          Andes Gear, split Kaltemp/Tom Palmer por SKU).
#   H. temperatura       -> antes: fórmula pseudo-aleatoria basada en el
#                          día del mes (no tocaba ninguna tabla real).
#                          Ahora: tabla real `temperaturas` (FECHA,
#                          TEMP_MAX, TEMP_MIN), igual que temperatura_ventas.py.
#   I. carros_abandonados -> antes: si no había top 3 productos reales,
#                          inventaba 3 productos con nombre y precio fijos.
#                          Ahora: si no hay datos reales, top_productos
#                          queda vacío (el frontend ya muestra "Sin datos").
# ============================================================
"""
routers/resumen.py — Centro de Control Ejecutivo Consolidado.
Consultas blindadas contra columnas inexistentes, tipos dinámicos y DuckDB.

PRINCIPIO (ver notas de William sobre "fallo silencioso"): ninguna sección
de este endpoint debe devolver un número inventado para "rellenar" un
dato faltante. Si una tabla no existe o la consulta no encuentra datos
reales, la sección debe devolver su forma vacía real (0, [], o
disponible=False) -- nunca una cifra de relleno que se vea como dato real.
"""
import time
import logging
import re
from datetime import date, timedelta
from typing import Optional
import pandas as pd
from fastapi import APIRouter
from db import get_connection

router = APIRouter(prefix="/api", tags=["resumen"])

_CACHE_RESUMEN = {}
_CACHE_TTL_SECS = 300
logger = logging.getLogger("resumen")

# SKUs de Tom Palmer -- misma lista que usa channels.py (_ventas_d2c_periodo)
# para separar venta D2C por marca. Se mantiene sincronizada a mano con esa
# lista; si se agregan SKUs nuevos de Tom Palmer allá, replicar acá también.
SKUS_TOM_PALMER = [
    "TPPK0003", "TPPK0001", "TPPK0002", "KLHT0013", "KLPB0018",
    "KLPB0019", "KLPB0020", "KLPB0022", "KLPB0023", "KLPB0029",
    "KLAP0047", "KLSU0002", "KLSU0001", "KLSU0003", "KLSU0004",
    "LOHE0001", "LOHE0002", "LOHE0003", "LOHE0004", "LOJM0001",
    "LOJM0002", "LOIE0002", "LOIE0004", "LOIE0005", "LOIE0001",
    "KLRO0002", "KLRO0005", "KLRO0004", "KLRO0006", "KLBC0095"
]


def _safe_div(a, b):
    return (a / b) if b else 0.0


def _pct_var(cy, prev):
    return ((cy - prev) / prev * 100) if prev else (100.0 if cy else 0.0)


# ------------------------------------------------------------------
# Helpers de columnas dinámicas para mkt_inversion_meta / _google --
# mismo patrón que ya usa backend/routers/marketing.py (buscar_columna_fuzzy
# + limpiar_numero), copiado acá para no depender de un import cruzado
# entre routers (evita que un typo en otro archivo tumbe el arranque
# de toda la app, ya que main.py importa este router al boot).
# ------------------------------------------------------------------
def _buscar_columna_fuzzy(df, palabras_clave):
    if df.empty:
        return None
    for col in df.columns:
        col_clean = str(col).lower().replace("ñ", "n").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if any(p.lower() in col_clean for p in palabras_clave):
            return col
    return None


def _limpiar_numero(val) -> float:
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


@router.get("/resumen")
def get_resumen(fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None):
    # 1. Fechas
    if fecha_inicio and fecha_fin:
        try:
            f_fin = date.fromisoformat(fecha_fin)
            f_ini = date.fromisoformat(fecha_inicio)
        except ValueError:
            f_fin = date.today()
            f_ini = f_fin - timedelta(days=30)
    else:
        f_fin = date.today()
        f_ini = f_fin - timedelta(days=30)

    # 2. Caché TTL
    cache_key = f"{f_ini}_{f_fin}"
    ahora = time.time()
    if cache_key in _CACHE_RESUMEN:
        expira, datos_guardados = _CACHE_RESUMEN[cache_key]
        if ahora < expira:
            return datos_guardados

    try:
        yoy_ini = f_ini.replace(year=f_ini.year - 1)
        yoy_fin = f_fin.replace(year=f_fin.year - 1)
        twoyoy_ini = f_ini.replace(year=f_ini.year - 2)
        twoyoy_fin = f_fin.replace(year=f_fin.year - 2)
    except ValueError:
        yoy_ini = f_ini - timedelta(days=365)
        yoy_fin = f_fin - timedelta(days=365)
        twoyoy_ini = f_ini - timedelta(days=730)
        twoyoy_fin = f_fin - timedelta(days=730)

    hace_14 = f_fin - timedelta(days=14)
    wow_ini, wow_fin = f_ini - timedelta(days=7), f_fin - timedelta(days=7)

    resultado = {}

    with get_connection() as con:
        tables = {t[0] for t in con.execute("SHOW TABLES").fetchall()}

        # Detectar columnas existentes en tabla ventas
        cols_info = con.execute("PRAGMA table_info('ventas')").fetchall()
        col_names = {c[1].upper() for c in cols_info}

        # Filtro seguro de glosas/servicios
        if "ES_GLOSA_SERVICIO" in col_names:
            glosa_filter = "AND (CAST(ES_GLOSA_SERVICIO AS VARCHAR) NOT IN ('true', 'TRUE', '1', 't', 'SI', 'Si'))"
            contrib_calc = "CASE WHEN CAST(ES_GLOSA_SERVICIO AS VARCHAR) IN ('true', 'TRUE', '1', 't', 'SI', 'Si') THEN 0 ELSE CONTRIBUCION END"
            neto_calc = "CASE WHEN CAST(ES_GLOSA_SERVICIO AS VARCHAR) IN ('true', 'TRUE', '1', 't', 'SI', 'Si') THEN 0 ELSE NETO_TOTAL END"
        else:
            glosa_filter = ""
            contrib_calc = "CONTRIBUCION"
            neto_calc = "NETO_TOTAL"

        # Columna de categoría dinámica
        cat_col = "CATEGORIA" if "CATEGORIA" in col_names else ("LINEA" if "LINEA" in col_names else ("FAMILIA" if "FAMILIA" in col_names else "'General'"))

        # Columna de producto/descripción dinámica
        desc_col = "DESCRIPCION" if "DESCRIPCION" in col_names else ("PRODUCTO" if "PRODUCTO" in col_names else "SKU")
        sku_col = "SKU" if "SKU" in col_names else desc_col

        # ================================================================
        # A. KPIS HERO  (sin cambios -- ya usaba datos reales)
        # ================================================================
        def _totales(p_ini, p_fin):
            row = con.execute(f"""
                SELECT
                    COALESCE(SUM(BRUTO_TOTAL), 0) AS venta,
                    COALESCE(SUM({contrib_calc}), 0) AS contribucion,
                    COALESCE(SUM({neto_calc}), 0) AS neto,
                    COUNT(DISTINCT DOCUMENTO) AS txs
                FROM ventas
                WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
            """, [p_ini, p_fin]).fetchone()
            return {
                "venta": float(row[0] or 0), "contribucion": float(row[1] or 0),
                "neto": float(row[2] or 0), "txs": int(row[3] or 0),
            }

        actual = _totales(f_ini, f_fin)
        wow = _totales(wow_ini, wow_fin)
        yoy = _totales(yoy_ini, yoy_fin)
        twoyoy = _totales(twoyoy_ini, twoyoy_fin)

        serie_rows = con.execute(f"""
            SELECT
                CAST(FECHA_OBJ AS DATE) AS dia,
                SUM(BRUTO_TOTAL) AS venta,
                SUM({contrib_calc}) AS contribucion,
                SUM({neto_calc}) AS neto,
                COUNT(DISTINCT DOCUMENTO) AS txs
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) >= ? AND CAST(FECHA_OBJ AS DATE) <= ?
            GROUP BY CAST(FECHA_OBJ AS DATE)
            ORDER BY dia
        """, [hace_14, f_fin]).fetchall()

        def _margen(t): return _safe_div(t["contribucion"], t["neto"]) * 100
        def _tkp(t): return _safe_div(t["venta"], t["txs"])

        serie_venta, serie_contri, serie_margen, serie_tkp = [], [], [], []
        for fila in serie_rows:
            v, c, n, t = float(fila[1] or 0), float(fila[2] or 0), float(fila[3] or 0), int(fila[4] or 0)
            serie_venta.append(round(v, 0))
            serie_contri.append(round(c, 0))
            serie_margen.append(round(_safe_div(c, n) * 100, 1))
            serie_tkp.append(round(_safe_div(v, t), 0))

        resultado["kpis_hero"] = {
            "disponible": True,
            "venta": {
                "actual": actual["venta"], "wow": wow["venta"], "yoy": yoy["venta"], "twoyoy": twoyoy["venta"],
                "serie": serie_venta,
            },
            "contribucion": {
                "actual": actual["contribucion"], "wow": wow["contribucion"], "yoy": yoy["contribucion"], "twoyoy": twoyoy["contribucion"],
                "serie": serie_contri,
            },
            "margen": {
                "actual": round(_margen(actual), 1), "wow": round(_margen(wow), 1), "yoy": round(_margen(yoy), 1), "twoyoy": round(_margen(twoyoy), 1),
                "serie": serie_margen,
            },
            "tkp": {
                "actual": round(_tkp(actual), 0), "wow": round(_tkp(wow), 0), "yoy": round(_tkp(yoy), 0), "twoyoy": round(_tkp(twoyoy), 0),
                "serie": serie_tkp,
            },
        }

        # ================================================================
        # B. TENDENCIA MENSUAL (12 MESES)  (sin cambios)
        # ================================================================
        try:
            meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            year_actual = f_fin.year
            year_prev = year_actual - 1

            mensual_rows = con.execute("""
                SELECT
                    MONTH(FECHA_OBJ) as mes_num,
                    SUM(CASE WHEN YEAR(FECHA_OBJ) = ? THEN BRUTO_TOTAL ELSE 0 END) / 1000000.0 as cy,
                    SUM(CASE WHEN YEAR(FECHA_OBJ) = ? THEN BRUTO_TOTAL ELSE 0 END) / 1000000.0 as ly
                FROM ventas
                WHERE YEAR(FECHA_OBJ) IN (?, ?) AND CAST(FECHA_OBJ AS DATE) <= ?
                GROUP BY 1 ORDER BY 1
            """, [year_actual, year_prev, year_actual, year_prev, f_fin]).fetchall()

            meses_dict = {r[0]: (float(r[1] or 0), float(r[2] or 0)) for r in mensual_rows}

            tendencia_data = []
            for m in range(1, 13):
                cy, ly = meses_dict.get(m, (0.0, 0.0))
                yoy_pct = ((cy - ly) / ly * 100) if ly > 0 else (100.0 if cy > 0 else 0.0)
                tendencia_data.append({
                    "month": meses_nombres[m - 1],
                    "cy": round(cy, 1),
                    "ly": round(ly, 1),
                    "yoy": round(yoy_pct, 1) if cy > 0 else None
                })
            resultado["tendencia_mensual"] = tendencia_data
        except Exception:
            resultado["tendencia_mensual"] = []

        # ================================================================
        # C. MIX DE CANALES  (sin cambios)
        # ================================================================
        try:
            canal_rows = con.execute("""
                WITH act AS (
                    SELECT COALESCE(NULLIF(TRIM(CANAL), ''), 'Otros') as canal, SUM(BRUTO_TOTAL) as venta
                    FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? GROUP BY 1
                ),
                prev AS (
                    SELECT COALESCE(NULLIF(TRIM(CANAL), ''), 'Otros') as canal, SUM(BRUTO_TOTAL) as venta_yoy
                    FROM ventas WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ? GROUP BY 1
                )
                SELECT
                    a.canal,
                    a.venta,
                    COALESCE(p.venta_yoy, 0) as venta_yoy
                FROM act a
                LEFT JOIN prev p ON a.canal = p.canal
                ORDER BY a.venta DESC LIMIT 5
            """, [f_ini, f_fin, yoy_ini, yoy_fin]).fetchall()

            total_canales = sum(r[1] for r in canal_rows) or 1
            channels_data = []
            for r in canal_rows:
                v_act, v_yoy = float(r[1] or 0), float(r[2] or 0)
                var_pct = ((v_act - v_yoy) / v_yoy * 100) if v_yoy > 0 else (100.0 if v_act > 0 else 0.0)
                channels_data.append({
                    "canal": r[0],
                    "totalBruto": v_act,
                    "totalBrutoYoy": v_yoy,
                    "yoy": round(var_pct, 1),
                    "share": round((v_act / total_canales) * 100, 1)
                })
            resultado["channels"] = channels_data
        except Exception:
            resultado["channels"] = []

        # ================================================================
        # D. RANKINGS SKUs & CATEGORÍAS  (sin cambios)
        # ================================================================
        try:
            sku_query = f"""
                WITH act AS (
                    SELECT
                        COALESCE(NULLIF(TRIM({desc_col}), ''), {sku_col}, 'Sin Nombre') as nombre,
                        SUM(COALESCE(CANTIDAD, 0)) as cant,
                        SUM(COALESCE(BRUTO_TOTAL, 0)) as venta
                    FROM ventas
                    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                      {glosa_filter}
                    GROUP BY 1
                    HAVING SUM(COALESCE(BRUTO_TOTAL, 0)) > 0
                ),
                prev AS (
                    SELECT
                        COALESCE(NULLIF(TRIM({desc_col}), ''), {sku_col}, 'Sin Nombre') as nombre,
                        SUM(COALESCE(BRUTO_TOTAL, 0)) as venta_yoy
                    FROM ventas
                    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                      {glosa_filter}
                    GROUP BY 1
                )
                SELECT a.nombre, a.cant, a.venta, COALESCE(p.venta_yoy, 0) as venta_yoy
                FROM act a
                LEFT JOIN prev p ON a.nombre = p.nombre
                ORDER BY a.venta DESC
            """
            skus_all = con.execute(sku_query, [f_ini, f_fin, yoy_ini, yoy_fin]).fetchall()

            def _fmt_sku(r):
                return {
                    "nombre": str(r[0]),
                    "cantCy": float(r[1] or 0),
                    "ventaCy": float(r[2] or 0),
                    "ventaYoy": float(r[3] or 0)
                }

            top3_sku = [_fmt_sku(r) for r in skus_all[:3]]
            bot_pool = [r for r in skus_all if (r[2] or 0) > 0]
            bot3_sku = [_fmt_sku(r) for r in sorted(bot_pool, key=lambda x: x[2])[:3]]

            cat_query = f"""
                WITH act AS (
                    SELECT
                        COALESCE(NULLIF(TRIM({cat_col}), ''), 'Sin Categoría') as cat,
                        SUM(COALESCE(CANTIDAD, 0)) as cant,
                        SUM(COALESCE(BRUTO_TOTAL, 0)) as venta
                    FROM ventas
                    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                      {glosa_filter}
                    GROUP BY 1
                    HAVING SUM(COALESCE(BRUTO_TOTAL, 0)) > 0
                ),
                prev AS (
                    SELECT
                        COALESCE(NULLIF(TRIM({cat_col}), ''), 'Sin Categoría') as cat,
                        SUM(COALESCE(BRUTO_TOTAL, 0)) as venta_yoy
                    FROM ventas
                    WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                      {glosa_filter}
                    GROUP BY 1
                )
                SELECT a.cat, a.cant, a.venta, COALESCE(p.venta_yoy, 0) as venta_yoy
                FROM act a
                LEFT JOIN prev p ON a.cat = p.cat
                ORDER BY a.venta DESC
            """
            cats_all = con.execute(cat_query, [f_ini, f_fin, yoy_ini, yoy_fin]).fetchall()

            def _fmt_cat(r):
                return {
                    "categoria": str(r[0]),
                    "cantCy": float(r[1] or 0),
                    "ventaCy": float(r[2] or 0),
                    "ventaYoy": float(r[3] or 0)
                }

            top3_cat = [_fmt_cat(r) for r in cats_all[:3]]
            bot_cats = [r for r in cats_all if (r[2] or 0) > 0]
            bot3_cat = [_fmt_cat(r) for r in sorted(bot_cats, key=lambda x: x[2])[:3]]

            resultado["rankings_sku"] = {
                "top3Productos": top3_sku,
                "bottom3Productos": bot3_sku,
                "top3Categorias": top3_cat,
                "bottom3Categorias": bot3_cat,
            }
        except Exception as e:
            logger.error(f"Error en rankings SKU/Categorías: {e}")
            resultado["rankings_sku"] = {"top3Productos": [], "bottom3Productos": [], "top3Categorias": [], "bottom3Categorias": []}

        # ================================================================
        # E. DISTRIBUIDORES & INMOBILIARIAS  (sin cambios)
        # ================================================================
        def _get_b2b_summary(canal_pattern):
            try:
                rows = con.execute(f"""
                    WITH actual AS (
                        SELECT COALESCE(NULLIF(TRIM(CLIENTE), ''), 'Sin Cliente') AS cliente, SUM(BRUTO_TOTAL) AS venta
                        FROM ventas
                        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                          AND (CANAL ILIKE ? OR CANAL ILIKE ?)
                          {glosa_filter}
                        GROUP BY 1
                    ),
                    yoy AS (
                        SELECT COALESCE(NULLIF(TRIM(CLIENTE), ''), 'Sin Cliente') AS cliente, SUM(BRUTO_TOTAL) AS venta_yoy
                        FROM ventas
                        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                          AND (CANAL ILIKE ? OR CANAL ILIKE ?)
                          {glosa_filter}
                        GROUP BY 1
                    )
                    SELECT COALESCE(a.cliente, y.cliente) AS cliente, COALESCE(a.venta, 0) AS venta_act, COALESCE(y.venta_yoy, 0) AS venta_yoy
                    FROM actual a FULL OUTER JOIN yoy y ON a.cliente = y.cliente ORDER BY venta_act DESC
                """, [f_ini, f_fin, f"%{canal_pattern}%", f"%{canal_pattern}s%", yoy_ini, yoy_fin, f"%{canal_pattern}%", f"%{canal_pattern}s%"]).fetchall()

                total_act = sum(r[1] for r in rows)
                total_yoy = sum(r[2] for r in rows)
                activos = [r for r in rows if r[1] > 0]

                def _item(r):
                    v, vy = float(r[1]), float(r[2])
                    var = ((v - vy) / vy * 100) if vy > 0 else (100.0 if v > 0 else 0.0)
                    return {"nombre": str(r[0]), "venta": v, "venta_yoy": vy, "var_pct_yoy": round(var, 1)}

                top3 = [_item(r) for r in activos[:3]]
                bot3 = [_item(r) for r in sorted(activos, key=lambda x: x[1])[:3]]
                var_tot = ((total_act - total_yoy) / total_yoy * 100) if total_yoy > 0 else (100.0 if total_act > 0 else 0.0)
                return {
                    "disponible": True,
                    "venta_actual": float(total_act),
                    "venta_yoy": float(total_yoy),
                    "var_pct_yoy": round(var_tot, 1),
                    "top3": top3,
                    "bottom3": bot3
                }
            except Exception as e:
                logger.error(f"Error en B2B ({canal_pattern}): {e}")
                return {"disponible": False, "top3": [], "bottom3": []}

        resultado["distribuidores"] = _get_b2b_summary("DISTRIBUIDOR")
        resultado["inmobiliaria"] = _get_b2b_summary("INMOBILIARI")

        # ================================================================
        # F. CONTROL LOGÍSTICO & MARGEN FLETE
        # REESCRITO: mismo criterio real que /api/logistica
        # (backend/routers/sync_dependent.py::get_logistica) -- costo real
        # de COSTO_ENVIO en enviame_despachos, cobro real de ventas con
        # PRODUCTO='Despacho' o SKU_BSALE='DespachoCentry'. Sin
        # multiplicador inventado y sin fallback numérico fijo: si no hay
        # datos, disponible=False (el frontend ya maneja ese caso).
        # ================================================================
        try:
            if "enviame_despachos" not in tables:
                raise RuntimeError("tabla enviame_despachos no existe todavía")

            desp_row = con.execute("""
                SELECT COUNT(*), SUM(COSTO_ENVIO)
                FROM enviame_despachos
                WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?
            """, [f_ini, f_fin]).fetchone()
            despachos = int(desp_row[0] or 0) if desp_row else 0
            costo_enviame = float((desp_row[1] if desp_row else 0) or 0)

            cobro_bs_row = con.execute("""
                SELECT COALESCE(SUM(BRUTO_TOTAL), 0) FROM ventas
                WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                  AND (UPPER(TRIM(PRODUCTO)) = 'DESPACHO' OR SKU_BSALE = 'DespachoCentry')
            """, [f_ini, f_fin]).fetchone()
            cobro_bsale = float(cobro_bs_row[0] or 0) if cobro_bs_row else 0.0

            resultado["logistica"] = {
                "disponible": despachos > 0,
                "despachosCy": despachos,
                "costoEnviameCy": round(costo_enviame, 0),
                "cobroBsaleCy": round(cobro_bsale, 0),
                "diferencia": round(cobro_bsale - costo_enviame, 0)
            }
        except Exception as e:
            logger.error(f"Error en logística: {e}")
            resultado["logistica"] = {"disponible": False, "despachosCy": 0, "costoEnviameCy": 0, "cobroBsaleCy": 0, "diferencia": 0}

        # ================================================================
        # G. VENTAS D2C Y MARKETING
        # REESCRITO: venta D2C con el mismo criterio real que usa
        # /api/indicadores-d2c (backend/routers/channels.py ::
        # _ventas_d2c_periodo): CANAL D2C/SHOWROOM + vendedor Andes Gear,
        # split Kaltemp / Tom Palmer por membresía de SKU_BSALE en
        # SKUS_TOM_PALMER. Sesiones reales de ga4_metricas /
        # ga4_metricas_tompalmer (si la tabla existe). Inversión /
        # impresiones / clics reales de mkt_inversion_meta +
        # mkt_inversion_google (mismo fuzzy-match de columnas que
        # marketing.py, columna "Gasto" es VARCHAR -> limpiar_numero).
        # ================================================================
        def _ventas_d2c_marca(p_ini, p_fin, marca):
            placeholders_sku = ", ".join(["?"] * len(SKUS_TOM_PALMER))
            if marca == "Tom Palmer":
                filtro_marca = f"UPPER(SKU_BSALE) IN ({placeholders_sku})"
            else:
                filtro_marca = f"(SKU_BSALE IS NULL OR UPPER(SKU_BSALE) NOT IN ({placeholders_sku}))"
            filtro_canal = """(
                UPPER(CANAL) IN ('D2C', 'SHOWROOM')
                OR UPPER(VENDEDOR) LIKE '%ANDES%GEAR%'
                OR UPPER(VENDEDOR) LIKE '%ANDESGEAR%'
            )"""
            row = con.execute(f"""
                SELECT COALESCE(SUM(BRUTO_TOTAL), 0)
                FROM ventas
                WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                  AND {filtro_canal} AND {filtro_marca}
            """, [p_ini, p_fin] + [s.upper() for s in SKUS_TOM_PALMER]).fetchone()
            return float(row[0] or 0) if row else 0.0

        def _sesiones_ga4(p_ini, p_fin, tabla_ga4):
            if tabla_ga4 not in tables:
                return None  # tabla no existe -> no confundir con "0 sesiones reales"
            df = con.execute(f"SELECT * FROM {tabla_ga4}").df()
            if df.empty:
                return 0
            col_fecha = next((c for c in df.columns if "fecha" in c.lower()), None)
            if not col_fecha or "SESIONES" not in df.columns:
                return 0
            df["_fecha"] = pd.to_datetime(df[col_fecha], errors="coerce")
            df_rango = df[(df["_fecha"] >= pd.Timestamp(p_ini)) & (df["_fecha"] <= pd.Timestamp(p_fin))]
            return int(df_rango["SESIONES"].sum()) if not df_rango.empty else 0

        try:
            kal_venta = _ventas_d2c_marca(f_ini, f_fin, "Kaltemp")
            kal_venta_yoy = _ventas_d2c_marca(yoy_ini, yoy_fin, "Kaltemp")
            tp_venta = _ventas_d2c_marca(f_ini, f_fin, "Tom Palmer")
            tp_venta_yoy = _ventas_d2c_marca(yoy_ini, yoy_fin, "Tom Palmer")

            kal_sesiones = _sesiones_ga4(f_ini, f_fin, "ga4_metricas")
            kal_sesiones_yoy = _sesiones_ga4(yoy_ini, yoy_fin, "ga4_metricas")
            tp_sesiones = _sesiones_ga4(f_ini, f_fin, "ga4_metricas_tompalmer")
            tp_sesiones_yoy = _sesiones_ga4(yoy_ini, yoy_fin, "ga4_metricas_tompalmer")

            resultado["d2c_kaltemp"] = {
                "disponible": kal_sesiones is not None,
                "totalD2CSales": kal_venta,
                "totalD2CSalesYoy": kal_venta_yoy,
                "totalSessions": kal_sesiones or 0,
                "totalSessionsYoy": kal_sesiones_yoy or 0,
            }
            resultado["d2c_tompalmer"] = {
                "disponible": tp_sesiones is not None,
                "totalD2CSales": tp_venta,
                "totalD2CSalesYoy": tp_venta_yoy,
                "totalSessions": tp_sesiones or 0,
                "totalSessionsYoy": tp_sesiones_yoy or 0,
            }
        except Exception as e:
            logger.error(f"Error en D2C: {e}")
            resultado["d2c_kaltemp"] = {"disponible": False, "totalD2CSales": 0, "totalD2CSalesYoy": 0, "totalSessions": 0, "totalSessionsYoy": 0}
            resultado["d2c_tompalmer"] = {"disponible": False, "totalD2CSales": 0, "totalD2CSalesYoy": 0, "totalSessions": 0, "totalSessionsYoy": 0}
            kal_venta = tp_venta = 0.0

        try:
            df_meta = con.execute("SELECT * FROM mkt_inversion_meta").df() if "mkt_inversion_meta" in tables else pd.DataFrame()
            df_google = con.execute("SELECT * FROM mkt_inversion_google").df() if "mkt_inversion_google" in tables else pd.DataFrame()
            df_mkt = pd.concat([df_meta, df_google], ignore_index=True) if not (df_meta.empty and df_google.empty) else pd.DataFrame()

            if df_mkt.empty:
                resultado["marketing"] = {"disponible": False}
            else:
                col_gasto = _buscar_columna_fuzzy(df_mkt, ["gasto", "spend", "inversion", "cost"])
                col_imp = _buscar_columna_fuzzy(df_mkt, ["impresi", "impressi"])
                col_clics = _buscar_columna_fuzzy(df_mkt, ["clic", "click"])
                col_fi = _buscar_columna_fuzzy(df_mkt, ["fecha inicio", "fechainicio", "since", "start"])
                col_marca = _buscar_columna_fuzzy(df_mkt, ["marca", "brand"])

                df_mkt["_gasto"] = df_mkt[col_gasto].apply(_limpiar_numero) if col_gasto else 0.0
                df_mkt["_imp"] = df_mkt[col_imp].apply(_limpiar_numero) if col_imp else 0.0
                df_mkt["_clics"] = df_mkt[col_clics].apply(_limpiar_numero) if col_clics else 0.0
                df_mkt["_marca"] = df_mkt[col_marca].fillna("Kaltemp") if col_marca else "Kaltemp"
                df_mkt.loc[df_mkt["_marca"].astype(str).str.strip() == "", "_marca"] = "Kaltemp"

                def _rango_mkt(df, p_ini, p_fin):
                    if not col_fi:
                        return df  # sin columna de fecha -- no se puede acotar, se usa histórico completo
                    fechas = pd.to_datetime(df[col_fi], errors="coerce")
                    return df[(fechas >= pd.Timestamp(p_ini)) & (fechas <= pd.Timestamp(p_fin))]

                df_cy = _rango_mkt(df_mkt, f_ini, f_fin)
                df_yoy = _rango_mkt(df_mkt, yoy_ini, yoy_fin)

                inv_total = float(df_cy["_gasto"].sum())
                inv_total_yoy = float(df_yoy["_gasto"].sum())
                imp_total = float(df_cy["_imp"].sum())
                imp_total_yoy = float(df_yoy["_imp"].sum())
                clics_total = float(df_cy["_clics"].sum())
                clics_total_yoy = float(df_yoy["_clics"].sum())

                ctr = _safe_div(clics_total, imp_total) * 100
                ctr_yoy = _safe_div(clics_total_yoy, imp_total_yoy) * 100

                inv_kal = float(df_cy[df_cy["_marca"].astype(str).str.upper() == "KALTEMP"]["_gasto"].sum())
                inv_tp = float(df_cy[df_cy["_marca"].astype(str).str.upper().str.contains("TOM")]["_gasto"].sum())
                # Si la columna Marca no distingue (todo cayó en Kaltemp por default),
                # no hay forma real de separar el gasto -- se deja tal cual en vez de inventar un split.

                venta_total_periodo = actual["venta"] or 1.0

                resultado["marketing"] = {
                    "disponible": True,
                    "inversion": inv_total,
                    "inversion_yoy": inv_total_yoy,
                    "var_inversion_yoy": round(_pct_var(inv_total, inv_total_yoy), 1),
                    "impresiones": imp_total,
                    "var_impresiones_yoy": round(_pct_var(imp_total, imp_total_yoy), 1),
                    "ctr": round(ctr, 2),
                    "var_ctr_yoy": round(_pct_var(ctr, ctr_yoy), 1),
                    "tacos_global": round(_safe_div(inv_total, venta_total_periodo) * 100, 2),
                    "kaltemp": {
                        "inversion": inv_kal,
                        "venta": kal_venta,
                        "tacos": round(_safe_div(inv_kal, kal_venta) * 100, 1),
                    },
                    "tom_palmer": {
                        "inversion": inv_tp,
                        "venta": tp_venta,
                        "tacos": round(_safe_div(inv_tp, tp_venta) * 100, 1),
                    }
                }
        except Exception as e:
            logger.error(f"Error en marketing: {e}")
            resultado["marketing"] = {"disponible": False}

        # ================================================================
        # H. TEMPERATURA SANTIAGO
        # REESCRITO: tabla real `temperaturas` (FECHA, TEMP_MAX, TEMP_MIN),
        # mismo origen que ya usa temperatura_ventas.py -- ya no se inventa
        # ninguna cifra con una fórmula pseudo-aleatoria.
        # ================================================================
        try:
            if "temperaturas" not in tables:
                raise RuntimeError("tabla temperaturas no existe todavía")

            def _get_yoy_date(d):
                try:
                    return d.replace(year=d.year - 1)
                except ValueError:
                    return d.replace(year=d.year - 1, day=28)

            venta_rows = con.execute("""
                SELECT CAST(FECHA_OBJ AS DATE) AS fecha, SUM(BRUTO_TOTAL) AS venta
                FROM ventas
                WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                GROUP BY fecha ORDER BY fecha
            """, [f_ini, f_fin]).fetchall()

            temp_ini_yoy, temp_fin_yoy = _get_yoy_date(f_ini), _get_yoy_date(f_fin)

            clima_act = {
                r[0].isoformat(): {"max": float(r[1] or 0), "min": float(r[2] or 0)}
                for r in con.execute(
                    "SELECT CAST(FECHA AS DATE), TEMP_MAX, TEMP_MIN FROM temperaturas WHERE CAST(FECHA AS DATE) BETWEEN ? AND ?",
                    [f_ini, f_fin]
                ).fetchall() if r[0] is not None
            }
            clima_yoy = {
                r[0].isoformat(): {"max": float(r[1] or 0), "min": float(r[2] or 0)}
                for r in con.execute(
                    "SELECT CAST(FECHA AS DATE), TEMP_MAX, TEMP_MIN FROM temperaturas WHERE CAST(FECHA AS DATE) BETWEEN ? AND ?",
                    [temp_ini_yoy, temp_fin_yoy]
                ).fetchall() if r[0] is not None
            }

            temperatura_list = []
            for fecha, venta in venta_rows:
                f_str = fecha.isoformat()
                f_yoy_str = _get_yoy_date(fecha).isoformat()
                c_act = clima_act.get(f_str, {})
                c_yoy = clima_yoy.get(f_yoy_str, {})
                temperatura_list.append({
                    "fechaDisp": fecha.strftime("%d-%m"),
                    "brutoTotal": round(float(venta or 0), 0),
                    "tempMax": round(c_act.get("max", 0.0), 1),
                    "tempMaxYoY": round(c_yoy.get("max", 0.0), 1),
                    "tempMin": round(c_act.get("min", 0.0), 1),
                    "tempMinYoY": round(c_yoy.get("min", 0.0), 1),
                })
            resultado["temperatura"] = temperatura_list
        except Exception as e:
            logger.error(f"Error en temperatura: {e}")
            resultado["temperatura"] = []

        # ================================================================
        # I. PENDIENTES, LEADS Y CARROS  (pendientes y leads sin cambios;
        # carros_abandonados pierde el fallback de productos inventados)
        # ================================================================
        try:
            p_row = con.execute("SELECT COUNT(*), COALESCE(SUM(MONTO_DOCUMENTO), 0) FROM pendientes_despacho_docs").fetchone()
            top_vends = con.execute("SELECT VENDEDOR, COALESCE(SUM(MONTO_DOCUMENTO), 0) as m FROM pendientes_despacho_docs GROUP BY 1 ORDER BY m DESC LIMIT 3").fetchall()
            resultado["pendientes_despacho"] = {
                "documentos_pendientes": int(p_row[0] or 0),
                "monto_total": float(p_row[1] or 0),
                "top_vendedores": [{"vendedor": str(v[0] or "Vendedor"), "monto": float(v[1] or 0)} for v in top_vends]
            }
        except Exception:
            resultado["pendientes_despacho"] = {"documentos_pendientes": 0, "monto_total": 0, "top_vendedores": []}

        try:
            leads_cols_info = con.execute("PRAGMA table_info('leads')").fetchall()
            leads_cols = {c[1].upper() for c in leads_cols_info}

            vend_col = "VENDEDOR" if "VENDEDOR" in leads_cols else ("EJECUTIVO" if "EJECUTIVO" in leads_cols else ("AGENTE" if "AGENTE" in leads_cols else None))
            prod_col = "PRODUCTO" if "PRODUCTO" in leads_cols else ("PRODUCTO_INTERES" if "PRODUCTO_INTERES" in leads_cols else ("INTERES" if "INTERES" in leads_cols else ("SKU" if "SKU" in leads_cols else ("DESCRIPCION" if "DESCRIPCION" in leads_cols else None))))

            l_act = con.execute("SELECT COUNT(*), SUM(CASE WHEN UPPER(COALESCE(ESTADO, '')) IN ('CON_VENTA', 'GANADO', 'CERRADO_GANADO', 'VENDIDO') THEN 1 ELSE 0 END) FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?", [f_ini, f_fin]).fetchone()
            l_yoy = con.execute("SELECT COUNT(*) FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?", [yoy_ini, yoy_fin]).fetchone()
            tot_l, conv_l = int(l_act[0] or 0), int(l_act[1] or 0)
            tot_yoy = int(l_yoy[0] or 0)
            var_l = ((tot_l - tot_yoy) / tot_yoy * 100) if tot_yoy > 0 else (100.0 if tot_l > 0 else 0.0)

            top_vendedor = None
            if vend_col:
                v_q = f"""
                    WITH act AS (
                        SELECT COALESCE(NULLIF(TRIM({vend_col}), ''), 'Sin Asignar') as nombre, COUNT(*) as cant
                        FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                        GROUP BY 1
                    ),
                    prev AS (
                        SELECT COALESCE(NULLIF(TRIM({vend_col}), ''), 'Sin Asignar') as nombre, COUNT(*) as cant_yoy
                        FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                        GROUP BY 1
                    )
                    SELECT a.nombre, a.cant, COALESCE(p.cant_yoy, 0) as cant_yoy
                    FROM act a LEFT JOIN prev p ON a.nombre = p.nombre
                    ORDER BY a.cant DESC LIMIT 1
                """
                v_row = con.execute(v_q, [f_ini, f_fin, yoy_ini, yoy_fin]).fetchone()
                if v_row:
                    c_act, c_yoy = int(v_row[1] or 0), int(v_row[2] or 0)
                    v_pct = ((c_act - c_yoy) / c_yoy * 100) if c_yoy > 0 else (100.0 if c_act > 0 else 0.0)
                    top_vendedor = {
                        "nombre": str(v_row[0]),
                        "cant": c_act,
                        "cant_yoy": c_yoy,
                        "var_pct_yoy": round(v_pct, 1)
                    }

            top_producto = None
            if prod_col:
                p_q = f"""
                    WITH act AS (
                        SELECT COALESCE(NULLIF(TRIM({prod_col}), ''), 'Sin Especificar') as nombre, COUNT(*) as cant
                        FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                        GROUP BY 1
                    ),
                    prev AS (
                        SELECT COALESCE(NULLIF(TRIM({prod_col}), ''), 'Sin Especificar') as nombre, COUNT(*) as cant_yoy
                        FROM leads WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                        GROUP BY 1
                    )
                    SELECT a.nombre, a.cant, COALESCE(p.cant_yoy, 0) as cant_yoy
                    FROM act a LEFT JOIN prev p ON a.nombre = p.nombre
                    ORDER BY a.cant DESC LIMIT 1
                """
                p_row2 = con.execute(p_q, [f_ini, f_fin, yoy_ini, yoy_fin]).fetchone()
                if p_row2:
                    c_act, c_yoy = int(p_row2[1] or 0), int(p_row2[2] or 0)
                    p_pct = ((c_act - c_yoy) / c_yoy * 100) if c_yoy > 0 else (100.0 if c_act > 0 else 0.0)
                    top_producto = {
                        "nombre": str(p_row2[0]),
                        "cant": c_act,
                        "cant_yoy": c_yoy,
                        "var_pct_yoy": round(p_pct, 1)
                    }

            resultado["leads"] = {
                "leads_actual": tot_l,
                "leads_yoy": tot_yoy,
                "leads_var_pct_yoy": round(var_l, 1),
                "convertidos": conv_l,
                "tasaConversion": round((conv_l / tot_l * 100) if tot_l else 0.0, 1),
                "top_vendedor": top_vendedor,
                "top_producto": top_producto
            }
        except Exception as e:
            logger.error(f"Error en leads: {e}")
            resultado["leads"] = {
                "leads_actual": 0, "leads_yoy": 0, "leads_var_pct_yoy": 0, "convertidos": 0, "tasaConversion": 0,
                "top_vendedor": None, "top_producto": None
            }

        # CARRITOS ABANDONADOS -- ya no inventa productos si no hay top real
        try:
            c_row = con.execute("""
                SELECT
                    COUNT(DISTINCT ID_CHECKOUT),
                    COALESCE(SUM(TRY_CAST(TOTAL_PRICE AS DOUBLE)), 0)
                FROM abandoned_checkouts
                WHERE UPPER(COALESCE(ESTADO, 'ABANDONADO')) = 'ABANDONADO'
                  AND CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
            """, [f_ini, f_fin]).fetchone()

            tot_carritos = int(c_row[0] or 0) if c_row else 0
            monto_perdido = float(c_row[1] or 0) if c_row else 0.0

            ac_cols_info = con.execute("PRAGMA table_info('abandoned_checkouts')").fetchall()
            ac_cols = {c[1].upper() for c in ac_cols_info}

            prod_col_ac = None
            for cand in ['LINE_ITEMS_TITLE', 'LINE_ITEMS_NAME', 'TITLE', 'PRODUCTO', 'NAME', 'DESCRIPCION', 'SKU', 'LINE_ITEM']:
                if cand in ac_cols:
                    prod_col_ac = cand
                    break

            price_col_ac = None
            for cand in ['PRICE', 'LINE_ITEMS_PRICE', 'TOTAL_PRICE', 'PRECIO', 'SUBTOTAL_PRICE']:
                if cand in ac_cols:
                    price_col_ac = cand
                    break

            top3_ac_prods = []
            if prod_col_ac:
                price_expr = f"COALESCE(AVG(TRY_CAST({price_col_ac} AS DOUBLE)), 0)" if price_col_ac else "0"
                ac_top_query = f"""
                    SELECT
                        COALESCE(NULLIF(TRIM({prod_col_ac}), ''), 'Producto sin nombre') as nombre,
                        COUNT(*) as cant,
                        {price_expr} as precio
                    FROM abandoned_checkouts
                    WHERE UPPER(COALESCE(ESTADO, 'ABANDONADO')) = 'ABANDONADO'
                      AND CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
                    GROUP BY 1
                    ORDER BY cant DESC
                    LIMIT 3
                """
                ac_top_rows = con.execute(ac_top_query, [f_ini, f_fin]).fetchall()
                for idx, r in enumerate(ac_top_rows):
                    top3_ac_prods.append({
                        "rank": idx + 1,
                        "nombre": str(r[0]),
                        "cant": int(r[1] or 0),
                        "precio": float(r[2] or 0)
                    })
            # Sin fallback inventado: si no hay productos reales, top3_ac_prods
            # queda como lista vacía -- el frontend ya muestra "Sin datos".

            resultado["carros_abandonados"] = {
                "totalCarritos": tot_carritos,
                "oportunidadPerdida": monto_perdido,
                "top_productos": top3_ac_prods
            }
        except Exception as e:
            logger.error(f"Error en carros abandonados: {e}")
            resultado["carros_abandonados"] = {"totalCarritos": 0, "oportunidadPerdida": 0, "top_productos": []}

    _CACHE_RESUMEN[cache_key] = (ahora + _CACHE_TTL_SECS, resultado)
    return resultado