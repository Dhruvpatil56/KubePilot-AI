# KubePilot AI

> Autonomous AIOps platform for Kubernetes self-healing — detect, investigate, remediate.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What It Does

KubePilot AI is an agentic SRE platform that automatically:

1. **Receives** Prometheus/Alertmanager webhook alerts for pod failures
2. **Investigates** using a LangGraph AI agent — checks pod status, logs, events, and deployment info
3. **Produces** a structured Root Cause Analysis (RCA) JSON with a confidence score
4. **Remediates** safely through configurable safety gates (confidence threshold, action whitelist, dry-run mode)
5. **Tracks outcomes** via a feedback loop — verifies pod health post-remediation, escalates on repeated failures

---

## Architecture

```
Alertmanager
     │
     ▼ POST /webhook/alert
┌────────────────────────────────────────────────────────────────┐
│                        KubePilot AI                            │
│                                                                │
│   Dedup Check ──► Suppression Check ──► LangGraph Agent        │
│                                              │                 │
│                           ┌──────────────────┤                 │
│                           │  Investigation   │                 │
│                           │  • pod status    │ ◄── LLM         │
│                           │  • current logs  │   (Groq/OpenAI/ │
│                           │  • previous logs │    Bedrock/     │
│                           │  • events        │    Ollama)      │
│                           │  • deployment    │                 │
│                           └──────────────────┘                 │
│                                   │                            │
│                      ┌────────────▼────────────┐               │
│                      │      Safety Gates        │               │
│                      │  • confidence threshold  │               │
│                      │  • action whitelist      │               │
│                      │  • dry-run mode          │               │
│                      │  • escalation check      │               │
│                      └────────────┬─────────────┘               │
│                                   │                            │
│                     ┌─────────────┴──────────────┐             │
│                     │                            │             │
│             ┌───────▼──────┐          ┌──────────▼──────────┐  │
│             │  Direct K8s  │          │    GitOps Mode      │  │
│             │  restart_pod │          │    GitHub PR        │  │
│             │  scale_up    │          │    ArgoCD sync      │  │
│             │  scale_down  │          └─────────────────────┘  │
│             │  rollback    │                                    │
│             └──────┬───────┘                                    │
│                    │                                            │
│          ┌─────────▼──────────────┐                            │
│          │     Feedback Loop      │                            │
│          │  • pod health verify   │ ──► Slack notification     │
│          │  • outcome tracking    │                            │
│          │  • failure counting    │                            │
│          │  • escalation/suppress │                            │
│          └────────────────────────┘                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| API Server | FastAPI + Uvicorn |
| Agent Orchestration | LangGraph 0.2 |
| LLM (default) | Groq — llama-3.3-70b-versatile |
| LLM alternatives | OpenAI GPT-4o-mini, AWS Bedrock, Ollama |
| Kubernetes SDK | kubernetes-python |
| Database | SQLite (persistent volume in K8s) |
| Notifications | Slack Block Kit |
| GitOps | GitHub REST API + ArgoCD |
| Container | Docker (Ubuntu 22.04 base) |
| Demo App | dhruvpatil56/kubepilot-broken-app:v3 |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info, LLM config, dry-run mode |
| `GET` | `/health` | DB + K8s connectivity health check |
| `GET` | `/dashboard` | Live web dashboard (dark theme) |
| `GET` | `/incidents` | All incidents as JSON |
| `POST` | `/webhook/alert` | Alertmanager webhook receiver |
| `GET` | `/gitops/status` | GitOps mode configuration |
| `GET` | `/feedback/{pod_name}` | Pod remediation history |

---

## Sprint Completion

- [x] **Sprint 1** — FastAPI server, webhook receiver, alert parsing, Pydantic models
- [x] **Sprint 2** — LangGraph agent, Kubernetes investigation tools, RCA generation
- [x] **Sprint 3** — SQLite persistence, dark-theme dashboard, Slack Block Kit notifications, rollback support
- [x] **Sprint 4** — GitOps mode: GitHub PR generation + ArgoCD integration
- [x] **Sprint 5** — Feedback loop: pod health verification, escalation, pod suppression
- [x] **Sprint 6** — Pluggable LLM: Groq, OpenAI, AWS Bedrock, Ollama via factory pattern
- [x] **Sprint 7 (Polish)** — Incident deduplication, Groq rate-limit retry, structured logging, Grafana-style dashboard upgrade

---

## Quick Start

### Prerequisites

- Python 3.10+
- Kubernetes cluster (Kind, k3d, GKE, EKS, AKS)
- Groq API key (free at [console.groq.com](https://console.groq.com)) **or** OpenAI/Bedrock/Ollama

### Local Development

```bash
# Clone
git clone https://github.com/Dhruvpatil56/KubePilot-AI
cd KubePilot-AI

# Install dependencies
pip install -r agent/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set GROQ_API_KEY and any other vars

# Run the server (port 8000)
python -m uvicorn agent.main:app --reload --port 8000

