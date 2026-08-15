# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_precio_ref_carritos.py
"""
diagnostico_precio_ref_carritos.py

"PRECIO REF." en Top Productos Más Abandonados sale con AVG(PRECIO_UNITARIO)
agrupado por nombre de PRODUCTO. Los valores no terminan en 990 como los
precios reales de Kaltemp -- este script separa dos hipótesis:

  A) Los valores CRUDOS de PRECIO_UNITARIO ya vienen "raros" (no terminan
     en 990) -- sugeriría que el campo capturado no es el precio limpio
     del producto (podría incluir despacho, o ser precio total de línea
     en vez de precio unitario).
  B) Los valores crudos SÍ terminan en 990 (limpios), pero son varios
     precios DISTINTOS agrupados bajo el mismo nombre de PRODUCTO
     (variantes distintas con el mismo título) -- el promedio de varios
     990 distintos da un número que ya no termina en 990, sin que haya
     ningún problema de datos.

Uso (desde backend/, con venv activo):
    python diagnostico_precio_ref_carritos.py
"""
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"), override=True)
DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

con = duckdb.connect(DB_PATH, read_only=True)

print(f"(usando DB_PATH: {DB_PATH})\n")

print("=== Valores CRUDOS de PRECIO_UNITARIO para el producto del ejemplo ===")
print("(ESTUFA ELÉCTRICA KALTEMP APOLO INVERTER 2000W WIFI | 25M2 -- promedio mostrado: $151.755)\n")

filas = con.execute("""
    SELECT PRECIO_UNITARIO, COUNT(*) AS veces
    FROM abandoned_checkouts
    WHERE PRODUCTO = 'ESTUFA ELÉCTRICA KALTEMP APOLO INVERTER 2000W WIFI | 25M2'
    GROUP BY PRECIO_UNITARIO
    ORDER BY veces DESC
""").fetchall()

for precio, veces in filas:
    termina_990 = "✅ termina en 990" if str(int(precio)).endswith("990") else "❌ NO termina en 990"
    print(f"  ${precio:,.0f}  ({veces} veces)  {termina_990}")

print(f"\nPromedio real de estos valores: ${sum(p * v for p, v in filas) / sum(v for _, v in filas):,.2f}")

print("\n\n=== Muestra general: ¿cuántos PRECIO_UNITARIO en TODA la tabla no terminan en 990/900/000? ===")
total = con.execute("SELECT COUNT(*) FROM abandoned_checkouts").fetchone()[0]
raros = con.execute("""
    SELECT COUNT(*) FROM abandoned_checkouts
    WHERE CAST(PRECIO_UNITARIO AS INTEGER) % 10 != 0
""").fetchone()[0]
print(f"Total filas: {total}, con PRECIO_UNITARIO 'raro' (no termina en 0): {raros}")

print("\n=== Muestra de 15 filas con su PRODUCTO, PRECIO_UNITARIO y TOTAL_PRICE (para comparar si hay relación con despacho) ===")
for row in con.execute("""
    SELECT PRODUCTO, PRECIO_UNITARIO, TOTAL_PRICE
    FROM abandoned_checkouts
    WHERE PRODUCTO = 'ESTUFA ELÉCTRICA KALTEMP APOLO INVERTER 2000W WIFI | 25M2'
    LIMIT 15
""").fetchall():
    print(f"  {row}")

con.close()