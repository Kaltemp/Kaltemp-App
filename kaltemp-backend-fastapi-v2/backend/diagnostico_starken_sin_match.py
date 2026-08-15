# ============================================================
# ARCHIVO: diagnostico_starken_sin_match.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_starken_sin_match.py
# ============================================================
"""
diagnostico_starken_sin_match.py — STARKEN matchea mucho peor que
BLUEXPRESS/CHILEPARCELS (9.5% vs 64-73%, confirmado real 13-ago-2026),
al revés de lo esperado (STARKEN es el courier de Showroom, debería
ser el más fácil). Para cada envío STARKEN sin match, busca el mismo
nombre en `ventas` SIN restricción de fecha -- si aparece, el problema
es la ventana de días (el documento está más lejos de lo que
permitimos); si NO aparece ni sin restricción, el problema es el
formato del nombre (mayúsculas, razón social vs persona, tildes, etc.)
o que ese cliente simple no tiene ninguna venta en la base.

Solo lee datos, no modifica nada.

Uso:
    cd backend
    python diagnostico_starken_sin_match.py
"""
import os
import re
import duckdb
from dotenv import load_dotenv
from collections import Counter

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))


def _normalizar(nombre: str) -> str:
    if not nombre:
        return ""
    limpio = re.sub(r"[^a-záéíóúñ\s]", "", str(nombre).lower())
    palabras = sorted(p for p in limpio.split() if len(p) > 1)
    return " ".join(palabras)


def main():
    con = duckdb.connect(DB_FILE, read_only=True)

    sin_match_starken = con.execute("""
        SELECT e.N_ENVIO_REF, e.CLIENTE, TRY_CAST(e.FECHA_CREACION AS DATE)
        FROM enviame_despachos e
        LEFT JOIN enviame_cruce_ventas c ON c.ID_INTERNO = e.ID_INTERNO
        WHERE c.ID_INTERNO IS NULL AND e.COURIER = 'STARKEN'
        ORDER BY e.FECHA_CREACION DESC
    """).fetchall()

    docs = con.execute("""
        SELECT CAST(NUMERO_DOCUMENTO AS VARCHAR), CLIENTE, TRY_CAST(FECHA_OBJ AS DATE)
        FROM ventas
        WHERE NUMERO_DOCUMENTO IS NOT NULL AND CLIENTE IS NOT NULL
    """).fetchall()

    from collections import defaultdict
    indice = defaultdict(list)
    for numero_doc, cliente, fecha_doc in docs:
        indice[_normalizar(cliente)].append((numero_doc, fecha_doc, cliente))

    print(f"Total envíos STARKEN sin match: {len(sin_match_starken)}\n")

    encontrados_sin_fecha = 0
    no_existe_para_nada = 0
    ejemplos_fecha = []
    ejemplos_ausentes = []

    for ref, cliente_e, fecha_envio in sin_match_starken:
        candidatos = indice.get(_normalizar(cliente_e), [])
        if candidatos:
            encontrados_sin_fecha += 1
            # Guarda la diferencia de días real (sin capar a una ventana)
            if fecha_envio:
                dias_mas_cercano = min(abs((fecha_envio - d[1]).days) for d in candidatos if d[1])
                ejemplos_fecha.append((ref, cliente_e, fecha_envio, dias_mas_cercano, len(candidatos)))
        else:
            no_existe_para_nada += 1
            ejemplos_ausentes.append((ref, cliente_e))

    print(f"El nombre SÍ existe en `ventas` (algún documento, sin restricción de fecha): {encontrados_sin_fecha}")
    print(f"El nombre NO existe en `ventas` para nada: {no_existe_para_nada}\n")

    print("--- Cuando el nombre SÍ existe: distancia en días al documento más cercano ---")
    print(f"{'REF':<14}{'CLIENTE':<28}{'FECHA ENVÍO':<14}{'DÍAS AL MÁS CERCANO':<22}{'# CANDIDATOS'}")
    for ref, cliente, fecha, dias, n_cand in sorted(ejemplos_fecha, key=lambda x: x[3])[:25]:
        print(f"{str(ref):<14}{str(cliente)[:26]:<28}{str(fecha):<14}{dias:<22}{n_cand}")

    print(f"\n--- Cuando el nombre NO existe en absoluto (primeros 15) ---")
    for ref, cliente in ejemplos_ausentes[:15]:
        print(f"  {str(ref):<14}{cliente}")

    con.close()


if __name__ == "__main__":
    main()