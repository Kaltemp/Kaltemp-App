# ============================================================
# ARCHIVO: fix_cargar_ventas_full_historico.py
# QUE HACE: aplica 2 mejoras de seguridad a Cargar_ventas_full_historico.py
# ANTES de correrlo contra la base restaurada:
#   1) Imprime DB_FILE en pantalla apenas se calcula, para que puedas
#      confirmar con tus propios ojos que apunta a la base correcta
#      ANTES de llegar a la pregunta "CARGAR".
#   2) Cambia el INSERT final de "SELECT *" (que depende del ORDEN FISICO
#      de las columnas en `ventas`) a un INSERT con columnas nombradas
#      explicitamente. Asi, si el orden de columnas de la base restaurada
#      no coincide exactamente con el de la base vieja donde se probo
#      ayer, el script FALLA CON UN ERROR CLARO en vez de insertar datos
#      en la columna equivocada sin avisar.
# No cambia ninguna otra logica (calculo de costo, categoria, filtrado,
# confirmacion "CARGAR", borrado de cargas previas, etc.) -- eso queda
# exactamente igual.
#
# COMO USARLO:
#   1. Copia este archivo DENTRO de la carpeta:
#      C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend
#      (la misma carpeta donde esta Cargar_ventas_full_historico.py)
#   2. Abre PowerShell ahi (con el venv activado)
#   3. Corre:
#      python fix_cargar_ventas_full_historico.py
#   4. Recien despues, corre Cargar_ventas_full_historico.py normal.
# ============================================================
import os

ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Cargar_ventas_full_historico.py")

# --- Cambio 1: imprimir DB_FILE apenas se calcula ---
DB_FILE_VIEJO = '''DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
CSV_PATH = os.path.join(_AQUI, "full_historico_a_cargar.csv")'''

DB_FILE_NUEVO = '''DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
CSV_PATH = os.path.join(_AQUI, "full_historico_a_cargar.csv")
print(f"Base de datos que se va a modificar: {DB_FILE}")'''

# --- Cambio 2: INSERT final con columnas explicitas, no SELECT * ---
# (Ojo: SOLO esta linea -- confirmado con Select-String contra el archivo
# real de William que hay una linea en blanco antes de ella, asi que no
# la incluimos en el bloque a buscar/reemplazar; matchear una sola linea
# evita depender de las lineas vecinas.)
INSERT_VIEJO = '''    con.execute(f"INSERT INTO ventas SELECT * FROM tmp_carga_full_historico")'''

INSERT_NUEVO = '''    columnas_explicitas = ", ".join(cols)
    con.execute(
        f"INSERT INTO ventas ({columnas_explicitas}) "
        f"SELECT {columnas_explicitas} FROM tmp_carga_full_historico"
    )'''


def main():
    if not os.path.exists(ARCHIVO):
        print(f"No encontre el archivo en: {ARCHIVO}")
        print("Asegurate de haber copiado fix_cargar_ventas_full_historico.py DENTRO de backend\\.")
        return

    with open(ARCHIVO, "r", encoding="utf-8") as f:
        contenido = f.read()

    ya_aplicado = (DB_FILE_NUEVO in contenido) and (INSERT_NUEVO in contenido)
    if ya_aplicado:
        print("El archivo ya tiene ambos arreglos aplicados. No hay nada que hacer.")
        return

    faltantes = []
    if DB_FILE_VIEJO not in contenido and DB_FILE_NUEVO not in contenido:
        faltantes.append("bloque DB_FILE/CSV_PATH")
    if INSERT_VIEJO not in contenido and INSERT_NUEVO not in contenido:
        faltantes.append("bloque INSERT final")

    if faltantes:
        print(f"No encontre el/los siguiente(s) bloque(s) esperado(s): {', '.join(faltantes)}")
        print("Puede que el archivo ya haya sido editado a mano y quedo distinto.")
        print("No se modifico nada -- avisale a Claude para revisar el archivo actual.")
        return

    backup = ARCHIVO + ".bak"
    with open(backup, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"Respaldo guardado en: {backup}")

    contenido_nuevo = contenido
    if DB_FILE_NUEVO not in contenido_nuevo:
        contenido_nuevo = contenido_nuevo.replace(DB_FILE_VIEJO, DB_FILE_NUEVO)
    if INSERT_NUEVO not in contenido_nuevo:
        contenido_nuevo = contenido_nuevo.replace(INSERT_VIEJO, INSERT_NUEVO)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido_nuevo)

    print("Cargar_ventas_full_historico.py arreglado con exito:")
    print("  1) Ahora imprime DB_FILE apenas arranca.")
    print("  2) El INSERT final ahora nombra columnas explicitamente (mas seguro).")
    print("\nAhora corre: python Cargar_ventas_full_historico.py")


if __name__ == "__main__":
    main()