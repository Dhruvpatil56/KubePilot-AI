# KubePilot-AI — Sprint 3 Completion Log

## Sprint 3 Progress

| Task | Status |
|------|--------|
| Task 1: Persistent SQLite Storage | COMPLETE |
| Task 2: Dashboard UI | COMPLETE |
| Task 3: Slack Notifications | COMPLETE |
| Task 4: Real Rollback Implementation | COMPLETE |

---

## Task 1: Persistent SQLite Storage — COMPLETE

### What Was Done

**New file: `agent/database.py`**

Created a full SQLite persistence layer with the following functions:

- `_get_db_path()` — Reads `DB_PATH` env var (default `/data/kubepilot.db`). Falls back to `./kubepilot.db` if the configured directory does not exist (handles local dev vs. K8s PVC mount).
- `init_db()` — Creates the `incidents` table with `AUTOINCREMENT` primary key on startup.
- `save_incident(incident: dict) -> int` — Inserts a complete incident dict into SQLite. Serializes the `rca` field as JSON. Returns the auto-assigned integer ID.
- `get_all_incidents() -> list` — Returns all incidents ordered by `timestamp DESC`. Deserializes `rca` JSON back to dict. Strips `None` fields to match the original in-memory format.
- `get_incident_by_id(incident_id: int) -> Optional[dict]` — Returns a single incident by ID or `None`.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS incidents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT NOT NULL,
    alert        TEXT,
    pod          TEXT,
    namespace    TEXT,
    status       TEXT,
    rca          TEXT,
    action_taken TEXT,
    error        TEXT
)
```

**Updated: `agent/main.py`**

- Removed `incidents = []` in-memory list
- Added `from agent.database import init_db, save_incident, get_all_incidents`
- Added `@app.on_event("startup")` calling `init_db()` so the DB table is created before the first request
- `/incidents` endpoint now calls `get_all_incidents()` — response format unchanged: `{"total": N, "incidents": [...]}`
- `process_alert()` no longer pre-assigns an ID. After all processing, calls `save_incident(incident)` which returns the DB-assigned ID and sets `incident["id"]`

### Verification

```
python -c "from agent.database import init_db, save_incident, get_all_incidents, get_incident_by_id; print('OK')"
# Output: database.py: OK

# Smoke test: init DB, save 2 incidents, read back, assert rca round-trip, assert None fields dropped
# Output: All assertions passed - smoke test: OK
```

---

## Task 2: Dashboard UI — COMPLETE

### What Was Done

**New file: `agent/dashboard.py`**

Contains a single function `get_dashboard_html() -> str` that returns a fully self-contained HTML page (no external CDN, no JS frameworks, no separate asset files).

**Dashboard features:**

| Requirement | Implementation |
|---|---|
| Dark terminal/SRE aesthetic | `#0d1117` background, `Courier New` monospace font throughout |
| Incident table | Columns: Timestamp, Alert, Pod, Namespace, Status, Confidence, Action Taken |
| Click row → expand RCA | Toggles a hidden row with a 2-column grid showing Root Cause, Reasoning, Recommended Action, Risk Level, Confidence |
| Color-coded by severity | critical/crash/oom = red, warning/slow/notready = yellow, remediated = green, dry_run = blue, other = gray |
| Auto-refresh every 30s | `setInterval(load, 30000)` + animated shrinking progress bar at top of page |
| Stats at top | 4 stat cards: Total / Remediated / Dry Run / Errors — plus header showing total count + last updated time |
| Empty state | "No incidents yet — the cluster looks healthy." message when list is empty |
| No external dependencies | Pure inline CSS + vanilla JavaScript, zero network requests except `/incidents` |
| XSS-safe rendering | All user data passed through `escHtml()` before insertion into DOM |

**Updated: `agent/main.py`**

- Added `from fastapi.responses import HTMLResponse`
- Added `from agent.dashboard import get_dashboard_html`
- Added route:
  ```python
  @app.get("/dashboard", response_class=HTMLResponse)
  def dashboard():
      return get_dashboard_html()
  ```
- All existing endpoints (`/`, `/health`, `/incidents`, `/webhook/alert`) untouched

### Verification

```
python -c "from agent.dashboard import get_dashboard_html; html = get_dashboard_html(); print(len(html), 'chars')"
# Output: dashboard.py: OK | HTML length: 10716 chars

# Assertions checked: DOCTYPE, fetch('/incidents'), setInterval/30000,
# rca-box, badge-red/yellow/green/blue, empty-state, refresh-bar
# All assertions passed
```

---

## Task 3: Slack Notifications — COMPLETE

