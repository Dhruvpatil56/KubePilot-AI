#!/bin/bash

echo "=== KubePilot AI - Sprint 1 Restructure ==="

cd ~/KubePilot-AI

# Create new folder structure
echo "[1/4] Creating new folder structure..."
mkdir -p agent llm gitops feedback chatops monitoring

# Copy files to new structure
echo "[2/4] Migrating old files..."
cp self-healing-app/k8s_client.py agent/k8s_client.py
cp self-healing-app/config.py config.py
cp self-healing-app/main.py agent/main.py
cp self-healing-app/requirements.txt agent/requirements.txt

# Remove old folder
echo "[3/4] Cleaning up old structure..."
rm -rf self-healing-app

# Add .gitignore
echo "[4/4] Adding .gitignore..."
cat > .gitignore << 'GITIGNORE'
__pycache__/
*.pyc
*.pyo
.env
*.env
.env.*
venv/
.venv/
*.egg-info/
.DS_Store
*.log
GITIGNORE

echo ""
echo "=== Done. Current structure ==="
find . -not -path './.git/*' -type f | sort

