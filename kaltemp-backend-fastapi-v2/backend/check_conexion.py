"""
Script de diagnóstico para ejecutar directamente en la terminal:
python check_conexion.py
"""
import sys
import os

try:
    from db import get_connection
except ImportError:
    import duckdb
    def get_connection():
        return duckdb.connect("kaltemp_matrix.duckdb")

def diagnosticar_base_datos():
    print("\n" + "=" * 65)
    print("🔍 DIAGNÓSTICO DE BASE DE DATOS DUCKDB (Kaltemp vs Tom Palmer)")
    print("=" * 65)
    
    try:
        with get_connection() as con:
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
            print(f"\n✅ Tablas encontradas en la BD ({len(tables)}):")
            print(f"   {', '.join(tables)}")

            # 1. CANALES EXISTENTES EN VENTAS
            print("\n1. 📊 CANALES DE VENTA REGISTRADOS (Top 10):")
            canales = con.execute("SELECT CANAL, COUNT(*) as txs, SUM(BRUTO_TOTAL) as total FROM ventas GROUP BY CANAL ORDER BY total DESC LIMIT 10").fetchall()
            for c in canales:
                print(f"   • Canal: '{c[0]}' | Transacciones: {c[1]} | Venta: ${c[2]:,.0f}")

            # 2. BÚSQUEDA DE MANUEL ERRAZURIZ Y TOM PALMER EN VENTAS
            print("\n2. 👤 BÚSQUEDA DE VENDEDORES (Manuel / Errázuriz):")
            vendedores = con.execute("SELECT DISTINCT VENDEDOR, COUNT(*) as txs, SUM(BRUTO_TOTAL) as total FROM ventas WHERE VENDEDOR ILIKE '%MANUEL%' OR VENDEDOR ILIKE '%ERR%' GROUP BY VENDEDOR").fetchall()
            if vendedores:
                for v in vendedores:
                    print(f"   • Vendedor exacto en BD: '{v[0]}' | Txs: {v[1]} | Venta: ${v[2]:,.0f}")
            else:
                print("   ⚠️ ATENCIÓN: No se encontraron registros con el nombre 'Manuel' o 'Errázuriz' en la columna VENDEDOR.")

            # 3. VERIFICACIÓN DE VENTAS KALTEMP VS TOM PALMER
            print("\n3. 💵 TOTALES DE VENTAS SEGÚN FILTROS D2C:")
            vta_kaltemp = con.execute("SELECT COALESCE(SUM(BRUTO_TOTAL), 0) FROM ventas WHERE CANAL ILIKE 'D2C'").fetchone()[0]
            vta_tom_palmer = con.execute("SELECT COALESCE(SUM(BRUTO_TOTAL), 0) FROM ventas WHERE CANAL ILIKE '%TOM PALMER%' OR VENDEDOR ILIKE '%MANUEL%ERR%'").fetchone()[0]
            print(f"   🔴 Kaltemp D2C (CANAL = 'D2C'): ${vta_kaltemp:,.0f}")
            print(f"   🟢 Tom Palmer D2C (Canal 'Tom Palmer' / Vendedor 'Manuel'): ${vta_tom_palmer:,.0f}")

            # 4. INSPECCIÓN DE LA TABLA GA4
            print("\n4. 📈 REVISIÓN DE TRÁFICO GA4 (google_analytics):")
            if "ga4_metricas" in tables:
                cols = [col[1] for col in con.execute("PRAGMA table_info('ga4_metricas')").fetchall()]
                print(f"   • Columnas existentes en ga4_metricas: {', '.join(cols)}")
                
                total_ga4 = con.execute("SELECT COUNT(*) FROM ga4_metricas").fetchone()[0]
                print(f"   • Total de filas registradas en GA4: {total_ga4}")
                
                cols_upper = [c.upper() for c in cols]
                if "MARCA" in cols_upper or "PROPIEDAD" in cols_upper:
                    col_m = "MARCA" if "MARCA" in cols_upper else "PROPIEDAD"
                    marcas_ga4 = con.execute(f"SELECT DISTINCT {col_m} FROM ga4_metricas").fetchall()
                    print(f"   • Marcas identificadas en GA4: {[m[0] for m in marcas_ga4]}")
                else:
                    print("   ⚠️ ATENCIÓN: La tabla 'ga4_metricas' NO TIENE una columna 'MARCA'. Por eso todo el tráfico web se muestra como una sola cuenta.")
            else:
                print("   ❌ La tabla 'ga4_metricas' no existe en DuckDB.")

    except Exception as e:
        print(f"\n❌ Error al intentar conectar a DuckDB: {e}")

    print("\n" + "=" * 65 + "\n")

if __name__ == "__main__":
    diagnosticar_base_datos()