# Open the dashboard
open http://localhost:8000/dashboard
```

### Docker

```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key_here \
  -e DRY_RUN=true \
  dhruvpatil56/kubepilot-healing-agent:v2
```

### Kubernetes with Kind

```bash
# Start Kind cluster
kind create cluster --name kubepilot

# Apply manifests
kubectl apply -f manifest_files/

# Deploy broken demo app (triggers CrashLoopBackOff alerts)
kubectl apply -f broken-app/k8s/

# Port-forward to dashboard
kubectl port-forward svc/kubepilot-agent 8000:8000 -n sre-demo
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `groq` | LLM provider: `groq`, `openai`, `bedrock`, `ollama` |
| `GROQ_API_KEY` | — | Groq API key (required for default provider) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model name |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | AWS Bedrock model ID |
| `BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.3` | Ollama model name |
| `DRY_RUN` | `true` | `false` to enable real K8s remediation |
| `ENABLE_AUTO_REMEDIATION` | `true` | Master toggle for auto-remediation |
| `CONFIDENCE_THRESHOLD` | `0.7` | Minimum RCA confidence to act (0.0–1.0) |
| `ALLOWED_ACTIONS` | (hardcoded) | `restart_pod`, `scale_up`, `scale_down`, `rollback`, `no_action` |
| `GITOPS_MODE` | `false` | `true` to create GitHub PRs instead of direct K8s changes |
| `GITHUB_TOKEN` | — | GitHub personal access token (for GitOps mode) |
| `GITHUB_REPO` | — | GitHub repo in `owner/repo` format |
| `ARGOCD_URL` | — | ArgoCD server URL |
| `ARGOCD_TOKEN` | — | ArgoCD auth token |
| `SLACK_BOT_TOKEN` | — | Slack bot OAuth token |
| `SLACK_CHANNEL` | — | Slack channel ID for notifications |
| `ESCALATION_THRESHOLD` | `3` | Consecutive failures before escalation |
| `K8S_NAMESPACE` | `sre-demo` | Default Kubernetes namespace |
| `DB_PATH` | `/data/kubepilot.db` | SQLite database file path |

---

## How It Works (Step by Step)

1. Prometheus detects a pod failure (CrashLoopBackOff, OOMKilled, NotReady)
2. Alertmanager fires a webhook to `POST /webhook/alert`
3. **Deduplication**: if the same pod+alert was processed in the last 5 minutes, skip it
4. **Suppression check**: if the pod is suppressed (too many failures), skip remediation
5. The LangGraph agent investigates: pod status → logs → previous logs → events → deployment info
6. The configured LLM returns a structured RCA JSON with `root_cause`, `recommended_action`, `confidence`, `reasoning`, `risk_level`
7. Safety gates evaluate:
   - Confidence ≥ threshold?
   - Action in whitelist?
   - Dry-run mode?
   - Escalation threshold reached?
8. If all gates pass, remediation executes (direct K8s API **or** GitOps PR)
9. A background thread verifies pod health for up to 10 minutes
10. Outcome recorded → failure counter updated → escalation/suppression triggered if needed
11. Slack notification sent with full incident details

---

## Docker Images

| Image | Description |
|-------|-------------|
| `dhruvpatil56/kubepilot-healing-agent:v2` | Main healing agent (FastAPI + LangGraph) |
| `dhruvpatil56/kubepilot-broken-app:v3` | Demo app that crashes on `CRASH_ON_START=true` |

---

## Project Structure

```
KubePilot-AI/
├── agent/
│   ├── main.py          # FastAPI server, webhook, safety gates, incident pipeline
│   ├── graph.py         # LangGraph agent loop, pluggable LLM, rate-limit retry
│   ├── tools.py         # K8s investigation tools (pod status, logs, events)
│   ├── k8s_client.py    # K8s actions: restart, scale, rollback
│   ├── database.py      # SQLite persistence + deduplication
│   ├── dashboard.py     # Self-contained HTML dashboard (Grafana-style dark theme)
│   ├── notifier.py      # Slack Block Kit notifications
│   ├── Dockerfile
│   └── requirements.txt
├── feedback/
│   ├── tracker.py       # Remediation outcome tracking
│   ├── verifier.py      # Pod health verification (post-remediation)
│   └── escalation.py    # Escalation + pod suppression
├── gitops/
│   ├── github_pr.py     # GitHub PR generation
│   └── argocd.py        # ArgoCD sync integration
├── llm/
│   ├── base.py          # Abstract LLM provider interface
│   ├── factory.py       # Provider factory (reads LLM_PROVIDER env var)
│   ├── groq_provider.py
│   ├── openai_provider.py
│   ├── bedrock_provider.py
│   └── ollama_provider.py
├── broken-app/          # Demo failure app (Flask + intentional crash)
├── manifest_files/      # Kubernetes manifests (deployment, service, RBAC)
├── config.py            # Central config (all env vars)
└── CLAUDE.md            # Claude Code context file
```
