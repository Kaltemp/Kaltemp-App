"""
importar_categorias_manual.py — Importa el archivo de clasificación
SKU -> Categoría (el CSV separado por ";" que exportaste) a la base de
categorías manuales. Se puede correr las veces que quieras -- si un SKU
ya tiene categoría asignada, la actualiza con el valor del CSV.

Uso:
    python importar_categorias_manual.py ruta\al\archivo.csv

Si no pasas la ruta, busca "SKU.csv" en la misma carpeta.
"""
import sys
import csv
import os
from datetime import datetime, timezone

from categorias_db import get_categorias_connection, init_categorias_db

VALORES_VACIOS = ("", "#N/D", "#N/A", "N/A", "NULL")


def importar(ruta_csv: str):
    if not os.path.exists(ruta_csv):
        print(f"❌ No encontré el archivo: {ruta_csv}")
        return

    init_categorias_db()

    filas_validas = []
    categorias_vistas = set()

    with open(ruta_csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = (row.get("SKU Seller") or "").strip().upper()
            categoria = (row.get("Categoría") or "").strip()
            if not sku or sku in ("CANAL",):
                continue
            if not categoria or categoria in VALORES_VACIOS:
                continue
            filas_validas.append((sku, categoria))
            categorias_vistas.add(categoria)

    if not filas_validas:
        print("⚠️ No se encontraron filas con SKU + categoría válida en el archivo.")
        return

    ahora = datetime.now(timezone.utc).isoformat()
    with get_categorias_connection() as con:
        for sku, categoria in filas_validas:
            con.execute("""
                INSERT INTO categorias_manual (sku, categoria, asignado_por, actualizado_en)
                VALUES (?, ?, 'importacion_inicial', ?)
                ON CONFLICT(sku) DO UPDATE SET
                    categoria = excluded.categoria,
                    actualizado_en = excluded.actualizado_en
            """, [sku, categoria, ahora])

        for categoria in categorias_vistas:
            con.execute(
                "INSERT OR IGNORE INTO categorias_catalogo (nombre) VALUES (?)",
                [categoria]
            )
        con.commit()

    print(f"✅ {len(filas_validas)} SKUs importados con categoría real.")
    print(f"✅ {len(categorias_vistas)} categorías distintas en el catálogo: {', '.join(sorted(categorias_vistas))}")
    print()
    print("Ahora corre: python sync/sync_ventas.py <dias> para que estas categorías")
    print("se apliquen a las ventas correspondientes.")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "SKU.csv")
    importar(ruta)
