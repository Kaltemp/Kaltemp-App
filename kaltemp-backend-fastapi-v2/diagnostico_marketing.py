"""
Diagnostico rapido: compara el total de inversion en marketing usando
el filtro VIEJO (solo "Fecha Inicio" dentro del rango) vs el filtro NUEVO
(traslape "Fecha Inicio" / "Fecha Fin"), para las tablas mkt_inversion_meta
y mkt_inversion_google, marca Kaltemp, rango 2026-08-10 a 2026-08-16.

No depende de pandas ni del servidor -- lee directo desde el .duckdb.

Uso:
    python diagnostico_marketing.py
"""
import duckdb
import re
import datetime as dt

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"
FECHA_INICIO = dt.date(2026, 8, 10)
FECHA_FIN = dt.date(2026, 8, 16)
MARCA = "Kaltemp"


def limpiar_numero(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    val_str = re.sub(r'[^\d.,-]', '', val_str)
    if not val_str:
        return 0.0
    if "." in val_str and "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    elif "." in val_str and len(val_str.split(".")[-1]) == 3:
        val_str = val_str.replace(".", "")
    elif "," in val_str:
        val_str = val_str.replace(",", ".")
    try:
        return float(val_str)
    except Exception:
        return 0.0


def parse_fecha(val):
    if val is None:
        return None
    if isinstance(val, dt.datetime):
        return val.date()
    if isinstance(val, dt.date):
        return val
    try:
        return dt.datetime.fromisoformat(str(val)[:19]).date()
    except Exception:
        return None


con = duckdb.connect(DUCKDB_PATH, read_only=True)

total_viejo = 0.0
total_nuevo = 0.0
n_filas = 0
n_marca_distinta = 0
n_sin_fecha = 0
filas_nuevo_no_viejo = []

for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    cur = con.execute(f'SELECT "Campaña", "Fecha Inicio", "Fecha Fin", "Gasto", "Marca" FROM {tabla}')
    cols = [c[0] for c in cur.description]
    for fila in cur.fetchall():
        d = dict(zip(cols, fila))
        n_filas += 1
        marca = str(d.get("Marca") or "Kaltemp").strip()
        if marca.upper() != MARCA.upper():
            n_marca_distinta += 1
            continue

        fi = parse_fecha(d.get("Fecha Inicio"))
        ff = parse_fecha(d.get("Fecha Fin")) or fi
        gasto = limpiar_numero(d.get("Gasto"))
        if fi is None:
            n_sin_fecha += 1
            continue

        en_rango_viejo = FECHA_INICIO <= fi <= FECHA_FIN
        en_rango_nuevo = (ff >= FECHA_INICIO) and (fi <= FECHA_FIN)

        if en_rango_viejo:
            total_viejo += gasto
        if en_rango_nuevo:
            total_nuevo += gasto
        if en_rango_nuevo and not en_rango_viejo:
            filas_nuevo_no_viejo.append((tabla, d.get("Campaña"), fi, ff, gasto))

print(f"Rango consultado: {FECHA_INICIO} a {FECHA_FIN}, marca={MARCA}")
print(f"Filas totales leidas: {n_filas} (marca distinta descartadas: {n_marca_distinta}, sin fecha: {n_sin_fecha})")
print()
print(f"TOTAL con filtro VIEJO (solo Fecha Inicio en rango): {total_viejo:,.0f}")
print(f"TOTAL con filtro NUEVO (traslape Fecha Inicio/Fecha Fin): {total_nuevo:,.0f}")
print()
print(f"Campañas que el filtro NUEVO suma y el VIEJO no ({len(filas_nuevo_no_viejo)}):")
for tabla, camp, fi, ff, gasto in filas_nuevo_no_viejo:
    print(f"  [{tabla}] {camp}: {fi} -> {ff}  gasto={gasto:,.0f}")