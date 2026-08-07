"""
diagnostico_match_pendientes_vendedor.py — Solo lectura (read_only=True).

Investiga por qué el cruce VENDEDOR/CANAL de sync_pendientes_despacho.py
matcheó solo 614/1499 documentos contra `ventas`. No modifica nada.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync
    python diagnostico_match_pendientes_vendedor.py
"""
import os
import duckdb

DB_PATH = os.getenv("DUCKDB_PATH", "kaltemp_matrix.duckdb")
if not os.path.isabs(DB_PATH):
    # mismo default relativo que usan los demás sync_*.py
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", DB_PATH)

con = duckdb.connect(DB_PATH, read_only=True)

print("=" * 70)
print("1) Valores distintos de TIPO_DOCUMENTO en `ventas` (para ver si")
print("   realmente contienen la palabra BOLETA / FACTURA)")
print("=" * 70)
for tipo, n in con.execute("""
    SELECT TIPO_DOCUMENTO, COUNT(*) 
    FROM ventas 
    GROUP BY TIPO_DOCUMENTO 
    ORDER BY 2 DESC
""").fetchall():
    print(f"  {tipo!r:35s} -> {n} filas")

print()
print("=" * 70)
print("2) Rango de fechas cubierto por `ventas` vs `pendientes_despacho`")
print("=" * 70)
print("  ventas:", con.execute("SELECT MIN(FECHA_OBJ), MAX(FECHA_OBJ) FROM ventas").fetchone())
print("  pendientes_despacho:", con.execute(
    "SELECT MIN(FECHA_EMISION), MAX(FECHA_EMISION) FROM pendientes_despacho"
).fetchone())

print()
print("=" * 70)
print("3) Muestra de NUMERO_DOCUMENTO crudo en `ventas` (para ver el formato real)")
print("=" * 70)
for row in con.execute("""
    SELECT NUMERO_DOCUMENTO, TIPO_DOCUMENTO 
    FROM ventas 
    WHERE NUMERO_DOCUMENTO IS NOT NULL 
    LIMIT 10
""").fetchall():
    print(f"  {row}")

print()
print("=" * 70)
print("4) Muestra de 10 documentos SIN match (VENDEDOR = 'Sin vendedor') en")
print("   pendientes_despacho, y si su número aparece EN ALGÚN LADO de")
print("   ventas.NUMERO_DOCUMENTO (sin filtrar por tipo, para aislar si el")
print("   problema es el tipo_bucket o directamente que no está en ventas)")
print("=" * 70)
sin_match = con.execute("""
    SELECT DOCUMENTO, FECHA_EMISION 
    FROM pendientes_despacho 
    WHERE VENDEDOR = 'Sin vendedor' 
    ORDER BY FECHA_EMISION DESC 
    LIMIT 10
""").fetchall()
for documento, fecha_emision in sin_match:
    numero = "".join(c for c in documento if c.isdigit())
    match_libre = con.execute("""
        SELECT NUMERO_DOCUMENTO, TIPO_DOCUMENTO, VENDEDOR, FECHA_OBJ 
        FROM ventas 
        WHERE regexp_extract(NUMERO_DOCUMENTO, '(\\d+)', 1) = ?
        LIMIT 3
    """, [numero]).fetchall()
    print(f"  {documento} (emitido {fecha_emision}) -> ¿aparece en ventas? {match_libre or 'NO, en ninguna parte'}")

con.close()