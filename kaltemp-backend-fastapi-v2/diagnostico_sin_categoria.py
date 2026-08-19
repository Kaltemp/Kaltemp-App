"""
Lista las campanas (Meta + Google) que caen en el bucket "Sin Categoria"
para el rango de fechas dado -- es decir, campanas cuyo nombre no matchea
ninguna palabra clave de categoria (SANITARIA, PISCINA, GENERADOR,
CALEFACTOR/CALEFACCION, PERGOLA, TERMO, VENTILACION, HOT TUB, AIRE,
HERRAMIENTA, MANGUERA, ILUMINACION) ni esta en la tabla de mapeo manual
campanas_categoria.

Sirve para confirmar si son campanas tipo PMax / Catalogo (que por
naturaleza cubren todo el catalogo, no una categoria puntual) u otra cosa.

Uso:
    python diagnostico_sin_categoria.py
"""
import duckdb
import re
import unicodedata
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


def normalizar_texto(s):
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("-", " ").replace("_", " ")


MAPA_CATEGORIA_REAL = [
    ("SANITARIA", "BC Agua Sanitaria"),
    ("PISCINA", "Temperado de Piscina"),
    ("GENERADOR", "Generadores"),
    ("CALEFACTOR", "Calefacción"),
    ("CALEFACCION", "Calefacción"),
    ("PERGOLA", "Pérgolas"),
    ("TERMO", "Termos"),
    ("VENTILACION", "Ventilación"),
    ("HOT TUB", "Hot Tub"),
    ("AIRE", "Aire Acondicionado"),
    ("HERRAMIENTA", "Herramientas"),
    ("MANGUERA", "Mangueras"),
    ("ILUMINACION", "Iluminación"),
]


def mapear_categoria_real(nombre_campana):
    n = normalizar_texto(nombre_campana)
    for palabra, categoria in MAPA_CATEGORIA_REAL:
        if palabra in n:
            return categoria
    return None


def obtener_mapa_manual():
    try:
        from categorias_db import get_categorias_connection, init_categorias_db
        init_categorias_db()
        with get_categorias_connection() as con:
            filas = con.execute("SELECT campana, categoria FROM campanas_categoria").fetchall()
            return {row["campana"]: row["categoria"] for row in filas}
    except Exception as e:
        print(f"(no se pudo leer mapeo manual: {e} -- se sigue solo con palabras clave)")
        return {}


mapa_manual = obtener_mapa_manual()
con = duckdb.connect(DUCKDB_PATH, read_only=True)

sin_categoria = []  # (tabla, campana, fecha_inicio, fecha_fin, gasto)
total_sin_categoria = 0.0

for tabla in ("mkt_inversion_meta", "mkt_inversion_google"):
    cur = con.execute(f'SELECT "Campaña", "Fecha Inicio", "Fecha Fin", "Gasto", "Marca" FROM {tabla}')
    cols = [c[0] for c in cur.description]
    for fila in cur.fetchall():
        d = dict(zip(cols, fila))
        marca = str(d.get("Marca") or "Kaltemp").strip()
        if marca.upper() != MARCA.upper():
            continue

        fi = parse_fecha(d.get("Fecha Inicio"))
        ff = parse_fecha(d.get("Fecha Fin")) or fi
        if fi is None:
            continue

        en_rango = (ff >= FECHA_INICIO) and (fi <= FECHA_FIN)
        if not en_rango:
            continue

        nombre_campana = str(d.get("Campaña")).strip()
        cat_camp = mapa_manual.get(nombre_campana) or mapear_categoria_real(nombre_campana)
        if cat_camp:
            continue  # tiene categoria, no nos interesa aca

        gasto = limpiar_numero(d.get("Gasto"))
        total_sin_categoria += gasto
        sin_categoria.append((tabla, nombre_campana, fi, ff, gasto))

# Agrupar por nombre de campana (puede haber varias filas/semanas por campana)
agrupado = {}
for tabla, camp, fi, ff, gasto in sin_categoria:
    key = (tabla, camp)
    if key not in agrupado:
        agrupado[key] = {"gasto": 0.0, "fi_min": fi, "ff_max": ff}
    agrupado[key]["gasto"] += gasto
    agrupado[key]["fi_min"] = min(agrupado[key]["fi_min"], fi)
    agrupado[key]["ff_max"] = max(agrupado[key]["ff_max"], ff)

print(f"Rango: {FECHA_INICIO} a {FECHA_FIN}, marca={MARCA}")
print(f"TOTAL 'Sin Categoría': {total_sin_categoria:,.0f}")
print()
print(f"Campañas sin categoría mapeada ({len(agrupado)}):")
filas_ordenadas = sorted(agrupado.items(), key=lambda kv: kv[1]["gasto"], reverse=True)
for (tabla, camp), info in filas_ordenadas:
    print(f"  [{tabla:18s}] {camp:50s}  {info['fi_min']} -> {info['ff_max']}  gasto={info['gasto']:,.0f}")