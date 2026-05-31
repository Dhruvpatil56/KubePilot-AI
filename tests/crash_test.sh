#!/bin/bash

echo "=== KubePilot AI — Crash Test & Monitor ==="

HEALING_POD=$(kubectl get pods -n sre-demo -l app=healing-agent -o jsonpath='{.items[0].metadata.name}')
BROKEN_POD=$(kubectl get pods -n sre-demo -l app=broken-app -o jsonpath='{.items[0].metadata.name}')
PUBLIC_IP=$(curl -s ifconfig.me)

echo "Healing Agent: $HEALING_POD"
echo "Broken App:    $BROKEN_POD"
echo "Dashboard:     http://$PUBLIC_IP:8000/dashboard"
echo ""

# Step 1: Start dashboard port-forward
echo "[1/4] Starting dashboard port-forward..."
kubectl port-forward -n sre-demo $HEALING_POD 8000:8000 --address 0.0.0.0 &
DASH_PID=$!
sleep 3

# Step 2: Trigger multiple crashes
echo "[2/4] Triggering crashes on broken-app..."
kubectl port-forward -n sre-demo $BROKEN_POD 5000:5000 &
BF_PID=$!
sleep 2

for i in {1..5}; do
  echo "  Crash $i/5..."
  curl -s http://localhost:5000/crash || true
  sleep 3
done

kill $BF_PID 2>/dev/null

# Step 3: Show restart count
echo ""
echo "[3/4] Pod restart counts:"
kubectl get pods -n sre-demo
echo ""

# Step 4: Monitor logs for alert
echo "[4/4] Monitoring healing agent logs for alert..."
echo "      Dashboard: http://$PUBLIC_IP:8000/dashboard"
echo "      Waiting for Prometheus to fire alert (up to 2 min)..."
echo "      Press Ctrl+C to stop watching"
echo ""

kubectl logs -n sre-demo $HEALING_POD -f

