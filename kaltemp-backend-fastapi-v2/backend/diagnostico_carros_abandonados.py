"""
diagnostico_carros_abandonados.py — Verifica que el módulo de Carros Abandonados
esté conectado a valores reales en kaltemp_matrix.duckdb.

Uso:
    cd C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend
    venv\\Scripts\\activate
    python diagnostico_carros_abandonados.py
"""
import os
import duckdb
from datetime import datetime
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "kaltemp_matrix.duckdb"))

print("=" * 70)
print("DIAGNÓSTICO — CARROS ABANDONADOS")
print("=" * 70)
print(f"📁 DUCKDB_PATH usado: {DB_FILE}")
print(f"   ¿Existe el archivo? {os.path.exists(DB_FILE)}")
print()

if not os.path.exists(DB_FILE):
    print("❌ El archivo .duckdb no existe en esa ruta. Revisa DUCKDB_PATH en tu .env")
    exit(1)

con = duckdb.connect(DB_FILE, read_only=True)

tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
print(f"📋 Tablas encontradas en la DB: {tables}")
print()

if "abandoned_checkouts" not in tables:
    print("❌ La tabla 'abandoned_checkouts' NO existe. Nunca se ha corrido la sync.")
    con.close()
    exit(1)

# 1. Conteo total y por estado
total = con.execute("SELECT COUNT(*) FROM abandoned_checkouts").fetchone()[0]
print(f"🛒 Total de filas en abandoned_checkouts: {total}")

if total == 0:
    print("⚠️  La tabla existe pero está VACÍA. La última sync no trajo datos")
    print("    (o SHOPIFY_TOKEN / SHOPIFY_STORE no están bien configurados).")
    con.close()
    exit(0)

print()
print("📊 Conteo por ESTADO:")
estados = con.execute("""
    SELECT ESTADO, COUNT(*) as cantidad, COUNT(DISTINCT ID_CHECKOUT) as checkouts_unicos
    FROM abandoned_checkouts
    GROUP BY ESTADO
    ORDER BY cantidad DESC
""").df()
print(estados.to_string(index=False))
print()

# 2. Rango de fechas — para saber qué tan reciente es la data
fechas = con.execute("""
    SELECT MIN(FECHA_OBJ) as fecha_min, MAX(FECHA_OBJ) as fecha_max
    FROM abandoned_checkouts
""").fetchone()
print(f"📅 Rango de fechas (FECHA_OBJ): {fechas[0]} → {fechas[1]}")

dias_desde_ultima = None
if fechas[1] is not None:
    dias_desde_ultima = (datetime.now() - fechas[1]).days
    print(f"   → El checkout más reciente es de hace {dias_desde_ultima} día(s)")
    if dias_desde_ultima > 3:
        print("   ⚠️  Han pasado más de 3 días desde el último checkout registrado.")
        print("      Puede ser normal (poca actividad) o la sync no se ha corrido.")
print()

# 3. Última sincronización según sync_meta
if "sync_meta" in tables:
    meta = con.execute("""
        SELECT ultima_actualizacion FROM sync_meta WHERE tabla = 'abandoned_checkouts'
    """).fetchone()
    if meta:
        ultima_sync = meta[0]
        horas_desde_sync = (datetime.now() - ultima_sync).total_seconds() / 3600
        print(f"🕐 Última sincronización registrada: {ultima_sync} (hace {horas_desde_sync:.1f} horas)")
    else:
        print("⚠️  No hay registro en sync_meta para 'abandoned_checkouts' — nunca se ha corrido"
              " sync_abandoned_carts.py, o corrió una versión anterior sin ese registro.")
else:
    print("⚠️  La tabla 'sync_meta' no existe — no se puede saber cuándo fue la última sync.")
print()

# 4. SKUs sin categoría mapeada (afecta el desglose por categoría del módulo)
sin_sku = con.execute("""
    SELECT COUNT(*) FROM abandoned_checkouts WHERE SKU IS NULL OR TRIM(SKU) = ''
""").fetchone()[0]
print(f"🏷️  Filas sin SKU (caen a categorización por keyword / 'Otros'): {sin_sku} de {total}"
      f" ({sin_sku/total*100:.1f}%)")
print()

# 5. Verificación cruzada de montos (oportunidad perdida real)
oportunidad = con.execute("""
    SELECT SUM(TOTAL_PRICE) FROM (
        SELECT DISTINCT ID_CHECKOUT, TOTAL_PRICE
        FROM abandoned_checkouts
        WHERE ESTADO = 'ABANDONADO'
    )
""").fetchone()[0]
print(f"💰 Oportunidad perdida total (histórica, sin filtro de fecha): "
      f"${oportunidad:,.0f}" if oportunidad else "💰 Oportunidad perdida total: $0")
print()

# 6. Muestra de 5 filas reales para inspección visual
print("🔍 Muestra de 5 filas reales:")
muestra = con.execute("""
    SELECT ID_CHECKOUT, FECHA_OBJ, PRODUCTO, SKU, PRECIO_UNITARIO, TOTAL_PRICE, ESTADO
    FROM abandoned_checkouts
    ORDER BY FECHA_OBJ DESC
    LIMIT 5
""").df()
print(muestra.to_string(index=False))
print()

# 7. Comparación en vivo contra Shopify (opcional, requiere credenciales)
print("=" * 70)
print("🌐 Comparación en vivo contra la API de Shopify...")
try:
    import requests
    SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
    SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "kaltemp.myshopify.com")
    if SHOPIFY_STORE:
        SHOPIFY_STORE = SHOPIFY_STORE.replace("https://", "").replace("http://", "").strip("/")

    if not SHOPIFY_TOKEN:
        print("⚠️  SHOPIFY_TOKEN no está en el .env — no se puede comparar en vivo.")
    else:
        url = f"https://{SHOPIFY_STORE}/admin/api/2024-04/checkouts.json?limit=250&status=any"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code == 200:
            checkouts_live = res.json().get("checkouts", [])
            print(f"   Checkouts devueltos AHORA por Shopify (máx 250, sin paginar): {len(checkouts_live)}")
            print(f"   Checkouts únicos guardados en DuckDB: "
                  f"{con.execute('SELECT COUNT(DISTINCT ID_CHECKOUT) FROM abandoned_checkouts').fetchone()[0]}")
            if len(checkouts_live) == 250:
                print("   ⚠️  Shopify devolvió exactamente 250 (el límite) — es posible que existan"
                      " más checkouts que no se están capturando por falta de paginación.")
        else:
            print(f"   ❌ Error consultando Shopify ({res.status_code}): {res.text[:200]}")
except Exception as e:
    print(f"   ❌ No se pudo comparar en vivo: {e}")

con.close()

print()
print("=" * 70)
print("✅ Diagnóstico completo. Copia y pega este output completo para revisión.")
print("=" * 70)