### What Was Done

**New file: `agent/notifier.py`**

- `_severity_emoji(incident)` — Returns 🔴 for critical/crash/oom alerts, 🟡 for everything else.
- `send_slack_notification(incident: dict)` — Main function:
  - Reads `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` from environment
  - Gracefully logs a warning and returns early if either is not set (no crash)
  - Calls `https://slack.com/api/chat.postMessage` via `requests.post`
  - 10-second timeout; catches all exceptions and logs a warning (never raises)
  - Logs Slack API-level errors (`data["ok"] == false`) without crashing

**Block Kit message format:**
```
[Header]   🔴 PodCrashLooping
[Section]  Pod | Namespace | Action Taken | Confidence
[Section]  Root Cause | Risk Level
[Divider]
[Context]  KubePilot AI | 2026-05-30T10:00:00 UTC
```

**Updated: `agent/requirements.txt`**

- Added `requests` (was missing; needed for Slack Web API calls)

**Updated: `agent/main.py`**

- Added `from agent.notifier import send_slack_notification`
- Called `send_slack_notification(incident)` immediately after `save_incident()` in `process_alert()`

### Verification

```
python -c "from agent.notifier import send_slack_notification; print('OK')"
# Output: notifier.py: import OK

# Smoke test (no token set):
# send_slack_notification(dummy_incident)  → logs WARNING, does not raise
# Output: WARNING:agent.notifier:SLACK_BOT_TOKEN not set — skipping Slack notification
#         graceful skip (no token): OK
```

---

## Task 4: Real Rollback Implementation — COMPLETE

### What Was Done

**Updated: `agent/k8s_client.py`**

Added imports: `from datetime import datetime, timezone` and `import time`.

**New standalone function: `rollback_deployment(pod_name, namespace) -> bool`**

Full 4-step implementation:

1. **Trace pod → ReplicaSet → Deployment** — follows owner references chain, same pattern as existing `get_deployment_from_pod()`
2. **Rollout history via revision annotation** — lists all ReplicaSets matching the deployment's label selector, sorts by `deployment.kubernetes.io/revision` annotation descending
3. **Rollback patch** — patches deployment with:
   - Container images from the previous revision's ReplicaSet (the actual rollback)
   - `kubectl.kubernetes.io/restartedAt` annotation to trigger a rolling update
   - Falls back to restart-only if no previous revision exists
4. **Wait up to 60s** — delegates to `verify_rollback()`, returns `True`/`False`

**New standalone function: `verify_rollback(deployment_name, namespace, timeout=60) -> bool`**

- Loads K8s config (in-cluster first, then local kubeconfig)
- Polls every 5 seconds until `availableReplicas >= replicas` or timeout
- Returns `True` if healthy within timeout, `False` otherwise

**Updated: `K8sClient.rollback_deployment(deployment_name, namespace)` class method**

- Replaced the placeholder (which just called `restart_deployment`) with the same real logic using the class's existing `self.apps_v1` client

### Verification

```
python -c "from agent.k8s_client import rollback_deployment, verify_rollback; print('OK')"
# Output: Task 4 — rollback_deployment, verify_rollback: import OK

# Structural assertions:
# - rollback_deployment signature: (pod_name, namespace)
# - verify_rollback signature: (deployment_name, namespace, ...)
# - Source contains: deployment.kubernetes.io/revision, kubectl.kubernetes.io/restartedAt,
#                    verify_rollback call, 60s timeout, available_replicas check, time.sleep
# All assertions passed
```

---

## Files Changed — Sprint 3 (All Tasks)

```
agent/
├── database.py      NEW     — SQLite persistence layer
├── dashboard.py     NEW     — Self-contained dark-theme HTML dashboard
├── notifier.py      NEW     — Slack Block Kit notifications
├── k8s_client.py    UPDATED — Real rollback_deployment + verify_rollback
├── main.py          UPDATED — DB init, Slack call, /dashboard route
└── requirements.txt UPDATED — Added requests
```

---

## Rules Followed (from CLAUDE.md)

- Webhook pipeline (`POST /webhook/alert`) untouched and working
- Dry-run mode preserved — no K8s actions taken when `DRY_RUN=true`
- Confidence threshold gate preserved
- Imports verified after every file with `python -c` checks
- Each task completed and verified before starting the next
- No Windows-specific code introduced (runs on Ubuntu 22.04)
- In-cluster K8s config attempted first (`load_incluster_config`), kubeconfig as fallback
- No breaking changes to `/health`, `/incidents`, `/` endpoints
- `/incidents` response format identical to original
