# ============================================================
# ARCHIVO: fix_sync_ventas.py
# QUE HACE: repara automáticamente el bug de "transacción abortada"
# en backend/sync/sync_ventas.py (la funcion _escribir_ventas_en_duckdb).
#
# COMO USARLO:
#   1. Copia este archivo DENTRO de la carpeta:
#      C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync
#      (la misma carpeta donde está sync_ventas.py)
#   2. Abre PowerShell en esa carpeta (donde ya tienes el venv activado)
#   3. Corre:
#      python fix_sync_ventas.py
#   4. Va a avisar si el arreglo se aplico bien, y va a dejar una copia
#      de respaldo llamada sync_ventas.py.bak por si algo sale mal.
# ============================================================
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_ventas.py")

TEXTO_VIEJO = '''        try:
            con.execute("ALTER TABLE ventas ADD COLUMN ES_GLOSA_SERVICIO BOOLEAN DEFAULT FALSE")
        except duckdb.Error:
            pass
'''

TEXTO_NUEVO = '''        columnas_existentes = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'ventas'"
            ).fetchall()
        }
        if "ES_GLOSA_SERVICIO" not in columnas_existentes:
            con.execute("ALTER TABLE ventas ADD COLUMN ES_GLOSA_SERVICIO BOOLEAN DEFAULT FALSE")
'''


def main():
    if not os.path.exists(ARCHIVO):
        print(f"❌ No encontré el archivo en: {ARCHIVO}")
        print("   Asegúrate de haber copiado fix_sync_ventas.py DENTRO de la carpeta backend/sync.")
        return

    with open(ARCHIVO, "r", encoding="utf-8") as f:
        contenido = f.read()

    if TEXTO_NUEVO in contenido:
        print("✅ El archivo ya tiene el arreglo aplicado. No hay nada que hacer.")
        return

    if TEXTO_VIEJO not in contenido:
        print("⚠️ No encontré el bloque de código esperado en sync_ventas.py.")
        print("   Puede que el archivo ya haya sido editado a mano y quedó distinto.")
        print("   No se modificó nada -- avísale a Claude para revisar el archivo actual.")
        return

    # Respaldo antes de tocar nada
    backup = ARCHIVO + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"💾 Respaldo guardado en: {backup}")

    contenido_nuevo = contenido.replace(TEXTO_VIEJO, TEXTO_NUEVO)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido_nuevo)

    print("✅ sync_ventas.py arreglado con éxito.")
    print("   Ahora corre de nuevo la sincronización de ventas para recuperar")
    print("   el rango que quedó sin actualizar (2026-07-19 -> 2026-08-18):")
    print("")
    print("   python sync_master.py")
    print("   (o si tienes un script específico solo para 'ventas', ese sirve también)")


if __name__ == "__main__":
    main()