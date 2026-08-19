"""
diagnostico_logistica.py — SOLO LECTURA, no modifica nada.

Chequea por qué "Control Logístico" (GET /api/logistica, tabla
enviame_despachos) podría estar mostrando "sin datos":

1. ¿Existe la tabla enviame_despachos?
2. Total de filas y filas en tu rango de fechas actual (ajusta FECHA_INICIO
   / FECHA_FIN abajo si quieres otro rango -- por defecto usa los últimos
   30 días).
3. ¿Cuántas de esas filas tienen COSTO_ENVIO en 0/NULL? (si el paso
   "enviame_despachos.COSTO_ENVIO" -- actualizar_fletes_enviame.py -- no
   corrió o falló, esto queda en 0 aunque el despacho SÍ exista).
4. ¿Están las credenciales ENVIAME_API_KEY / ENVIAME_COMPANY_ID presentes
   en el .env? (si faltan, actualizar_fletes_enviame.py lanza
   RuntimeError apenas se importa, y ese paso de sync_master.py falla
   siempre, silenciosamente, gracias al try/except que rodea cada paso).
5. Última fecha de despacho sincronizada (para saber si sync_enviame.py
   está corriendo al día).

Correr desde backend/sync/ (o ajustar DB_FILE abajo si tu .duckdb vive en
otra ruta):
    python diagnostico_logistica.py
"""
import os
import duckdb
from datetime import date, timedelta
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))

FECHA_FIN = date.today()
FECHA_INICIO = FECHA_FIN - timedelta(days=30)

print(f"📂 DB: {DB_FILE}")
print(f"📅 Rango de chequeo: {FECHA_INICIO} → {FECHA_FIN}\n")

con = duckdb.connect(DB_FILE, read_only=True)

tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
if "enviame_despachos" not in tablas:
    print("❌ La tabla 'enviame_despachos' NO existe en esta base -- ese es el problema.")
    print("   Corre sync_enviame.py para crearla y poblarla por primera vez.")
    con.close()
    raise SystemExit(0)

print("✅ La tabla 'enviame_despachos' existe.\n")

total = con.execute("SELECT COUNT(*) FROM enviame_despachos").fetchone()[0]
print(f"📦 Total histórico de despachos en la tabla: {total}")

en_rango = con.execute(
    "SELECT COUNT(*) FROM enviame_despachos WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?",
    [FECHA_INICIO, FECHA_FIN],
).fetchone()[0]
print(f"📦 Despachos en el rango {FECHA_INICIO} → {FECHA_FIN}: {en_rango}")

ultima_fecha = con.execute(
    "SELECT MAX(TRY_CAST(FECHA_CREACION AS DATE)) FROM enviame_despachos"
).fetchone()[0]
print(f"🕒 Último despacho sincronizado: {ultima_fecha}")

if en_rango > 0:
    stats_costo = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN COSTO_ENVIO IS NULL OR COSTO_ENVIO = 0 THEN 1 ELSE 0 END) AS en_cero_o_null,
            SUM(COSTO_ENVIO) AS suma_costo
        FROM enviame_despachos
        WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?
    """, [FECHA_INICIO, FECHA_FIN]).fetchone()
    total_r, en_cero, suma = stats_costo
    print(f"\n💰 De esos {total_r} despachos en el rango:")
    print(f"   - {en_cero} tienen COSTO_ENVIO en 0/NULL ({en_cero/total_r*100:.1f}%)")
    print(f"   - SUM(COSTO_ENVIO) total del rango: ${suma or 0:,.0f}")
    if en_cero == total_r:
        print("   ⚠️  El 100% de los despachos del rango tiene COSTO_ENVIO en 0/NULL.")
        print("       Esto hace que 'Costo Envíame' y 'Margen de Flete' se vean vacíos/raros")
        print("       en el módulo, aunque 'Total Despachos' sí muestre número.")
        print("       Causa probable: el paso 'enviame_despachos.COSTO_ENVIO' (actualizar_fletes_enviame.py)")
        print("       no ha corrido, o está fallando, para estos despachos.")

    comunas = con.execute("""
        SELECT COMUNA, COUNT(*) FROM enviame_despachos
        WHERE TRY_CAST(FECHA_CREACION AS DATE) BETWEEN ? AND ?
          AND COMUNA IS NOT NULL AND TRIM(COMUNA) != ''
        GROUP BY COMUNA ORDER BY 2 DESC LIMIT 5
    """, [FECHA_INICIO, FECHA_FIN]).fetchall()
    print(f"\n🏙️  Top comunas en el rango: {comunas}")
else:
    print("\n⚠️  0 despachos en este rango de fechas -- por eso el módulo se ve vacío.")
    print("    Puede ser que simplemente no haya habido despachos en estos 30 días,")
    print("    o que sync_enviame.py no esté corriendo al día (revisa 'Último despacho")
    print("    sincronizado' arriba -- si es una fecha vieja, ese es el problema real).")

con.close()

print("\n🔑 Credenciales Envíame en el .env:")
api_key = os.getenv("ENVIAME_API_KEY")
company_id = os.getenv("ENVIAME_COMPANY_ID") or os.getenv("COMPANY_ID")
print(f"   ENVIAME_API_KEY presente: {'sí' if api_key else 'NO -- falta'}")
print(f"   ENVIAME_COMPANY_ID presente: {'sí' if company_id else 'NO -- falta'}")
if not api_key or not company_id:
    print("   ⚠️  Sin estas credenciales, actualizar_fletes_enviame.py lanza un error apenas")
    print("       se importa, y ese paso de sync_master.py SIEMPRE falla (silenciosamente,")
    print("       protegido por el try/except de cada paso) -- COSTO_ENVIO se queda en 0.")

print("\n✅ Diagnóstico completo.")