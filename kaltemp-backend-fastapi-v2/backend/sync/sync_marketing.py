"""
sync/sync_marketing.py — Sincroniza dos fuentes REALES hacia DuckDB:

  - Historico_Test_Meta      -> llenada por nuestro Apps Script (API de
                                 Meta en vivo), ya trae imagen real y marca.
  - Historico_Diario_Google  -> llenada por el Google Ads Script NATIVO
                                 de William (corre dentro de Google Ads,
                                 API GAQL oficial, datos diarios reales
                                 vía segments.date). NO trae imagen ni
                                 marca -- ese script no las calcula.

Este archivo le completa a Google lo que le falta:
  - Marca (Kaltemp / Tom Palmer): por palabras clave en el nombre.
  - Imagen: primero la propia si algún día la trae: si no, la imagen
    real de la campaña de Meta de la MISMA categoría de producto (ya
    que es la misma pieza gráfica corriendo en ambas plataformas);
    si tampoco hay equivalente en Meta, el logo de Kaltemp.

06-ago-2026, confirmado con William tras varias vueltas -- este es el
diseño definitivo: Meta y Google se DESCARGAN por separado (cada uno
con su propio script en su plataforma nativa), y este archivo es el
único lugar donde se combinan y enriquecen antes de llegar a DuckDB.
"""
import os
import sys
import re
import unicodedata
import requests
import duckdb
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))

load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)

DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))
print(f"   💾 DB_FILE resuelto: {DB_FILE}")

GOOGLE_SHEET_MKT_ID = os.getenv("GOOGLE_SHEET_MKT_ID", "10u9QTyopMSIeyz2TyK0pnnc5aY5miQo9H_dOPzgYl_8")
CREDS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", os.path.abspath(os.path.join(BACKEND_DIR, "..", "google_credentials.json")))

KALTEMP_LOGO_URL = "https://kaltemp.cl/cdn/shop/files/Logo_Horizontal-01_PNG.png?height=96&v=1659535251"
TOM_PALMER_LOGO_URL = "https://www.tompalmer.cl/cdn/shop/files/Diseno_sin_titulo_3.png?v=1767198984&width=500"


# ============================================================
# NORMALIZACIÓN / CATEGORÍA / MARCA -- mismas reglas que el Apps
# Script de Meta, portadas a Python, para que Google se clasifique
# exactamente igual.
# ============================================================
def _normalizar(s: str) -> str:
    s = str(s or "").upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # quita tildes
    s = s.replace("-", " ").replace("_", " ")
    return s


def _extraer_categoria(nombre_campana: str):
    n = _normalizar(nombre_campana)
    if "PISCINA" in n: return "PISCINA"
    if "SANITARIA" in n: return "SANITARIA"
    if "BOMBA" in n and "CALEFAC" in n: return "BOMBA_CALEFACCION"
    if "GENERADOR" in n: return "GENERADOR"
    if "CALEFACTOR" in n: return "CALEFACTOR"
    if "CALEFAC" in n and "EXT" in n: return "CALEFACCION_EXTERIOR"
    if "CALEF" in n and "EXT" in n: return "CALEFACCION_EXTERIOR"
    if "EXTERIOR" in n: return "CALEFACCION_EXTERIOR"
    if "PERGOLA" in n: return "PERGOLA"
    if "TERMO" in n: return "TERMO"
    if "VENTILACION" in n: return "VENTILACION"
    if "HOT TUB" in n or "HOTTUB" in n: return "HOT_TUB"
    if "AIRE" in n: return "AIRE_ACONDICIONADO"
    # Categorías de producto de Tom Palmer (distintas a las de Kaltemp)
    if "HERRAMIENTA" in n: return "HERRAMIENTAS"
    if "MANGUERA" in n: return "MANGUERAS"
    if "ILUMINACION" in n or "LIGHTING" in n: return "ILUMINACION"
    if "OUTDOOR" in n or "EXTERIORES" in n: return "OUTDOOR_TP"
    return None


def _detectar_marca(nombre_campana: str) -> str:
    n = _normalizar(nombre_campana)
    if "TOM PALMER" in n or "TOMPALMER" in n: return "Tom Palmer"
    if "HERRAMIENTA" in n: return "Tom Palmer"
    if "MANGUERA" in n: return "Tom Palmer"
    if "ILUMINACION" in n or "LIGHTING" in n: return "Tom Palmer"
    if "OUTDOOR" in n or "EXTERIORES" in n: return "Tom Palmer"
    return "Kaltemp"


