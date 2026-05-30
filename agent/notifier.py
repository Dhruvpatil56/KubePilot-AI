import logging
import os

import requests

logger = logging.getLogger(__name__)


def _severity_emoji(incident: dict) -> str:
    alert = (incident.get("alert") or "").lower()
    if "critical" in alert or "crash" in alert or "oom" in alert:
        return "\U0001f534"  # 🔴
    return "\U0001f7e1"      # 🟡


def send_slack_notification(incident: dict) -> None:
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = os.environ.get("SLACK_CHANNEL")

    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — skipping Slack notification")
        return
    if not channel:
        logger.warning("SLACK_CHANNEL not set — skipping Slack notification")
        return

    rca = incident.get("rca") or {}
    alert_name = incident.get("alert") or "Unknown Alert"
    emoji = _severity_emoji(incident)

    confidence = rca.get("confidence")
    confidence_str = f"{round(confidence * 100)}%" if confidence is not None else "N/A"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji}  {alert_name}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Pod*\n{incident.get('pod') or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Namespace*\n{incident.get('namespace') or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Action Taken*\n{incident.get('action_taken') or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Confidence*\n{confidence_str}"},
            ],
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Root Cause*\n{rca.get('root_cause') or 'N/A'}"},
                {"type": "mrkdwn", "text": f"*Risk Level*\n{rca.get('risk_level') or 'N/A'}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*KubePilot AI*  |  {incident.get('timestamp', '')} UTC",
                }
            ],
        },
    ]

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "channel": channel,
                "blocks": blocks,
                # Fallback plain-text for notifications/accessibility
                "text": f"{emoji} {alert_name} on pod {incident.get('pod', 'unknown')}",
            },
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            logger.warning(f"Slack API error: {data.get('error')}")
        else:
            logger.info(f"Slack notification sent for incident #{incident.get('id')}")
    except Exception as e:
        logger.warning(f"Failed to send Slack notification: {e}")
