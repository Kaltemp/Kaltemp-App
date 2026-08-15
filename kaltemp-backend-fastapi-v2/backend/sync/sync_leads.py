# ============================================================
# ARCHIVO: sync_leads.py
# GUARDAR EN: C:\kaltemp_app\kaltemp-backend-fastapi-v2\backend\sync\sync_leads.py
# (Agrega soporte para 'dias_atras' -- el campo de días del motor
#  ahora controla también esta tabla. Respaldar: Copy-Item sync_leads.py sync_leads.py.bak)
# ============================================================

"""
sync/sync_leads.py — Sincroniza los leads de Cliengo hacia la tabla `leads`
en kaltemp_matrix.duckdb.

CORREGIDO (10-ago-2026, diagnóstico real con William):
1. PAGINACIÓN: el endpoint legacy (api.cliengo.com/1.0/contacts) IGNORA
   el parámetro 'page=' -- siempre devuelve la página 1 sin importar qué
   número se mande (confirmado con diagnostico_cliengo_legacy.py: 5
   páginas pedidas, 5 respuestas idénticas). El parámetro real que SÍ
   funciona es 'offset='. Antes de este fix, el sync se cortaba siempre
   en 50 registros -- no por un límite de la cuenta, sino por pedir mal
   la página siguiente.
2. VENTANA DE FECHA: el endpoint SÍ acepta un filtro 'since=' (probado
   contra el total real: sin filtro=108.113, con since=2023-01-01
   =29.281 -- los demás nombres candidatos como date_from/created_at_min
   no tienen efecto). Se agrega CLIENGO_FECHA_DESDE (env var, default
   2023-01-01) para no traer los 108k contactos completos.
3. CAMPOS MAL MAPEADOS: el JSON real de un contacto (confirmado con
   diagnóstico) NO trae 'created_at'/'createdAt'/'date' -- la fecha real
   viene en 'creationDate'. Esto significa que TODOS los leads
   sincronizados hasta ahora quedaron guardados con la fecha del
   momento de la sync, no su fecha real de creación -- se corrige acá.
   La comuna tampoco viene en 'geo' sino anidada en 'geoip.city'.
4. TOKEN: el CLIENGO_API_KEY actual (formato UUID) da 401 "Invalid
   token format" contra la API nueva Connect v1 (que exige sk_.../JWT)
   -- por eso el fallback a la API legacy siempre se activa. El fallback
   ahora es la ruta principal en la práctica; se mantiene el intento a
   Connect v1 por si en el futuro se genera un token válido para esa API.
5. Se corrige además el bug de silenciar errores: antes, si una página
   fallaba (status != 200) el loop hacía 'break' sin imprimir nada --
   ahora se loguea el status code y el cuerpo de la respuesta.
6. LÍMITE DE OFFSET: confirmado con diagnostico_cliengo_corte.py que la
   API rechaza offset > 1000 ("Offset cannot be greater than 1000"),
   sin importar el filtro since -- por eso el primer fix (solo offset+
   since) se quedaba en ~1.050 registros (los más recientes, ya que el
   orden es descendente y no se puede cambiar). Se corrige partiendo el
   rango completo en ventanas de fecha (since+until, confirmado real con
   diagnostico_cliengo_ventanas.py) que se subdividen recursivamente
   hasta que cada una quepa bajo el límite de 1000.
"""
import os
import sys
import requests
import duckdb
from datetime import datetime, timezone, timedelta, date
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

CLIENGO_API_KEY = os.getenv("CLIENGO_API_KEY")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))
CLIENGO_FECHA_DESDE = os.getenv("CLIENGO_FECHA_DESDE", "2023-01-01")

# Confirmado real (10-ago-2026, diagnostico_cliengo_corte.py): la API
# legacy de Cliengo rechaza offset > 1000 ("Offset cannot be greater
# than 1000"), sin importar el filtro 'since'. Como además los
# resultados vienen ordenados del más reciente al más antiguo (sin
# forma de cambiar el orden -- se probaron sort/order/orderBy/sortBy,
# ninguno tiene efecto), un solo pedido con since=2023-01-01 solo
# alcanza a traer los ~1.050 contactos más recientes, nunca llega a
# 2023. La solución: partir el rango completo en VENTANAS de fecha
# usando 'since'+'until' (confirmado real con diagnostico_cliengo_
# ventanas.py: total baja de 29.281 a 500 al acotar a un mes), y si una
# ventana individual todavía supera los 1000 registros, partirla a la
# mitad recursivamente hasta que quepa.
CLIENGO_OFFSET_MAXIMO = 1000
CLIENGO_LIMIT = 50


