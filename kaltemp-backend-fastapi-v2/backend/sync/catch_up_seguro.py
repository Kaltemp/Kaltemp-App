# ============================================================
# ARCHIVO: catch_up_seguro.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\catch_up_seguro.py
# (reemplaza la version anterior -- respaldar antes: Copy-Item catch_up_seguro.py catch_up_seguro.py.bak)
#
# QUE HACE (actualizado 19-ago-2026): 1) busca el ultimo dia con datos en
# `ventas` dentro del kaltemp_matrix.duckdb, 2) calcula cuantos dias hay
# que traer para llegar a hoy (con margen de seguridad), 3) corre
# sync_ventas() con ESE numero exacto -- no un valor fijo a ciegas como
# hace sync_master.py (dias_atras=30) -- y AHORA TAMBIEN corre
# sync_ventas_full(), sync_leads() y sync_enviame() en la misma pasada,
# porque son los modulos que mas rapido se quedan atras si solo se corre
# este script "seguro" en vez de sync_master.py completo.
#
# AGREGADO 19-ago-2026 (reportado por William: "el modulo de control
# logistico no esta trayendo datos"): confirmado con
# diagnostico_logistica.py que el problema NO era de datos corruptos ni
# de filtro -- 'enviame_despachos' simplemente no se sincronizaba desde
# hacia 14 dias (ultimo despacho: 2026-08-05) porque nadie corria
# sync_enviame.py directo, solo este catch_up_seguro.py (que hasta ahora
# no lo cubria) o sync_master.py completo (que muchas veces no se corria
# despues). Se agrega el mismo criterio de "brecha real + margen" que ya
# se usa para 'ventas': se mide el ultimo FECHA_CREACION real en
# enviame_despachos y se sincroniza esa brecha, no un numero fijo.
#
# Tambien se agrega, como paso final opcional, actualizar_fletes_enviame.py
# -- sin esto, los despachos recien sincronizados quedan con COSTO_ENVIO
# en 0 (que es exactamente lo que hace ver "Margen de Flete" vacio o raro
# en el modulo aunque el conteo de despachos si aparezca). Este paso llama
# a la API de Envíame por cada despacho pendiente, asi que puede tardar
# mas que los otros -- se pregunta aparte para poder saltarlo si se
# quiere una pasada rapida.
#
# AGREGADO 19-ago-2026 (reportado por William: "el modulo campañas de
# marketing no me esta trayendo datos"): mismo patron que enviame_despachos
# -- catch_up_seguro.py no cubria 'marketing' (mkt_inversion_meta /
# mkt_inversion_google), asi que si nadie corria sync_master.py completo
# esas tablas se quedaban con la ultima foto de hace semanas. A diferencia
# de ventas/ventas_full/enviame, sync_marketing() NO tiene dias_atras --
# siempre vuelve a descargar el historico completo desde las pestañas de
# Google Sheets (Historico_Test_Meta / Historico_Diario_Google), asi que
# no hay "brecha" que calcular: se corre directo, sin pedir un numero de
# dias.
#
# AGREGADO 19-ago-2026 (reportado por William: "el modulo Indicadores D2C
# & Funnel GA4 tambien tiene fallas de actualizacion"): INVERSIÓN MKT y
# TACOS GLOBAL de ese modulo leen las MISMAS tablas mkt_inversion_meta /
# mkt_inversion_google que el paso 'marketing' de arriba -- esas ya
# quedan cubiertas. Pero SESIONES (GA4), % CONVERSIÓN y TASA REBOTE salen
# de 'ga4_metricas' (Kaltemp) / 'ga4_metricas_tompalmer' (Tom Palmer),
# pobladas por sync_ga4_kaltemp.py / sync_ga4_tompalmer.py, que NO
# corrian aca. Se agregan como pasos 6 y 7.
#
# OJO -- a diferencia de ventas/enviame (que son incrementales, solo
# agregan filas nuevas), sync_ga4_kaltemp()/sync_ga4_tompalmer() hacen
# DROP TABLE + CREATE TABLE completo en cada corrida, reemplazando TODA
# la tabla por lo que devuelva la API en ese momento. Por eso NUNCA se le
# pasa un dias_atras chico calculado por "brecha" como a enviame_despachos
# -- eso BORRARIA el historico viejo y lo reemplazaria solo por esos
# pocos dias. Se llaman sin dias_atras (default: todo el historico desde
# GA4_KALTEMP_FECHA_DESDE / 2024-01-01 hasta hoy), mismo criterio que ya
# se usa para 'marketing'.
#
# LO QUE SIGUE SIN CUBRIR (correr sync_master.py completo para esto):
# stock_bsale, notas_credito, falabella_estados, planilla_despachos --
# estos no dependen de "ultimo dia con datos" del mismo modo, y no son
# criticos para un chequeo rapido antes de presentar KPIs de
# venta/leads/logistica/marketing/D2C.
#
# COMO USARLO:
#   1. Copia este archivo DENTRO de la carpeta:
#      C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync
#      (la misma carpeta donde estan sync_ventas.py, sync_ventas_full.py,
#       sync_leads.py, sync_enviame.py, actualizar_fletes_enviame.py,
#       sync_marketing.py, sync_ga4_kaltemp.py, sync_ga4_tompalmer.py)
#   2. Abre PowerShell ahi (con el venv activado)
#   3. Corre:
#      python catch_up_seguro.py
# ============================================================
import os
import sys
import datetime
import duckdb

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)

