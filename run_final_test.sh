#!/bin/bash

echo "========================================"
echo "   KubePilot AI — Final System Test"
echo "========================================"

HEALING_POD=$(kubectl get pods -n sre-demo -l app=healing-agent -o jsonpath='{.items[0].metadata.name}')
BROKEN_POD1=$(kubectl get pods -n sre-demo -l app=broken-app -o jsonpath='{.items[0].metadata.name}')
BROKEN_POD2=$(kubectl get pods -n sre-demo -l app=broken-app -o jsonpath='{.items[1].metadata.name}')
PUBLIC_IP=$(curl -s ifconfig.me)

echo ""
echo "Healing Agent: $HEALING_POD"
echo "Broken Pod 1:  $BROKEN_POD1"
echo "Broken Pod 2:  $BROKEN_POD2"
echo "Dashboard:     http://$PUBLIC_IP:8000"
echo ""

# Kill any existing port-forward
pkill -f "port-forward" 2>/dev/null
sleep 2

# Start port-forward
kubectl port-forward -n sre-demo $HEALING_POD 8000:8000 --address 0.0.0.0 &
sleep 3

echo "========================================"
echo "   STEP 1: System Health Check"
echo "========================================"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""
curl -s http://localhost:8000/api/info | python3 -m json.tool
echo ""

echo "========================================"
echo "   STEP 2: GitOps Status"
echo "========================================"
curl -s http://localhost:8000/gitops/status | python3 -m json.tool
echo ""

echo "========================================"
echo "   STEP 3: Alert 1 — PodCrashLooping"
echo "   Expect: restart_pod recommended"
echo "========================================"
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodCrashLooping\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BROKEN_POD1\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Investigating... (40s)"
sleep 40

echo "========================================"
echo "   STEP 4: Alert 2 — PodOOMKilled"
echo "   Expect: scale_up recommended"
echo "========================================"
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodOOMKilled\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BROKEN_POD1\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Investigating... (40s)"
sleep 40

echo "========================================"
echo "   STEP 5: Alert 3 — PodNotReady"
echo "   Expect: rollback recommended"
echo "========================================"
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodNotReady\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BROKEN_POD2\",
        \"severity\": \"warning\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Investigating... (40s)"
sleep 40

echo "========================================"
echo "   STEP 6: Alert 4 — Duplicate Test"
echo "   Expect: SKIPPED (same pod+alert)"
echo "========================================"
curl -s -X POST http://localhost:8000/webhook/alert \
  -H "Content-Type: application/json" \
  -d "{
    \"status\": \"firing\",
    \"alerts\": [{
      \"status\": \"firing\",
      \"labels\": {
        \"alertname\": \"PodCrashLooping\",
        \"namespace\": \"sre-demo\",
        \"pod\": \"$BROKEN_POD1\",
        \"severity\": \"critical\"
      },
      \"annotations\": {}
    }]
  }"
echo ""
echo "Waiting... (15s)"
sleep 15

echo "========================================"
echo "   STEP 7: Check All Incidents"
echo "========================================"
curl -s http://localhost:8000/incidents | python3 -m json.tool
echo ""

echo "========================================"
echo "   STEP 8: Check Feedback"
echo "========================================"
curl -s http://localhost:8000/feedback/$BROKEN_POD1 | python3 -m json.tool
echo ""

echo "========================================"
echo "   FINAL: Dashboard URL"
echo "========================================"
echo ""
echo "  ✅ Open this in your browser:"
echo "  http://$PUBLIC_IP:8000"
echo ""
echo "========================================"
echo "   What to expect on dashboard:"
echo "========================================"
echo "  Total Incidents:  3 (4th deduplicated)"
echo "  Remediated:       0 (dry-run mode)"
echo "  Dry Run:          3"
echo "  Errors:           0"
echo ""
echo "  Incident 1 — PodCrashLooping  → restart_pod (high confidence)"
echo "  Incident 2 — PodOOMKilled     → scale_up or no_action"
echo "  Incident 3 — PodNotReady      → rollback (medium confidence)"
echo ""
echo "  Activity Feed: shows last 3 incidents with time-ago"
echo "  System Health: Agent Online, LLM groq, Dry Run Enabled"
echo ""
echo "========================================"
echo "   Test Complete!"
echo "========================================"
