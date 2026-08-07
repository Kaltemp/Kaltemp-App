"""
sync_stock_bsale.py — Puebla la tabla `stock_bsale` en kaltemp_matrix.duckdb
leyendo /v1/stocks.json de Bsale.

Alineado 100% con el reporte nativo "Stock Actual" de Bsale:
  - DISPONIBLE (quantityAvailable): Unidades libres para venta
  - RESERVADO (quantityReserved): Unidades comprometidas por despachar
  - TOTAL_FISICO (quantity): Stock físico real presente en bodega
"""
import os
import sys
import duckdb
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from bsale_client import bsale_get_all  # noqa: E402

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")


def _cargar_oficinas() -> dict:
    return {str(o["id"]): o["name"] for o in bsale_get_all("offices.json")}


def _cargar_variantes() -> dict:
    """variant_id -> (sku, nombre_producto)"""
    mapa = {}
    for v in bsale_get_all("variants.json", params={"expand": "[product]"}):
        vid = str(v["id"])
        sku = v.get("code") or ""
        producto = v.get("product")
        producto_nombre = producto.get("name") if isinstance(producto, dict) else None
        nombre = v.get("description") or producto_nombre or sku
        mapa[vid] = (sku, nombre)
    return mapa


def sync_stock():
    print(f"[{datetime.now()}] Sync stock_bsale: cargando oficinas...")
    oficinas = _cargar_oficinas()
    print(f"  {len(oficinas)} oficinas encontradas")

    print(f"[{datetime.now()}] Cargando variantes (SKU + producto)...")
    variantes = _cargar_variantes()
    print(f"  {len(variantes)} variantes encontradas")

    print(f"[{datetime.now()}] Descargando stock (disponible + reservado + total) por variante/oficina...")
    filas = []
    for s in bsale_get_all("stocks.json"):
        variant_id = str(s.get("variant", {}).get("id", ""))
        office_id = str(s.get("office", {}).get("id", ""))
        sku, producto = variantes.get(variant_id, ("", f"Variante {variant_id}"))
        bodega = oficinas.get(office_id, f"Oficina {office_id}")
        
        raw_total = float(s.get("quantity", 0) or 0)
        raw_reserved = float(s.get("quantityReserved", 0) or 0)
        raw_available = s.get("quantityAvailable")

        # Garantiza coincidencia exacta con Bsale (Disponible = Total - Reservado)
        if raw_available is not None:
            disponible = float(raw_available)
        else:
            disponible = max(0.0, raw_total - raw_reserved)

        reservado = raw_reserved
        total_fisico = raw_total if raw_total > 0 else (disponible + reservado)

        if not sku:
            continue  # Variantes sin SKU se omiten
            
        filas.append((sku, producto, bodega, float(disponible), float(reservado), float(total_fisico)))

    print(f"[{datetime.now()}] {len(filas)} filas de stock a escribir")

    con = duckdb.connect(DB_PATH, read_only=False)
    try:
        con.execute("DROP TABLE IF EXISTS stock_bsale")
        con.execute("""
            CREATE TABLE stock_bsale (
                SKU VARCHAR, PRODUCTO VARCHAR, BODEGA VARCHAR,
                DISPONIBLE DOUBLE, RESERVADO DOUBLE, TOTAL_FISICO DOUBLE
            )
        """)

        con.executemany(
            "INSERT INTO stock_bsale (SKU, PRODUCTO, BODEGA, DISPONIBLE, RESERVADO, TOTAL_FISICO) VALUES (?, ?, ?, ?, ?, ?)",
            filas,
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["stock_bsale", datetime.now(timezone.utc)],
        )
        con.commit()
        print(f"[{datetime.now()}] ✅ stock_bsale actualizada ({len(filas)} filas escritas con éxito)")
    finally:
        con.close()


if __name__ == "__main__":
    sync_stock()