from sync_ventas import sync_ventas, DB_FILE  # noqa: E402
from sync_ventas_full import sync_ventas_full  # noqa: E402
from sync_leads import sync_leads  # noqa: E402
from sync_enviame import sync_enviame  # noqa: E402
from actualizar_fletes_enviame import ejecutar_actualizacion_costos  # noqa: E402
from sync_marketing import sync_marketing  # noqa: E402
from sync_ga4_kaltemp import sync_ga4_kaltemp  # noqa: E402
from sync_ga4_tompalmer import sync_ga4_tompalmer  # noqa: E402

MARGEN_DIAS_EXTRA = 3  # margen de seguridad además de la brecha detectada
MARGEN_MINIMO_FULL = 10  # ventas_full siempre trae al menos estos días atrás,
# aunque 'ventas' esté al día -- un pedido fulfillment puede tardar unos
# días en generar el consumo en Bsale después de la fecha de venta real.
MARGEN_MINIMO_ENVIAME = 10  # mismo criterio que ventas_full: un despacho
# puede crearse en Envíame unos días después de la venta que lo originó.


def main():
    print(f"🔎 Consultando último día en 'ventas' y 'enviame_despachos' de: {DB_FILE}\n")

    with duckdb.connect(DB_FILE, read_only=True) as con:
        ultima_fecha = con.execute("SELECT MAX(CAST(FECHA_OBJ AS DATE)) FROM ventas").fetchone()[0]

        tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
        ultima_fecha_enviame = None
        if "enviame_despachos" in tablas:
            ultima_fecha_enviame = con.execute(
                "SELECT MAX(TRY_CAST(FECHA_CREACION AS DATE)) FROM enviame_despachos"
            ).fetchone()[0]

    if ultima_fecha is None:
        print("⚠️ La tabla 'ventas' está vacía -- no se puede calcular la brecha.")
        print("   Corre sync_master.py normal en ese caso.")
        return

    hoy = datetime.date.today()
    brecha_dias = (hoy - ultima_fecha).days
    dias_atras = brecha_dias + MARGEN_DIAS_EXTRA

    print(f"📅 Último día con datos en 'ventas': {ultima_fecha}")
    print(f"📅 Hoy: {hoy}")
    print(f"📏 Brecha real en 'ventas': {brecha_dias} días")

    if brecha_dias <= 0:
        print("✅ 'ventas' ya está al día -- no hace falta traer nada ahí.")
        dias_atras_ventas = 0
    else:
        print(f"🛡️ Con margen de seguridad (+{MARGEN_DIAS_EXTRA} días): se van a traer los últimos {dias_atras} días de 'ventas'.")
        dias_atras_ventas = dias_atras

    dias_atras_full = max(dias_atras, MARGEN_MINIMO_FULL)
    print(f"🛡️ 'ventas_full' (fulfillment ML/Paris/Ripley) se sincroniza con {dias_atras_full} días atrás.")

    if ultima_fecha_enviame is None:
        print("⚠️ 'enviame_despachos' no existe o está vacía -- se sincroniza con el default (ENVIAME_DIAS_ATRAS / 60 días).")
        dias_atras_enviame = None
    else:
        brecha_enviame = (hoy - ultima_fecha_enviame).days
        print(f"📅 Último despacho sincronizado en 'enviame_despachos': {ultima_fecha_enviame} ({brecha_enviame} días de brecha)")
        dias_atras_enviame = max(brecha_enviame + MARGEN_DIAS_EXTRA, MARGEN_MINIMO_ENVIAME)
        print(f"🛡️ 'enviame_despachos' se sincroniza con {dias_atras_enviame} días atrás.")

    print("🛡️ 'leads' se sincroniza completo (Cliengo no soporta incremental) -- puede tardar unos minutos.")
    print("🛡️ 'marketing' (Google Ads + Meta Ads) se sincroniza completo -- sin dias_atras, siempre trae el histórico entero de la planilla.")
    print("🛡️ 'ga4_kaltemp' y 'ga4_tompalmer' (Indicadores D2C) se sincronizan completos -- mismo criterio, sin dias_atras (reemplazan toda la tabla, no son incrementales).\n")

    respuesta = input("¿Confirmas sincronizar ventas + ventas_full + leads + enviame_despachos + marketing + ga4 con lo anterior? (s/n): ").strip().lower()
    if respuesta != "s":
        print("Cancelado -- no se hizo ningún cambio.")
        return

    if dias_atras_ventas > 0:
        print(f"\n🚀 [1/7] Sincronizando 'ventas' con dias_atras={dias_atras_ventas}...\n")
        try:
            sync_ventas(dias_atras=dias_atras_ventas)
            print("✅ 'ventas' OK.")
        except Exception as e:
            print(f"❌ Error en 'ventas': {e} -- se sigue igual con el resto.")
    else:
        print("\n⏭️ [1/7] 'ventas' ya estaba al día, se salta.")

    print(f"\n🚀 [2/7] Sincronizando 'ventas_full' (fulfillment ML/Paris/Ripley) con dias_atras={dias_atras_full}...\n")
    try:
        sync_ventas_full(dias_atras=dias_atras_full)
        print("✅ 'ventas_full' OK.")
    except Exception as e:
        print(f"❌ Error en 'ventas_full': {e}")

    print(f"\n🚀 [3/7] Sincronizando 'leads' (Cliengo, historial completo)...\n")
    try:
        sync_leads()
        print("✅ 'leads' OK.")
    except Exception as e:
        print(f"❌ Error en 'leads': {e}")

    print(f"\n🚀 [4/7] Sincronizando 'enviame_despachos' (Control Logístico) con dias_atras={dias_atras_enviame}...\n")
    try:
        sync_enviame(dias_atras=dias_atras_enviame)
        print("✅ 'enviame_despachos' OK.")
    except Exception as e:
        print(f"❌ Error en 'enviame_despachos': {e}")

    print(f"\n🚀 [5/7] Sincronizando 'marketing' (Google Ads + Meta Ads, histórico completo)...\n")
    try:
        sync_marketing()
        print("✅ 'marketing' OK.")
    except Exception as e:
        print(f"❌ Error en 'marketing': {e}")

    print(f"\n🚀 [6/7] Sincronizando 'ga4_kaltemp' (Indicadores D2C, kaltemp.cl, histórico completo)...\n")
    try:
        sync_ga4_kaltemp()
        print("✅ 'ga4_kaltemp' OK.")
    except Exception as e:
        print(f"❌ Error en 'ga4_kaltemp': {e}")

    print(f"\n🚀 [7/7] Sincronizando 'ga4_tompalmer' (Indicadores D2C, tompalmer.cl, histórico completo)...\n")
    try:
        sync_ga4_tompalmer()
        print("✅ 'ga4_tompalmer' OK.")
    except Exception as e:
        print(f"❌ Error en 'ga4_tompalmer': {e}")

    print("\n" + "=" * 70)
    print("✅ Listo. ventas + ventas_full + leads + enviame_despachos + marketing + ga4 (Kaltemp y Tom Palmer) quedaron al día.")
    print("=" * 70)

    respuesta_costos = input(
        "\n¿Correr también actualizar_fletes_enviame.py para calcular COSTO_ENVIO de los "
        "despachos recién sincronizados? Llama a la API de Envíame por cada despacho "
        "pendiente, así que puede tardar más. (s/n): "
    ).strip().lower()
    if respuesta_costos == "s":
        print("\n🚀 Calculando COSTO_ENVIO de despachos pendientes...\n")
        try:
            ejecutar_actualizacion_costos()
            print("✅ 'COSTO_ENVIO' OK.")
        except Exception as e:
            print(f"❌ Error calculando COSTO_ENVIO: {e}")
    else:
        print("⏭️ Se saltó el cálculo de COSTO_ENVIO -- los despachos nuevos quedan con costo en 0 hasta la próxima corrida.")

    print("\n" + "=" * 70)
    print("   Si necesitas stock, notas de crédito, etc. al día también,")
    print("   corre sync_master.py completo.")
    print("=" * 70)


if __name__ == "__main__":
    main()