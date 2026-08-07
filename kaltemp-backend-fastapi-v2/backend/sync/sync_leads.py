"""
sync/sync_leads.py — Sincroniza TODOS los leads de Cliengo hacia la tabla `leads`
en kaltemp_matrix.duckdb usando la API oficial Cliengo Connect v1.
"""
import os
import sys
import requests
import duckdb
from datetime import datetime, timezone
from dotenv import load_dotenv

_AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_AQUI, "..", "..", ".env"), override=True)
load_dotenv(os.path.join(_AQUI, "..", ".env"), override=True)

CLIENGO_API_KEY = os.getenv("CLIENGO_API_KEY")
DB_FILE = os.getenv("DUCKDB_PATH", os.path.join(_AQUI, "..", "kaltemp_matrix.duckdb"))


def descargar_leads_cliengo():
    """Descarga TODOS los contactos de Cliengo recorriendo todas las páginas"""
    if not CLIENGO_API_KEY:
        return []

    todos_los_contactos = []
    page = 1
    limit = 50

    headers = {
        "Authorization": f"Bearer {CLIENGO_API_KEY}",
        "Accept": "application/json"
    }

    print(f"  [Cliengo Connect] Descargando contactos...")
    while True:
        url = f"https://connect.cliengo.com/v1/contacts?page={page}&limit={limit}"
        try:
            res = requests.get(url, headers=headers, timeout=25)
            if res.status_code == 200:
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
            else:
                break
        except Exception as e:
            print(f"⚠️ Error en página {page} de Cliengo Connect: {e}")
            break

    # Fallback a API v1.0 legacy
    if not todos_los_contactos:
        print(f"  [Cliengo Legacy v1.0] Probando endpoint secundario...")
        page = 1
        while True:
            url_legacy = f"https://api.cliengo.com/1.0/contacts?api_key={CLIENGO_API_KEY}&page={page}&limit=50"
            try:
                res = requests.get(url_legacy, timeout=25)
                if res.status_code != 200:
                    break
                data = res.json()
                items = data.get("contacts") or data.get("results") or (data if isinstance(data, list) else [])
                if not items:
                    break

                if todos_los_contactos and str(items[0].get("id")) == str(todos_los_contactos[0].get("id")):
                    break

                todos_los_contactos.extend(items)
                if len(items) < 50:
                    break
                page += 1
            except Exception:
                break

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
    comuna = c.get("city") or c.get("comuna") or c.get("location") or c.get("geo")
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

    # 2. Probar campos de URL o landing page
    for field in ("product", "producto", "interest", "category", "landing_page", "landingPage", "url"):
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


def sync_leads(progress_callback=None):
    def report(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)
        print(f"[{pct}%] {msg}")

    report(5, "🎯 Conectando con Cliengo Connect API para sincronizar Leads...")
    raw_contacts = descargar_leads_cliengo()
    report(40, f"📥 {len(raw_contacts)} prospectos/leads totales descargados de Cliengo.")

    filas = []
    for idx, c in enumerate(raw_contacts):
        if not isinstance(c, dict):
            continue

        id_lead = str(c.get("id") or c.get("_id") or f"LEAD_{idx}")
        fecha_obj = parsear_fecha(c.get("created_at") or c.get("createdAt") or c.get("date"))
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
        # Eliminamos la tabla previa para reconstruir el esquema con la columna PRODUCTO
        con.execute("DROP TABLE IF EXISTS leads")
        con.execute("""
            CREATE TABLE leads (
                ID_LEAD VARCHAR, FECHA_OBJ TIMESTAMP, NOMBRE VARCHAR,
                FUENTE VARCHAR, ESTADO VARCHAR, VENDEDOR VARCHAR,
                CALIFICACION INTEGER, COMUNA VARCHAR, CANAL VARCHAR,
                PRODUCTO VARCHAR
            )
        """)
        con.execute("DELETE FROM leads")
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