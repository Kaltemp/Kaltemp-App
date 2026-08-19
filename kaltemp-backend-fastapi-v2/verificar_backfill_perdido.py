# ============================================================
# ARCHIVO: verificar_backfill_perdido.py
# QUE HACE: consulta de SOLO LECTURA sobre kaltemp_matrix.duckdb ya
# restaurado -- cuenta cuántas filas hay con ORIGEN='FULL_HISTORICO_MANUAL'
# (el backfill manual del 18-ago) y compara contra lo que sabemos que se
# cargó ese día (6971 filas, $985.126.624 bruto total, desglosado por
# canal). Si el conteo da 0 (o muy por debajo), confirma que el backfill
# se perdió en la restauración y hay que volver a cargarlo. No escribe
# nada -- solo lee.
#
# COMO USARLO:
#   1. Copia este archivo a C:\kaltemp_app\kaltemp-backend-fastapi-v2
#      (la misma carpeta donde está kaltemp_matrix.duckdb)
#   2. Abre PowerShell ahí (con el venv activado)
#   3. Corre:
#      python verificar_backfill_perdido.py
# ============================================================
import os
import duckdb

AQUI = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(AQUI, "kaltemp_matrix.duckdb")

# Lo que se confirmó cargado el 18-ago-2026 (del resumen de esa sesión).
ESPERADO_FILAS = 6971
ESPERADO_BRUTO_TOTAL = 985_126_624
ESPERADO_POR_CANAL = {
    "Falabella": 302_328_973,
    "Mercado Libre": 579_730_291,
    "Paris": 82_192_100,
    "Ripley": 20_875_260,
}


def main():
    if not os.path.exists(DB_FILE):
        print(f"❌ No encontré {DB_FILE}")
        print("   Asegúrate de haber copiado este script junto a kaltemp_matrix.duckdb.")
        return

    print(f"🔎 Consultando (solo lectura): {DB_FILE}\n")

    with duckdb.connect(DB_FILE, read_only=True) as con:
        total = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(BRUTO_TOTAL), 0) "
            "FROM ventas WHERE ORIGEN = 'FULL_HISTORICO_MANUAL'"
        ).fetchone()
        filas, bruto = total

        print("=" * 70)
        print(f"Filas encontradas con ORIGEN='FULL_HISTORICO_MANUAL': {filas}")
        print(f"Bruto total de esas filas:                            ${bruto:,.0f}".replace(",", "."))
        print("=" * 70)
        print(f"Esperado (cargado el 18-ago-2026):                    {ESPERADO_FILAS} filas")
        print(f"Bruto esperado:                                       ${ESPERADO_BRUTO_TOTAL:,.0f}".replace(",", "."))
        print()

        if filas == 0:
            print("❌ CONFIRMADO: el backfill histórico NO está en la base restaurada.")
            print("   Hay que volver a correr cargar_ventas_full_historico.py contra esta base.")
        elif filas < ESPERADO_FILAS:
            print(f"⚠️ Hay datos parciales: faltan {ESPERADO_FILAS - filas} filas respecto a lo esperado.")
            print("   Revisar antes de recargar, para no duplicar lo que sí quedó.")
        elif filas == ESPERADO_FILAS:
            print("✅ El backfill YA está completo en la base restaurada -- no hace falta recargarlo.")
        else:
            print(f"⚠️ Hay MÁS filas de las esperadas ({filas} vs {ESPERADO_FILAS}) -- revisar posible duplicado.")

        if filas > 0:
            print("\nDesglose por canal (encontrado vs esperado):")
            desglose = con.execute(
                "SELECT CANAL, COUNT(*), COALESCE(SUM(BRUTO_TOTAL), 0) "
                "FROM ventas WHERE ORIGEN = 'FULL_HISTORICO_MANUAL' "
                "GROUP BY CANAL ORDER BY CANAL"
            ).fetchall()
            for canal, n, s in desglose:
                esperado = ESPERADO_POR_CANAL.get(canal)
                comp = f"(esperado: ${esperado:,.0f})".replace(",", ".") if esperado else "(canal no esperado)"
                print(f"   {canal or '(sin canal)'}: {n} filas, ${s:,.0f} {comp}".replace(",", "."))


if __name__ == "__main__":
    main()