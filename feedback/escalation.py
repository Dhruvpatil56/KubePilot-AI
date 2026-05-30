import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feedback.tracker import get_failure_count, _get_db_path, _connect as _tracker_connect

logger = logging.getLogger(__name__)

ESCALATION_THRESHOLD = int(os.environ.get("ESCALATION_THRESHOLD", "3"))


# ---------- Suppression helpers ----------

def _ensure_suppression_table() -> None:
    con = _tracker_connect()
    con.execute("""
        CREATE TABLE IF NOT EXISTS suppressed_pods (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pod_name    TEXT NOT NULL,
            namespace   TEXT NOT NULL,
            suppressed_at TEXT NOT NULL,
            expires_at  TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def add_to_suppress_list(pod_name: str, namespace: str) -> None:
    _ensure_suppression_table()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)
    con = _tracker_connect()
    # Remove any existing suppression for this pod first
    con.execute(
        "DELETE FROM suppressed_pods WHERE pod_name=? AND namespace=?",
        (pod_name, namespace),
    )
    con.execute(
        "INSERT INTO suppressed_pods (pod_name, namespace, suppressed_at, expires_at) VALUES (?, ?, ?, ?)",
        (pod_name, namespace, now.isoformat(), expires.isoformat()),
    )
    con.commit()
    con.close()
    logger.info(f"Pod {pod_name}/{namespace} suppressed for 1 hour")


def is_suppressed(pod_name: str, namespace: str) -> bool:
    try:
        _ensure_suppression_table()
        con = _tracker_connect()
        now = datetime.now(timezone.utc).isoformat()
        row = con.execute(
            """SELECT id FROM suppressed_pods
               WHERE pod_name=? AND namespace=? AND expires_at > ?
               LIMIT 1""",
            (pod_name, namespace, now),
        ).fetchone()
        con.close()
        return row is not None
    except Exception as e:
        logger.warning(f"is_suppressed check failed: {e}")
        return False


# ---------- Escalation logic ----------

def should_escalate(pod_name: str, namespace: str) -> bool:
    try:
        count = get_failure_count(pod_name, namespace)
        return count >= ESCALATION_THRESHOLD
    except Exception as e:
        logger.warning(f"should_escalate check failed: {e}")
        return False


def escalate_incident(incident: dict, pod_name: str, namespace: str) -> dict:
    failure_count = get_failure_count(pod_name, namespace)
    rca = incident.get("rca") or {}
    last_action = incident.get("action_taken") or "unknown"
    last_rca = rca.get("root_cause") or "N/A"

    logger.warning(
        f"ESCALATION: {pod_name}/{namespace} — {failure_count} consecutive failures, manual intervention needed"
    )

    _send_escalation_slack(incident, pod_name, namespace, failure_count, last_action, last_rca)
    add_to_suppress_list(pod_name, namespace)

    # Log escalation to incidents table
    try:
        from agent.database import save_incident
        escalation_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert": incident.get("alert", "unknown"),
            "pod": pod_name,
            "namespace": namespace,
            "status": "escalated",
            "action_taken": f"escalated after {failure_count} consecutive failures",
            "rca": rca,
        }
        save_incident(escalation_record)
    except Exception as e:
        logger.warning(f"Failed to save escalation incident: {e}")

    return {"escalated": True, "reason": f"failure_count >= {ESCALATION_THRESHOLD}"}


def _send_escalation_slack(
    incident: dict,
    pod_name: str,
    namespace: str,
    failure_count: int,
    last_action: str,
    last_rca: str,
) -> None:
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")

    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — skipping escalation Slack message")
        return
    if not channel:
        logger.warning("SLACK_CHANNEL not set — skipping escalation Slack message")
        return

    try:
        import requests

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "\U0001f6a8 ESCALATION REQUIRED — Human Intervention Needed",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Pod*\n{pod_name}"},
                    {"type": "mrkdwn", "text": f"*Namespace*\n{namespace}"},
                    {"type": "mrkdwn", "text": f"*Consecutive Failures*\n{failure_count}"},
                    {"type": "mrkdwn", "text": f"*Last Action*\n{last_action}"},
                ],
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Last RCA*\n{last_rca}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"KubePilot AI has attempted auto-remediation *{failure_count}* times without success. "
                        "Manual investigation required. "
                        f"Auto-remediation for this pod is *suppressed for 1 hour*."
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*KubePilot AI Escalation*  |  {datetime.now(timezone.utc).isoformat()} UTC",
                    }
                ],
            },
        ]

        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "channel": channel,
                "blocks": blocks,
                "text": f"\U0001f6a8 ESCALATION: {pod_name} in {namespace} needs manual intervention ({failure_count} failures)",
            },
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(f"Escalation Slack error: {data.get('error')}")
        else:
            logger.info(f"Escalation Slack message sent for {pod_name}/{namespace}")
    except Exception as e:
        logger.warning(f"Failed to send escalation Slack message: {e}")
