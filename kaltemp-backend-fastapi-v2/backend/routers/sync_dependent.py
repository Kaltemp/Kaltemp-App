# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\sync_dependent.py
# (respaldar antes: Copy-Item sync_dependent.py sync_dependent.py.bak)
"""
Módulos que dependen de tablas pobladas por sync_bsale_operativo.py:
  - stock_bsale            (Stock por bodega)
  - pendientes_despacho    (Pendientes por Despachar)
  - notas_credito_desfase  (Notas de Crédito)

En el snapshot de kaltemp_matrix.duckdb que compartiste, NINGUNA de estas
3 tablas existe todavía (confirmado leyendo el catálogo del archivo). Este
router replica el patrón defensivo de `leer_tabla_sync()` en app.py: en vez
de asumir que la tabla existe (y fallar feo, o peor, devolver datos
inventados), primero consulta information_schema y devuelve un estado
explícito que el frontend puede mostrar como "módulo pendiente de sync".

Apenas corras el script de sync correspondiente en el servidor, estos
mismos endpoints empiezan a devolver datos reales sin tocar una línea.
"""
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Query
from db import get_connection

router = APIRouter(prefix="/api", tags=["sync-tables"])


def _tabla_existe(con, nombre_tabla: str) -> bool:
    fila = con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [nombre_tabla]
    ).fetchone()
    return fila is not None


def _ultima_actualizacion(con, nombre_tabla: str):
    if not _tabla_existe(con, "sync_meta"):
        return None
    fila = con.execute(
        "SELECT ultima_actualizacion FROM sync_meta WHERE tabla = ?", [nombre_tabla]
    ).fetchone()
    return fila[0].isoformat() if fila and fila[0] else None


# ------------------------------------------------------------------
# STOCK — tabla `stock_bsale` (columnas esperadas: SKU, PRODUCTO, BODEGA,
# DISPONIBLE). El pivot bodega->columna y el cálculo de días de cobertura
# se hacen igual que en app.py, cruzando con `ventas` de los últimos 14 días.
# ------------------------------------------------------------------
@router.get("/stock")
def get_stock():
    with get_connection() as con:
        if not _tabla_existe(con, "stock_bsale"):
            return {
                "disponible": False,
                "mensaje": (
                    "La tabla 'stock_bsale' aún no existe en kaltemp_matrix.duckdb. "
                    "Corre el script de sync que la puebla desde Bsale (BSALE_TOKEN) "
                    "antes de conectar este módulo."
                ),
                "items": [],
            }

        dias_venta = 14
        f_fin = date.today()
        f_ini = f_fin - timedelta(days=dias_venta)

        df_stock = con.execute("""
            SELECT SKU, PRODUCTO, BODEGA, SUM(DISPONIBLE) AS DISPONIBLE
            FROM stock_bsale
            WHERE UPPER(BODEGA) NOT IN ('ÑUÑOA', 'CONCEPCION SOLARSUR', 'CONCEPCIÓN SOLARSUR')
            GROUP BY SKU, PRODUCTO, BODEGA
        """).fetchall()

        ventas_recientes = dict(con.execute("""
            SELECT SKU_BSALE, SUM(CANTIDAD)
            FROM ventas
            WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
              AND ORIGEN != 'FALABELLA_API'
            GROUP BY SKU_BSALE
        """, [f_ini, f_fin]).fetchall())

        # stock_bsale no trae categoría ni costo unitario -- se cruza por SKU
        # contra `ventas` (histórico completo) para heredar la categoría real
        # con la que se vendió ese SKU. Costo unitario NO está disponible en
        # los datos que sincroniza Bsale para stock, así que no se muestra
        # "Valor de Inventario" (mejor omitirlo que inventar un costo).
        categoria_por_sku_raw = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(CATEGORIA)
            FROM ventas
            WHERE SKU_BSALE IS NOT NULL AND CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
            GROUP BY SKU_BSALE
        """).fetchall()
        categoria_por_sku = {str(sku).strip().upper(): cat for sku, cat in categoria_por_sku_raw}

        # El nombre de producto que trae el stock de Bsale suele ser genérico
        # (ej. "ESTUFAS", "CALEFACTOR MURAL") -- se prioriza el nombre
        # completo real que ya usa el resto de la app (Ventas por SKU),
        # heredado del mismo cruce por SKU contra `ventas`.
        producto_por_sku_raw = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(PRODUCTO)
            FROM ventas
            WHERE SKU_BSALE IS NOT NULL AND PRODUCTO IS NOT NULL AND TRIM(PRODUCTO) != ''
            GROUP BY SKU_BSALE
        """).fetchall()
        producto_por_sku = {str(sku).strip().upper(): prod for sku, prod in producto_por_sku_raw}

    # Pivot SKU -> bodegas
    por_sku: dict = {}
    for sku, producto, bodega, disponible in df_stock:
        item = por_sku.setdefault(sku, {"sku": sku, "producto": producto, "bodegas": {}, "total": 0})
        item["bodegas"][bodega] = (item["bodegas"].get(bodega, 0) or 0) + (disponible or 0)
        item["total"] += disponible or 0

    items = []
    for sku, it in por_sku.items():
        unidades = ventas_recientes.get(sku.strip().upper(), 0) or 0
        venta_diaria = unidades / dias_venta
        dias_cobertura = (it["total"] / venta_diaria) if venta_diaria > 0 else (999.0 if it["total"] > 0 else 0.0)
        if it["total"] <= 0:
            estado = "🔴 QUIEBRE"
        elif dias_cobertura < 7:
            estado = "🔴"
        elif dias_cobertura < 14:
            estado = "🟡"
        else:
            estado = "🟢"
        items.append({
            "sku": sku,
            "producto": producto_por_sku.get(sku.strip().upper()) or it["producto"],
            "categoria": categoria_por_sku.get(sku.strip().upper(), "Sin categoría"),
            "bodegas": it["bodegas"],
            "totalStock": it["total"],
            "venta14d": unidades,
            "ventaDiariaProm": round(venta_diaria, 2),
            "diasCobertura": round(dias_cobertura, 1),
            "estado": estado,
        })
    items.sort(key=lambda x: x["diasCobertura"])

    return {"disponible": True, "mensaje": None, "items": items}