def _pedir_pagina_cliengo(desde: str, hasta: str, offset: int, limit: int = CLIENGO_LIMIT):
    """Un solo GET a la API legacy. Devuelve (status_code, items, total)."""
    url = (
        f"https://api.cliengo.com/1.0/contacts"
        f"?api_key={CLIENGO_API_KEY}&offset={offset}&limit={limit}&since={desde}&until={hasta}"
    )
    try:
        res = requests.get(url, timeout=25)
    except Exception as e:
        print(f"  ⚠️ Error de conexión (since={desde} until={hasta} offset={offset}): {e}")
        return None, [], 0

    if res.status_code != 200:
        print(f"  ⚠️ Cliengo legacy devolvió {res.status_code} (since={desde} until={hasta} offset={offset}): {res.text[:300]!r}")
        return res.status_code, [], 0

    try:
        data = res.json()
    except Exception as e:
        print(f"  ⚠️ Respuesta no es JSON válido (since={desde} until={hasta} offset={offset}): {e}")
        return res.status_code, [], 0

    paging = data.get("paging") or {}
    items = data.get("contacts") or data.get("results") or (data if isinstance(data, list) else [])
    return res.status_code, items, paging.get("total", 0)


def _descargar_ventana(desde: str, hasta: str, total: int, acumulados: list, vistos: set, report=print, total_general: int = 1):
    """Pagina UNA ventana de fecha ya confirmada <= CLIENGO_OFFSET_MAXIMO."""
    offset = 0
    while offset <= total and offset < CLIENGO_OFFSET_MAXIMO:
        status, items, _ = _pedir_pagina_cliengo(desde, hasta, offset)
        if not items:
            break
        for it in items:
            id_it = it.get("id") if isinstance(it, dict) else None
            # Dedup por si 'until' resulta ser inclusivo -- evita contar
            # dos veces un contacto justo en el borde entre dos ventanas.
            if id_it is not None:
                if id_it in vistos:
                    continue
                vistos.add(id_it)
            acumulados.append(it)
        if len(acumulados) % 500 < CLIENGO_LIMIT:
            report(min(5 + int((len(acumulados) / max(total_general, 1)) * 35), 40),
                   f"📥 {len(acumulados)}/{total_general} contactos descargados de Cliengo...")
        offset += CLIENGO_LIMIT
        if len(items) < CLIENGO_LIMIT:
            break


