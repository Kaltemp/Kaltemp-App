# ============================================================
# ARCHIVO: fix_enviame_costo.py
# QUE HACE: repara el mismo bug de "transacción abortada" en
# backend/sync/actualizar_fletes_enviame.py (paso
# "enviame_despachos.COSTO_ENVIO" del sync_master.py).
#
# COMO USARLO:
#   1. Copia este archivo DENTRO de la carpeta:
#      C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync
#      (la misma carpeta donde está actualizar_fletes_enviame.py)
#   2. Abre PowerShell en esa carpeta (con el venv activado)
#   3. Corre:
#      python fix_enviame_costo.py
#   4. Vuelve a correr sync_master.py (o solo este paso) para confirmar
#      que "enviame_despachos.COSTO_ENVIO" ya no tira error.
# ============================================================
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actualizar_fletes_enviame.py")

TEXTO_VIEJO = '''    con = duckdb.connect(DB_FILE)

    try:
        con.execute("ALTER TABLE enviame_despachos ADD COLUMN ES_COSTO_REAL BOOLEAN DEFAULT FALSE")
    except duckdb.Error:
        pass  # ya existe -- normal en corridas posteriores a la primera
'''

TEXTO_NUEVO = '''    con = duckdb.connect(DB_FILE)

    columnas_existentes = {
        row[0] for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'enviame_despachos'"
        ).fetchall()
    }
    if "ES_COSTO_REAL" not in columnas_existentes:
        con.execute("ALTER TABLE enviame_despachos ADD COLUMN ES_COSTO_REAL BOOLEAN DEFAULT FALSE")
'''


def main():
    if not os.path.exists(ARCHIVO):
        print(f"❌ No encontré el archivo en: {ARCHIVO}")
        print("   Asegúrate de haber copiado fix_enviame_costo.py DENTRO de la carpeta backend/sync.")
        return

    with open(ARCHIVO, "r", encoding="utf-8") as f:
        contenido = f.read()

    if TEXTO_NUEVO in contenido:
        print("✅ El archivo ya tiene el arreglo aplicado. No hay nada que hacer.")
        return

    if TEXTO_VIEJO not in contenido:
        print("⚠️ No encontré el bloque de código esperado en actualizar_fletes_enviame.py.")
        print("   Puede que el archivo ya haya sido editado a mano y quedó distinto.")
        print("   No se modificó nada -- avísale a Claude para revisar el archivo actual.")
        return

    backup = ARCHIVO + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"💾 Respaldo guardado en: {backup}")

    contenido_nuevo = contenido.replace(TEXTO_VIEJO, TEXTO_NUEVO)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido_nuevo)

    print("✅ actualizar_fletes_enviame.py arreglado con éxito.")
    print("   Corre de nuevo sync_master.py (o solo este paso) para confirmar.")


if __name__ == "__main__":
    main()