# ============================================================
# ARCHIVO: corregir_canal_mal_clasificado.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\corregir_canal_mal_clasificado.py
#
# QUÉ HACE: corrige el CANAL de las filas que YA están sincronizadas en
# `ventas` y que cayeron en "OTROS" (o en su propio nombre de vendedor,
# caso Pablo Opazo) por el bug de mapeo en sync_ventas.py -- ese fix ya
# corregido solo afecta ventas NUEVAS que se sincronicen de ahora en
# adelante, no repara lo que ya está guardado.
#
# USO (una sola vez, no hace falta repetirlo):
#   cd C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend
#   venv\Scripts\activate
#   python corregir_canal_mal_clasificado.py
#
# IMPORTANTE: no lo corras mientras un sync esté en curso (solo una
# conexión de escritura a la vez a kaltemp_matrix.duckdb).
# ============================================================
import os
import duckdb
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, ".env"), override=True)
DB_PATH = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

# (VENDEDOR tal cual aparece en la tabla, CANAL_VIEJO que tenía hoy, CANAL_NUEVO correcto)
CORRECCIONES = [
    ("KALTEMP HITES", "OTROS", "HITES"),
    ("KALTEMP ANDESGEAR", "OTROS", "D2C"),
    ("PARIS FULLFILMENT", "OTROS", "PARIS"),
    ("PABLO OPAZO", "PABLO OPAZO", "DISTRIBUIDORES"),
]

print(f"Conectando a: {DB_PATH}\n")
con = duckdb.connect(DB_PATH, read_only=False)

total_filas = 0
for vendedor, canal_viejo, canal_nuevo in CORRECCIONES:
    antes = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(BRUTO_TOTAL), 0) FROM ventas WHERE VENDEDOR = ? AND CANAL = ?",
        [vendedor, canal_viejo]
    ).fetchone()
    filas, monto = antes[0], antes[1]

    if filas == 0:
        print(f"  {vendedor}: 0 filas en '{canal_viejo}' -- nada que corregir (¿ya se corrió este script antes?)")
        continue

    con.execute(
        "UPDATE ventas SET CANAL = ? WHERE VENDEDOR = ? AND CANAL = ?",
        [canal_nuevo, vendedor, canal_viejo]
    )
    print(f"  {vendedor}: {filas} filas (${monto:,.0f}) movidas de '{canal_viejo}' -> '{canal_nuevo}'")
    total_filas += filas

con.close()
print(f"\nListo. {total_filas} filas corregidas en total.")
print("Refresca la app (F5) para ver los canales actualizados.")