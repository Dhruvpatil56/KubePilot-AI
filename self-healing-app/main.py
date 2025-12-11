from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from datetime import datetime
import json

from config import config
from k8s_client import K8sClient
from llm_analyzer import LLMAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SRE Self-Healing Agent")

# Initialize clients
k8s_client = K8sClient()
llm_analyzer = LLMAnalyzer()

# In-memory incident history (simple but fine for demo)
incident_history: List[Dict] = []


class AlertWebhook(BaseModel):
    receiver: str
    status: str
    alerts: List[Dict]
    groupLabels: Optional[Dict] = None
    commonLabels: Optional[Dict] = None
    commonAnnotations: Optional[Dict] = None


@app.get("/")
async def root():
    return {
        "service": "SRE Self-Healing Agent",
        "status": "running",
        "version": "1.0.0",
        "config": {
            "auto_remediation_enabled": config.ENABLE_AUTO_REMEDIATION,
            "dry_run": config.DRY_RUN,
            "confidence_threshold": config.CONFIDENCE_THRESHOLD,
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/incidents")
async def get_incidents():
    """Get incident history (last 20)"""
    return {
        "total": len(incident_history),
        "incidents": incident_history[-20:],
    }


@app.post("/webhook/alert")
async def handle_alert(webhook: AlertWebhook, background_tasks: BackgroundTasks):
    """Main webhook endpoint for Alertmanager"""

    logger.info(f"Received webhook: status={webhook.status}, alerts={len(webhook.alerts)}")

    # Only process firing alerts
    if webhook.status != "firing":
        return {"status": "ignored", "reason": "alert not firing"}

    results = []
    for alert in webhook.alerts:
        alertname = alert.get("labels", {}).get("alertname")
        logger.info(f"Queueing alert for processing: {alertname}")
        background_tasks.add_task(process_alert, alert)
        results.append(
            {
                "alertname": alertname,
                "status": "queued_for_processing",
            }
        )

    return {
        "status": "accepted",
        "processed": len(results),
        "results": results,
    }


def process_alert(alert: Dict):
    """Process a single alert and take action (runs in background)"""

    incident_id = f"incident-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    labels = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    try:
        alertname = labels.get("alertname", "Unknown")
        pod_name = labels.get("pod", "")
        namespace = labels.get("namespace", config.K8S_NAMESPACE)

        logger.info(f"[{incident_id}] Processing {alertname} for pod={pod_name} ns={namespace}")

        if not pod_name:
            logger.warning(f"[{incident_id}] No pod name in alert, skipping")
            return

        # 1) Gather pod info
        pod_details = k8s_client.get_pod_details(pod_name, namespace)
        if not pod_details:
            logger.error(f"[{incident_id}] Could not get pod details for {pod_name}")
            return

        logs = k8s_client.get_pod_logs(pod_name, namespace, lines=50)
        previous_logs = k8s_client.get_previous_pod_logs(pod_name, namespace, lines=50)
        events = k8s_client.get_pod_events(pod_name, namespace)

        # 2) Analyze with LLM (or fallback)
        logger.info(f"[{incident_id}] Analyzing incident with LLM / rules...")
        analysis = llm_analyzer.analyze_incident(
            alert_data=alert,
            pod_details=pod_details,
            logs=logs,
            previous_logs=previous_logs,
            events=events,
        )

        logger.info(f"[{incident_id}] Analysis:\n{json.dumps(analysis, indent=2)}")

        # 3) Decide whether to take action
        action_taken: Optional[str] = None
        action_result: Optional[str] = None

        if not config.ENABLE_AUTO_REMEDIATION:
            logger.info(f"[{incident_id}] Auto-remediation disabled, skipping action")
            action_taken = "none (disabled)"

        elif float(analysis.get("confidence", 0.0)) < float(config.CONFIDENCE_THRESHOLD):
            logger.warning(
                f"[{incident_id}] Confidence {analysis.get('confidence')} below threshold "
                f"{config.CONFIDENCE_THRESHOLD}"
            )
            action_taken = "none (low confidence)"

        elif analysis.get("recommended_action") == "no_action":
            logger.info(f"[{incident_id}] LLM/rules recommended no_action")
            action_taken = "none (llm recommendation)"

        else:
            action_taken = analysis["recommended_action"]
            logger.info(f"[{incident_id}] Taking action: {action_taken}")

            if config.DRY_RUN:
                logger.info(f"[{incident_id}] DRY RUN - would execute: {action_taken}")
                action_result = "dry_run_success"
            else:
                action_result = execute_action(
                    action=action_taken,
                    pod_name=pod_name,
                    namespace=namespace,
                    pod_details=pod_details,
                )

        # 4) Record incident
        restart_count = 0
        if pod_details.get("container_statuses"):
            restart_count = pod_details["container_statuses"][0].get("restart_count", 0)

        incident = {
            "incident_id": incident_id,
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "name": alertname,
                "severity": labels.get("severity"),
                "pod": pod_name,
                "namespace": namespace,
                "description": annotations.get("description"),
            },
            "analysis": analysis,
            "action_taken": action_taken,
            "action_result": action_result,
            "pod_details_summary": {
                "status": pod_details.get("status"),
                "restart_count": restart_count,
            },
        }

        incident_history.append(incident)
        logger.info(f"[{incident_id}] Incident processing complete")

    except Exception as e:
        logger.error(f"[{incident_id}] Error processing alert: {e}", exc_info=True)


def execute_action(action: str, pod_name: str, namespace: str, pod_details: Dict) -> str:
    """Execute the remediation action"""

    try:
        if action == "restart_pod":
            success = k8s_client.restart_pod(pod_name, namespace)
            return "success" if success else "failed"

        elif action in ("scale_up", "scale_down", "rollback"):
            deployment_name = k8s_client.get_deployment_from_pod(pod_name, namespace)
            if not deployment_name:
                return "failed (no deployment found)"

            deployment = k8s_client.apps_v1.read_namespaced_deployment(deployment_name, namespace)
            current_replicas = deployment.spec.replicas or 1

            if action == "scale_up":
                new_replicas = current_replicas + 1
                success = k8s_client.scale_deployment(deployment_name, namespace, new_replicas)
                return f"success (scaled to {new_replicas})" if success else "failed"

            elif action == "scale_down":
                if current_replicas <= 1:
                    return "skipped (already at minimum replicas)"
                new_replicas = current_replicas - 1
                success = k8s_client.scale_deployment(deployment_name, namespace, new_replicas)
                return f"success (scaled to {new_replicas})" if success else "failed"

            elif action == "rollback":
                success = k8s_client.rollback_deployment(deployment_name, namespace)
                return "success (restart/rollback triggered)" if success else "failed"

        else:
            return "unknown action"

    except Exception as e:
        logger.error(f"Error executing action {action}: {e}")
        return f"failed ({str(e)})"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

