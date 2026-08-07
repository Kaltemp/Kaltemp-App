"""
sync/calcular_ajuste_flete.py — Calcula el % de ajuste entre el costo
TEÓRICO (cotización /v1/prices a 1kg fijo) y el costo REAL facturado por
Envíame, usando los archivos de factura mensual (hoja "Detalle") como
fuente de verdad.

⚠️ LIMITACIÓN CONOCIDA: la cotización teórica siempre usa 1kg fijo, pero
el peso real mediano de los envíos de Kaltemp es ~12kg (correlación
peso-costo real: 0.93-0.94 en la muestra analizada). El % resultante es
un promedio razonable, pero subestimará envíos pesados y sobreestimará
envíos livianos. Para mayor precisión habría que cotizar con el peso
real de cada pedido (si Bsale registra peso por SKU) en vez de aplicar
un % plano -- pendiente de evaluar como mejora futura.

Uso:
    1. Coloca todos los .xlsx de factura de Envíame (hoja "Detalle") en
       la carpeta backend/sync/facturas_enviame/
    2. python sync\\calcular_ajuste_flete.py

Si hay archivos duplicados o reemitidos para el mismo envío (mismo 'id'),
se queda automáticamente con el de la factura más reciente (por fecha de
modificación del archivo) -- no hace falta limpiar la carpeta a mano.

Guarda el resultado en la tabla `enviame_factor_ajuste` de DuckDB, que
actualizar_fletes_enviame.py lee automáticamente para corregir sus
cotizaciones.
"""
import os
import glob
import requests
import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
    override=True,
)

API_KEY = os.getenv("ENVIAME_API_KEY")
if not API_KEY:
    raise RuntimeError("Falta ENVIAME_API_KEY en el .env de la raíz.")

HEADERS = {"api-key": API_KEY, "x-api-key": API_KEY, "Accept": "application/json"}
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kaltemp_matrix.duckdb")
CARPETA_FACTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "facturas_enviame")


def cargar_facturas_reales():
    archivos = glob.glob(os.path.join(CARPETA_FACTURAS, "*.xlsx"))
    if not archivos:
        raise RuntimeError(
            f"No se encontraron .xlsx en {CARPETA_FACTURAS}. "
            "Copia ahí los archivos de factura de Envíame (hoja 'Detalle')."
        )
    # Se ordenan por fecha de modificación ASCENDENTE -- si hay 'id' de
    # envío repetido entre archivos (duplicados o facturas reemitidas),
    # drop_duplicates(keep='last') más abajo se queda con el más reciente.
    archivos.sort(key=lambda a: os.path.getmtime(a))

    print(f"📂 {len(archivos)} archivo(s) .xlsx encontrados (ordenados por fecha):")
    dfs = []
    for a in archivos:
        d = pd.read_excel(a, sheet_name="Detalle")
        d["archivo_origen"] = os.path.basename(a)
        dfs.append(d)
        print(f"   {os.path.basename(a)}: {len(d)} filas")

    df = pd.concat(dfs, ignore_index=True)
    filas_antes = len(df)

    df = df.dropna(subset=["com_destino", "carrier", "total", "id"])
    df = df[df["total"] > 0]

    duplicados = df.duplicated(subset=["id"], keep=False).sum()
    if duplicados > 0:
        print(f"\n⚠️ {duplicados} filas con 'id' de envío repetido entre archivos "
              f"(duplicados o facturas reemitidas) -- se conserva la versión del "
              f"archivo más reciente para cada una.")
    df = df.drop_duplicates(subset=["id"], keep="last")

    print(f"\n✅ {len(df)} envíos únicos tras deduplicar (de {filas_antes} filas leídas).")
    return df


def cotizar_teorico(comuna_destino, carrier_code):
    url = "https://api.enviame.io/api/v1/prices"
    params = {
        "from_place": "Santiago", "to_place": comuna_destino,
        "weight": 1.0, "length": 10, "width": 10, "height": 10,
        "carrier": carrier_code,
    }
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("data", []):
                services = item.get("services", [])
                if services:
                    return float(services[0].get("price", 0.0))
        elif res.status_code == 404:
            # Código de courier no válido en /prices -- reintenta sin filtro
            # y busca por nombre entre los resultados.
            res2 = requests.get(url, headers=HEADERS, params={k: v for k, v in params.items() if k != "carrier"}, timeout=10)
            if res2.status_code == 200:
                for item in res2.json().get("data", []):
                    if str(item.get("carrier", "")).upper() == carrier_code.upper():
                        services = item.get("services", [])
                        if services:
                            return float(services[0].get("price", 0.0))
    except Exception as e:
        print(f"⚠️ Error cotizando {comuna_destino}/{carrier_code}: {e}")
    return None


def calcular():
    df = cargar_facturas_reales()

    cache_teorico = {}
    rutas_unicas = df[["com_destino", "carrier_code"]].drop_duplicates()
    print(f"\n🔎 Cotizando {len(rutas_unicas)} rutas únicas (comuna + courier) al precio teórico actual...")

    for _, r in rutas_unicas.iterrows():
        comuna, carrier_code = r["com_destino"], r["carrier_code"]
        key = f"{comuna}_{carrier_code}"
        if key not in cache_teorico:
            cache_teorico[key] = cotizar_teorico(comuna, carrier_code)

    df["precio_teorico"] = df.apply(
        lambda row: cache_teorico.get(f"{row['com_destino']}_{row['carrier_code']}"), axis=1
    )
    df_validos = df.dropna(subset=["precio_teorico"])
    df_validos = df_validos[df_validos["precio_teorico"] > 0]
    df_validos["ratio"] = df_validos["total"] / df_validos["precio_teorico"]

    print(f"\n📊 {len(df_validos)}/{len(df)} envíos con cotización teórica válida para comparar.\n")

    resumen = df_validos.groupby("carrier").agg(
        muestras=("ratio", "count"),
        ratio_mediana=("ratio", "median"),
        ratio_promedio=("ratio", "mean"),
    ).round(3)
    print(resumen)

    con = duckdb.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS enviame_factor_ajuste (
            CARRIER VARCHAR, FACTOR DOUBLE, MUESTRAS INTEGER, FECHA_CALCULO TIMESTAMP
        )
    """)
    con.execute("DELETE FROM enviame_factor_ajuste")
    for carrier, row in resumen.iterrows():
        con.execute(
            "INSERT INTO enviame_factor_ajuste VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            [carrier, float(row["ratio_mediana"]), int(row["muestras"])],
        )
    factor_global = float(df_validos["ratio"].median())
    con.execute(
        "INSERT INTO enviame_factor_ajuste VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
        ["__GLOBAL__", factor_global, len(df_validos)],
    )
    con.close()

    print(f"\n✅ Factores guardados en enviame_factor_ajuste. Factor global de respaldo: {factor_global:.3f}")
    print("   (se usa la MEDIANA, no el promedio -- más robusta ante envíos outlier muy pesados)")


if __name__ == "__main__":
    calcular()