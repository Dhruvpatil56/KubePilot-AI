# KubePilot-AI — Project Summary & Sprint 3 Plan

## What KubePilot-AI Does

**KubePilot-AI is an autonomous SRE (Site Reliability Engineering) agent** that automatically investigates and remediates Kubernetes pod incidents without human intervention. When Prometheus fires an alert, the agent wakes up, uses AI to investigate the pod (logs, events, status), generates a Root Cause Analysis (RCA), and — if confident enough — executes a remediation action like restarting the pod or scaling the deployment.

**Core tech stack:** FastAPI + LangGraph + Groq LLM (llama-3.3-70b) + Kubernetes Python client

---

## File Structure

```
KubePilot-AI/
├── agent/
│   ├── main.py          # FastAPI server — webhook receiver, incident tracker, safety gates
│   ├── graph.py         # LangGraph agent — multi-step AI investigation workflow
│   ├── tools.py         # LangChain tools — get_pod_status, logs, events, deployment info
│   ├── k8s_client.py    # K8s client — restart, scale, rollback, log retrieval
│   ├── requirements.txt
│   └── Dockerfile
├── broken-app/          # Deliberately broken Flask app for testing (OOM, crash, slow, errors)
├── manifest_files/      # K8s YAMLs — RBAC, deployments, Prometheus alerts, kustomization
├── config.py            # Env var config — LLM, thresholds, dry-run, Slack/GitHub tokens
└── README.md
```

---

## What's Done (Sprints 1-2)

| Feature | Status |
|---|---|
| FastAPI webhook server | Done |
| LangGraph multi-step investigation agent | Done |
| Pod investigation tools (logs, events, status) | Done |
| K8s remediation actions (restart, scale, rollback) | Done |
| Confidence-based safety gates + dry-run mode | Done |
| Prometheus/AlertManager integration | Done |
| Broken-app test fixture | Done |
| K8s manifests + RBAC | Done |

---

## Sprint 3 Recommendations

Based on what's built and what's missing, Sprint 3 should focus on **production-readiness and observability**:

### High Priority
1. **Persistent incident storage** — Currently incidents are stored in-memory (`incidents = []` in main.py). Any restart loses history. Replace with SQLite or Redis.
2. **Slack notifications** — Config already has `SLACK_BOT_TOKEN` and `SLACK_CHANNEL` placeholders but nothing sends to Slack. Wire up alerts + RCA summaries.
3. **Real rollback implementation** — `rollback_deployment()` in `agent/k8s_client.py` is a placeholder stub. Implement actual `apps/v1` rollout history + rollback.

### Medium Priority
4. **A proper frontend/dashboard** — The `/incidents` API exists but there's no UI. A simple React or Streamlit dashboard showing incident history + RCA + actions taken would make this demo-able.
5. **Multi-namespace support** — Namespace is hardcoded to `sre-demo` in config. Generalize to monitor multiple namespaces.
6. **GitOps integration** — `GITHUB_TOKEN` and `GITHUB_REPO` are in config but unused. Implement auto-PR creation for config changes (e.g., resource limit adjustments).

### Lower Priority
7. **Agent memory/context** — Currently each alert is investigated fresh. Adding short-term memory (recent incidents for the same pod) would improve RCA accuracy.
8. **Test suite** — No tests exist. Add unit tests for tools and integration tests using the broken-app fixture.

---

## Sprint 3 Focus Recommendation

**Persistent storage + Slack notifications + dashboard UI** — these three together turn this from a working prototype into something you can actually demo and show stakeholders.
