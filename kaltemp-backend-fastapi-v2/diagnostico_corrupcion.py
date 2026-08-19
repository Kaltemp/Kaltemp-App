# ============================================================
# ARCHIVO: diagnostico_corrupcion.py
# QUE HACE: prueba abrir kaltemp_matrix.duckdb.CORRUPTO_BACKUP (la copia
# de respaldo, NO el archivo original) y cuenta las filas de cada tabla
# por separado, para ver si la corrupción es total o afecta solo a
# algunas tablas. No escribe nada -- solo lee.
#
# COMO USARLO:
#   1. Copia este archivo a C:\kaltemp_app\kaltemp-backend-fastapi-v2
#      (la misma carpeta donde está kaltemp_matrix.duckdb)
#   2. Abre PowerShell ahí (con el venv activado)
#   3. Corre:
#      python diagnostico_corrupcion.py
# ============================================================
import os
import duckdb

AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(AQUI, "kaltemp_matrix.duckdb.CORRUPTO_BACKUP")


def main():
    if not os.path.exists(ARCHIVO):
        print(f"❌ No encontré {ARCHIVO}")
        print("   Asegúrate de haber copiado este script junto a kaltemp_matrix.duckdb.CORRUPTO_BACKUP")
        return

    print(f"🔎 Probando abrir: {ARCHIVO}\n")

    try:
        con = duckdb.connect(ARCHIVO, read_only=True)
        print("✅ La conexión se pudo abrir (read_only=True).\n")
    except Exception as e:
        print(f"❌ NO se pudo ni abrir la conexión: {type(e).__name__}: {e}")
        print("\n⚠️ Esto indica corrupción a nivel de todo el archivo (catálogo/metadata).")
        return

    try:
        tablas = [r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name"
        ).fetchall()]
        print(f"📋 {len(tablas)} tablas encontradas en el catálogo:\n")
    except Exception as e:
        print(f"❌ Se pudo conectar, pero NO se pudo ni listar las tablas: {type(e).__name__}: {e}")
        con.close()
        return

    sanas = []
    rotas = []
    for t in tablas:
        try:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            print(f"   ✅ {t}: {n} filas")
            sanas.append(t)
        except Exception as e:
            print(f"   ❌ {t}: ERROR -- {type(e).__name__}: {e}")
            rotas.append(t)

    con.close()

    print("\n" + "=" * 60)
    print(f"RESUMEN: {len(sanas)} tablas OK, {len(rotas)} tablas con error.")
    if rotas:
        print(f"Tablas dañadas: {', '.join(rotas)}")
    print("=" * 60)


if __name__ == "__main__":
    main()