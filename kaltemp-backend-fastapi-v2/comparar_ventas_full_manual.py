"""
Compara, mes a mes y canal a canal, el archivo historico manual
VENTAS_FULL.xlsx (montos ya agregados por mes, embebidos abajo en
MANUAL_MONTHLY) contra lo que YA existe hoy en la tabla `ventas` para
esos mismos canales (Falabella, Mercadolibre, Paris, Ripley),
agrupado tambien por ORIGEN -- para detectar si algun mes ya esta
cubierto (evitar duplicar venta) o si es un hueco real que hay que
rellenar.

No modifica nada -- solo lee y compara. El siguiente paso (la carga
real) se decide con esta salida en la mano.

Uso:
    python comparar_ventas_full_manual.py
"""
import duckdb

DUCKDB_PATH = r"C:\kaltemp_app\kaltemp-backend-fastapi-v2\kaltemp_matrix.duckdb"

MANUAL_MONTHLY = {
    ("FALABELLA", "2023-01"): 779980,
    ("FALABELLA", "2023-03"): 2099960,
    ("FALABELLA", "2023-04"): 2119950,
    ("FALABELLA", "2023-05"): 22766680,
    ("FALABELLA", "2023-06"): 11322200,
    ("FALABELLA", "2023-07"): 5479590,
    ("FALABELLA", "2023-08"): 4840680,
    ("FALABELLA", "2023-09"): 4504840,
    ("FALABELLA", "2023-10"): 26691230,
    ("FALABELLA", "2023-11"): 29249310,
    ("FALABELLA", "2023-12"): 6979820,
    ("FALABELLA", "2024-01"): 20689370,
    ("FALABELLA", "2024-02"): 8354720,
    ("FALABELLA", "2024-03"): 5649760,
    ("FALABELLA", "2024-04"): 7494460,
    ("FALABELLA", "2024-05"): 16902640,
    ("FALABELLA", "2024-06"): 19450992,
    ("FALABELLA", "2024-07"): 5199580,
    ("FALABELLA", "2024-08"): 10759660,
    ("FALABELLA", "2024-09"): 19474450,
    ("FALABELLA", "2024-10"): 22147201,
    ("FALABELLA", "2024-11"): 25863390,
    ("FALABELLA", "2024-12"): 23508510,
    ("FALABELLA", "2025-01"): 3302330,
    ("FALABELLA", "2025-02"): 2319440,
    ("FALABELLA", "2025-03"): 11667740,
    ("FALABELLA", "2025-04"): 15647340,
    ("FALABELLA", "2025-05"): 20319287,
    ("FALABELLA", "2025-06"): 26502331,
    ("FALABELLA", "2025-07"): 8254140,
    ("FALABELLA", "2025-08"): 2834743,
    ("FALABELLA", "2025-09"): 4382740,
    ("FALABELLA", "2025-10"): 18788161,
    ("FALABELLA", "2025-11"): 10645350,
    ("FALABELLA", "2025-12"): 17686351,
    ("FALABELLA", "2026-01"): 861900,
    ("FALABELLA", "2026-02"): 99980,
    ("FALABELLA", "2026-03"): 1149900,
    ("FALABELLA", "2026-04"): 6024540,
    ("FALABELLA", "2026-05"): 29552510,
    ("FALABELLA", "2026-06"): 18052914,
    ("FALABELLA", "2026-07"): 13794094,
    ("FALABELLA", "2026-08"): 3632110,
    ("MERCADOLIBRE", "2022-09"): 1328942,
    ("MERCADOLIBRE", "2022-10"): 1660882,
    ("MERCADOLIBRE", "2022-11"): 1239538,
    ("MERCADOLIBRE", "2022-12"): 319990,
    ("MERCADOLIBRE", "2023-01"): 2239952,
    ("MERCADOLIBRE", "2023-02"): 2639870,
    ("MERCADOLIBRE", "2023-03"): 3739760,
    ("MERCADOLIBRE", "2023-04"): 11281270,
    ("MERCADOLIBRE", "2023-05"): 44916030,
    ("MERCADOLIBRE", "2023-06"): 31570090,
    ("MERCADOLIBRE", "2023-07"): 32217818,
    ("MERCADOLIBRE", "2023-08"): 6831789,
    ("MERCADOLIBRE", "2023-09"): 4800160,
    ("MERCADOLIBRE", "2023-10"): 5328366,
    ("MERCADOLIBRE", "2023-11"): 2589680,
    ("MERCADOLIBRE", "2023-12"): 1508310,
    ("MERCADOLIBRE", "2024-01"): 12408500,
    ("MERCADOLIBRE", "2024-02"): 12557850,
    ("MERCADOLIBRE", "2024-03"): 12993459,
    ("MERCADOLIBRE", "2024-04"): 33793584,
    ("MERCADOLIBRE", "2024-05"): 40375924,
    ("MERCADOLIBRE", "2024-06"): 36829940,
    ("MERCADOLIBRE", "2024-07"): 23096810,
    ("MERCADOLIBRE", "2024-08"): 7275722,
    ("MERCADOLIBRE", "2024-09"): 4549740,
    ("MERCADOLIBRE", "2024-10"): 1913689,
    ("MERCADOLIBRE", "2024-11"): 1277439,
    ("MERCADOLIBRE", "2024-12"): 3750960,
    ("MERCADOLIBRE", "2025-01"): 5250781,
    ("MERCADOLIBRE", "2025-02"): 6588180,
    ("MERCADOLIBRE", "2025-03"): 10923094,
    ("MERCADOLIBRE", "2025-04"): 22850358,
    ("MERCADOLIBRE", "2025-05"): 22030985,
    ("MERCADOLIBRE", "2025-06"): 29950216,
    ("MERCADOLIBRE", "2025-07"): 15686916,
    ("MERCADOLIBRE", "2025-08"): 4993169,
    ("MERCADOLIBRE", "2025-09"): 2811474,
    ("MERCADOLIBRE", "2025-10"): 1152977,
    ("MERCADOLIBRE", "2025-11"): 7092944,
    ("MERCADOLIBRE", "2025-12"): 7497107,
    ("MERCADOLIBRE", "2026-01"): 3323495,
    ("MERCADOLIBRE", "2026-02"): 1729890,
    ("MERCADOLIBRE", "2026-03"): 8481426,
    ("MERCADOLIBRE", "2026-04"): 19392508,
    ("MERCADOLIBRE", "2026-05"): 24607860,
    ("MERCADOLIBRE", "2026-06"): 37491527,
    ("MERCADOLIBRE", "2026-07"): 2839320,
    ("PARIS", "2024-09"): 1629960,
    ("PARIS", "2024-10"): 6169820,
    ("PARIS", "2024-11"): 5243820,
    ("PARIS", "2024-12"): 12199550,
    ("PARIS", "2025-01"): 3719930,
    ("PARIS", "2025-02"): 149990,
    ("PARIS", "2025-03"): 1148890,
    ("PARIS", "2025-04"): 3132770,
    ("PARIS", "2025-05"): 1919870,
    ("PARIS", "2025-06"): 1919840,
    ("PARIS", "2025-07"): 339980,
    ("PARIS", "2025-08"): 469970,
    ("PARIS", "2025-09"): 1869810,
    ("PARIS", "2025-10"): 9644690,
    ("PARIS", "2025-11"): 3549900,
    ("PARIS", "2025-12"): 22049070,
    ("PARIS", "2026-01"): 2004710,
    ("PARIS", "2026-02"): 1044790,
    ("PARIS", "2026-03"): 984910,
    ("PARIS", "2026-04"): 2999830,
    ("RIPLEY", "2025-03"): 84990,
    ("RIPLEY", "2025-04"): 1500890,
    ("RIPLEY", "2025-05"): 1664820,
    ("RIPLEY", "2025-06"): 5264500,
    ("RIPLEY", "2025-07"): 969930,
    ("RIPLEY", "2025-08"): 89990,
    ("RIPLEY", "2025-09"): 149980,
    ("RIPLEY", "2025-10"): 264960,
    ("RIPLEY", "2025-11"): 1125870,
    ("RIPLEY", "2025-12"): 4209720,
    ("RIPLEY", "2026-01"): 2719790,
    ("RIPLEY", "2026-02"): 659920,
    ("RIPLEY", "2026-03"): 329980,
    ("RIPLEY", "2026-04"): 689970,
    ("RIPLEY", "2026-05"): 1149950,
}

