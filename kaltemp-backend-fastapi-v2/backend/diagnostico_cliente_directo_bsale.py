# ============================================================
# ARCHIVO: diagnostico_cliente_directo_bsale.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\diagnostico_cliente_directo_bsale.py
# ============================================================
"""
diagnostico_cliente_directo_bsale.py — Para un envío STARKEN que no
matcheó en `ventas` por nombre, busca ese mismo cliente DIRECTO en la
API de Bsale (/v1/clients.json), no en la copia sincronizada. Esto
aísla dos causas posibles muy distintas:

  A) El cliente SÍ existe en Bsale (con RUT y nombre real) pero el
     nombre está escrito distinto que en Envíame (típico: orden
     apellido/nombre, razón social vs nombre de fantasía, tildes) --
     arreglo: mejorar la normalización de nombres en el cruce.

  B) El cliente NO existe en Bsale con ningún nombre parecido -- esa
     venta puede no estar asociada a un cliente real en Bsale (venta
     "genérica"/sin cliente registrado), o el documento que le
     corresponde nunca se sincronizó a `ventas` -- arreglo distinto,
     hay que revisar sync_ventas.py o cómo se registra esa venta en
     Bsale mismo.

Uso:
    cd backend
    python diagnostico_cliente_directo_bsale.py "claudio espinosa Howard"
"""
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync"))
from bsale_client import bsale_get_all, bsale_get_one  # noqa: E402


def _normalizar(nombre: str) -> set:
    if not nombre:
        return set()
    limpio = re.sub(r"[^a-záéíóúñ\s]", "", nombre.lower())
    return set(p for p in limpio.split() if len(p) > 1)


def main():
    if len(sys.argv) < 2:
        print('Uso: python diagnostico_cliente_directo_bsale.py "Nombre Completo"')
        return

    nombre_buscado = sys.argv[1]
    palabras_buscadas = _normalizar(nombre_buscado)

    print(f"Buscando en Bsale clientes que compartan alguna palabra con: {nombre_buscado!r}\n")

    try:
        total_cuenta = bsale_get_one("clients.json", params={"limit": 1}).get("count")
        print(f"Total de clientes en la cuenta Bsale: {total_cuenta}")
    except Exception:
        total_cuenta = None

    print("(Recorriendo /v1/clients.json completo -- puede tardar unos minutos)\n")

    encontrados = []
    revisados = 0
    for cliente in bsale_get_all("clients.json"):
        revisados += 1
        if revisados % 2000 == 0:
            print(f"  ...{revisados} clientes revisados")

        nombre_completo = " ".join(filter(None, [
            cliente.get("firstName", ""), cliente.get("lastName", ""),
        ])).strip()
        razon_social = cliente.get("company", "") or ""

        palabras_cliente = _normalizar(nombre_completo) | _normalizar(razon_social)
        # Exige 2+ palabras en común (antes bastaba 1, ej. "Claudio" solo,
        # lo que traía cientos de falsos positivos sin relación real).
        # Si el nombre buscado tiene una sola palabra, se exige esa igual.
        minimo = min(2, len(palabras_buscadas))
        if len(palabras_buscadas & palabras_cliente) >= minimo:
            encontrados.append({
                "id": cliente.get("id"),
                "nombre": nombre_completo,
                "razon_social": razon_social,
                "rut": cliente.get("code"),
                "email": cliente.get("email"),
            })

    print(f"\nClientes revisados: {revisados}")
    if encontrados:
        print(f"✅ Encontrados {len(encontrados)} cliente(s) con nombre parecido en Bsale:\n")
        for c in encontrados[:10]:
            print(f"  id={c['id']}  nombre={c['nombre']!r}  razón_social={c['razon_social']!r}  "
                  f"RUT={c['rut']!r}  email={c['email']!r}")
    else:
        print("❌ NINGÚN cliente en Bsale comparte nombre con esa búsqueda -- "
              "esa venta probablemente no tiene un cliente registrado en Bsale, "
              "o el nombre está MUY distinto (revisar a mano en el panel de Bsale).")


if __name__ == "__main__":
    main()