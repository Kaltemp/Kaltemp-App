"""
diagnostico_env_falabella.py — Verifica, SIN mostrar ningún valor real,
por qué falabella_client.py no encuentra FALABELLA_API_KEY/FALABELLA_USER
después de load_dotenv(). Corre esto desde backend/ (o desde backend/sync/,
funciona igual).
"""
import os

ruta_env_relativa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
ruta_env_absoluta = os.path.abspath(ruta_env_relativa)

print(f"Ruta de .env que falabella_client.py intenta cargar:\n  {ruta_env_absoluta}")
print(f"¿Existe ese archivo?: {os.path.exists(ruta_env_absoluta)}")

if os.path.exists(ruta_env_absoluta):
    print("\n--- Nombres de variables encontradas en el archivo (sin valores) ---")
    with open(ruta_env_absoluta, "r", encoding="utf-8-sig") as f:
        for i, linea in enumerate(f, 1):
            linea_limpia = linea.strip()
            if not linea_limpia or linea_limpia.startswith("#"):
                continue
            if "=" in linea_limpia:
                nombre = linea_limpia.split("=", 1)[0].strip()
                print(f"  Línea {i}: {nombre!r}")
            else:
                print(f"  Línea {i}: (sin '=', formato raro) {linea_limpia[:30]!r}")

print("\n--- Cargando con python-dotenv (igual que falabella_client.py) ---")
from dotenv import load_dotenv  # noqa: E402
resultado = load_dotenv(ruta_env_absoluta)
print(f"load_dotenv() devolvió: {resultado}  (True = encontró y parseó el archivo)")

print("\n--- ¿Quedaron las variables en os.environ después de cargar? ---")
for clave in ["FALABELLA_API_KEY", "FALABELLA_USER", "FALABELLA_SELLER_ID"]:
    valor = os.environ.get(clave)
    if valor is None:
        print(f"  {clave}: NO ENCONTRADA")
    else:
        print(f"  {clave}: encontrada (largo={len(valor)} caracteres, empieza con {valor[:3]!r}...)")