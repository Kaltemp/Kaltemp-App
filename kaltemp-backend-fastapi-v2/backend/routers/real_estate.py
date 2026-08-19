import duckdb
from fastapi import APIRouter, Query
from typing import Optional
import os
import pandas as pd

router = APIRouter(prefix="/api", tags=["real_estate"])

_AQUI = os.path.dirname(os.path.abspath(__file__))
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    os.path.abspath(os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
)

# Filtro de canal reutilizado por TODOS los endpoints de este archivo (el
# principal /api/real-estate y los dos nuevos del acordeón de Tabla 1) --
# antes vivía duplicado inline, ahora centralizado.
#
# Maximiliano Díaz (18-ago-2026, cambio de vendedor reportado por William):
# es de Inmobiliarias DESDE ene-2026 -- se mantiene en el WHERE para traer
# su historial completo por SQL, y se recorta a "desde 2026" en pandas más
# abajo (_excluir_ventas_max_diaz_antes_2026), porque hasta dic-2025 era de
# Distribuidores (ver distributors.py) y esas ventas ya se cuentan allá.
_WHERE_CANAL_INMOBILIARIAS = """
    UPPER(CANAL) LIKE '%INMOBILIARIA%'
       OR UPPER(VENDEDOR) LIKE '%INMOBILIARIA%'
       OR UPPER(VENDEDOR) IN ('MAXIMILIANO DIAZ', 'LUIS BAEZA', 'RAFAEL ESCOBAR')
"""

# Fecha de corte del traspaso de Maximiliano Díaz de Distribuidores a
# Inmobiliarias (18-ago-2026). Sus ventas HASTA esta fecha son historial de
# Distribuidores; DESDE el día siguiente son de Inmobiliarias.
_FECHA_CORTE_TRASPASO_MAX_DIAZ = pd.Timestamp("2025-12-31")


def _excluir_ventas_max_diaz_antes_2026(df: pd.DataFrame) -> pd.DataFrame:
    """
    Inmobiliarias: el WHERE de arriba trae TODAS las ventas de Maximiliano
    Díaz (sin filtro de fecha en SQL, para no depender del tipo/formato de
    FECHA_OBJ en la tabla origen). Acá se descartan en pandas -- con el
    mismo parseo robusto que usa el resto del archivo -- las que son HASTA
    2025, porque esas ya son historial de Distribuidores.
    """
    if df.empty or "VENDEDOR" not in df.columns:
        return df
    fechas = pd.to_datetime(df["FECHA_OBJ"], errors="coerce")
    es_max_diaz = df["VENDEDOR"].astype(str).str.strip().str.upper() == "MAXIMILIANO DIAZ"
    excluir = es_max_diaz & (fechas <= _FECHA_CORTE_TRASPASO_MAX_DIAZ)
    return df[~excluir].copy()


# Cuántos períodos históricos se calculan (CY, YoY-1, YoY-2, YoY-3) -- a
# pedido de William (18-ago-2026) para "potenciar" Tabla 1 y Tabla 2 con
# 4 años de comparativo en vez de solo CY vs YoY-1.
N_PERIODOS = 4

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


def _multi_year_split(df_inm: pd.DataFrame, fecha_inicio, fecha_fin, n_periodos: int = N_PERIODOS):
    """
    Generaliza el comparativo YoY a n_periodos: devuelve una lista de
    DataFrames [CY, YoY-1, YoY-2, YoY-3, ...], cada uno con el mismo rango
    de días/mes que pidió el filtro (fecha_inicio/fecha_fin, o el histórico
    completo si vienen vacíos), desplazado i años hacia atrás.

    Usado por Tabla 1 (Categoría/Producto/Proyecto, con Cantidad) y Tabla 2
    (Ranking de Proyectos, solo Venta) -- ambas ahora piden 4 años de
    comparativo (18-ago-2026, a pedido de William).

    Devuelve (lista_de_dataframes, anio_base) -- anio_base es el año
    calendario del período CY (índice 0), para que el frontend pueda
    rotular las columnas con el año real (2026, 2025, 2024...) en vez de
    siglas genéricas tipo "YOY"/"2YOY" (18-ago-2026, 2da vuelta, a pedido
    de William: "el usuario debe entender de manera rápida lo que ve").
    """
    df_inm = df_inm.copy()
    df_inm["FECHA_OBJ"] = pd.to_datetime(df_inm["FECHA_OBJ"], errors="coerce")
    df_inm = df_inm.dropna(subset=["FECHA_OBJ"])
    df_inm["FECHA_CORTE"] = df_inm["FECHA_OBJ"].dt.date

    if df_inm.empty:
        return [df_inm.copy() for _ in range(n_periodos)], None

    min_date = df_inm["FECHA_CORTE"].min()
    max_date = df_inm["FECHA_CORTE"].max()

    f_in = parse_date_safe(fecha_inicio, min_date)
    f_fi = parse_date_safe(fecha_fin, max_date)

    resultados = []
    for i in range(n_periodos):
        try:
            f_in_i = f_in.replace(year=f_in.year - i)
            f_fi_i = f_fi.replace(year=f_fi.year - i)
            df_i = df_inm[(df_inm["FECHA_CORTE"] >= f_in_i) & (df_inm["FECHA_CORTE"] <= f_fi_i)]
        except Exception:
            # p.ej. 29-feb en un rango que cae en año no bisiesto
            df_i = df_inm.iloc[0:0]
        resultados.append(df_i)
    return resultados, f_in.year


