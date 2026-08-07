"""
reporte_sin_categoria.py — Lista los SKUs que hoy están marcados como
"Sin Tipo" (sin categoría real asignada en Bsale) en sku_maestro,
ordenados por cuánto han vendido -- para priorizar cuáles categorizar
primero en Bsale.

Uso:
    python reporte_sin_categoria.py

Genera un archivo `sin_categoria.csv` en la misma carpeta, y también
imprime un resumen en pantalla.
"""
import os
import csv
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import duckdb
from db import DB_PATH


def generar_reporte():
    con = duckdb.connect(DB_PATH, read_only=True)

    filas = con.execute("""
        SELECT
            sm.SKU,
            sm.PRODUCTO,
            sm.CATEGORIA,
            COALESCE(SUM(v.BRUTO_TOTAL), 0) AS venta_total,
            COALESCE(SUM(v.CANTIDAD), 0) AS unidades_vendidas
        FROM sku_maestro sm
        LEFT JOIN ventas v ON v.SKU_BSALE = sm.SKU
        WHERE sm.CATEGORIA IN ('Sin Tipo', 'Sin Categoría Mapeada')
        GROUP BY sm.SKU, sm.PRODUCTO, sm.CATEGORIA
        ORDER BY venta_total DESC
    """).fetchall()

    con.close()

    if not filas:
        print("✅ No hay productos sin categoría -- todo tu catálogo está categorizado.")
        return

    ruta_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sin_categoria.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["SKU", "Producto", "Categoría actual en Bsale", "Venta total ($)", "Unidades vendidas"])
        for sku, producto, categoria, venta, unidades in filas:
            writer.writerow([sku, producto, categoria, int(venta), int(unidades)])

    total_sin_categoria = len(filas)
    venta_afectada = sum(f[3] for f in filas)

    print(f"📋 {total_sin_categoria} SKUs sin categoría real en Bsale")
    print(f"💰 Venta total afectada: ${venta_afectada:,.0f}")
    print(f"📄 Reporte completo guardado en: {ruta_csv}")
    print()
    print("Top 15 por venta (prioriza estos primero en Bsale):")
    print("-" * 90)
    for sku, producto, categoria, venta, unidades in filas[:15]:
        print(f"  {sku:15} {producto[:45]:45} ${venta:>12,.0f}  ({int(unidades)} u.)")


if __name__ == "__main__":
    generar_reporte()