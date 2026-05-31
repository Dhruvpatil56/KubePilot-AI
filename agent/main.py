from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import json
import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    ENABLE_AUTO_REMEDIATION, DRY_RUN, CONFIDENCE_THRESHOLD, ALLOWED_ACTIONS,
    GITOPS_MODE, GITHUB_TOKEN, GITHUB_REPO, ARGOCD_URL,
    GROQ_MODEL, LLM_PROVIDER, OPENAI_MODEL, BEDROCK_MODEL_ID, OLLAMA_MODEL,
    K8S_NAMESPACE,
)
from agent.graph import investigate
from agent.k8s_client import restart_pod, scale_deployment
from agent.database import init_db, save_incident, get_all_incidents, is_duplicate_incident
from agent.dashboard import get_dashboard_html
from agent.notifier import send_slack_notification
from gitops.github_pr import create_remediation_pr
from gitops.argocd import sync_argocd_app
from feedback.tracker import (
    init_remediation_table, record_remediation, update_outcome,
    increment_failure_count, reset_failure_count, get_failure_count, get_pod_history,
)
from feedback.verifier import verify_pod_health
from feedback.escalation import should_escalate, escalate_incident, is_suppressed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="KubePilot AI", version="2.0.0")


@app.on_event("startup")
def startup():
    init_db()
    init_remediation_table()


# ---------- Models ----------
class AlertLabel(BaseModel):
    alertname: Optional[str] = ""
    namespace: Optional[str] = "sre-demo"
    pod: Optional[str] = ""
    severity: Optional[str] = ""


class Alert(BaseModel):
    status: str
    labels: AlertLabel
    annotations: Optional[dict] = {}


class AlertPayload(BaseModel):
    alerts: List[Alert]
    status: str


# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
def root():
    return get_dashboard_html()


@app.get("/api/info")
def api_info():
    model_map = {
        "groq": GROQ_MODEL,
        "openai": OPENAI_MODEL,
        "bedrock": BEDROCK_MODEL_ID,
        "ollama": OLLAMA_MODEL,
    }
    return {
        "service": "KubePilot AI",
        "version": "2.0.0",
        "status": "running",
        "llm_provider": LLM_PROVIDER,
        "llm_model": model_map.get(LLM_PROVIDER, LLM_PROVIDER),
        "auto_remediation": ENABLE_AUTO_REMEDIATION,
        "dry_run": DRY_RUN,
        "gitops_mode": GITOPS_MODE,
        "namespace": K8S_NAMESPACE,
    }


@app.get("/health")
def health():
    db_ok = True
    try:
        get_all_incidents()
    except Exception:
        db_ok = False

    k8s_ok = True
    try:
        from kubernetes import client as _k8s_client, config as _k8s_config
        try:
            _k8s_config.load_incluster_config()
        except Exception:
            _k8s_config.load_kube_config()
        _k8s_client.CoreV1Api().list_namespace(limit=1)
    except Exception:
        k8s_ok = False

    all_ok = db_ok and k8s_ok
    return {
        "status": "healthy" if all_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "kubernetes": "ok" if k8s_ok else "error",
        "llm_provider": LLM_PROVIDER,
        "dry_run": DRY_RUN,
        "version": "2.0.0",
    }


@app.get("/incidents")
def get_incidents():
    all_incidents = get_all_incidents()
    return {"total": len(all_incidents), "incidents": all_incidents}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return get_dashboard_html()


@app.get("/gitops/status")
def gitops_status():
    return {
        "gitops_mode": GITOPS_MODE,
        "github_configured": bool(GITHUB_TOKEN and GITHUB_REPO),
        "argocd_configured": bool(ARGOCD_URL),
    }


@app.get("/feedback/{pod_name}")
def get_feedback(pod_name: str, namespace: str = "sre-demo"):
    history = get_pod_history(pod_name, namespace)
    return {
        "pod": pod_name,
        "namespace": namespace,
        "failure_count": get_failure_count(pod_name, namespace),
        "suppressed": is_suppressed(pod_name, namespace),
        "history": history,
    }


@app.post("/webhook/alert")
async def handle_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    logger.info(f"📨 Webhook received: status={payload.status}, alerts={len(payload.alerts)}")
    for alert in payload.alerts:
        if alert.status == "firing" and alert.labels.pod:
            background_tasks.add_task(process_alert, alert)
    return {"status": "received", "queued": len(payload.alerts)}