# ------------------------------------------------------------------
# PENDIENTES POR DESPACHAR — tabla `pendientes_despacho`, poblada por
# sync_pendientes_despacho.py (filtra Bsale por codesii=52/39/33 directo,
# ver diagnóstico: esta cuenta SÍ emite guías, el bug anterior era mío).
# ------------------------------------------------------------------
@router.get("/pendientes-despacho")
def get_pendientes_despacho():
    """
    REDISEÑADO (02-ago-2026): antes reconstruíamos "qué documentos están
    pendientes" cruzando guías de despacho por relatedDetailId -- un método
    frágil que traía falsos positivos y solo cubría 180 días. Se descubrió
    que Bsale genera su propio reporte nativo "Productos Por Despachar"
    (export_reserved) directamente desde `quantityReserved` en /v1/stocks.json
    -- el mismo endpoint que ya usa el módulo Stock. Ahora usamos esa misma
    fuente: stock reservado (comprometido en una venta, aún no despachado
    físicamente) por SKU y bodega, sin ventana de fecha artificial.
    """
    with get_connection() as con:
        if not _tabla_existe(con, "stock_bsale"):
            return {
                "disponible": False,
                "mensaje": (
                    "La tabla 'stock_bsale' aún no existe. Corre "
                    "backend/sync/sync_stock_bsale.py (alimenta Stock y "
                    "Pendientes por Despachar con la misma sincronización)."
                ),
                "items": [],
            }
        columnas = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'stock_bsale'"
            ).fetchall()
        }
        if "RESERVADO" not in columnas:
            return {
                "disponible": False,
                "mensaje": (
                    "La tabla 'stock_bsale' es de una corrida anterior y no tiene "
                    "la columna RESERVADO todavía. Vuelve a correr "
                    "backend/sync/sync_stock_bsale.py para agregarla."
                ),
                "items": [],
            }

        df_reservado = con.execute("""
            SELECT SKU, PRODUCTO, BODEGA, SUM(RESERVADO) AS RESERVADO
            FROM stock_bsale
            WHERE RESERVADO > 0
              AND SKU != 'DespachoCentry'
              AND UPPER(TRIM(PRODUCTO)) != 'DESPACHO'
              AND UPPER(TRIM(BODEGA)) = 'CASA MATRIZ'
            GROUP BY SKU, PRODUCTO, BODEGA
        """).fetchall()

        # Mismo cruce por SKU contra `ventas` que ya usa el módulo Stock,
        # para categoría real y nombre de producto completo.
        categoria_por_sku_raw = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(CATEGORIA)
            FROM ventas
            WHERE SKU_BSALE IS NOT NULL AND CATEGORIA IS NOT NULL AND TRIM(CATEGORIA) != ''
            GROUP BY SKU_BSALE
        """).fetchall()
        categoria_por_sku = {str(sku).strip().upper(): cat for sku, cat in categoria_por_sku_raw}

        producto_por_sku_raw = con.execute("""
            SELECT SKU_BSALE, ANY_VALUE(PRODUCTO)
            FROM ventas
            WHERE SKU_BSALE IS NOT NULL AND PRODUCTO IS NOT NULL AND TRIM(PRODUCTO) != ''
            GROUP BY SKU_BSALE
        """).fetchall()
        producto_por_sku = {str(sku).strip().upper(): prod for sku, prod in producto_por_sku_raw}

    items = []
    for sku, producto_stock, bodega, reservado in df_reservado:
        sku_key = sku.strip().upper()
        items.append({
            "id": f"{sku}|{bodega}",
            "sku": sku,
            "producto": producto_por_sku.get(sku_key) or producto_stock,
            "categoria": categoria_por_sku.get(sku_key, "Sin categoría"),
            "bodega": bodega,
            "cantidadReservada": reservado or 0,
        })
    items.sort(key=lambda x: x["cantidadReservada"], reverse=True)

    return {"disponible": True, "mensaje": None, "items": items}


@router.get("/pendientes-despacho-documentos")
def get_pendientes_despacho_documentos():
    """
    Detalle por documento (boleta/factura) de qué está pendiente, con
    vendedor y monto -- para tracking operativo. Complementa a
    /api/pendientes-despacho (que da el agregado por SKU desde RESERVADO).
    Poblada por sync_pendientes_documentos.py.

    EXCLUYE (02-ago-2026) documentos que ya tienen una nota de crédito
    asociada: si la boleta/factura fue devuelta/anulada, ya no es una
    venta comprometida pendiente de despacho -- mostrarla sería un falso
    positivo (ver caso real: BOLETA N° 37573, con Nota de Crédito N° 4304
    asociada por el mismo monto). El cruce usa DOCUMENTO_REFERENCIA de
    notas_credito_desfase, poblado por sync_notas_credito.py.

    EXCLUYE (02-ago-2026) también las líneas con SKU = 'DespachoCentry' o
    con DESCRIPCION = 'Despacho' (sin distinguir mayúsculas) -- no son
    productos reales pendientes de despachar, son cargos de flete/despacho
    que Bsale registra como una línea de detalle más dentro del mismo
    documento (confirmado real: decenas de líneas con SKU numérico tipo
    "1782914414" y descripción "Despacho"/"despacho"). Se deja "despacho
    repuesto" SIN excluir a propósito -- match exacto, no LIKE, porque ese
    caso sí es un producto real (un repuesto físico pendiente de despachar,
    no un cargo de flete).

    RESTRINGIDO (02-ago-2026, decisión de William) a ÚNICAMENTE la bodega
    'Casa Matriz'. Se descartó intentar distinguir "Por Despachar" de
    "Entrega Inmediata" en las demás bodegas (Kennedy resultó ser mixta --
    a veces despacha, a veces entrega en el momento -- sin un campo
    confiable a nivel de documento para diferenciarlas; ver diagnósticos
    previos). En vez de filtrar mal, se acota el alcance del módulo
    completo a Casa Matriz, donde SÍ se puede hacer una revisión
    exhaustiva y confiable. Si más adelante se encuentra la señal correcta
    para Kennedy/Servicio Técnico/otras bodegas, se puede reincorporar.
    A pedido de William: solo
    ensucia el conteo de líneas pendientes, no aporta información
    operativa. Si un documento SOLO tenía esa línea (sin ningún producto
    real pendiente), el documento completo desaparece de este detalle --
    comportamiento correcto: no había nada físico pendiente de despachar
    en ese documento, solo el cargo de flete.
    """
    with get_connection() as con:
        if not _tabla_existe(con, "pendientes_despacho_docs"):
            return {
                "disponible": False,
                "mensaje": (
                    "La tabla 'pendientes_despacho_docs' aún no existe. "
                    "Corre backend/sync/sync_pendientes_documentos.py."
                ),
                "items": [],
            }

        # Igual que con notas de crédito: si la tabla es de una corrida
        # vieja sin PEDIDO_NUMERO/PEDIDO_ORIGEN, no se rompe el endpoint --
        # simplemente esas columnas vienen NULL hasta que se corra el sync
        # actualizado.
        columnas_pendientes = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'pendientes_despacho_docs'"
            ).fetchall()
        }
        tiene_pedido = "PEDIDO_NUMERO" in columnas_pendientes
        select_pedido_p = "p.PEDIDO_NUMERO, p.PEDIDO_ORIGEN" if tiene_pedido else "NULL, NULL"

        # Estado de envío real para Falabella (02-ago-2026): cruce contra
        # falabella_estados_pedido por PEDIDO_NUMERO + SKU, poblada por
        # sync_falabella_estados.py (GetOrders/GetOrderItems vía Seller
        # Center). Defensivo: si la tabla no existe todavía, simplemente
        # no hay estado (columna NULL), sin romper el endpoint.
        tiene_estado_falabella = _tabla_existe(con, "falabella_estados_pedido")

        # El cruce con notas de crédito es opcional y defensivo: si la
        # tabla aún no existe, o es de una corrida vieja sin la columna
        # DOCUMENTO_REFERENCIA, simplemente no se excluye nada (mejor
        # mostrar de más que fallar el endpoint completo).
        tiene_notas_credito = _tabla_existe(con, "notas_credito_desfase")
        if tiene_notas_credito:
            columnas_nc = {
                row[0] for row in con.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'notas_credito_desfase'"
                ).fetchall()
            }
            tiene_notas_credito = "DOCUMENTO_REFERENCIA" in columnas_nc

        join_falabella = (
            "LEFT JOIN falabella_estados_pedido fe "
            "ON fe.PEDIDO_NUMERO = p.PEDIDO_NUMERO AND fe.SKU = p.SKU"
            if tiene_estado_falabella else ""
        )
        select_estado = "fe.ESTADO_LEGIBLE" if tiene_estado_falabella else "NULL"

        if tiene_notas_credito:
            filas = con.execute(f"""
                SELECT p.SKU, p.DESCRIPCION, p.DOCUMENTO, p.TIPO_DOCUMENTO, p.CLIENTE,
                       p.VENDEDOR, p.BODEGA, p.FECHA_EMISION, p.MONTO_DOCUMENTO, p.CANTIDAD,
                       {select_pedido_p}, {select_estado}
                FROM pendientes_despacho_docs p
                {join_falabella}
                WHERE p.SKU != 'DespachoCentry'
                  AND UPPER(TRIM(p.DESCRIPCION)) != 'DESPACHO'
                  AND UPPER(TRIM(p.BODEGA)) = 'CASA MATRIZ'
                  AND NOT EXISTS (
                    SELECT 1 FROM notas_credito_desfase nc
                    WHERE nc.DOCUMENTO_REFERENCIA = p.DOCUMENTO
                  )
                ORDER BY p.FECHA_EMISION DESC
            """).fetchall()
        else:
            filas = con.execute(f"""
                SELECT p.SKU, p.DESCRIPCION, p.DOCUMENTO, p.TIPO_DOCUMENTO, p.CLIENTE, p.VENDEDOR,
                       p.BODEGA, p.FECHA_EMISION, p.MONTO_DOCUMENTO, p.CANTIDAD,
                       {select_pedido_p}, {select_estado}
                FROM pendientes_despacho_docs p
                {join_falabella}
                WHERE p.SKU != 'DespachoCentry'
                  AND UPPER(TRIM(p.DESCRIPCION)) != 'DESPACHO'
                  AND UPPER(TRIM(p.BODEGA)) = 'CASA MATRIZ'
                ORDER BY FECHA_EMISION DESC
            """).fetchall()

    avisos = []
    if not tiene_notas_credito:
        avisos.append(
            "sin excluir notas de crédito -- corre backend/sync/sync_notas_credito.py "
            "(versión actualizada)"
        )
    if not tiene_pedido:
        avisos.append(
            "sin N° de pedido -- corre backend/sync/sync_pendientes_documentos.py "
            "(versión actualizada)"
        )
    if not tiene_estado_falabella:
        avisos.append(
            "sin estado de envío Falabella -- corre backend/sync/sync_falabella_estados.py"
        )
    mensaje = None if not avisos else "Mostrando " + "; ".join(avisos) + "."

    items = []
    # Un mismo documento puede traer 2+ líneas con el mismo SKU (caso real
    # confirmado: Boleta N° 41153 trae "APOLO 1500 INVERTER" en 2 líneas
    # separadas, cantidad 1 cada una -- así llegó desde el marketplace).
    # Si el id fuera solo "documento|sku", ambas filas comparten el mismo
    # id -- React no puede distinguirlas como key y produce artefactos de
    # renderizado (filas que parecen duplicarse/no reordenarse bien). Se
    # agrega un contador por combinación documento+sku para que el id sea
    # siempre único, sin cambiar ningún otro dato.
    contador_id: dict[str, int] = {}
    for (sku, descripcion, documento, tipo_doc, cliente, vendedor, bodega, fecha_emision,
         monto, cantidad, pedido_numero, pedido_origen, estado_falabella) in filas:
        dias_pendiente = None
        try:
            dias_pendiente = (date.today() - fecha_emision.date()).days
        except (AttributeError, TypeError):
            pass

        clave_base = f"{documento}|{sku}"
        ocurrencia = contador_id.get(clave_base, 0)
        contador_id[clave_base] = ocurrencia + 1
        id_unico = clave_base if ocurrencia == 0 else f"{clave_base}|{ocurrencia}"

        # Estado de envío: real para Falabella (cruce por PEDIDO_NUMERO +
        # SKU contra falabella_estados_pedido). Para el resto de los
        # canales (D2C/Showroom/Distribuidores vía Envíame, y otros
        # marketplaces sin forma de rastrear) sigue en None -- pendiente
        # de sync_enviame.py real.
        items.append({
            "id": id_unico,
            "sku": sku,
            "descripcion": descripcion,
            "documento": documento,
            "tipoDocumento": tipo_doc,
            "cliente": cliente,
            "vendedor": vendedor,
            "bodega": bodega,
            "fechaEmision": str(fecha_emision) if fecha_emision else None,
            "diasPendiente": dias_pendiente or 0,
            "montoDocumento": monto or 0,
            "cantidad": cantidad or 0,
            "pedidoNumero": pedido_numero,
            "pedidoOrigen": pedido_origen,
            "estadoEnvio": estado_falabella,
        })

    return {"disponible": True, "mensaje": mensaje, "items": items}


@router.get("/notas-credito")
def get_notas_credito(fecha_inicio: date = Query(None), fecha_fin: date = Query(None)):
    """
    fecha_inicio / fecha_fin (YYYY-MM-DD, opcionales): filtran por
    FECHA_EMISION -- la "Fecha Impacto" declarada ante el SII (mismo campo
    que usa el resto del dashboard para ubicar un documento en el tiempo).
    Si no vienen, se devuelve el histórico completo (comportamiento
    anterior, para no romper a nadie que llame este endpoint sin filtros).

    FIX (19-ago-2026, reportado por William: "el módulo notas de crédito
    no está respetando el filtro de fecha"): esta función NUNCA declaraba
    fecha_inicio/fecha_fin como parámetros, pese a que CreditNotesView.tsx
    (vía fetchNotasCredito) siempre los mandaba en la URL -- FastAPI
    ignora en silencio cualquier query param que el endpoint no declare
    (no da error), así que el filtro del sidebar nunca llegaba a tocar la
    consulta SQL y el módulo siempre devolvía el histórico completo de
    notas_credito_desfase sin importar el rango elegido.
    """
    with get_connection() as con:
        if not _tabla_existe(con, "notas_credito_desfase"):
            return {
                "disponible": False,
                "mensaje": (
                    "La tabla 'notas_credito_desfase' aún no existe en kaltemp_matrix.duckdb "
                    "(en el app.py original este módulo también estaba pendiente de confirmar "
                    "el campo de 'fecha de caída' contable con soporte de Bsale)."
                ),
                "items": [],
            }

        # Chequeo defensivo (02-ago-2026): VENDEDOR y DOCUMENTO_REFERENCIA
        # son columnas nuevas -- si la tabla es de una corrida vieja sin
        # ellas, no se rompe el endpoint, solo vienen NULL hasta que se
        # corra el sync actualizado.
        columnas_nc = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'notas_credito_desfase'"
            ).fetchall()
        }
        select_vendedor = "VENDEDOR" if "VENDEDOR" in columnas_nc else "NULL"
        select_doc_original = "DOCUMENTO_REFERENCIA" if "DOCUMENTO_REFERENCIA" in columnas_nc else "NULL"
        select_descripcion = "DESCRIPCION_PRODUCTO" if "DESCRIPCION_PRODUCTO" in columnas_nc else "NULL"
        select_generacion = "GENERACION_DATE" if "GENERACION_DATE" in columnas_nc else "NULL"

        filtro_fecha = ""
        params: list = []
        if fecha_inicio and fecha_fin:
            filtro_fecha = "WHERE CAST(FECHA_EMISION AS DATE) BETWEEN ? AND ?"
            params = [fecha_inicio, fecha_fin]

        filas = con.execute(f"""
            SELECT DOCUMENTO, CLIENTE, {select_vendedor}, {select_doc_original}, {select_descripcion},
                   FECHA_EMISION, FECHA_CAIDA, {select_generacion}, DIAS_DESFASE, MONTO, ALERTA
            FROM notas_credito_desfase
            {filtro_fecha}
            ORDER BY DIAS_DESFASE DESC
        """, params).fetchall()

    mensaje = None
    if ("VENDEDOR" not in columnas_nc or "DOCUMENTO_REFERENCIA" not in columnas_nc
            or "DESCRIPCION_PRODUCTO" not in columnas_nc or "GENERACION_DATE" not in columnas_nc):
        mensaje = (
            "Mostrando datos incompletos (falta vendedor / documento original / "
            "descripción / fecha de creación real): corre backend/sync/sync_notas_credito.py "
            "(versión actualizada)."
        )

    items = [{
        "id": f[0], "documento": f[0], "cliente": f[1], "vendedor": f[2],
        "documentoOriginal": f[3], "descripcionProducto": f[4],
        "fechaEmision": f[5].isoformat() if f[5] else None,
        "fechaCaida": f[6].isoformat() if f[6] else None,
        "fechaGeneracion": f[7].isoformat() if f[7] else None,
        "diasDesfase": f[8] or 0, "monto": f[9] or 0, "alerta": bool(f[10]),
    } for f in filas]

    return {"disponible": True, "mensaje": mensaje, "items": items}


# ------------------------------------------------------------------
# CONTROL LOGÍSTICO — mapeo desde `enviame_despachos`, sincronizada por
# sync_enviame.py.
# ------------------------------------------------------------------
@router.get("/enviame-shipments")
def get_enviame_shipments(
    fecha_inicio: date = Query(None),
    fecha_fin: date = Query(None),
):
    """
    Historial de cambios relevantes en este endpoint (12/13-ago-2026):

    1) Filtro de fecha: antes no existía -- siempre traía los últimos 2000
       registros por FECHA_CREACION DESC sin importar el sidebar. Ahora
       fecha_inicio/fecha_fin son opcionales: si llegan ambos, filtra por
       TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?.

    2) fechaEnvio: antes NO se incluía en la respuesta (solo se usaba
       FECHA_CREACION para el ORDER BY). Ahora viaja por fila.

    3) fechaEntrega: viene de la columna FECHA_ENTREGA en enviame_despachos,
       poblada por sync_enviame.py con status.created_at de la API de
       Envíame cuando el estado es "Entregado".

    4) vendedor / producto / cobroBsale: MOVIDO a tabla precalculada
       (13-ago-2026). Antes este endpoint calculaba el cruce con `ventas`
       EN VIVO en cada request (JOIN con validación de fecha por número de
       referencia). Ahora solo LEE `enviame_cruce_ventas`, poblada por
       sync/sync_cruce_enviame_bsale.py -- que corre el cruce POR ETAPAS
       (1: nombre+fecha, 2: número+fecha como respaldo, 3: texto de
       descripción, pendiente hasta que Envíame habilite ese campo por
       API) una sola vez por ciclo de sync, no en cada carga del módulo.
       Ver ese script para el detalle completo y la justificación de cada
       etapa con datos reales de los diagnósticos.

    5) costoEnviame: FIX de bug propio -- en una ronda anterior el campo
       había quedado escrito como "costoEnvio" (sin la "e" final) en vez
       de "costoEnviame", que es la key que efectivamente lee
       LogisticsView.tsx. Esto hacía que la columna "Costo Envíame" se
       viera vacía en pantalla AUNQUE el dato sí existiera en la base.
    """
    with get_connection() as con:
        if not _tabla_existe(con, "enviame_despachos"):
            return {
                "disponible": False,
                "mensaje": "La tabla 'enviame_despachos' aún no existe en kaltemp_matrix.duckdb.",
                "items": [],
            }

        columnas = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'enviame_despachos'"
            ).fetchall()
        }
        select_fecha_entrega = "e.FECHA_ENTREGA" if "FECHA_ENTREGA" in columnas else "NULL"

        params_fecha = [fecha_inicio, fecha_fin] if (fecha_inicio and fecha_fin) else []
        filtro_sql = "WHERE TRY_CAST(e.FECHA_CREACION AS DATE) BETWEEN ? AND ?" if params_fecha else ""

        tiene_cruce = _tabla_existe(con, "enviame_cruce_ventas")

        if tiene_cruce:
            filas = con.execute(f"""
                SELECT
                    e.ID_INTERNO, e.N_ENVIO_REF, e.CLIENTE, e.TELEFONO, e.COMUNA, e.DIRECCION,
                    e.COURIER, e.ESTADO, e.COSTO_ENVIO, e.TRACKING_NUMBER, e.TRACKING_URL,
                    e.ES_INCIDENCIA, e.FECHA_CREACION, {select_fecha_entrega},
                    c.VENDEDOR, c.PRODUCTO, c.COBRO_BSALE_DESPACHO
                FROM enviame_despachos e
                LEFT JOIN enviame_cruce_ventas c ON c.ID_INTERNO = e.ID_INTERNO
                {filtro_sql}
                ORDER BY e.FECHA_CREACION DESC
                LIMIT 2000
            """, params_fecha).fetchall()
        else:
            filas = [
                f + (None, None, None) for f in con.execute(f"""
                    SELECT
                        ID_INTERNO, N_ENVIO_REF, CLIENTE, TELEFONO, COMUNA, DIRECCION,
                        COURIER, ESTADO, COSTO_ENVIO, TRACKING_NUMBER, TRACKING_URL,
                        ES_INCIDENCIA, FECHA_CREACION, {select_fecha_entrega}
                    FROM enviame_despachos e
                    {filtro_sql.replace('e.FECHA_CREACION', 'FECHA_CREACION')}
                    ORDER BY FECHA_CREACION DESC
                    LIMIT 2000
                """, params_fecha).fetchall()
            ]

    items = [{
        "id": str(f[0]), "ref": f[1], "cliente": f[2], "telefono": f[3] or "",
        "comuna": f[4] or "", "direccion": f[5] or "", "courier": f[6] or "",
        "estado": f[7] or "", "costoEnviame": f[8] or 0,
        "trackingNumber": f[9] or "", "trackingUrl": f[10] or "",
        "esIncidencia": bool(f[11]),
        "fechaEnvio": f[12] or None,
        "fechaEntrega": f[13] or None,
        "vendedor": f[14] or "", "producto": f[15] or "", "cobroBsale": f[16] or 0,
    } for f in filas]

    return {"disponible": True, "mensaje": None, "items": items}


# ------------------------------------------------------------------
# CONTROL LOGÍSTICO — KPIs agregados (02-ago-2026): total despachos,
# costo reportado por Envíame, y "cobro real Bsale" (suma de las líneas
# Despacho/DespachoCentry que sí cobramos al cliente en `ventas` -- NO es
# lo mismo que el costo que Envíame nos cobra a nosotros; la diferencia
# entre ambos es el margen de flete real). Esto SÍ se puede calcular a
# nivel agregado sin necesitar el cruce fila-a-fila con Envíame.
# ------------------------------------------------------------------
def _despachos_periodo(con, fecha_inicio: date, fecha_fin: date) -> dict:
    # FECHA_CREACION es VARCHAR en enviame_despachos (no TIMESTAMP) --
    # TRY_CAST defensivo por si algún valor no parsea, en vez de romper
    # todo el query.
    sql = """
        SELECT COUNT(*), SUM(COSTO_ENVIO)
        FROM enviame_despachos
        WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?
    """
    fila = con.execute(sql, [fecha_inicio, fecha_fin]).fetchone()
    count, costo = fila or (0, 0)
    return {"despachos": count or 0, "costoEnviame": costo or 0}


def _cobro_bsale_despacho_periodo(con, fecha_inicio: date, fecha_fin: date) -> float:
    """
    Suma BRUTO_TOTAL de las líneas de "Despacho" reales en `ventas` (el
    cargo de flete que se le cobra al cliente en la boleta/factura) --
    mismo criterio de detección que ya usamos para EXCLUIR estas líneas
    en Pendientes por Despachar (SKU='DespachoCentry' o
    PRODUCTO='Despacho'), pero acá se usan a propósito porque es
    justamente el dato que se necesita.
    """
    sql = """
        SELECT SUM(BRUTO_TOTAL)
        FROM ventas
        WHERE CAST(FECHA_OBJ AS DATE) BETWEEN ? AND ?
          AND (UPPER(TRIM(PRODUCTO)) = 'DESPACHO' OR SKU_BSALE = 'DespachoCentry')
    """
    fila = con.execute(sql, [fecha_inicio, fecha_fin]).fetchone()
    return (fila[0] if fila else 0) or 0


def _comuna_breakdown(con, fecha_inicio: date, fecha_fin: date) -> list:
    sql = """
        SELECT COMUNA, COUNT(*) AS envios, SUM(COSTO_ENVIO) AS costo
        FROM enviame_despachos
        WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?
          AND COMUNA IS NOT NULL AND TRIM(COMUNA) != ''
        GROUP BY COMUNA
        ORDER BY envios DESC
        LIMIT 8
    """
    filas = con.execute(sql, [fecha_inicio, fecha_fin]).fetchall()
    return [{"comuna": f[0], "envios": f[1] or 0, "costo": round(f[2] or 0, 0)} for f in filas]


@router.get("/logistica")
def get_logistica(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
):
    yoy_ini = fecha_inicio.replace(year=fecha_inicio.year - 1)
    yoy_fin = fecha_fin.replace(year=fecha_fin.year - 1)

    with get_connection() as con:
        if not _tabla_existe(con, "enviame_despachos"):
            return {
                "disponible": False,
                "mensaje": "La tabla 'enviame_despachos' aún no existe en kaltemp_matrix.duckdb.",
            }

        cy = _despachos_periodo(con, fecha_inicio, fecha_fin)
        yoy = _despachos_periodo(con, yoy_ini, yoy_fin)
        cobro_cy = _cobro_bsale_despacho_periodo(con, fecha_inicio, fecha_fin)
        cobro_yoy = _cobro_bsale_despacho_periodo(con, yoy_ini, yoy_fin)
        comunas = _comuna_breakdown(con, fecha_inicio, fecha_fin)

    diferencia = cobro_cy - cy["costoEnviame"]
    margen_pct = (diferencia / cy["costoEnviame"] * 100) if cy["costoEnviame"] else 0.0

    return {
        "disponible": True,
        "mensaje": None,
        "despachosCy": cy["despachos"],
        "despachosYoy": yoy["despachos"],
        "costoEnviameCy": round(cy["costoEnviame"], 0),
        "costoEnviameYoy": round(yoy["costoEnviame"], 0),
        "cobroBsaleCy": round(cobro_cy, 0),
        "cobroBsaleYoy": round(cobro_yoy, 0),
        "diferencia": round(diferencia, 0),
        "margenPct": round(margen_pct, 1),
        "comunas": comunas,
    }