def _cy_yoy_split(df_inm: pd.DataFrame, fecha_inicio, fecha_fin):
    """Caso particular de _multi_year_split con 2 períodos (CY, YoY-1) --
    se mantiene para el KPI principal y el gráfico mensual, que no
    necesitan más historia que la comparación año actual vs año anterior."""
    dfs, _anio_base = _multi_year_split(df_inm, fecha_inicio, fecha_fin, 2)
    df_cy, df_yoy = dfs
    return df_cy, df_yoy


def _agregar_multi_periodo(dfs, columna: str, agg_cols: dict):
    """
    Agrupa cada DataFrame de `dfs` (lista ordenada [CY, YoY-1, YoY-2, ...])
    por `columna`, sumando `agg_cols` (dict nombre_columna -> 'sum'), y
    devuelve un único DataFrame indexado por `columna` con sufijos
    _0, _1, _2... por cada período (0 = CY). Valores/períodos sin datos
    quedan en 0 en vez de romper el merge.
    """
    grupos = []
    todas_claves = set()
    for df in dfs:
        if df.empty:
            grupos.append(pd.DataFrame(columns=[columna, *agg_cols.keys()]))
            continue
        gp = df.groupby(columna).agg(agg_cols).reset_index()
        grupos.append(gp)
        todas_claves.update(gp[columna].tolist())

    if not todas_claves:
        return pd.DataFrame(columns=[columna])

    out = pd.DataFrame({columna: list(todas_claves)})
    for i, gp in enumerate(grupos):
        gp_r = gp.rename(columns={c: f"{c}_{i}" for c in agg_cols.keys()})
        out = pd.merge(out, gp_r, on=columna, how="left")
    return out.fillna(0)


def _ranking_multi_anio(dfs, columna: str, key_out: str, incluir_cantidad: bool = True):
    """
    Igual que el histórico _ranking_por_columna, pero con hasta N_PERIODOS
    períodos (CY, YoY-1, YoY-2, YoY-3). Devuelve venta/ventaYoy/venta2Yoy/
    venta3Yoy (y cantidad equivalentes si incluir_cantidad=True), ordenado
    por venta CY desc. VAR% se mantiene con el mismo criterio de siempre:
    CY vs YoY-1 (no contra 2 o 3 años atrás).
    """
    # OJO: antes se cortaba acá si el año actual (CY) no tenía filas, aunque
    # los años anteriores sí tuvieran ventas -- un producto/proyecto sin
    # venta este año pero con historial desaparecía por completo del
    # acordeón (bug reportado por William, 18-ago-2026: "si no hay venta
    # del año actual no salen datos"). Ahora solo corta si TODOS los
    # períodos están vacíos.
    if not dfs or all(d.empty for d in dfs):
        return []

    agg_cols = {"BRUTO_TOTAL": "sum"}
    if incluir_cantidad and "CANTIDAD" in dfs[0].columns:
        agg_cols["CANTIDAD"] = "sum"

    m = _agregar_multi_periodo(dfs, columna, agg_cols)
    if m.empty:
        return []

    n = len(dfs)
    # Orden: venta CY desc primero (igual que siempre); como criterio
    # secundario, la suma de venta en todos los períodos -- así las filas
    # con venta 0 en el año actual pero historial en años anteriores no
    # quedan con un orden arbitrario, sino agrupadas por relevancia histórica.
    venta_cols = [f"BRUTO_TOTAL_{i}" for i in range(n)]
    m["_total_historico"] = m[venta_cols].sum(axis=1)
    m = m.sort_values(by=["BRUTO_TOTAL_0", "_total_historico"], ascending=False)

    tiene_cantidad = "CANTIDAD" in agg_cols

    filas = []
    for _, r in m.iterrows():
        ventas = [float(r.get(f"BRUTO_TOTAL_{i}", 0.0)) for i in range(n)]
        v_cy = ventas[0]
        v_yy = ventas[1] if n > 1 else 0.0
        v_var = round(((v_cy - v_yy) / v_yy * 100), 1) if v_yy > 0 else (100.0 if v_cy > 0 else 0.0)

        nombre = str(r[columna]).strip()
        if columna == "CLIENTE":
            nombre = nombre.title()

        fila = {
            key_out: nombre,
            "name": nombre,
            "venta": v_cy,
            "value": v_cy,
            "ventaYoy": v_yy,
            "venta2Yoy": ventas[2] if n > 2 else 0.0,
            "venta3Yoy": ventas[3] if n > 3 else 0.0,
            "variacion": v_var,
        }
        if tiene_cantidad:
            cantidades = [float(r.get(f"CANTIDAD_{i}", 0.0)) for i in range(n)]
            fila.update({
                "cantidad": cantidades[0],
                "cantidadYoy": cantidades[1] if n > 1 else 0.0,
                "cantidad2Yoy": cantidades[2] if n > 2 else 0.0,
                "cantidad3Yoy": cantidades[3] if n > 3 else 0.0,
            })
        filas.append(fila)
    return filas


