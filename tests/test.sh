#!/bin/bash

echo "=== KubePilot AI — Full E2E Test ==="

HEALING_POD=$(kubectl get pods -n sre-demo -l app=healing-agent -o jsonpath='{.items[0].metadata.name}')
BROKEN_POD=$(kubectl get pods -n sre-demo -l app=broken-app -o jsonpath='{.items[0].metadata.name}')

echo "Healing Agent Pod: $HEALING_POD"
echo "Broken App Pod:    $BROKEN_POD"
echo ""

# Step 1: Verify services healthy
echo "[1/6] Checking all pods are Running..."
kubectl get pods -n sre-demo
echo ""

# Step 2: Check healing agent root endpoint
echo "[2/6] Checking healing agent status..."
kubectl port-forward -n sre-demo $HEALING_POD 8000:8000 &
PF_PID=$!
sleep 3
curl -s http://localhost:8000/ | python3 -m json.tool
echo ""

# Step 3: Check gitops status
echo "[3/6] Checking GitOps status..."
curl -s http://localhost:8000/gitops/status | python3 -m json.tool
echo ""

# Step 4: Fire manual test webhook
echo "[4/6] Firing test webhook (PodCrashLooping)..."
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodCrashLooping\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BROKEN_POD\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Waiting 30s for agent to investigate..."
sleep 30

# Step 5: Check incidents
echo "[5/6] Checking incidents..."
curl -s http://localhost:8000/incidents | python3 -m json.tool
echo ""

# Step 6: Check feedback
echo "[6/6] Checking feedback for pod..."
curl -s http://localhost:8000/feedback/$BROKEN_POD | python3 -m json.tool
echo ""

kill $PF_PID 2>/dev/null

# Step 7: Trigger real crash
echo "[7/7] Triggering real pod crash..."
kubectl delete pod -n sre-demo $BROKEN_POD
echo "Pod deleted — Kubernetes will recreate it"
echo "Watch logs: kubectl logs -n sre-demo $HEALING_POD -f"
echo ""

echo "=== Test Complete ==="
echo "Dashboard: kubectl port-forward -n sre-demo $HEALING_POD 8000:8000 then open http://localhost:8000/dashboard"
