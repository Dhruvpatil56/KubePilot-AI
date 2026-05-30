import sqlite3
import json
import os
from typing import Optional


def _get_db_path() -> str:
    path = os.environ.get("DB_PATH", "/data/kubepilot.db")
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.isdir(db_dir):
        path = "./kubepilot.db"
    return path


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_get_db_path())


def init_db() -> None:
    con = _connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            alert       TEXT,
            pod         TEXT,
            namespace   TEXT,
            status      TEXT,
            rca         TEXT,
            action_taken TEXT,
            error       TEXT
        )
    """)
    con.commit()
    con.close()
    print(f"✅ Database initialised at {_get_db_path()}")


def save_incident(incident: dict) -> int:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO incidents
            (timestamp, alert, pod, namespace, status, rca, action_taken, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            incident.get("timestamp"),
            incident.get("alert"),
            incident.get("pod"),
            incident.get("namespace"),
            incident.get("status"),
            json.dumps(incident["rca"]) if incident.get("rca") is not None else None,
            incident.get("action_taken"),
            incident.get("error"),
        ),
    )
    con.commit()
    incident_id = cur.lastrowid
    con.close()
    return incident_id


def _row_to_dict(row: tuple) -> dict:
    keys = ["id", "timestamp", "alert", "pod", "namespace", "status", "rca", "action_taken", "error"]
    d = dict(zip(keys, row))
    if d.get("rca") is not None:
        d["rca"] = json.loads(d["rca"])
    # Drop None values to match the original in-memory incident format
    return {k: v for k, v in d.items() if v is not None}


def get_all_incidents() -> list:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, timestamp, alert, pod, namespace, status, rca, action_taken, error "
        "FROM incidents ORDER BY timestamp DESC"
    )
    rows = cur.fetchall()
    con.close()
    return [_row_to_dict(r) for r in rows]


def get_incident_by_id(incident_id: int) -> Optional[dict]:
    con = _connect()
    cur = con.cursor()
    cur.execute(
        "SELECT id, timestamp, alert, pod, namespace, status, rca, action_taken, error "
        "FROM incidents WHERE id = ?",
        (incident_id,),
    )
    row = cur.fetchone()
    con.close()
    if row is None:
        return None
    return _row_to_dict(row)