def _recolectar_por_ventanas(desde_dt: date, hasta_dt: date, acumulados: list, vistos: set, report=print, total_general: int = 1, profundidad: int = 0):
    """Recursivo: cuenta el total real de la ventana [desde_dt, hasta_dt).
    Si cabe bajo el límite de offset, la descarga directo. Si no, la
    parte en dos mitades por fecha y recurre en cada una."""
    desde_str = desde_dt.strftime("%Y-%m-%d")
    hasta_str = hasta_dt.strftime("%Y-%m-%d")

    if desde_dt >= hasta_dt:
        return

    _, _, total_ventana = _pedir_pagina_cliengo(desde_str, hasta_str, offset=0, limit=1)

    if total_ventana == 0:
        return

    dias_en_ventana = (hasta_dt - desde_dt).days

    if total_ventana <= CLIENGO_OFFSET_MAXIMO or dias_en_ventana <= 1:
        if total_ventana > CLIENGO_OFFSET_MAXIMO:
            print(f"  ⚠️ Ventana {desde_str}→{hasta_str} tiene {total_ventana} contactos en 1 solo día -- "
                  f"no se puede acotar más, se traen solo los primeros {CLIENGO_OFFSET_MAXIMO}.")
        print(f"  [Ventana {desde_str} → {hasta_str}] {total_ventana} contactos")
        _descargar_ventana(desde_str, hasta_str, total_ventana, acumulados, vistos, report=report, total_general=total_general)
        return

    # Ventana muy grande -- partir a la mitad por fecha y recurrir
    mitad = desde_dt + timedelta(days=dias_en_ventana // 2)
    _recolectar_por_ventanas(desde_dt, mitad, acumulados, vistos, report=report, total_general=total_general, profundidad=profundidad + 1)
    _recolectar_por_ventanas(mitad, hasta_dt, acumulados, vistos, report=report, total_general=total_general, profundidad=profundidad + 1)


def _descargar_legacy(fecha_desde: str, report=print):
    """Descarga vía api.cliengo.com/1.0/contacts, partiendo el rango
    completo en ventanas de fecha para nunca chocar con el límite real
    de offset<=1000 de esta API (ver comentario arriba de
    CLIENGO_OFFSET_MAXIMO)."""
    desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
    hasta_dt = date.today() + timedelta(days=1)  # +1 para incluir contactos de hoy (until parece exclusivo)

    _, _, total_general = _pedir_pagina_cliengo(fecha_desde, hasta_dt.strftime("%Y-%m-%d"), offset=0, limit=1)
    print(f"  [Cliengo Legacy] Total de contactos desde {fecha_desde}: {total_general}")

    resultados = []
    vistos = set()
    _recolectar_por_ventanas(desde_dt, hasta_dt, resultados, vistos, report=report, total_general=max(total_general, 1))
    print(f"  [Cliengo Legacy] {len(resultados)} contactos únicos recolectados tras deduplicar por id.")
    return resultados


def descargar_leads_cliengo(fecha_desde: str, report=print):
    """Intenta primero la API nueva Connect v1 (requiere token sk_.../JWT
    -- hoy falla con 401 porque CLIENGO_API_KEY es un token legacy tipo
    UUID, confirmado con diagnostico_cliengo.py). Si falla, cae a la API
    legacy (api.cliengo.com/1.0), que sí funciona con este token."""
    if not CLIENGO_API_KEY:
        return []

    todos_los_contactos = []
    page = 1
    limit = 50

    headers = {
        "Authorization": f"Bearer {CLIENGO_API_KEY}",
        "Accept": "application/json"
    }

    print(f"  [Cliengo Connect] Probando API v1 (requiere token sk_.../JWT)...")
    while True:
        url = f"https://connect.cliengo.com/v1/contacts?page={page}&limit={limit}"
        try:
            res = requests.get(url, headers=headers, timeout=25)
        except Exception as e:
            print(f"  ⚠️ Error de conexión en página {page} de Cliengo Connect: {e}")
            break

        if res.status_code != 200:
            print(f"  ⚠️ Cliengo Connect v1 devolvió {res.status_code}: {res.text[:300]!r} -- cayendo a API legacy.")
            break

        data = res.json()
        items = data.get("results") or data.get("contacts") or (data if isinstance(data, list) else [])
        if not items:
            break
        todos_los_contactos.extend(items)

        pagination = data.get("pagination") or {}
        total = pagination.get("total", 0)
        if total and len(todos_los_contactos) >= total:
            break
        if len(items) < limit:
            break
        page += 1

    if not todos_los_contactos:
        print(f"  [Cliengo Legacy v1.0] Descargando desde {fecha_desde}...")
        todos_los_contactos = _descargar_legacy(fecha_desde, report=report)

    return todos_los_contactos


def parsear_fecha(val_fecha):
    if not val_fecha:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        if isinstance(val_fecha, (int, float)):
            if val_fecha > 1e11:
                val_fecha = val_fecha / 1000.0
            return datetime.fromtimestamp(val_fecha, tz=timezone.utc).replace(tzinfo=None)
        s = str(val_fecha).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def extraer_vendedor(c: dict) -> str:
    agent = c.get("assignedTo") or c.get("agent") or c.get("assignedUser") or c.get("assigned_user") or c.get("user")
    if isinstance(agent, dict):
        nombre = agent.get("name") or agent.get("first_name") or agent.get("email") or ""
        if nombre:
            return str(nombre).strip().title()
    elif isinstance(agent, str) and agent.strip() and agent.strip().lower() not in ("none", "null", "unassigned", ""):
        return agent.strip().title()
    return "Sin Vendedor"


def extraer_comuna(c: dict) -> str:
    # Confirmado real (10-ago-2026): la comuna viene anidada en geoip.city,
    # no en un campo plano "geo" -- ese nombre nunca existió en la
    # respuesta real de Cliengo, por eso siempre caía en "Sin Comuna".
    geoip = c.get("geoip") or {}
    comuna = None
    if isinstance(geoip, dict):
        comuna = geoip.get("city") or geoip.get("state")
    if not comuna:
        comuna = c.get("city") or c.get("comuna") or c.get("location")
    if isinstance(comuna, dict):
        comuna = comuna.get("city") or comuna.get("name") or comuna.get("comuna") or ""
    if isinstance(comuna, str) and comuna.strip() and comuna.strip().lower() not in ("none", "null", ""):
        return comuna.strip().title()

    cf = c.get("customFields") or c.get("custom_fields") or c.get("additional_fields") or []
    if isinstance(cf, list):
        for item in cf:
            if isinstance(item, dict):
                k = str(item.get("key") or item.get("name") or "").lower()
                if any(x in k for x in ("comuna", "ciudad", "city", "ubicacion")):
                    v = item.get("value")
                    if v and str(v).strip():
                        return str(v).strip().title()
    elif isinstance(cf, dict):
        for k, v in cf.items():
            if any(x in str(k).lower() for x in ("comuna", "ciudad", "city")):
                if v and str(v).strip():
                    return str(v).strip().title()

    return "Sin Comuna"


def extraer_producto(c: dict) -> str:
    """Extrae el producto o categoría por el cual llegó el prospecto"""
    # 1. Probar en customFields
    cf = c.get("customFields") or c.get("custom_fields") or c.get("additional_fields") or []
    if isinstance(cf, list):
        for item in cf:
            if isinstance(item, dict):
                k = str(item.get("key") or item.get("name") or "").lower()
                if any(x in k for x in ("producto", "product", "categoria", "category", "interes", "equipo", "modelo")):
                    v = item.get("value")
                    if v and str(v).strip():
                        return str(v).strip().title()
    elif isinstance(cf, dict):
        for k, v in cf.items():
            if any(x in str(k).lower() for x in ("producto", "product", "categoria", "category", "interes")):
                if v and str(v).strip():
                    return str(v).strip().title()

    # 2. Probar campos de URL o landing page -- "conversionUrl" y
    # "landingUrl" son los nombres reales confirmados en la respuesta de
    # Cliengo (antes se probaban "landing_page"/"landingPage"/"url", que
    # no existen en el JSON real).
    for field in ("product", "producto", "interest", "category", "conversionUrl", "landingUrl", "referalUrl"):
        val = c.get(field)
        if isinstance(val, str) and val.strip() and val.strip().lower() not in ("none", "null", ""):
            v_lower = val.lower()
            if "aire" in v_lower or "split" in v_lower:
                return "Aire Acondicionado"
            elif "estufa" in v_lower or "pellet" in v_lower:
                return "Estufas a Pellet"
            elif "calefacc" in v_lower or "radiador" in v_lower or "caldera" in v_lower:
                return "Calefacción"
            elif "bomba" in v_lower or "aeroterm" in v_lower:
                return "Bomba de Calor"
            elif "solar" in v_lower or "termo" in v_lower:
                return "Energía Solar / Termos"
            else:
                return val.strip().title()

    # 3. Analizar primer mensaje / conversación
    msg = str(c.get("message") or c.get("first_message") or c.get("notes") or "").lower()
    if msg:
        if any(x in msg for x in ("aire", "clima", "acondicionado", "split", "inverter")):
            return "Aire Acondicionado"
        elif any(x in msg for x in ("estufa", "pellet", "leña")):
            return "Estufas a Pellet"
        elif any(x in msg for x in ("calefaccion", "caldera", "radiador", "piso radiante")):
            return "Calefacción"
        elif any(x in msg for x in ("bomba de calor", "aerotermia", "boiler")):
            return "Bomba de Calor"
        elif any(x in msg for x in ("solar", "termo", "colector")):
            return "Energía Solar / Termos"

    return "General / Consulta Web"


def extraer_estado(c: dict) -> str:
    st = c.get("status") or c.get("stage") or c.get("state")
    if isinstance(st, dict):
        st = st.get("name") or st.get("label") or ""
    s_upper = str(st or "").strip().upper()

    if s_upper in ("CLIENT", "CLIENTE", "WON") or any(k in s_upper for k in ("VENTA", "CON_VENTA", "COMPRA", "CLOSED")):
        return "CON_VENTA"
    elif s_upper in ("LONG_TERM", "DISCARDED", "PERDIDO") or any(k in s_upper for k in ("LOST", "NO INTERESADO", "SIN_VENTA")):
        return "SIN_VENTA"
    elif s_upper in ("ACTIVE", "PROGRESO") or any(k in s_upper for k in ("PROGRESS", "CONTACTADO", "COTIZADO", "SEGUIMIENTO")):
        return "EN_PROGRESO"

    return "NUEVO"


def sync_leads(progress_callback=None, fecha_desde: str = None, dias_atras: int = None):
    """dias_atras (opcional): alternativa a fecha_desde -- se convierte
    internamente. Agregado 11-ago-2026 para que el campo de días del
    motor de actualización controle también esta tabla."""
    if dias_atras and not fecha_desde:
        fecha_desde = (datetime.now(timezone.utc) - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    fecha_desde = fecha_desde or CLIENGO_FECHA_DESDE
    report(5, f"🎯 Conectando con Cliengo para sincronizar Leads (desde {fecha_desde})...")
    raw_contacts = descargar_leads_cliengo(fecha_desde, report=report)
    report(40, f"📥 {len(raw_contacts)} prospectos/leads descargados de Cliengo.")

    filas = []
    for idx, c in enumerate(raw_contacts):
        if not isinstance(c, dict):
            continue

        id_lead = str(c.get("id") or c.get("_id") or f"LEAD_{idx}")
        # "creationDate" es el campo real confirmado en el JSON de Cliengo
        # (10-ago-2026) -- created_at/createdAt/date nunca existieron ahí,
        # por eso todos los leads anteriores quedaron con la fecha de la
        # sync en vez de su fecha real de creación.
        fecha_obj = parsear_fecha(c.get("creationDate") or c.get("created_at") or c.get("createdAt") or c.get("date"))
        nombre = str(c.get("name") or c.get("contactName") or c.get("email") or "Contacto Web").strip().upper()
        
        fuente = str(c.get("source") or c.get("utm_source") or c.get("referrer") or c.get("entryMethod") or "kaltemp.cl").strip()

        estado = extraer_estado(c)
        vendedor = extraer_vendedor(c)
        comuna = extraer_comuna(c)
        producto = extraer_producto(c)

        try:
            calificacion = int(c.get("score") or c.get("rating") or 0)
        except Exception:
            calificacion = 0

        entry_method = str(c.get("entryMethod") or c.get("channel") or c.get("type") or "").lower()
        if any(x in entry_method for x in ("whatsapp", "wsp", "wa")):
            canal = "WhatsApp"
        else:
            canal = "Chat Web"

        filas.append((
            id_lead, fecha_obj, nombre, fuente, estado,
            vendedor, calificacion, comuna, canal, producto
        ))

    report(70, f"💾 Escribiendo {len(filas)} filas en la tabla 'leads' de DuckDB...")

    with duckdb.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                ID_LEAD VARCHAR, FECHA_OBJ TIMESTAMP, NOMBRE VARCHAR,
                FUENTE VARCHAR, ESTADO VARCHAR, VENDEDOR VARCHAR,
                CALIFICACION INTEGER, COMUNA VARCHAR, CANAL VARCHAR,
                PRODUCTO VARCHAR
            )
        """)
        # CORREGIDO (12-ago-2026, confirmado real con William: pidió 7
        # días de histórico y le borró TODOS los leads, dejando solo
        # esos 7 días). Antes: DROP TABLE + DELETE FROM leads (sin
        # condición) -- borraba TODO sin importar que solo se hubiera
        # descargado una ventana chica de Cliengo. Ahora: solo se borra
        # el rango [fecha_desde, hoy] que realmente se volvió a
        # descargar -- el resto del histórico queda intacto. Mismo
        # patrón ya usado en sync_ventas.py / Test.gs (Meta) / el script
        # de Google Ads.
        con.execute(
            "DELETE FROM leads WHERE CAST(FECHA_OBJ AS DATE) >= CAST(? AS DATE)",
            [fecha_desde]
        )
        con.executemany(
            """INSERT INTO leads
               (ID_LEAD, FECHA_OBJ, NOMBRE, FUENTE, ESTADO, VENDEDOR, CALIFICACION, COMUNA, CANAL, PRODUCTO)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas
        )
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (tabla VARCHAR PRIMARY KEY, ultima_actualizacion TIMESTAMP)
        """)
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (tabla, ultima_actualizacion) VALUES (?, ?)",
            ["leads", datetime.now(timezone.utc).replace(tzinfo=None)]
        )

    report(100, f"✨ Sincronización de Leads completa ({len(filas)} registros procesados).")


if __name__ == "__main__":
    sync_leads()