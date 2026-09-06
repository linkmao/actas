import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "actas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS actas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_acta INTEGER NOT NULL,
    fecha TEXT NOT NULL,
    hora_inicio TEXT,
    hora_fin TEXT,
    lugar TEXT DEFAULT 'Coordinación',
    elaborada_por TEXT,
    personas_json TEXT NOT NULL,
    descripcion_breve TEXT NOT NULL,
    tipificacion_json TEXT,
    narrativa_antecedentes TEXT,
    acciones_json TEXT,
    acuerdos_texto TEXT,
    proxima_reunion_json TEXT,
    estado TEXT NOT NULL DEFAULT 'borrador',
    archivo_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def next_numero_acta(conn) -> int:
    row = conn.execute("SELECT MAX(numero_acta) AS m FROM actas").fetchone()
    return (row["m"] or 0) + 1


def create_acta(conn, data: dict) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    numero_acta = data.get("numero_acta") or next_numero_acta(conn)
    cur = conn.execute(
        """
        INSERT INTO actas (
            numero_acta, fecha, hora_inicio, hora_fin, lugar, elaborada_por,
            personas_json, descripcion_breve, tipificacion_json,
            narrativa_antecedentes, acciones_json, acuerdos_texto,
            proxima_reunion_json, estado, archivo_path, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            numero_acta,
            data["fecha"],
            data.get("hora_inicio"),
            data.get("hora_fin"),
            data.get("lugar", "Coordinación"),
            data.get("elaborada_por"),
            json.dumps(data.get("personas", []), ensure_ascii=False),
            data.get("descripcion_breve", ""),
            json.dumps(data.get("tipificacion"), ensure_ascii=False) if data.get("tipificacion") else None,
            data.get("narrativa_antecedentes"),
            json.dumps(data.get("acciones", []), ensure_ascii=False),
            data.get("acuerdos_texto"),
            json.dumps(data.get("proxima_reunion")) if data.get("proxima_reunion") else None,
            data.get("estado", "borrador"),
            data.get("archivo_path"),
            now,
            now,
        ),
    )
    conn.commit()
    return cur.lastrowid


def update_acta(conn, acta_id: int, data: dict):
    now = datetime.now().isoformat(timespec="seconds")
    fields = []
    values = []
    mapping = {
        "fecha": "fecha",
        "hora_inicio": "hora_inicio",
        "hora_fin": "hora_fin",
        "lugar": "lugar",
        "elaborada_por": "elaborada_por",
        "descripcion_breve": "descripcion_breve",
        "acuerdos_texto": "acuerdos_texto",
        "estado": "estado",
        "archivo_path": "archivo_path",
    }
    for key, column in mapping.items():
        if key in data:
            fields.append(f"{column} = ?")
            values.append(data[key])
    json_mapping = {
        "personas": "personas_json",
        "tipificacion": "tipificacion_json",
        "acciones": "acciones_json",
        "proxima_reunion": "proxima_reunion_json",
    }
    for key, column in json_mapping.items():
        if key in data:
            fields.append(f"{column} = ?")
            values.append(json.dumps(data[key], ensure_ascii=False) if data[key] is not None else None)
    if "narrativa_antecedentes" in data:
        fields.append("narrativa_antecedentes = ?")
        values.append(data["narrativa_antecedentes"])
    fields.append("updated_at = ?")
    values.append(now)
    values.append(acta_id)
    conn.execute(f"UPDATE actas SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()


def get_acta(conn, acta_id: int):
    row = conn.execute("SELECT * FROM actas WHERE id = ?", (acta_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_actas(conn, search: str | None = None):
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            """
            SELECT * FROM actas
            WHERE descripcion_breve LIKE ? OR personas_json LIKE ? OR CAST(numero_acta AS TEXT) LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM actas ORDER BY id DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for key in ("personas_json", "tipificacion_json", "acciones_json", "proxima_reunion_json"):
        raw = d.pop(key, None)
        new_key = key.replace("_json", "")
        d[new_key] = json.loads(raw) if raw else ([] if new_key in ("personas", "acciones") else None)
    return d


# --- Configuración del proveedor de IA (guardada localmente, nunca sale de este equipo) ---

def get_config_values(conn) -> dict:
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_config_values(conn, values: dict):
    now = datetime.now().isoformat(timespec="seconds")
    for key, value in values.items():
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()