# ============================================================
# DESCARGA DE PESTAÑAS (API oficial de Sheets v4)
# ============================================================
def descargar_csv_google_sheet(sheet_id, nombres_pestana):
    if not sheet_id:
        print("   ❌ GOOGLE_SHEET_MKT_ID está vacío.")
        return pd.DataFrame()
    if "/d/" in sheet_id:
        sheet_id = sheet_id.split("/d/")[1].split("/")[0]

    headers = {}
    print(f"   🔑 ¿Existe archivo de credenciales en {CREDS_PATH}? {os.path.exists(CREDS_PATH)}")
    try:
        if os.path.exists(CREDS_PATH):
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            credentials = service_account.Credentials.from_service_account_file(
                CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            credentials.refresh(Request())
            headers["Authorization"] = f"Bearer {credentials.token}"
            print(f"   🔑 Token OK. Cuenta de Servicio: {credentials.service_account_email}")
    except Exception as e:
        print(f"   ⚠️ No se pudo generar el token de Cuenta de Servicio: {e}")

    pestañas = [nombres_pestana] if isinstance(nombres_pestana, str) else nombres_pestana

    for nombre_pestana in pestañas:
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/"
            f"{requests.utils.quote(nombre_pestana)}?majorDimension=ROWS"
        )
        print(f"   🌐 Pidiendo pestaña '{nombre_pestana}' (API oficial v4)...")
        try:
            res = requests.get(url, headers=headers, timeout=25)
            print(f"      status={res.status_code}")
            if res.status_code != 200:
                print(f"      respuesta: {res.text[:400]!r}")
                continue

            data = res.json()
            filas = data.get("values", [])
            if len(filas) < 2:
                print(f"      la pestaña respondió OK pero no trae filas de datos.")
                continue

            encabezados = list(filas[0])
            max_cols = max([len(encabezados)] + [len(f) for f in filas[1:]])
            if len(encabezados) < max_cols:
                encabezados += [f"Columna_{i+1}" for i in range(len(encabezados), max_cols)]

            filas_datos = [f + [""] * (max_cols - len(f)) for f in filas[1:]]
            df = pd.DataFrame(filas_datos, columns=encabezados[:max_cols])

            if not df.empty:
                print(f"✅ Pestaña '{nombre_pestana}' descargada con éxito ({len(df)} filas).")
                return df
        except Exception as e:
            print(f"      ❌ ERROR al pedir/parsear '{nombre_pestana}': {e}")

    return pd.DataFrame()


def _col(df, *nombres_posibles):
    """Busca la primera columna del df cuyo nombre (sin tildes/mayúsculas)
    coincida con alguno de los nombres posibles."""
    for col in df.columns:
        limpio = _normalizar(col)
        for n in nombres_posibles:
            if _normalizar(n) == limpio:
                return col
    return None


