# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\routers\diagnostico_falabella_y_garrido.py
# (o cualquier carpeta backend\ -- solo necesita el .duckdb, no llama a ninguna API)
"""
diagnostico_falabella_y_garrido.py

Dos preguntas, con datos ya sincronizados (no llama a Bsale ni a Falabella,
corre en segundos):

1. ¿falabella_estados_pedido tiene cobertura para los pedidos viejos
   (ene-2025) que aparecen en el detalle de Pendientes por Despachar?
   Si no, el LEFT JOIN de /api/pendientes-despacho-documentos no tiene
   nada que encontrar -- por eso "ESTADO ENVÍO" sale "No disponible".

2. ¿Dónde están las ventas D2C de William Garrido? Se revisa si existen
   en pendientes_despacho_docs pero quedan afuera por el filtro
   BODEGA='CASA MATRIZ', o si ni siquiera llegaron a esa tabla.

Uso (desde cualquier carpeta backend\\, con el venv activo):
    python diagnostico_falabella_y_garrido.py
"""
import duckdb

DB_PATH = "../kaltemp_matrix.duckdb"  # ajustar si se corre desde otra profundidad


def _tabla_existe(con, nombre):
    return con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [nombre]
    ).fetchone() is not None


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    print("=" * 70)
    print("PARTE 1: falabella_estados_pedido")
    print("=" * 70)

    if not _tabla_existe(con, "falabella_estados_pedido"):
        print("❌ La tabla falabella_estados_pedido NO existe todavía.")
    else:
        total = con.execute("SELECT COUNT(*) FROM falabella_estados_pedido").fetchone()[0]
        print(f"Total filas: {total}")

        meta = con.execute(
            "SELECT ultima_actualizacion FROM sync_meta WHERE tabla = 'falabella_estados_pedido'"
        ).fetchone()
        print(f"Última actualización: {meta[0] if meta else 'sin registro en sync_meta'}")

        print("\n--- Distribución de ESTADO_LEGIBLE ---")
        for row in con.execute(
            "SELECT ESTADO_LEGIBLE, COUNT(*) FROM falabella_estados_pedido "
            "GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n--- ¿Existen los PEDIDO_NUMERO de ene-2025 que aparecen pendientes? ---")
        pedidos_prueba = ["3501007626", "3501013134", "3501011179", "3501011250"]
        for pedido in pedidos_prueba:
            filas = con.execute(
                "SELECT SKU, ESTADO_LEGIBLE FROM falabella_estados_pedido WHERE PEDIDO_NUMERO = ?",
                [pedido],
            ).fetchall()
            print(f"  Pedido {pedido}: {'ENCONTRADO -> ' + str(filas) if filas else 'NO encontrado'}")

    print("\n" + "=" * 70)
    print("PARTE 2: Ventas D2C bajo William Garrido")
    print("=" * 70)

    if not _tabla_existe(con, "pendientes_despacho_docs"):
        print("❌ La tabla pendientes_despacho_docs NO existe todavía.")
    else:
        print("\n--- ¿Cuántas líneas pendientes tiene Garrido, por bodega? ---")
        for row in con.execute(
            "SELECT BODEGA, COUNT(*), COUNT(DISTINCT DOCUMENTO) "
            "FROM pendientes_despacho_docs "
            "WHERE VENDEDOR ILIKE '%Garrido%' "
            "GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall():
            print(f"  Bodega '{row[0]}': {row[1]} líneas, {row[2]} documentos distintos")

        print("\n--- Total general (todas las bodegas) vs. solo CASA MATRIZ (lo que hoy muestra el módulo) ---")
        total = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT DOCUMENTO) FROM pendientes_despacho_docs "
            "WHERE VENDEDOR ILIKE '%Garrido%'"
        ).fetchone()
        solo_matriz = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT DOCUMENTO) FROM pendientes_despacho_docs "
            "WHERE VENDEDOR ILIKE '%Garrido%' AND UPPER(TRIM(BODEGA)) = 'CASA MATRIZ'"
        ).fetchone()
        print(f"  Total (todas las bodegas): {total[0]} líneas, {total[1]} documentos")
        print(f"  Solo CASA MATRIZ (lo que hoy se muestra): {solo_matriz[0]} líneas, {solo_matriz[1]} documentos")

        print("\n--- Muestra de 10 documentos de Garrido fuera de CASA MATRIZ ---")
        for row in con.execute(
            "SELECT DOCUMENTO, BODEGA, CLIENTE, FECHA_EMISION, CANTIDAD, MONTO_DOCUMENTO "
            "FROM pendientes_despacho_docs "
            "WHERE VENDEDOR ILIKE '%Garrido%' AND UPPER(TRIM(BODEGA)) != 'CASA MATRIZ' "
            "ORDER BY FECHA_EMISION DESC LIMIT 10"
        ).fetchall():
            print(f"  {row}")

    con.close()


if __name__ == "__main__":
    main()