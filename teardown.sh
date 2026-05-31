#!/bin/bash

echo "========================================"
echo "   KubePilot AI — Teardown"
echo "========================================"

echo ""
echo "[1/3] Stopping port-forwards..."
pkill -f "port-forward" 2>/dev/null && echo "  Port-forwards stopped" || echo "  No port-forwards running"

echo ""
echo "[2/3] Scaling down deployments..."
kubectl scale deployment healing-agent --replicas=0 -n sre-demo 2>/dev/null
kubectl scale deployment broken-app --replicas=0 -n sre-demo 2>/dev/null
kubectl scale deployment prometheus-grafana --replicas=0 -n monitoring 2>/dev/null
kubectl scale deployment prometheus-kube-prometheus-operator --replicas=0 -n monitoring 2>/dev/null
kubectl scale deployment prometheus-kube-state-metrics --replicas=0 -n monitoring 2>/dev/null
kubectl scale statefulset alertmanager-prometheus-kube-prometheus-alertmanager --replicas=0 -n monitoring 2>/dev/null
kubectl scale statefulset prometheus-prometheus-kube-prometheus-prometheus --replicas=0 -n monitoring 2>/dev/null
echo "  All deployments scaled to zero"

echo ""
echo "[3/3] Final state..."
kubectl get pods -n sre-demo
kubectl get pods -n monitoring

echo ""
echo "========================================"
echo "   Stack stopped. Cluster is idle."
echo ""
echo "   To restart:  ./setup.sh"
echo "   To destroy:  kind delete cluster --name kubepilot"
echo "========================================"
