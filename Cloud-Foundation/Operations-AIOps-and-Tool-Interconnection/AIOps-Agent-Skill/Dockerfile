FROM python:3.10-slim

WORKDIR /opt/aiops-agent

COPY scripts/requirements.txt /opt/aiops-agent/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ /opt/aiops-agent/agent/
COPY policies/ /opt/aiops-agent/policies/
COPY runbooks/ /opt/aiops-agent/runbooks/
COPY index_templates/ /opt/aiops-agent/index_templates/
COPY demo/ /opt/aiops-agent/demo/
COPY scripts/aiops_loop.py /opt/aiops-agent/scripts/aiops_loop.py

ENV AIOPS_AGENT_DIR=/opt/aiops-agent
ENV AIOPS_CYCLE_SLEEP=120
ENV AIOPS_MAX_CYCLES=0

CMD ["python3", "/opt/aiops-agent/scripts/aiops_loop.py"]
