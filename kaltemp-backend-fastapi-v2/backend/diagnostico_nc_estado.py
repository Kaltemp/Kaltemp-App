"""
diagnostico_nc_estado.py — Verifica el estado de notas_credito_desfase:
si existe, si tiene la columna DOCUMENTO_REFERENCIA, cuántas filas tiene,
y si la Boleta N° 37573 aparece referenciada.

Uso (desde backend/, con el venv activo):
    python diagnostico_nc_estado.py
"""
import duckdb

DB_PATH = "../kaltemp_matrix.duckdb"  # el .duckdb vive un nivel arriba de backend/

con = duckdb.connect(DB_PATH, read_only=True)

print("=== 1) ¿Existe la tabla? ===")
tablas = con.execute(
    "SELECT table_name FROM information_schema.tables WHERE table_name ILIKE '%notas_credito%'"
).fetchall()
print(tablas)

if not tablas:
    print("\n❌ La tabla notas_credito_desfase NO existe en este .duckdb.")
    con.close()
    raise SystemExit

print("\n=== 2) Columnas de la tabla ===")
columnas = con.execute(
    "SELECT column_name FROM information_schema.columns WHERE table_name = 'notas_credito_desfase'"
).fetchall()
print(columnas)

print("\n=== 3) Total de filas ===")
print(con.execute("SELECT COUNT(*) FROM notas_credito_desfase").fetchall())

print("\n=== 4) Filas con DOCUMENTO_REFERENCIA no nulo ===")
try:
    print(con.execute(
        "SELECT COUNT(*) FROM notas_credito_desfase WHERE DOCUMENTO_REFERENCIA IS NOT NULL"
    ).fetchall())
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 5) ¿La Boleta N° 37573 aparece referenciada? ===")
try:
    filas = con.execute(
        "SELECT DOCUMENTO, DOCUMENTO_REFERENCIA, CLIENTE, MONTO "
        "FROM notas_credito_desfase WHERE DOCUMENTO_REFERENCIA = 'BOLETA N\u00b0 37573'"
    ).fetchall()
    print(filas)
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 6) sync_meta: última actualización de la tabla ===")
try:
    print(con.execute(
        "SELECT * FROM sync_meta WHERE tabla = 'notas_credito_desfase'"
    ).fetchall())
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 7) Comparación de caracteres: DOCUMENTO_REFERENCIA vs DOCUMENTO ===")
print("(buscamos si ambas tablas usan el mismo símbolo para 'N°')")

print("\n--- Ejemplo de DOCUMENTO_REFERENCIA (notas_credito_desfase) ---")
ejemplo_nc = con.execute(
    "SELECT DOCUMENTO_REFERENCIA FROM notas_credito_desfase "
    "WHERE DOCUMENTO_REFERENCIA LIKE '%37573%' OR DOCUMENTO_REFERENCIA LIKE '%37634%' "
    "LIMIT 3"
).fetchall()
for (val,) in ejemplo_nc:
    print(repr(val), [hex(ord(c)) for c in val if not c.isalnum() and c != ' '])

print("\n--- Ejemplo de DOCUMENTO (pendientes_despacho_docs) ---")
try:
    ejemplo_p = con.execute(
        "SELECT DOCUMENTO FROM pendientes_despacho_docs "
        "WHERE DOCUMENTO LIKE '%37573%' LIMIT 3"
    ).fetchall()
    for (val,) in ejemplo_p:
        print(repr(val), [hex(ord(c)) for c in val if not c.isalnum() and c != ' '])
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 8) Búsqueda flexible (ignorando el símbolo) para 37573 ===")
flex = con.execute(
    "SELECT DOCUMENTO_REFERENCIA FROM notas_credito_desfase "
    "WHERE DOCUMENTO_REFERENCIA LIKE '%37573%'"
).fetchall()
print(flex)

print("\n=== 9) ¿Está la Nota de Crédito N° 4304 en la tabla? (la de la Boleta 37573) ===")
nc4304 = con.execute(
    "SELECT DOCUMENTO, DOCUMENTO_REFERENCIA, CLIENTE, MONTO, FECHA_EMISION "
    "FROM notas_credito_desfase WHERE DOCUMENTO LIKE '%4304%'"
).fetchall()
print(nc4304)

print("\n=== 10) Total de notas con DOCUMENTO_REFERENCIA nulo (no identificadas) ===")
print(con.execute(
    "SELECT COUNT(*) FROM notas_credito_desfase WHERE DOCUMENTO_REFERENCIA IS NULL"
).fetchall())

print("\n=== 11) Rango de fechas de las notas de crédito en la tabla ===")
print(con.execute(
    "SELECT MIN(FECHA_EMISION), MAX(FECHA_EMISION) FROM notas_credito_desfase"
).fetchall())

con.close()