#!/bin/bash

set -e

echo "========================================"
echo "   KubePilot AI — Full Stack Setup"
echo "========================================"

# ── 0. Preflight checks ───────────────────
echo ""
echo "[0/8] Preflight checks..."

if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker not found. Install Docker first."
  exit 1
fi

if ! command -v kind &>/dev/null; then
  echo "ERROR: Kind not found."
  echo "  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
  echo "  chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
  exit 1
fi

if ! command -v kubectl &>/dev/null; then
  echo "ERROR: kubectl not found."
  echo "  curl -LO https://dl.k8s.io/release/v1.27.3/bin/linux/amd64/kubectl"
  echo "  chmod +x kubectl && sudo mv kubectl /usr/local/bin/kubectl"
  exit 1
fi

if ! command -v helm &>/dev/null; then
  echo "ERROR: Helm not found."
  echo "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
  exit 1
fi

# ── 1. Check secrets ─────────────────────
echo ""
echo "[1/8] Checking required secrets..."

if [ -z "$GROQ_API_KEY" ]; then
  echo ""
  echo "ERROR: GROQ_API_KEY is not set."
  echo ""
  echo "  Get a free key at https://console.groq.com"
  echo "  Then run:"
  echo "    export GROQ_API_KEY=gsk_your_key_here"
  echo "    ./setup.sh"
  echo ""
  exit 1
fi
echo "  GROQ_API_KEY found"

# ── 2. Create Kind cluster ────────────────
echo ""
echo "[2/8] Creating Kind cluster..."

if kind get clusters | grep -q "^kubepilot$"; then
  echo "  Kind cluster 'kubepilot' already exists — skipping creation"
else
  cat > /tmp/kind-config.yaml << 'KINDEOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
KINDEOF
  kind create cluster --name kubepilot --config /tmp/kind-config.yaml
  echo "  Kind cluster created"
fi

kubectl cluster-info --context kind-kubepilot

# ── 3. Create namespaces ──────────────────
echo ""
echo "[3/8] Creating namespaces..."
kubectl create namespace sre-demo   --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
echo "  Namespaces ready"

# ── 4. Create Kubernetes secret ───────────
echo ""
echo "[4/8] Creating kubepilot-secrets..."
kubectl delete secret kubepilot-secrets -n sre-demo --ignore-not-found
kubectl create secret generic kubepilot-secrets \
  -n sre-demo \
  --from-literal=GROQ_API_KEY="$GROQ_API_KEY"
echo "  Secret created (key stored in K8s, never on disk)"

# ── 5. Apply RBAC ─────────────────────────
echo ""
echo "[5/8] Applying RBAC..."
kubectl apply -f manifest_files/healing-agent-rbac.yaml
echo "  RBAC applied"

# ── 6. Deploy monitoring stack ────────────
echo ""
echo "[6/8] Deploying Prometheus + Alertmanager + Grafana..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set alertmanager.enabled=true \
  --set grafana.enabled=true \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --wait --timeout 5m

echo "  Monitoring stack deployed"

# ── 6b. Configure Alertmanager webhook ───
echo ""
echo "  Configuring Alertmanager webhook..."
kubectl create secret generic alertmanager-prometheus-kube-prometheus-alertmanager \
  -n monitoring \
  --from-literal='alertmanager.yaml=global:
  resolve_timeout: 5m
inhibit_rules:
- equal:
  - namespace
  - alertname
  source_matchers:
  - severity = critical
  target_matchers:
  - severity =~ warning|info
receivers:
- name: "null"
- name: kubepilot-webhook
  webhook_configs:
  - url: http://healing-agent.sre-demo.svc.cluster.local:8000/webhook/alert
    send_resolved: false
route:
  group_by:
  - namespace
  group_interval: 5m
  group_wait: 30s
  receiver: "null"
  repeat_interval: 12h
  routes:
  - matchers:
    - alertname = Watchdog
    receiver: "null"
  - matchers:
    - namespace = sre-demo
    receiver: kubepilot-webhook
    group_wait: 10s
    group_interval: 30s
    repeat_interval: 5m' \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart statefulset \
  alertmanager-prometheus-kube-prometheus-alertmanager \
  -n monitoring
echo "  Alertmanager webhook configured"

# ── 7. Deploy apps ────────────────────────
echo ""
echo "[7/8] Deploying broken-app and healing-agent..."

kubectl apply -f manifest_files/deployment.yaml
kubectl apply -f manifest_files/service.yaml
kubectl apply -f manifest_files/healing-agent-deployment.yaml
kubectl apply -f manifest_files/healing-agent-service.yaml
kubectl apply -f manifest_files/broken-app-alerts.yaml

kubectl set image deployment/healing-agent \
  healing-agent=dhruvpatil56/kubepilot-healing-agent:v4 \
  -n sre-demo

kubectl set image deployment/broken-app \
  broken-app=dhruvpatil56/kubepilot-broken-app:v3 \
  -n sre-demo

echo "  Waiting for pods to be ready..."
kubectl rollout status deployment/healing-agent -n sre-demo --timeout=120s
kubectl rollout status deployment/broken-app -n sre-demo --timeout=120s
echo "  Apps deployed"

# ── 8. Done ───────────────────────────────
echo ""
echo "[8/8] Verifying all pods..."
echo ""
kubectl get pods -n sre-demo
echo ""
kubectl get pods -n monitoring
echo ""

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")

echo "========================================"
echo "   KubePilot AI is running!"
echo "========================================"
echo ""
echo "  Access the dashboard:"
echo ""
echo "  kubectl port-forward -n sre-demo \\"
echo "    deployment/healing-agent 8000:8000 --address 0.0.0.0"
echo ""
echo "  Then open: http://$PUBLIC_IP:8000"
echo ""
echo "  To run a stress test:"
echo "    ./run_stress_test.sh"
echo ""
echo "========================================"
