"""
diagnostico_enviame.py — Exploratorio: la API clásica de Envíame (company_id
+ api-key, confirmada por las variables ENVIAME_API_KEY / COMPANY_ID en tu
.env) no tiene una documentación fácilmente indexable por búsqueda, así que
este script prueba varias combinaciones razonables de endpoint + formato de
autenticación, en vez de asumir una a ciegas.

Objetivo: encontrar el campo que Envíame usa para la referencia externa
(candidato fuerte: "imported_id", visto en la documentación de webhooks de
Envíame) -- el dato que ustedes pasan como # de pedido (D2C) o # de boleta/
factura (Showroom/Distribuidores) al crear el envío.

Uso (ya no hace falta exportar variables a mano -- se cargan solas desde
el .env de la raíz del proyecto):
    python diagnostico_enviame.py
"""
import os
import json
import requests
from dotenv import load_dotenv

# El .env con las credenciales de Envíame vive en la RAÍZ del proyecto
# (kaltemp-backend-fastapi-v2/.env), no en backend/.env -- mismo hallazgo
# que ya confirmamos con falabella_client.py. Este script vive en
# backend/, así que sube un solo nivel.
# override=True es CRÍTICO acá: si en esta misma sesión de PowerShell ya
# se seteó $env:ENVIAME_API_KEY a mano (aunque sea con un valor de
# ejemplo/placeholder), load_dotenv() por defecto NO lo pisa -- override=True
# fuerza a que el .env real siempre gane, sin importar qué haya quedado
# pegado en la terminal.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"), override=True)

API_KEY = os.getenv("ENVIAME_API_KEY")
# COMPANY_ID es el nombre real de la variable en tu .env (confirmado).
# Se revisa primero -- ENVIAME_COMPANY_ID queda solo como respaldo, pero
# si esa variable quedó "sucia" en la sesión de PowerShell de un intento
# anterior, override=True no la toca (no existe con ese nombre en el
# .env), así que no debe tener prioridad.
COMPANY_ID = os.getenv("COMPANY_ID") or os.getenv("ENVIAME_COMPANY_ID")

if not API_KEY or not COMPANY_ID:
    print("Faltan ENVIAME_API_KEY y/o ENVIAME_COMPANY_ID (o COMPANY_ID) en el .env de la raíz del proyecto.")
    raise SystemExit(1)

# Confirmación enmascarada (nunca el valor completo) de que se está usando
# el valor real del .env, no un placeholder viejo pegado en la sesión.
print(f"ENVIAME_API_KEY cargada: largo={len(API_KEY)}, empieza con {API_KEY[:3]!r}...")
print(f"ENVIAME_COMPANY_ID cargada: {COMPANY_ID!r}")

BASE_URL = "https://api.enviame.io"

# Combinaciones candidatas de endpoint + headers/params a probar. Se
# detiene en la primera que responda 200 con un JSON que parezca una
# lista de envíos.
CANDIDATOS = [
    {
        "nombre": "headers api-key/company-id, /deliveries",
        "url": f"{BASE_URL}/deliveries",
        "headers": {"api-key": API_KEY, "company-id": str(COMPANY_ID)},
        "params": {"limit": 3},
    },
    {
        "nombre": "headers api-key/company_id, /deliveries",
        "url": f"{BASE_URL}/deliveries",
        "headers": {"api-key": API_KEY, "company_id": str(COMPANY_ID)},
        "params": {"limit": 3},
    },
    {
        "nombre": "query params, /deliveries",
        "url": f"{BASE_URL}/deliveries",
        "headers": {},
        "params": {"api_key": API_KEY, "company_id": str(COMPANY_ID), "limit": 3},
    },
    {
        "nombre": "headers api-key/company-id, /v1/deliveries",
        "url": f"{BASE_URL}/v1/deliveries",
        "headers": {"api-key": API_KEY, "company-id": str(COMPANY_ID)},
        "params": {"limit": 3},
    },
    {
        "nombre": "headers api-key/company-id, /shippings",
        "url": f"{BASE_URL}/shippings",
        "headers": {"api-key": API_KEY, "company-id": str(COMPANY_ID)},
        "params": {"limit": 3},
    },
    {
        "nombre": "headers Authorization Bearer, /deliveries",
        "url": f"{BASE_URL}/deliveries",
        "headers": {"Authorization": f"Bearer {API_KEY}", "company-id": str(COMPANY_ID)},
        "params": {"limit": 3},
    },
]


def main():
    for candidato in CANDIDATOS:
        print(f"\n--- Probando: {candidato['nombre']} ---")
        print(f"    GET {candidato['url']} params={candidato['params']}")
        try:
            res = requests.get(
                candidato["url"],
                headers=candidato["headers"],
                params=candidato["params"],
                timeout=15,
            )
        except Exception as e:
            print(f"    ERROR de red: {e}")
            continue

        print(f"    Status: {res.status_code}")
        if res.status_code != 200:
            print(f"    Respuesta: {res.text[:300]}")
            continue

        try:
            data = res.json()
        except Exception:
            print(f"    No es JSON válido: {res.text[:300]}")
            continue

        print("    ¡200 OK! Respuesta cruda (primeros 2000 caracteres):")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
        print(f"\n>>> Esta combinación funcionó: {candidato['nombre']}")
        print(">>> Revisa arriba si aparece 'imported_id', 'identifier', 'reference' u otro")
        print(">>> campo que reconozcas como el N° de pedido/boleta que ustedes pasan.")
        return

    print("\nNinguna combinación funcionó. Vamos a necesitar el sync_enviame.py real,")
    print("o que revises en el dashboard de Envíame (Configuración > API) el formato exacto.")


if __name__ == "__main__":
    main()