@router.get("/real-estate")
@router.get("/inmobiliaria")
def get_real_estate(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """
    Devuelve los Indicadores B2B de INMOBILIARIAS exclusivamente.
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
                    "totalProyectos": 0,
                    "ticketPromedio": 0.0,
                    "rankingProyectos": [],
                    "distribucionCategoria": [],
                    "tendenciaMensual": [],
                    "aniosPeriodos": []
                }

            if "ventas" not in tables:
                return response_vacia()

            # Filtrar EXCLUSIVAMENTE el canal y vendedores de INMOBILIARIAS
            query = f"""
                SELECT
                    DOCUMENTO, PRODUCTO, SKU_BSALE, CANTIDAD,
                    NETO_TOTAL, BRUTO_TOTAL, CONTRIBUCION, CANAL,
                    VENDEDOR, CLIENTE, CATEGORIA, FECHA_OBJ
                FROM ventas
                WHERE {_WHERE_CANAL_INMOBILIARIAS}
            """
            df_inm = conn.execute(query).df()
        finally:
            conn.close()

        df_inm = _excluir_ventas_max_diaz_antes_2026(df_inm)

        if df_inm.empty:
            return response_vacia()

        # Un solo split de 4 períodos: [CY, YoY-1, YoY-2, YoY-3]. df_cy/df_yoy
        # (índices 0/1) alimentan el KPI principal y el gráfico mensual
        # (que siguen siendo solo CY vs YoY-1); la lista completa alimenta
        # Tabla 1 y Tabla 2, que ahora piden 4 años de comparativo.
        dfs4, anio_base = _multi_year_split(df_inm, fecha_inicio, fecha_fin, N_PERIODOS)
        df_cy, df_yoy = dfs4[0], dfs4[1]

        # Año calendario real de cada período -- el frontend rotula las
        # columnas con esto en vez de siglas ("YOY", "2YOY"), a pedido de
        # William (18-ago-2026, 2da vuelta).
        anios_periodos = [anio_base - i for i in range(N_PERIODOS)] if anio_base is not None else []

        total_ventas = float(df_cy["BRUTO_TOTAL"].sum()) if not df_cy.empty else 0.0
        venta_yoy = float(df_yoy["BRUTO_TOTAL"].sum()) if not df_yoy.empty else 0.0
        var_yoy = round(((total_ventas - venta_yoy) / venta_yoy * 100), 1) if venta_yoy > 0 else (100.0 if total_ventas > 0 else 0.0)

        total_proyectos = int(df_cy["CLIENTE"].nunique()) if not df_cy.empty else 0
        total_txs = int(df_cy["DOCUMENTO"].nunique()) if not df_cy.empty else 0
        tkp = float(total_ventas / total_txs) if total_txs > 0 else 0.0

        # Tabla 2: ranking de proyectos/clientes con 4 períodos de VENTA (sin
        # cantidad, a pedido explícito de William -- "solo para las ventas
        # en montos").
        ranking_proyectos = _ranking_multi_anio(dfs4, "CLIENTE", "cliente", incluir_cantidad=False)
        if ranking_proyectos:
            ranking_proyectos = ranking_proyectos[:15]

            # Categoría dominante por proyecto/cliente (la de mayor venta) --
            # mismo fix aplicado en distributors.py (05-ago-2026).
            categoria_por_cliente = {}
            if "CATEGORIA" in df_cy.columns:
                gp_cli_cat = df_cy.groupby(["CLIENTE", "CATEGORIA"])["BRUTO_TOTAL"].sum().reset_index()
                idx_top_cat = gp_cli_cat.groupby("CLIENTE")["BRUTO_TOTAL"].idxmax()
                for _, row in gp_cli_cat.loc[idx_top_cat].iterrows():
                    categoria_por_cliente[str(row["CLIENTE"]).strip().title()] = str(row["CATEGORIA"]).strip()

            for fila in ranking_proyectos:
                fila["proyecto"] = fila["cliente"]
                fila["categoria"] = categoria_por_cliente.get(fila["cliente"], "Sin Categoría Mapeada")

        # Tabla 1 (nivel 1 - Categoría): 4 períodos de VENTA y CANTIDAD.
        distribucion_categoria = _ranking_multi_anio(dfs4, "CATEGORIA", "categoria", incluir_cantidad=True)
        distribucion_categoria = [c for c in distribucion_categoria if c["categoria"] and c["categoria"] != "nan"]

        meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        df_cy_mes = df_cy.copy()
        df_yoy_mes = df_yoy.copy()
        if not df_cy_mes.empty:
            df_cy_mes["MES_NUM"] = pd.to_datetime(df_cy_mes["FECHA_OBJ"]).dt.month
        if not df_yoy_mes.empty:
            df_yoy_mes["MES_NUM"] = pd.to_datetime(df_yoy_mes["FECHA_OBJ"]).dt.month
        m_cy = df_cy_mes.groupby("MES_NUM")["BRUTO_TOTAL"].sum().to_dict() if not df_cy_mes.empty else {}
        m_yy = df_yoy_mes.groupby("MES_NUM")["BRUTO_TOTAL"].sum().to_dict() if not df_yoy_mes.empty else {}

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
            "totalProyectos": total_proyectos,
            "ticketPromedio": tkp,
            "rankingProyectos": ranking_proyectos,
            "distribucionCategoria": distribucion_categoria,
            "tendenciaMensual": tendencia_mensual,
            "aniosPeriodos": anios_periodos
        }
    except Exception as e:
        print(f"❌ ERROR en /api/real-estate: {e}")
        return response_vacia()


# ============================================================
# ACORDEÓN TABLA 1 (18-ago-2026, a pedido de William): Categoría -> Producto
# -> Proyecto/Cliente. La categoría (nivel 1) ya se arma arriba en
# distribucionCategoria; estos 2 endpoints son los niveles 2 y 3, cargados
# en lazy-load solo cuando el usuario despliega una fila, igual que el
# árbol de sku.py y el mismo patrón aplicado en distributors.py. Desde el
# 18-ago-2026 (2da vuelta) traen 4 períodos (CY, YoY-1, YoY-2, YoY-3) de
# Venta y Cantidad.
# ============================================================

@router.get("/real-estate/productos-por-categoria")
def get_real_estate_productos_por_categoria(
    categoria: str = Query(...),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """Nivel 2 del acordeón: productos dentro de una categoría de Inmobiliarias."""
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if "ventas" not in tables:
                return []

            query = f"""
                SELECT DOCUMENTO, PRODUCTO, CLIENTE, CATEGORIA, CANTIDAD, BRUTO_TOTAL, FECHA_OBJ, VENDEDOR
                FROM ventas
                WHERE ({_WHERE_CANAL_INMOBILIARIAS})
                  AND CATEGORIA = ?
            """
            df_inm = conn.execute(query, [categoria]).df()
        finally:
            conn.close()

        df_inm = _excluir_ventas_max_diaz_antes_2026(df_inm)

        if df_inm.empty:
            return []

        dfs, _anio_base = _multi_year_split(df_inm, fecha_inicio, fecha_fin, N_PERIODOS)
        return _ranking_multi_anio(dfs, "PRODUCTO", "producto", incluir_cantidad=True)
    except Exception as e:
        print(f"❌ ERROR en /api/real-estate/productos-por-categoria: {e}")
        return []


@router.get("/real-estate/clientes-por-producto")
def get_real_estate_clientes_por_producto(
    producto: str = Query(...),
    categoria: str = Query(...),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    """Nivel 3 del acordeón: proyectos/clientes que compraron un producto dentro de una categoría."""
    try:
        conn = get_db_connection()
        try:
            tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
            if "ventas" not in tables:
                return []

            query = f"""
                SELECT DOCUMENTO, PRODUCTO, CLIENTE, CATEGORIA, CANTIDAD, BRUTO_TOTAL, FECHA_OBJ, VENDEDOR
                FROM ventas
                WHERE ({_WHERE_CANAL_INMOBILIARIAS})
                  AND CATEGORIA = ? AND PRODUCTO = ?
            """
            df_inm = conn.execute(query, [categoria, producto]).df()
        finally:
            conn.close()

        df_inm = _excluir_ventas_max_diaz_antes_2026(df_inm)

        if df_inm.empty:
            return []

        dfs, _anio_base = _multi_year_split(df_inm, fecha_inicio, fecha_fin, N_PERIODOS)
        return _ranking_multi_anio(dfs, "CLIENTE", "cliente", incluir_cantidad=True)
    except Exception as e:
        print(f"❌ ERROR en /api/real-estate/clientes-por-producto: {e}")
        return []