def enriquecer_google_con_imagen_y_marca(df_google: pd.DataFrame, df_meta: pd.DataFrame,
                                          marca_forzada: str = None, logo_respaldo: str = KALTEMP_LOGO_URL) -> pd.DataFrame:
    """
    El Google Ads Script (de Kaltemp o de Tom Palmer) trae datos reales
    pero SIN imagen ni marca (no las calcula). Acá se completan:
      - Marca: si `marca_forzada` viene seteado (ej. toda la pestaña es
        de Tom Palmer, viene de SU cuenta separada de Google Ads), se
        usa esa directamente -- más confiable que adivinar por palabra
        clave. Si no, se asume Kaltemp (el caso por defecto).
      - Imagen: 1) la propia si alguna vez viniera con una URL real,
        2) la de la campaña de Meta de la MISMA categoría de producto
        Y LA MISMA MARCA (misma pieza gráfica que corre en ambas
        plataformas -- IMPORTANTE: nunca cruzar marcas acá, Kaltemp y
        Tom Palmer pueden tener una campaña "Pérgolas" cada una, con
        fotos DISTINTAS -- confirmado el bug de mezcla 06-ago-2026),
        3) `logo_respaldo` (logo de la marca correspondiente) si no hay
        ningún equivalente de la MISMA marca.
    """
    if df_google.empty:
        return df_google

    col_camp_g = _col(df_google, "Campaña", "Campaign", "Nombre") or df_google.columns[3]
    col_img_g = _col(df_google, "Imagen", "Image", "ImageUrl")
    marca_objetivo = marca_forzada if marca_forzada else "Kaltemp"

    # Mapa categoría -> imagen real de Meta, SOLO de la marca objetivo
    # (nunca mezclar -- una "Pérgolas" de Kaltemp no debe prestarle su
    # foto a una "Pérgolas" de Tom Palmer, ni viceversa).
    mapa_categoria_imagen = {}
    if not df_meta.empty:
        col_camp_m = _col(df_meta, "Campaña", "Campaign", "Nombre") or df_meta.columns[3]
        col_img_m = _col(df_meta, "Imagen", "Image", "ImageUrl")
        col_marca_m = _col(df_meta, "Marca")
        df_meta_marca = df_meta[df_meta[col_marca_m] == marca_objetivo] if col_marca_m else df_meta
        if col_img_m:
            for _, fila in df_meta_marca.iterrows():
                nombre = str(fila[col_camp_m])
                img = str(fila[col_img_m]).strip()
                categoria = _extraer_categoria(nombre)
                if categoria and img.startswith("http") and "Logo_Horizontal" not in img and "Diseno_sin_titulo" not in img and categoria not in mapa_categoria_imagen:
                    mapa_categoria_imagen[categoria] = img

    def _resolver_imagen(row):
        actual = str(row[col_img_g]).strip() if col_img_g else ""
        if actual.startswith("http"):
            return actual
        categoria = _extraer_categoria(str(row[col_camp_g]))
        if categoria and categoria in mapa_categoria_imagen:
            return mapa_categoria_imagen[categoria]
        return logo_respaldo

    df_google = df_google.copy()
    df_google["Marca"] = marca_forzada if marca_forzada else df_google[col_camp_g].apply(_detectar_marca)
    df_google["Imagen"] = df_google.apply(_resolver_imagen, axis=1)
    return df_google


def sync_marketing():
    print(f"[{datetime.now()}] 📢 Sincronizando datos diarios hacia {DB_FILE}")

    df_meta = descargar_csv_google_sheet(GOOGLE_SHEET_MKT_ID, ["Historico_Test_Meta"])
    df_google_kaltemp = descargar_csv_google_sheet(GOOGLE_SHEET_MKT_ID, ["Historico_Diario_Google"])
    df_google_tp = descargar_csv_google_sheet(GOOGLE_SHEET_MKT_ID, ["Historico_Diario_Google_TomPalmer"])

    if not df_google_kaltemp.empty:
        df_google_kaltemp = enriquecer_google_con_imagen_y_marca(
            df_google_kaltemp, df_meta, marca_forzada=None, logo_respaldo=KALTEMP_LOGO_URL
        )
        n_tom_palmer = int((df_google_kaltemp["Marca"] == "Tom Palmer").sum())
        print(f"ℹ️ Google Kaltemp enriquecido: {len(df_google_kaltemp)} filas -- {n_tom_palmer} clasificadas como Tom Palmer, resto Kaltemp.")

    if not df_google_tp.empty:
        df_google_tp = enriquecer_google_con_imagen_y_marca(
            df_google_tp, df_meta, marca_forzada="Tom Palmer", logo_respaldo=TOM_PALMER_LOGO_URL
        )
        print(f"ℹ️ Google Tom Palmer enriquecido: {len(df_google_tp)} filas (cuenta separada, marca forzada).")

    # Unir ambas marcas en una sola tabla -- incluso si alguna de las
    # dos viene vacía, pd.concat maneja eso sin problema.
    df_google = pd.concat([df for df in [df_google_kaltemp, df_google_tp] if not df.empty], ignore_index=True) \
        if (not df_google_kaltemp.empty or not df_google_tp.empty) else pd.DataFrame()

    with duckdb.connect(DB_FILE) as con:
        if not df_meta.empty:
            con.execute("DROP TABLE IF EXISTS mkt_inversion_meta")
            con.register("df_meta_tmp", df_meta)
            con.execute("CREATE TABLE mkt_inversion_meta AS SELECT * FROM df_meta_tmp")
            print(f"[{datetime.now()}] ✅ mkt_inversion_meta actualizada con {len(df_meta)} filas.")

        if not df_google.empty:
            con.execute("DROP TABLE IF EXISTS mkt_inversion_google")
            con.register("df_google_tmp", df_google)
            con.execute("CREATE TABLE mkt_inversion_google AS SELECT * FROM df_google_tmp")
            print(f"[{datetime.now()}] ✅ mkt_inversion_google actualizada con {len(df_google)} filas (Kaltemp + Tom Palmer).")


if __name__ == "__main__":
    sync_marketing()