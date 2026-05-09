#!/bin/bash
# Deploy AIOps Agent to Huawei Cloud ECS.
# Usage: ./deploy_to_ecs.sh [ECS_HOST] [SSH_KEY]
# Defaults: ECS_HOST=101.44.184.244, SSH_KEY=~/.ssh/gov-rag-20260508055113

set -euo pipefail

ECS_HOST="${1:-101.44.184.244}"
SSH_KEY="${2:-$HOME/.ssh/gov-rag-20260508055113}"
REMOTE_DIR="/opt/aiops-agent"
SKILL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== AIOps Agent Deployment ==="
echo "  ECS: ${ECS_HOST}"
echo "  SSH key: ${SSH_KEY}"
echo "  Skill root: ${SKILL_ROOT}"
echo "  Remote dir: ${REMOTE_DIR}"
echo

SSH="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no"
SCP="scp -i ${SSH_KEY} -o StrictHostKeyChecking=no"

# 1. Create directories on ECS
echo "[1/6] Creating directories on ECS..."
${SSH} root@${ECS_HOST} "mkdir -p ${REMOTE_DIR}/{agent,policies,runbooks,index_templates,demo,scripts,logs}"

# 2. Copy files
echo "[2/6] Copying agent code..."
${SCP} ${SKILL_ROOT}/agent/*.py root@${ECS_HOST}:${REMOTE_DIR}/agent/

echo "[3/6] Copying policies, runbooks, templates, demo..."
${SCP} ${SKILL_ROOT}/policies/*.json root@${ECS_HOST}:${REMOTE_DIR}/policies/
${SCP} ${SKILL_ROOT}/runbooks/*.md root@${ECS_HOST}:${REMOTE_DIR}/runbooks/
${SCP} ${SKILL_ROOT}/index_templates/*.json root@${ECS_HOST}:${REMOTE_DIR}/index_templates/
${SCP} ${SKILL_ROOT}/demo/*.json root@${ECS_HOST}:${REMOTE_DIR}/demo/

echo "[4/6] Copying scripts and config..."
${SCP} ${SKILL_ROOT}/scripts/aiops_loop.py root@${ECS_HOST}:${REMOTE_DIR}/scripts/
${SCP} ${SKILL_ROOT}/.env root@${ECS_HOST}:${REMOTE_DIR}/.env

# 3. Install Python dependencies
echo "[5/6] Installing Python dependencies on ECS..."
${SSH} root@${ECS_HOST} "pip3 install -q langgraph langchain-core langgraph-checkpoint-sqlite opensearch-py openai python-dotenv cachetools 2>&1 | tail -3"

# 4. Deploy systemd service
echo "[6/6] Deploying systemd service..."
${SCP} ${SKILL_ROOT}/scripts/aiops-agent.service root@${ECS_HOST}:/etc/systemd/system/aiops-agent.service
${SSH} root@${ECS_HOST} "systemctl daemon-reload && systemctl enable aiops-agent && systemctl restart aiops-agent && sleep 3 && systemctl status aiops-agent --no-pager"

echo
echo "=== Deployment Complete ==="
echo "  Service:  systemctl status aiops-agent"
echo "  Logs:     journalctl -u aiops-agent -f"
echo "  Log file: ${REMOTE_DIR}/aiops_loop.log"
echo "  Stop:     systemctl stop aiops-agent"
