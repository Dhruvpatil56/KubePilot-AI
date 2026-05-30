# KubePilot-AI — Claude Code Context

## What This Project Is

KubePilot-AI is an agentic AIOps platform that automatically detects Kubernetes failures,
investigates them using a LangGraph AI agent, and remediates safely. Think of it as an
autonomous SRE engineer that never sleeps.

## Current State (Sprints 1-2 Complete)

- FastAPI webhook server receives Prometheus/Alertmanager alerts
- LangGraph agent investigates pods step by step (logs, events, status, deployment info)
- Groq LLM (llama-3.3-70b-versatile) produces structured RCA with confidence scores
- Safety gates: confidence threshold (0.7), action whitelist, dry-run mode
- Kubernetes remediation: restart_pod, scale_deployment, rollback
- Full E2E pipeline tested and working on AWS + Kind cluster

## File Structure

```
KubePilot-AI/
├── agent/
│   ├── main.py        # FastAPI server, webhook receiver, safety gates, incident tracker
│   ├── graph.py       # LangGraph agent loop, tool orchestration, RCA generation
│   ├── tools.py       # K8s tools: get_pod_status, get_pod_logs, get_previous_pod_logs, get_pod_events, get_deployment_info
│   ├── k8s_client.py  # K8s actions: restart_pod, scale_deployment, rollback_deployment
│   ├── Dockerfile     # Container image for healing agent
│   └── requirements.txt
├── broken-app/        # Deliberately broken Flask app with /crash, /memory-leak, /slow endpoints
├── manifest_files/    # All K8s YAMLs: RBAC, deployments, services, Prometheus alert rules
├── config.py          # Central config from .env: LLM provider, thresholds, dry-run, tokens
├── monitoring/        # Prometheus + Alertmanager configs
└── README.md
```

## Tech Stack

- **Runtime**: Python 3.11, FastAPI, Uvicorn
- **AI**: LangGraph, LangChain, Groq (llama-3.3-70b-versatile)
- **Kubernetes**: Python kubernetes SDK (in-cluster + kubeconfig support)
- **Infrastructure**: AWS EC2 (t3.large, us-east-1), Kind cluster (1 control-plane + 2 workers)
- **Monitoring**: Prometheus, Alertmanager, Grafana, kube-state-metrics
- **Namespaces**: sre-demo (app), monitoring (observability stack)

## Sprint Roadmap

- [x] Sprint 1 — Repo restructure, clean foundation, README
- [x] Sprint 2 — LangGraph agent loop, Groq LLM, full E2E pipeline working
- [ ] Sprint 3 — Persistent storage + Dashboard UI + Slack notifications + Real rollback
- [ ] Sprint 4 — GitOps PR generation + ArgoCD integration
- [ ] Sprint 5 — Feedback loop + Escalation engine
- [ ] Sprint 6 — Pluggable LLM providers (OpenAI + Bedrock + Ollama)

---

## Sprint 3 — Current Focus

### Task 1: Persistent Storage (SQLite)

**Problem**: Incidents stored in `incidents = []` in main.py. Any pod restart loses all history.
**Solution**: Create `agent/database.py` with SQLite. Update main.py to use it.

**Requirements**:

- Create `agent/database.py` with the following functions:
  - `init_db()` — create tables on startup
  - `save_incident(incident: dict)` — insert incident into DB
  - `get_all_incidents()` — return all incidents ordered by timestamp desc
  - `get_incident_by_id(id: int)` — return single incident
- Update `agent/main.py`:
  - Call `init_db()` on startup
  - Replace `incidents.append()` with `save_incident()`
  - Replace `incidents` list reads with `get_all_incidents()`
- Keep `/incidents` endpoint response format exactly the same
- DB file path configurable via `DB_PATH` env var, default `/data/kubepilot.db`
- Fallback to `./kubepilot.db` if `/data/` directory doesn't exist

### Task 2: Dashboard UI

**Problem**: No visual interface. Incidents only accessible via raw JSON API.
**Solution**: Build a clean dark-themed dashboard served directly by FastAPI.

**Requirements**:

- Add `/dashboard` route to `agent/main.py` returning HTML response
- Single self-contained HTML file (inline CSS + JS, no external dependencies)
- Dark theme matching a terminal/SRE aesthetic (dark background, monospace fonts)
- Shows incident list with: timestamp, alert name, pod name, status, confidence score, action taken
- Click any incident row to expand full RCA details (root cause, reasoning, risk level)
- Color coded by severity: critical=red, warning=yellow, resolved=green, dry_run=blue
- Auto-refreshes every 30 seconds
- Shows total incident count and last updated time at top
- Empty state message when no incidents yet

