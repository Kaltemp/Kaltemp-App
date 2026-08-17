# ============================================================
# ARCHIVO: revertir_andesgear_a_otros.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\revertir_andesgear_a_otros.py
#
# Corrige la sobre-corrección del script anterior: Andes Gear debe
# quedarse en "OTROS" (a pedido de William, 17-ago-2026), no pasar a D2C.
# Deja intactas las otras 3 correcciones (Hites, Paris Fulfillment,
# Pablo Opazo) -- esas sí eran correctas.
#
# USO (una sola vez):
#   cd C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend
#   venv\Scripts\activate
#   python revertir_andesgear_a_otros.py
# ============================================================
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"), override=True)
DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

print(f"Conectando a: {DB_PATH}\n")
con = duckdb.connect(DB_PATH, read_only=False)

antes = con.execute(
    "SELECT COUNT(*), COALESCE(SUM(BRUTO_TOTAL), 0) FROM ventas WHERE VENDEDOR = 'KALTEMP ANDESGEAR' AND CANAL = 'D2C'"
).fetchone()
filas, monto = antes[0], antes[1]

if filas == 0:
    print("0 filas de KALTEMP ANDESGEAR en D2C -- nada que revertir (¿ya se corrió este script antes?)")
else:
    con.execute("UPDATE ventas SET CANAL = 'OTROS' WHERE VENDEDOR = 'KALTEMP ANDESGEAR' AND CANAL = 'D2C'")
    print(f"KALTEMP ANDESGEAR: {filas} filas (${monto:,.0f}) movidas de vuelta de 'D2C' -> 'OTROS'")

con.close()
print("\nListo. Refresca la app (F5) para ver el cambio.")