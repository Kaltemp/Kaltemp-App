# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_falabella_estados.py
"""
sync_falabella_estados.py — Puebla `falabella_estados_pedido` en
kaltemp_matrix.duckdb: el Status real por línea de cada pedido Falabella
(GetOrders + GetOrderItems, vía falabella_client.py), para poder cruzar
contra PEDIDO_NUMERO en `pendientes_despacho_docs` y mostrar el "Estado de
Envío" real en el módulo Pendientes por Despachar (canal Falabella).

Esto es la MISMA fuente que ya usa `obtener_ventas_falabella_api()` en el
app.py original (Streamlit) para poblar `ventas.ORIGEN='FALABELLA_API'` --
acá se agrega también el campo Status por línea, que esa función
consultaba pero NO guardaba (se usaba solo para filtrar canceladas/
devueltas y se descartaba).

Uso:
    export FALABELLA_API_KEY=...
    export FALABELLA_USER=...
    export DUCKDB_PATH=/ruta/a/kaltemp_matrix.duckdb
    export FALABELLA_FECHA_DESDE=2026-01-01   # opcional, mismo default que Pendientes
    python sync_falabella_estados.py

CORREGIDO (19-ago-2026, mismo bug real que sync_ga4_kaltemp.py /
sync_notas_credito.py -- ver hallazgo en sync_admin.py): el guardado en
DuckDB hacía DROP TABLE + CREATE TABLE completo, usando SOLO los pedidos
de la ventana [fecha_desde, hoy] recién consultada a Falabella. El botón
"Actualizar Ahora (últimos 30 días)" del panel web le pasa dias_atras=30
a esta función igual que a cualquier otra que lo acepte -- así que
borraba TODA la tabla y la dejaba solo con pedidos de los últimos 30
días. Esta tabla no tiene una columna de fecha del pedido (solo
ACTUALIZADO_EN, la hora de la corrida), así que en vez de borrar por
rango de fecha se borra puntualmente por los N° de pedido que se
volvieron a consultar esta corrida (ya se conocen, vienen de GetOrders)
y se reinsertan -- los pedidos que no estaban en la ventana consultada
quedan intactos, sin importar qué tan chico sea dias_atras.
"""
import os
import sys
import duckdb
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from falabella_client import get_orders, get_order_items, estado_legible  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
FECHA_DESDE_STR = os.getenv("FALABELLA_FECHA_DESDE", "2026-01-01")


def sync_falabella_estados(dias_atras: int = None, progress_callback=None):
    """
    dias_atras (agregado 11-ago-2026, mismo motivo que en
    sync_notas_credito.py): si se pasa, la ventana se calcula como hoy
    menos esos días, con prioridad sobre FALABELLA_FECHA_DESDE.
    progress_callback se acepta solo para no romper si sync_admin.py lo
    pasa (este script no reporta progreso incremental todavía).
    """
    if dias_atras is not None:
        fecha_desde = (datetime.now() - timedelta(days=dias_atras)).date()
    else:
        fecha_desde = datetime.strptime(FECHA_DESDE_STR, "%Y-%m-%d").date()
    fecha_hasta = datetime.now().date()
    print(f"[{datetime.now()}] Consultando GetOrders Falabella: {fecha_desde} a {fecha_hasta}...")

    pedidos = get_orders(fecha_desde, fecha_hasta)
    print(f"[{datetime.now()}] {len(pedidos)} pedidos encontrados. Consultando GetOrderItems de cada uno...")

    filas = []
    pedido_numeros_consultados = set()
    procesados = 0
    for pedido in pedidos:
        order_id = pedido.get("OrderId")
        order_number = pedido.get("OrderNumber", order_id)
        if not order_id:
            continue

        pedido_numeros_consultados.add(str(order_number))

        items = get_order_items(order_id)
        for it in items:
            sku = str(it.get("Sku", "")).strip().upper()
            estado_raw = str(it.get("Status", "")).lower().strip()
            filas.append((
                str(order_number),
                sku,
                estado_raw,
                estado_legible(estado_raw),
                datetime.now(timezone.utc).replace(tzinfo=None),  # ver sync_notas_credito.py: DuckDB + tzinfo = bug de zona horaria
            ))

        procesados += 1
        if procesados % 50 == 0:
            print(f"  {procesados}/{len(pedidos)} pedidos revisados...")

    print(f"[{datetime.now()}] {len(filas)} líneas de estado (de {procesados} pedidos)")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS falabella_estados_pedido (
                PEDIDO_NUMERO VARCHAR, SKU VARCHAR,
                ESTADO_RAW VARCHAR, ESTADO_LEGIBLE VARCHAR,
                ACTUALIZADO_EN TIMESTAMP
            )
        """)
        # CORREGIDO (19-ago-2026): antes era DROP+CREATE completo -- ver
        # nota arriba. Esta tabla no tiene columna de fecha de pedido, así
        # que se borra por los N° de pedido que efectivamente se
        # volvieron a consultar esta corrida (conocidos, vienen de
        # GetOrders), no la tabla entera -- los pedidos fuera de la
        # ventana consultada quedan intactos.
        pedido_numeros_lista = list(pedido_numeros_consultados)
        if pedido_numeros_lista:
            placeholders = ",".join(["?"] * len(pedido_numeros_lista))
            con.execute(
                f"DELETE FROM falabella_estados_pedido WHERE PEDIDO_NUMERO IN ({placeholders})",
                pedido_numeros_lista,
            )
        con.executemany(
            """INSERT INTO falabella_estados_pedido
               (PEDIDO_NUMERO, SKU, ESTADO_RAW, ESTADO_LEGIBLE, ACTUALIZADO_EN)
               VALUES (?, ?, ?, ?, ?)""",
            filas,
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["falabella_estados_pedido", datetime.now(timezone.utc).replace(tzinfo=None)],
        )
        con.commit()
        print(f"[{datetime.now()}] ✅ falabella_estados_pedido actualizada ({len(filas)} filas, {len(pedido_numeros_lista)} pedidos refrescados)")
    finally:
        con.close()


if __name__ == "__main__":
    sync_falabella_estados()