### Task 3: Slack Notifications

**Problem**: `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` in config but nothing sends to Slack.
**Solution**: Send rich Slack notification after each incident is processed.

**Requirements**:

- Create `agent/notifier.py` with:
  - `send_slack_notification(incident: dict)` — main function
  - Uses `requests` library to call Slack Web API
  - Gracefully skips (logs warning) if `SLACK_BOT_TOKEN` not set
- Slack message format using Block Kit:
  - Header: alert name + severity emoji (🔴 critical, 🟡 warning)
  - Fields: Pod, Namespace, Root Cause, Action Taken, Confidence, Risk Level
  - Footer: timestamp + "KubePilot AI"
- Update `agent/main.py` to call `send_slack_notification(incident)` after logging each incident

### Task 4: Real Rollback Implementation

**Problem**: `rollback_deployment()` in k8s_client.py is a stub that doesn't actually work.
**Solution**: Implement real Kubernetes rollout rollback using apps/v1 API.

**Requirements**:

- Implement `rollback_deployment(pod_name, namespace)` in `agent/k8s_client.py`:
  - Trace pod → ReplicaSet → Deployment (same pattern as existing code)
  - Get rollout history via ReplicaSets ordered by revision annotation
  - Patch deployment with `kubectl.kubernetes.io/restartedAt` annotation to trigger rollback
  - Wait up to 60 seconds for rollback to complete
  - Return success/failure status
- Add `verify_rollback(deployment_name, namespace)` helper:
  - Check deployment `availableReplicas == replicas`
  - Return True if healthy within timeout

---

## Important Rules for Claude Code

1. **Never break the existing webhook pipeline** — `POST /webhook/alert` must always work
2. **Always keep dry_run mode** — never execute real K8s actions when `DRY_RUN=true`
3. **Always keep confidence threshold** — never act below `CONFIDENCE_THRESHOLD`
4. **Verify imports after every file** — run `python3 -c "from agent.X import Y"` before finishing
5. **One task at a time** — complete and verify Task 1 before starting Task 2
6. **Server runs on AWS Ubuntu 22.04** — no Windows-specific code
7. **In-cluster K8s config** — agent runs inside K8s pod, always try `load_incluster_config()` first
8. **No breaking changes** — existing `/health`, `/incidents`, `/` endpoints must keep working

---

## How to Test Each Task

### Task 1 (SQLite)

```bash
python3 -c "from agent.database import init_db, save_incident, get_all_incidents; print('OK')"
python3 -c "from agent.main import app; print('OK')"
curl http://localhost:8000/incidents
```

### Task 2 (Dashboard)

```bash
curl http://localhost:8000/dashboard | head -20
# Open in browser: http://<AWS_IP>:8000/dashboard
```

### Task 3 (Slack)

```bash
python3 -c "from agent.notifier import send_slack_notification; print('OK')"
# Test with dummy incident dict
```

### Task 4 (Rollback)

```bash
python3 -c "from agent.k8s_client import rollback_deployment; print('OK')"
```

### Full E2E Test

```bash
# Send test webhook
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PodCrashLooping",
        "namespace": "sre-demo",
        "pod": "broken-app-7d74666fd4-cmzlh",
        "severity": "critical"
      },
      "annotations": {}
    }]
  }'

# Check incident was saved
curl http://localhost:8000/incidents | python3 -m json.tool

# Check dashboard
curl http://localhost:8000/dashboard
```

---

## Environment Variables (.env)

```
# LLM
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Kubernetes
K8S_NAMESPACE=sre-demo

# Agent Safety
CONFIDENCE_THRESHOLD=0.7
ENABLE_AUTO_REMEDIATION=true
DRY_RUN=true

# Storage
DB_PATH=/data/kubepilot.db

# GitOps (Sprint 4)
GITHUB_TOKEN=
GITHUB_REPO=Dhruvpatil56/KubePilot-AI

# Slack (Sprint 3 Task 3)
SLACK_BOT_TOKEN=
SLACK_CHANNEL=

# ArgoCD (Sprint 4)
ARGOCD_URL=
```

---
