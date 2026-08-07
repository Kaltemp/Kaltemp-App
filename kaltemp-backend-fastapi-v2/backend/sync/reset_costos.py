"""
sync/reset_costos.py — Resetea COSTO_ENVIO a 0.0 para los despachos de los
últimos 60 días, para forzar que actualizar_fletes_enviame.py los recalcule
con el factor de ajuste ya aplicado. Uso único.
"""
import duckdb

con = duckdb.connect("kaltemp_matrix.duckdb")
resultado = con.execute("""
    UPDATE enviame_despachos
    SET COSTO_ENVIO = 0.0
    WHERE TRY_CAST(FECHA_CREACION AS DATE) >= CAST((CURRENT_DATE - INTERVAL 60 DAY) AS DATE)
""")
con.close()
print("✅ Costos reseteados para los últimos 60 días.")