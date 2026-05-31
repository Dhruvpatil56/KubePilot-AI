#!/bin/bash

echo "========================================"
echo "   KubePilot AI — Real Stress Test"
echo "========================================"

HEALING_POD=$(kubectl get pods -n sre-demo -l app=healing-agent -o jsonpath='{.items[0].metadata.name}')
PUBLIC_IP=$(curl -s ifconfig.me)

echo "Dashboard: http://$PUBLIC_IP:8000"
echo "Healing Agent: $HEALING_POD"
echo ""

# Ensure port-forward is running
pkill -f "port-forward" 2>/dev/null
sleep 2
kubectl port-forward -n sre-demo $HEALING_POD 8000:8000 --address 0.0.0.0 &
sleep 3

# ─────────────────────────────────────────
echo "========================================"
echo "   SCENARIO 1: CrashLoopBackOff"
echo "   Real crash — pod exits on startup"
echo "   Expect RCA: app crashing on start"
echo "   Expect Action: restart_pod/rollback"
echo "========================================"

# Deploy a new broken deployment that crashes immediately
kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-crash
  namespace: sre-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stress-crash
  template:
    metadata:
      labels:
        app: stress-crash
    spec:
      containers:
      - name: stress-crash
        image: python:3.11-slim
        command: ["python", "-c", "import sys; print('Starting...'); sys.exit(1)"]
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
YAML

echo "Waiting for pod to crash and Prometheus to detect (90s)..."
sleep 30

# Get crashing pod name
CRASH_POD=$(kubectl get pods -n sre-demo -l app=stress-crash -o jsonpath='{.items[0].metadata.name}')
echo "Crash pod: $CRASH_POD"
kubectl get pods -n sre-demo

sleep 30

# Manually send webhook since Alertmanager routing needs time
echo "Sending alert to agent..."
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodCrashLooping\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$CRASH_POD\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Agent investigating... (45s)"
sleep 45

echo "Restart count after scenario 1:"
kubectl get pods -n sre-demo

# ─────────────────────────────────────────
echo ""
echo "========================================"
echo "   SCENARIO 2: OOMKilled"
echo "   Real OOM — pod exceeds memory limit"
echo "   Expect RCA: memory exhaustion"
echo "   Expect Action: scale_up"
echo "========================================"

kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-oom
  namespace: sre-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stress-oom
  template:
    metadata:
      labels:
        app: stress-oom
    spec:
      containers:
      - name: stress-oom
        image: python:3.11-slim
        command: ["python", "-c", "
data = []
print('Allocating memory...')
while True:
    data.append(' ' * 10 * 1024 * 1024)
    print(f'Allocated {len(data)*10}MB')
"]
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
YAML

echo "Waiting for OOM kill (60s)..."
sleep 60

OOM_POD=$(kubectl get pods -n sre-demo -l app=stress-oom -o jsonpath='{.items[0].metadata.name}')
echo "OOM pod: $OOM_POD"
kubectl get pods -n sre-demo

curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodOOMKilled\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$OOM_POD\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Agent investigating... (45s)"
sleep 45

# ─────────────────────────────────────────
echo ""
echo "========================================"
echo "   SCENARIO 3: Bad Image / ImagePullBackOff"
echo "   Wrong image tag — cant pull"
echo "   Expect RCA: image pull failure"
echo "   Expect Action: rollback"
echo "========================================"

kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-badimage
  namespace: sre-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stress-badimage
  template:
    metadata:
      labels:
        app: stress-badimage
    spec:
      containers:
      - name: stress-badimage
        image: dhruvpatil56/kubepilot-broken-app:v999-does-not-exist
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
YAML

echo "Waiting for ImagePullBackOff (60s)..."
sleep 60

BADIMAGE_POD=$(kubectl get pods -n sre-demo -l app=stress-badimage -o jsonpath='{.items[0].metadata.name}')
echo "Bad image pod: $BADIMAGE_POD"
kubectl get pods -n sre-demo

curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodNotReady\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BADIMAGE_POD\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Agent investigating... (45s)"
sleep 45

# ─────────────────────────────────────────
echo ""
echo "========================================"
echo "   SCENARIO 4: Liveness Probe Failure"
echo "   App runs but health check fails"
echo "   Expect RCA: health check failing"
echo "   Expect Action: restart_pod"
echo "========================================"

kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stress-probe
  namespace: sre-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stress-probe
  template:
    metadata:
      labels:
        app: stress-probe
    spec:
      containers:
      - name: stress-probe
        image: python:3.11-slim
        command: ["python", "-c", "
import time
print('App started but health is broken')
while True:
    time.sleep(1)
"]
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
YAML

echo "Waiting for liveness probe failure (90s)..."
sleep 90

PROBE_POD=$(kubectl get pods -n sre-demo -l app=stress-probe -o jsonpath='{.items[0].metadata.name}')
echo "Probe pod: $PROBE_POD"
kubectl get pods -n sre-demo

curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodCrashLooping\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$PROBE_POD\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Agent investigating... (45s)"
sleep 45

# ─────────────────────────────────────────
echo ""
echo "========================================"
echo "   FINAL RESULTS"
echo "========================================"
echo ""
echo "Pod status:"
kubectl get pods -n sre-demo
echo ""
echo "Incidents detected:"
curl -s http://localhost:8000/incidents | python3 -m json.tool
echo ""
echo "========================================"
echo "   Cleanup stress test deployments"
echo "========================================"
kubectl delete deployment stress-crash stress-oom stress-badimage stress-probe -n sre-demo 2>/dev/null
echo "Stress deployments cleaned up"
echo ""
echo "Dashboard: http://$PUBLIC_IP:8000"
echo "========================================"
echo "   Stress Test Complete!"
echo "========================================"
