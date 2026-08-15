# ============================================================
# ARCHIVO: importar_pesos_manual.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\importar_pesos_manual.py
# ============================================================

# ============================================================
# ARCHIVO: importar_pesos_manual.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\importar_pesos_manual.py
# (o junto a importar_categorias_manual.py, donde lo tengas hoy)
# ============================================================
"""
importar_pesos_manual.py — Importa el archivo de peso/dimensiones por
SKU (pesos_resueltos_final.xlsx, ya deduplicado: de 193 filas con 75
SKUs repetidos -- 68 de ellos con medidas EN CONFLICTO entre las dos
filas -- se resolvió quedándose con la 2da ocurrencia de cada SKU
repetido, la que viene directo de bodega, a pedido de William
11-ago-2026) a la base de pesos manuales.

Se puede correr las veces que quieras -- si un SKU ya tiene peso
asignado, lo actualiza con el valor del archivo.

Uso:
    python importar_pesos_manual.py ruta\al\archivo.xlsx

Si no pasas la ruta, busca "pesos_resueltos_final.xlsx" en la misma carpeta.

Columnas esperadas (nombres exactos del archivo real, ojo con el
espacio al final de "Peso del paquete "):
    SKU de la variante, Nombre del Producto, Alto del paquete cm,
    Largo del paquete cm, Ancho del paquete cm, Peso del paquete
"""
import sys
import os
from datetime import datetime, timezone

import pandas as pd

# categorias_db.py vive en backend/ (un nivel arriba de backend/sync/, donde
# corre este script) -- sin esto, Python no lo encuentra al correr
# `python importar_pesos_manual.py` parado en la carpeta sync/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from categorias_db import get_categorias_connection, init_categorias_db

COL_SKU = "SKU de la variante"
COL_ALTO = "Alto del paquete cm"
COL_LARGO = "Largo del paquete cm"
COL_ANCHO = "Ancho del paquete cm"
COL_PESO = "Peso del paquete "  # ojo: trae un espacio al final en el archivo real


def importar(ruta_xlsx: str):
    if not os.path.exists(ruta_xlsx):
        print(f"❌ No encontré el archivo: {ruta_xlsx}")
        return

    init_categorias_db()

    df = pd.read_excel(ruta_xlsx)

    # Tolerante a que alguien reexporte el archivo sin el espacio final
    # en "Peso del paquete " -- busca la columna por coincidencia parcial
    # si el nombre exacto no está.
    col_peso_real = COL_PESO if COL_PESO in df.columns else next(
        (c for c in df.columns if c.strip().lower().startswith("peso del paquete")), None
    )
    if col_peso_real is None:
        print(f"❌ No encontré una columna de peso en el archivo. Columnas disponibles: {list(df.columns)}")
        return

    filas_validas = []
    omitidas = 0
    for _, row in df.iterrows():
        sku = str(row.get(COL_SKU, "")).strip().upper()
        if not sku or sku == "NAN":
            omitidas += 1
            continue

        try:
            peso = float(row.get(col_peso_real))
            largo = float(row.get(COL_LARGO))
            ancho = float(row.get(COL_ANCHO))
            alto = float(row.get(COL_ALTO))
        except (TypeError, ValueError):
            print(f"  ⚠️ {sku}: medidas no numéricas, se omite -- revisar a mano.")
            omitidas += 1
            continue

        if peso <= 0:
            print(f"  ⚠️ {sku}: peso es 0 o negativo, se omite -- revisar a mano.")
            omitidas += 1
            continue

        filas_validas.append((sku, peso, largo, ancho, alto))

    if not filas_validas:
        print("⚠️ No se encontraron filas válidas para importar.")
        return

    ahora = datetime.now(timezone.utc).isoformat()
    with get_categorias_connection() as con:
        for sku, peso, largo, ancho, alto in filas_validas:
            con.execute("""
                INSERT INTO pesos_manual (sku, peso_kg, largo_cm, ancho_cm, alto_cm, descontinuado, asignado_por, actualizado_en)
                VALUES (?, ?, ?, ?, ?, 0, 'importacion_inicial', ?)
                ON CONFLICT(sku) DO UPDATE SET
                    peso_kg = excluded.peso_kg,
                    largo_cm = excluded.largo_cm,
                    ancho_cm = excluded.ancho_cm,
                    alto_cm = excluded.alto_cm,
                    descontinuado = 0,
                    actualizado_en = excluded.actualizado_en
            """, [sku, peso, largo, ancho, alto, ahora])
        con.commit()

    print(f"✅ {len(filas_validas)} SKUs importados con peso/medidas reales.")
    if omitidas:
        print(f"⚠️ {omitidas} filas omitidas (sin SKU válido o medidas no numéricas) -- revisar a mano en la app.")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "pesos_resueltos_final.xlsx")
    importar(ruta)