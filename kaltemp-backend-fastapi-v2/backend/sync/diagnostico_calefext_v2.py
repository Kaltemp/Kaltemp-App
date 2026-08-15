"""
GUARDAR EN: C:\\kaltemp_app\\kaltemp-backend-fastapi-v2\\backend\\sync\\diagnostico_calefext_v2.py

Compara CALEF-EXT vs CALEFACTORES usando solo el ID real del archivo de
imagen de Facebook (todo lo que viene antes del "?", ignorando los
parámetros de firma que rotan en cada request y no indican una imagen
distinta). Muestra la fila MÁS RECIENTE de cada campaña.
"""
import os
import duckdb
import pandas as pd
from dotenv import load_dotenv

pd.set_option("display.max_colwidth", 120)
pd.set_option("display.width", 220)

_AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(_AQUI, ".."))
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"), override=True)
load_dotenv(os.path.join(BACKEND_DIR, ".env"), override=True)
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(BACKEND_DIR, "kaltemp_matrix.duckdb"))

with duckdb.connect(DB_FILE, read_only=True) as con:
    df = con.execute("SELECT * FROM mkt_inversion_meta").fetchdf()

df["_id_imagen"] = df["Imagen"].astype(str).str.split("?").str[0].str.extract(r"([\d]+_[\d]+_[\d]+)")

campanas = ["LDK | CONV | CALEF-EXT | CL", "LDK | CONV | CALEFACTORES | CL"]
sub = df[df["Campaña"].isin(campanas)].copy()

print("=" * 100)
print("FILA MÁS RECIENTE DE CADA CAMPAÑA (por Fecha Fin)")
print("=" * 100)
mas_reciente = sub.sort_values("Fecha Fin").groupby("Campaña").tail(1)
print(mas_reciente[["Campaña", "Fecha Fin", "Guardado", "_id_imagen"]].to_string(index=False))

print("\n" + "=" * 100)
print("¿Son el mismo ID de imagen en la fila más reciente?")
print("=" * 100)
ids = mas_reciente.set_index("Campaña")["_id_imagen"].to_dict()
if len(set(ids.values())) == 1:
    print(f"⚠️  MISMA imagen en ambas campañas (ID: {list(ids.values())[0]})")
else:
    print("✅ Imágenes DISTINTAS en ambas campañas:")
    for camp, idimg in ids.items():
        print(f"   {camp}: {idimg}")

print("\n" + "=" * 100)
print("IDs de imagen únicos por campaña (histórico completo, ignorando tokens de firma)")
print("=" * 100)
for camp, grupo in sub.groupby("Campaña"):
    ids_unicos = grupo["_id_imagen"].unique()
    print(f"\n{camp}: {len(ids_unicos)} ID(s) de imagen real distinto(s)")
    for idimg in ids_unicos:
        n = (grupo["_id_imagen"] == idimg).sum()
        primera = grupo.loc[grupo["_id_imagen"] == idimg, "Fecha Fin"].min()
        ultima = grupo.loc[grupo["_id_imagen"] == idimg, "Fecha Fin"].max()
        print(f"   {idimg}  ({n} filas, de {primera} a {ultima})")