#!/bin/bash
# Install AIOps Agent runtime on provisioned ECS.
# Usage: ./install_agent.sh [AGENT_DIR]
# Default: /opt/aiops-agent

set -euo pipefail

AGENT_DIR="${1:-/opt/aiops-agent}"
PYTHON_VENV="${AGENT_DIR}/venv"

echo "=== Installing AIOps Agent ==="
echo "  Agent dir: ${AGENT_DIR}"

# System dependencies
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip

# Agent directory
mkdir -p "${AGENT_DIR}"
cd "${AGENT_DIR}"

# Python virtual environment
if [ ! -d "${PYTHON_VENV}" ]; then
    python3 -m venv "${PYTHON_VENV}"
fi
source "${PYTHON_VENV}/bin/activate"

# Install dependencies
pip install --quiet -r scripts/requirements.txt

# Deploy CSS index templates
echo "=== Deploying CSS index templates ==="
CSS_ENDPOINT="${CSS_ENDPOINT:-}"
CSS_USERNAME="${CSS_USERNAME:-admin}"
CSS_PASSWORD="${CSS_PASSWORD:-}"

if [ -n "${CSS_ENDPOINT}" ] && [ -n "${CSS_PASSWORD}" ]; then
    for template in index_templates/*.json; do
        tmpl_name=$(python3 -c "import json,os; d=json.load(open('${template}')); print(os.path.basename('${template}').replace('.json',''))")
        echo "  Deploying: ${tmpl_name}"
        curl -s -u "${CSS_USERNAME}:${CSS_PASSWORD}" \
            -X PUT "${CSS_ENDPOINT}/_index_template/${tmpl_name}" \
            -H "Content-Type: application/json" \
            -d @"${template}" > /dev/null 2>&1 && echo "    OK" || echo "    FAILED"
    done
else
    echo "  Skipped (CSS_ENDPOINT or CSS_PASSWORD not set)"
fi

# Systemd service
cp scripts/aiops-agent.service /etc/systemd/system/aiops-agent.service
systemctl daemon-reload
systemctl enable aiops-agent

echo "=== AIOps Agent installed ==="
echo "  Start:     systemctl start aiops-agent"
echo "  Status:    systemctl status aiops-agent"
echo "  Logs:      journalctl -u aiops-agent -f"
echo "  Log file:  ${AGENT_DIR}/aiops_loop.log"
echo "  Stop:      systemctl stop aiops-agent"