con = duckdb.connect(DUCKDB_PATH, read_only=True)

# Total actual en `ventas` por CANAL + mes + ORIGEN (para ver cuál origen,
# si alguno, ya cubre cada mes)
filas = con.execute("""
    SELECT
        CANAL,
        strftime(CAST(FECHA_OBJ AS DATE), '%Y-%m') AS ym,
        ORIGEN,
        SUM(BRUTO_TOTAL) AS monto
    FROM ventas
    WHERE CANAL IN ('FALABELLA', 'MERCADOLIBRE', 'PARIS', 'RIPLEY')
    GROUP BY CANAL, ym, ORIGEN
""").fetchall()

# db_por_canal_mes[(canal, ym)] = {origen: monto, ...}
db_por_canal_mes = {}
for canal, ym, origen, monto in filas:
    db_por_canal_mes.setdefault((canal, ym), {})[origen] = monto or 0

canales = ["FALABELLA", "MERCADOLIBRE", "PARIS", "RIPLEY"]
todos_los_meses = sorted(set(ym for (_, ym) in MANUAL_MONTHLY.keys()) | set(ym for (_, ym) in db_por_canal_mes.keys()))

for canal in canales:
    print("=" * 100)
    print(f"CANAL: {canal}")
    print("=" * 100)
    print(f"{'MES':10s} {'MANUAL (Excel)':>18s} {'DB (todos orig.)':>18s} {'DB detalle por ORIGEN':>40s}  DIAGNÓSTICO")
    for ym in todos_los_meses:
        manual = MANUAL_MONTHLY.get((canal, ym))
        db_detalle = db_por_canal_mes.get((canal, ym), {})
        db_total = sum(db_detalle.values())
        if manual is None and not db_detalle:
            continue
        detalle_str = ", ".join(f"{o}={m:,.0f}" for o, m in db_detalle.items()) if db_detalle else "(nada)"
        manual_str = f"{manual:,.0f}" if manual is not None else "-"

        if manual is None:
            diag = "sólo en DB (no está en el Excel)"
        elif not db_detalle:
            diag = ">>> HUECO: falta cargar"
        elif db_total >= manual * 0.9:
            diag = "ya cubierto (DB >= 90% del Excel)"
        elif db_total > 0:
            diag = f">>> PARCIAL: DB sólo cubre {db_total/manual*100:.0f}% del Excel"
        else:
            diag = ">>> HUECO: falta cargar"

        print(f"{ym:10s} {manual_str:>18s} {db_total:>18,.0f} {detalle_str:>40s}  {diag}")
    print()