from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import json
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENABLE_AUTO_REMEDIATION, DRY_RUN, CONFIDENCE_THRESHOLD, ALLOWED_ACTIONS
from agent.graph import investigate
from agent.k8s_client import restart_pod, scale_deployment
from agent.database import init_db, save_incident, get_all_incidents
from agent.dashboard import get_dashboard_html
from agent.notifier import send_slack_notification

app = FastAPI(title="KubePilot AI", version="2.0.0")

@app.on_event("startup")
def startup():
    init_db()

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
@app.get("/")
def root():
    return {
        "service": "KubePilot AI",
        "version": "2.0.0",
        "status": "running",
        "auto_remediation": ENABLE_AUTO_REMEDIATION,
        "dry_run": DRY_RUN
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/incidents")
def get_incidents():
    all_incidents = get_all_incidents()
    return {"total": len(all_incidents), "incidents": all_incidents}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return get_dashboard_html()

@app.post("/webhook/alert")
async def handle_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    print(f"\n📨 Webhook received: status={payload.status}, alerts={len(payload.alerts)}")
    for alert in payload.alerts:
        if alert.status == "firing" and alert.labels.pod:
            background_tasks.add_task(process_alert, alert)
    return {"status": "received", "queued": len(payload.alerts)}

# ---------- Core Logic ----------
async def process_alert(alert: Alert):
    pod_name = alert.labels.pod
    namespace = alert.labels.namespace or "sre-demo"
    alert_name = alert.labels.alertname

    print(f"\n⚡ Processing: {alert_name} | Pod: {pod_name}")

    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "alert": alert_name,
        "pod": pod_name,
        "namespace": namespace,
        "status": "investigating"
    }

    try:
        # Run LangGraph agent
        result = investigate(pod_name, namespace, alert_name)
        raw = result.get("raw", "")

        # Try to parse JSON from agent response
        rca = {}
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end != 0:
                rca = json.loads(raw[start:end])
        except:
            rca = {
                "root_cause": raw,
                "recommended_action": "no_action",
                "confidence": 0.5,
                "reasoning": "Could not parse structured response",
                "risk_level": "low"
            }

        incident["rca"] = rca
        incident["status"] = "analyzed"

        print(f"\n🧠 RCA: {json.dumps(rca, indent=2)}")

        # Safety checks
        action = rca.get("recommended_action", "no_action")
        confidence = rca.get("confidence", 0)

        if not ENABLE_AUTO_REMEDIATION:
            print("⚠️  Auto remediation disabled")
            incident["action_taken"] = "skipped - remediation disabled"
        elif confidence < CONFIDENCE_THRESHOLD:
            print(f"⚠️  Confidence {confidence} below threshold {CONFIDENCE_THRESHOLD}")
            incident["action_taken"] = f"skipped - low confidence ({confidence})"
        elif action not in ALLOWED_ACTIONS:
            print(f"⚠️  Action {action} not in whitelist")
            incident["action_taken"] = f"skipped - action not allowed"
        elif DRY_RUN:
            print(f"🧪 DRY RUN: would execute {action} on {pod_name}")
            incident["action_taken"] = f"dry_run: {action}"
        else:
            execute_action(action, pod_name, namespace, incident)

    except Exception as e:
        print(f"❌ Error processing alert: {str(e)}")
        incident["status"] = "error"
        incident["error"] = str(e)

    incident_id = save_incident(incident)
    incident["id"] = incident_id
    print(f"\n📋 Incident logged: #{incident['id']}")
    send_slack_notification(incident)

# ---------- Execute Action ----------
def execute_action(action: str, pod_name: str, namespace: str, incident: dict):
    print(f"\n🔧 Executing: {action} on {pod_name}")
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
        print(f"✅ Action {action} executed successfully")
    except Exception as e:
        print(f"❌ Action failed: {str(e)}")
        incident["action_taken"] = f"failed: {str(e)}"

if __name__ == "__main__":
    uvicorn.run("agent.main:app", host="0.0.0.0", port=8000, reload=True)
