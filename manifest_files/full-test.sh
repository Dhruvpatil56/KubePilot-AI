#!/bin/bash

echo "=========================================="
echo "   SRE Self-Healing - Full E2E Test"
echo "=========================================="

# Setup
kubectl port-forward -n sre-demo svc/broken-app-service 8080:80 > /dev/null 2>&1 &
PF_PID=$!
sleep 2

echo ""
echo "=== STEP 1: Initial State ==="
echo "Broken-app pods:"
kubectl get pods -n sre-demo -l app=broken-app
echo ""
echo "Healing agent status:"
kubectl run quick-check --image=curlimages/curl:latest -n sre-demo --rm -i --restart=Never -- \
  curl -s http://healing-agent.sre-demo.svc.cluster.local:8000/incidents | head -20

echo ""
echo "=== STEP 2: Trigger Pod Crash ==="
POD_NAME=$(kubectl get pods -n sre-demo -l app=broken-app -o jsonpath='{.items[0].metadata.name}')
echo "Target pod: $POD_NAME"
curl -s http://localhost:8080/crash > /dev/null 2>&1 || echo "✓ Pod crashed successfully"

echo ""
echo "=== STEP 3: Wait for Pod to Restart (20 seconds) ==="
sleep 20

echo ""
echo "Pods after crash:"
kubectl get pods -n sre-demo -l app=broken-app

echo ""
echo "=== STEP 4: Wait for Alert to Fire (90 seconds) ==="
echo "Prometheus detects crash -> Fires alert -> Sends to Alertmanager -> Webhooks to healing agent"
for i in {1..90}; do
  echo -n "."
  sleep 1
  if [ $((i % 30)) -eq 0 ]; then
    echo " ${i}s"
  fi
done
echo ""

echo ""
echo "=== STEP 5: Check Healing Agent Logs ==="
kubectl logs -n sre-demo -l app=healing-agent --tail=50 | grep -A10 -B5 "Processing alert\|incident\|action"

echo ""
echo "=== STEP 6: Check Incidents via API ==="
kubectl run check-incidents --image=curlimages/curl:latest -n sre-demo --rm -i --restart=Never -- \
  curl -s http://healing-agent.sre-demo.svc.cluster.local:8000/incidents

echo ""
echo "=== STEP 7: Check Current Alerts in Alertmanager ==="
kubectl run check-alerts --image=curlimages/curl:latest -n monitoring --rm -i --restart=Never -- \
  curl -s http://kube-prometheus-stack-alertmanager.monitoring.svc.cluster.local:9093/api/v2/alerts

echo ""
echo "=== STEP 8: Final Pod Status ==="
kubectl get pods -n sre-demo -l app=broken-app -o wide

echo ""
echo "=== Test Complete ==="

# Cleanup
kill $PF_PID 2>/dev/null