# ---------- Core Logic ----------
async def process_alert(alert: Alert):
    pod_name = alert.labels.pod
    namespace = alert.labels.namespace or "sre-demo"
    alert_name = alert.labels.alertname

    if is_duplicate_incident(pod_name, alert_name):
        logger.info(f"⏩ Skipping duplicate alert: {alert_name} for pod {pod_name} (within 5 min)")
        return

    logger.info(f"🔄 Processing: {alert_name} | Pod: {pod_name}")

    if is_suppressed(pod_name, namespace):
        logger.info(f"🔕 Pod {pod_name}/{namespace} is suppressed — skipping auto-remediation")
        incident = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert": alert_name,
            "pod": pod_name,
            "namespace": namespace,
            "status": "suppressed",
            "action_taken": "suppressed - manual intervention required",
        }
        incident_id = save_incident(incident)
        incident["id"] = incident_id
        return

    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "alert": alert_name,
        "pod": pod_name,
        "namespace": namespace,
        "status": "investigating",
    }

    try:
        result = investigate(pod_name, namespace, alert_name)
        raw = result.get("raw", "")

        rca = {}
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end != 0:
                rca = json.loads(raw[start:end])
        except Exception:
            rca = {
                "root_cause": raw,
                "recommended_action": "no_action",
                "confidence": 0.5,
                "reasoning": "Could not parse structured response",
                "risk_level": "low",
            }

        incident["rca"] = rca
        incident["status"] = "analyzed"

        logger.info(f"📋 RCA: {json.dumps(rca, indent=2)}")

        action = rca.get("recommended_action", "no_action")
        confidence = rca.get("confidence", 0)

        if not ENABLE_AUTO_REMEDIATION:
            logger.info("⚙️  Auto remediation disabled")
            incident["action_taken"] = "skipped - remediation disabled"
        elif confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"⚠️  Confidence {confidence} below threshold {CONFIDENCE_THRESHOLD}")
            incident["action_taken"] = f"skipped - low confidence ({confidence})"
        elif action not in ALLOWED_ACTIONS:
            logger.warning(f"🚫 Action {action} not in whitelist")
            incident["action_taken"] = "skipped - action not allowed"
        elif should_escalate(pod_name, namespace):
            logger.warning(f"🔺 Escalating {pod_name}/{namespace} — consecutive failure threshold reached")
            escalate_incident(incident, pod_name, namespace)
            incident["action_taken"] = "escalated - human intervention required"
            incident["status"] = "escalated"
        elif DRY_RUN:
            logger.info(f"🧪 DRY RUN: would execute {action} on {pod_name}")
            incident["action_taken"] = f"dry_run: {action}"
        else:
            execute_action(action, pod_name, namespace, incident)

    except Exception as e:
        logger.error(f"❌ Error processing alert: {str(e)}")
        incident["status"] = "error"
        incident["error"] = str(e)

    incident_id = save_incident(incident)
    incident["id"] = incident_id
    logger.info(f"💾 Incident logged: #{incident['id']}")
    send_slack_notification(incident)


# ---------- Execute Action ----------
def execute_action(action: str, pod_name: str, namespace: str, incident: dict):
    logger.info(f"⚡ Executing: {action} on {pod_name} (gitops_mode={GITOPS_MODE})")

    if GITOPS_MODE:
        try:
            pr_result = create_remediation_pr(incident, action, pod_name, namespace)
            if pr_result.get("status") == "created":
                pr_url = pr_result.get("pr_url", "")
                logger.info(f"✅ GitOps PR created: {pr_url}")
                incident["action_taken"] = f"gitops_pr: {action}"
                incident["gitops_pr_url"] = pr_url
                incident["status"] = "remediated"
            else:
                reason = pr_result.get("reason", "unknown")
                logger.warning(f"⚠️  GitOps PR skipped/failed: {reason}")
                incident["action_taken"] = f"gitops_skipped: {reason}"
                incident["status"] = "analyzed"
        except Exception as e:
            logger.error(f"❌ GitOps PR error: {str(e)}")
            incident["action_taken"] = f"gitops_error: {str(e)}"
        return

    try:
        if action == "restart_pod":
            restart_pod(pod_name, namespace)
            incident["action_taken"] = "restart_pod"
        elif action in ["scale_up", "scale_down"]:
            replicas = 3 if action == "scale_up" else 1
            scale_deployment(pod_name, namespace, replicas)
            incident["action_taken"] = action
        else:
            incident["action_taken"] = "no_action"
        incident["status"] = "remediated"
        logger.info(f"✅ Action {action} executed successfully")

        # Only track remediation and launch verifier for real live actions
        if not DRY_RUN and action != "no_action":
            incident_id = incident.get("id")
            record_id = record_remediation(pod_name, namespace, action, incident_id)
            import threading
            t = threading.Thread(
                target=_verify_and_update,
                args=(record_id, pod_name, namespace, action),
                daemon=True,
            )
            t.start()

    except Exception as e:
        logger.error(f"❌ Action failed: {str(e)}")
        incident["action_taken"] = f"failed: {str(e)}"


# ---------- Background Feedback Verification ----------
def _verify_and_update(record_id: int, pod_name: str, namespace: str, action: str):
    logger.info(f"🔍 Verifying pod health after {action} on {pod_name} (record #{record_id})")
    try:
        result = verify_pod_health(pod_name, namespace, timeout=600)
        if result.get("healthy"):
            update_outcome(record_id, "success")
            reset_failure_count(pod_name, namespace)
            logger.info(f"✅ {pod_name} healthy after {result['duration_seconds']}s — outcome: success")
        else:
            update_outcome(record_id, "failure")
            increment_failure_count(pod_name, namespace)
            logger.warning(f"❌ {pod_name} unhealthy ({result.get('reason')}) — outcome: failure")
    except Exception as e:
        logger.error(f"❌ verify_and_update error: {e}")
        try:
            update_outcome(record_id, "failure")
            increment_failure_count(pod_name, namespace)
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run("agent.main:app", host="0.0.0.0", port=8000, reload=True)
