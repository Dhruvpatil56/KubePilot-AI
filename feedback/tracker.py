import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional


def _get_db_path() -> str:
    path = os.environ.get("DB_PATH", "/data/kubepilot.db")
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.isdir(db_dir):
        path = "./kubepilot.db"
    return path


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(_get_db_path())
    con.row_factory = sqlite3.Row
    return con


def init_remediation_table() -> None:
    con = _connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS remediation_outcomes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pod_name        TEXT NOT NULL,
            namespace       TEXT NOT NULL,
            action          TEXT NOT NULL,
            incident_id     INTEGER,
            applied_at      TEXT NOT NULL,
            outcome         TEXT,
            checked_at      TEXT,
            failure_count   INTEGER DEFAULT 0
        )
    """)
    con.commit()
    con.close()


def record_remediation(pod_name: str, namespace: str, action: str, incident_id: Optional[int] = None) -> int:
    con = _connect()
    now = datetime.now(timezone.utc).isoformat()
    cur = con.execute(
        """INSERT INTO remediation_outcomes (pod_name, namespace, action, incident_id, applied_at, outcome)
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (pod_name, namespace, action, incident_id, now),
    )
    con.commit()
    record_id = cur.lastrowid
    con.close()
    return record_id


def update_outcome(record_id: int, outcome: str) -> None:
    con = _connect()
    now = datetime.now(timezone.utc).isoformat()
    con.execute(
        "UPDATE remediation_outcomes SET outcome=?, checked_at=? WHERE id=?",
        (outcome, now, record_id),
    )
    con.commit()
    con.close()


def get_failure_count(pod_name: str, namespace: str) -> int:
    con = _connect()
    row = con.execute(
        """SELECT failure_count FROM remediation_outcomes
           WHERE pod_name=? AND namespace=?
           ORDER BY id DESC LIMIT 1""",
        (pod_name, namespace),
    ).fetchone()
    con.close()
    return row["failure_count"] if row else 0


def reset_failure_count(pod_name: str, namespace: str) -> None:
    con = _connect()
    con.execute(
        """UPDATE remediation_outcomes SET failure_count=0
           WHERE pod_name=? AND namespace=?
           AND id=(SELECT MAX(id) FROM remediation_outcomes WHERE pod_name=? AND namespace=?)""",
        (pod_name, namespace, pod_name, namespace),
    )
    con.commit()
    con.close()


def increment_failure_count(pod_name: str, namespace: str) -> None:
    con = _connect()
    current = get_failure_count(pod_name, namespace)
    con.execute(
        """UPDATE remediation_outcomes SET failure_count=?
           WHERE pod_name=? AND namespace=?
           AND id=(SELECT MAX(id) FROM remediation_outcomes WHERE pod_name=? AND namespace=?)""",
        (current + 1, pod_name, namespace, pod_name, namespace),
    )
    con.commit()
    con.close()


def get_pod_history(pod_name: str, namespace: str) -> list:
    con = _connect()
    rows = con.execute(
        """SELECT * FROM remediation_outcomes
           WHERE pod_name=? AND namespace=?
           ORDER BY id DESC LIMIT 10""",
        (pod_name, namespace),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]
