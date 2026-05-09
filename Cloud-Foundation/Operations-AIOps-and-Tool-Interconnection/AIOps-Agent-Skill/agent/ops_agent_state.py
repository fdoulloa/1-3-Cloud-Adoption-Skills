"""LangGraph StateGraph for the AIOps Agent.

8-state flow: Observe → Diagnose → Recommend → Preview → Approve → Execute → Verify → Report

Conditional routing:
- After Approve: L0/L1 → Report; L2+approved → Execute; L2+rejected → Report
- After Verify: healthy → Report; degraded → Observe (max 2 loops); failed → Report (escalation)
"""

import json
import time
from datetime import datetime, timezone
from typing import TypedDict, Optional, Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from ops_agent_config import OpsAgentConfig
from aom_ces_connector import AOMCESConnector
from cts_connector import CTSConnector
from css_log_correlator import CSSLogCorrelator
from tools_huawei_cloud import HuaweiCloudToolRegistry
from tools_knowledge import OpsKnowledgeBase
from tools_prometheus import PrometheusTools
from runbook_engine import RunbookEngine
from action_policy import ActionPolicy
from approval_token import ApprovalToken
from remediation_executor import RemediationExecutor
from maas_client import create_maas_client, call_maas
from otel_tracing import init_otel_tracing, get_tracer


class OpsAgentState(TypedDict, total=False):
    # Input
    alert_event: dict
    alert_source: str
    alert_severity: str

    # Observation
    observed_metrics: dict
    observed_logs: list
    observed_cts_events: list
    observation_summary: str

    # Diagnosis
    root_cause: str
    related_incidents: list
    confidence_score: float

    # Recommendation
    recommended_action: str
    runbook_id: str
    runbook_steps: list
    action_level: str

    # Preview
    preview_result: dict
    preview_summary: str

    # Approval
    approval_token: str
    approval_status: str
    approver_identity: str

    # Execution
    execution_result: dict
    execution_timestamp: str

    # Verification
    verification_metrics: dict
    verification_status: str

    # Report
    incident_report: dict
    report_url: str

    # Metadata
    trace_id: str
    agent_version: str
    loop_count: int


class OpsAgent:
    """AIOps Agent with LangGraph state machine orchestration."""

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self.monitor = AOMCESConnector(config)
        self.cts = CTSConnector(config)
        self.log_correlator = CSSLogCorrelator(config)
        self.tools = HuaweiCloudToolRegistry(config)
        self.knowledge = OpsKnowledgeBase(config)
        self.prometheus = PrometheusTools(config)
        self.runbook_engine = RunbookEngine(config)
        self.policy = ActionPolicy(config.policy_dir)
        self.approval = ApprovalToken(config)
        self.executor = RemediationExecutor(config, self.tools)
        self.maas = create_maas_client(config)
        self.tracer = get_tracer("aiops-agent")

    def build_graph(self, checkpoint_path: str = "aiops_checkpoints.db") -> StateGraph:
        """Build the LangGraph StateGraph with all nodes and edges."""
        graph = StateGraph(OpsAgentState)

        graph.add_node("observe", self.observe_node)
        graph.add_node("diagnose", self.diagnose_node)
        graph.add_node("recommend", self.recommend_node)
        graph.add_node("preview", self.preview_node)
        graph.add_node("approve", self.approve_node)
        graph.add_node("execute", self.execute_node)
        graph.add_node("verify", self.verify_node)
        graph.add_node("report", self.report_node)

        graph.add_edge("observe", "diagnose")
        graph.add_edge("diagnose", "recommend")
        graph.add_edge("recommend", "preview")
        graph.add_edge("preview", "approve")
        graph.add_conditional_edges("approve", self._route_after_approval)
        graph.add_edge("execute", "verify")
        graph.add_conditional_edges("verify", self._route_after_verification)
        graph.add_edge("report", END)

        graph.set_entry_point("observe")

        from langgraph.checkpoint.memory import InMemorySaver
        return graph.compile(checkpointer=InMemorySaver())

    def run(self, alert: dict, thread_id: str = "default") -> dict:
        """Run the agent for a given alert event."""
        graph = self.build_graph()
        initial_state = {
            "alert_event": alert,
            "alert_source": alert.get("alert_source", "unknown"),
            "alert_severity": alert.get("severity", "medium"),
            "loop_count": 0,
            "agent_version": self.config.agent_version,
            "trace_id": alert.get("trace_id", ""),
        }
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(initial_state, config)
        return result

    # ── Node implementations ──

    def observe_node(self, state: OpsAgentState) -> dict:
        """Observe: Collect metrics, logs, and CTS events for the alert resource."""
        alert = state.get("alert_event", {})
        resource_type = alert.get("resource_type", "")
        resource_id = alert.get("resource_id", "")

        observed_metrics = self.monitor.get_current_metrics(
            resource_type, resource_id,
            metric_names=["cpu_utilization", "mem_utilization", "disk_utilization"],
        )

        observed_logs = self.log_correlator.query_recent_logs(
            resource_id=resource_id, minutes=15,
        )

        observed_cts_events = self.cts.correlate_with_alert(alert)

        # LLM summary of observations
        system = "You are an O&M analyst. Summarize the following observations about a cloud resource anomaly. Be concise."
        user = json.dumps({
            "alert": alert,
            "metrics": observed_metrics,
            "recent_logs": observed_logs[:10],
            "recent_changes": observed_cts_events[:5],
        }, ensure_ascii=False)
        observation_summary = call_maas(self.maas, system, user, max_tokens=1024)

        return {
            "observed_metrics": observed_metrics,
            "observed_logs": observed_logs,
            "observed_cts_events": observed_cts_events,
            "observation_summary": observation_summary,
        }

    def diagnose_node(self, state: OpsAgentState) -> dict:
        """Diagnose: Identify root cause using LLM + knowledge base."""
        alert = state.get("alert_event", {})
        observation_summary = state.get("observation_summary", "")

        related_incidents = self.knowledge.search_past_incidents(
            observation_summary, limit=5,
        )

        system = (
            "You are an expert cloud O&M diagnostician. "
            "Given the observation summary and related past incidents, "
            "identify the most likely root cause. "
            "Provide: 1) root cause description, 2) confidence score (0.0-1.0). "
            "Respond in JSON: {\"root_cause\": \"...\", \"confidence\": 0.0-1.0}"
        )
        user = json.dumps({
            "alert": alert,
            "observation_summary": observation_summary,
            "related_incidents": [
                {"content": inc.get("content", ""), "score": inc.get("score", 0)}
                for inc in related_incidents
            ],
        }, ensure_ascii=False)

        response = call_maas(self.maas, system, user, max_tokens=1024)

        try:
            diagnosis = json.loads(response)
            root_cause = diagnosis.get("root_cause", "Unknown")
            confidence_score = float(diagnosis.get("confidence", 0.5))
        except (json.JSONDecodeError, ValueError):
            root_cause = response[:500]
            confidence_score = 0.5

        return {
            "root_cause": root_cause,
            "related_incidents": related_incidents,
            "confidence_score": confidence_score,
        }

    def recommend_node(self, state: OpsAgentState) -> dict:
        """Recommend: Find matching runbook and determine action level."""
        alert = state.get("alert_event", {})
        alert_type = alert.get("alert_type", "")
        root_cause = state.get("root_cause", "")

        runbook_id = self.runbook_engine.lookup_runbook(alert_type)

        context = {
            "alert_type": alert_type,
            "resource_id": alert.get("resource_id", ""),
            "resource_type": alert.get("resource_type", ""),
            "region": alert.get("region", ""),
            "metric_value": alert.get("metric_value", ""),
            "threshold": alert.get("threshold", ""),
            "root_cause": root_cause,
        }

        runbook_steps = []
        recommended_action = ""
        action_level = "L1"

        if runbook_id:
            runbook_steps = self.runbook_engine.render_runbook(runbook_id, context)
            # Determine action level from the highest-level step
            level_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
            for step in runbook_steps:
                step_level = step.get("level", "L1")
                if level_order.get(step_level, 0) > level_order.get(action_level, 0):
                    action_level = step_level

            recommended_action = self.runbook_engine.preview_runbook(runbook_id, context)
        else:
            # No runbook found; LLM generates recommendation
            system = (
                "You are a cloud O&M advisor. Given the alert and diagnosis, "
                "recommend a remediation action. State the action and whether "
                "it requires human approval. "
                "Respond in JSON: {\"action\": \"...\", \"requires_approval\": bool}"
            )
            user = json.dumps({"alert": alert, "root_cause": root_cause}, ensure_ascii=False)
            response = call_maas(self.maas, system, user, max_tokens=512)
            try:
                rec = json.loads(response)
                recommended_action = rec.get("action", "")
                action_level = "L2" if rec.get("requires_approval") else "L1"
            except (json.JSONDecodeError, ValueError):
                recommended_action = response[:300]
                action_level = "L1"

        # Enforce: if any step is L3, block entirely
        if action_level == "L3":
            recommended_action = f"BLOCKED: Recommended action is L3 (forbidden). {recommended_action}"

        return {
            "recommended_action": recommended_action,
            "runbook_id": runbook_id or "",
            "runbook_steps": runbook_steps,
            "action_level": action_level,
        }

    def preview_node(self, state: OpsAgentState) -> dict:
        """Preview: Dry-run the recommended action and show effects."""
        action_level = state.get("action_level", "L1")
        runbook_steps = state.get("runbook_steps", [])

        if action_level in ("L0", "L1") and not runbook_steps:
            return {
                "preview_result": {"skipped": True, "reason": "L0/L1, no execution needed"},
                "preview_summary": "No execution preview needed (read-only or suggest only).",
            }

        previews = []
        for step in runbook_steps:
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            if tool_name:
                dry = self.tools.dry_run(tool_name, params)
                previews.append(dry)

        preview_summary = "\n".join(
            f"- {p['tool']}: level={p['level']}, would_execute={p['would_execute']}, "
            f"requires_approval={p['requires_approval']}"
            for p in previews
        ) if previews else "No previewable actions."

        return {
            "preview_result": {"previews": previews},
            "preview_summary": preview_summary,
        }

    def approve_node(self, state: OpsAgentState) -> dict:
        """Approve: Handle L2 approval or auto-approve L0/L1."""
        action_level = state.get("action_level", "L1")

        if action_level in ("L0", "L1"):
            return {
                "approval_token": "",
                "approval_status": "auto_approved",
                "approver_identity": "system",
            }

        if action_level == "L3":
            return {
                "approval_token": "",
                "approval_status": "blocked",
                "approver_identity": "system",
            }

        # L2: generate approval token
        alert = state.get("alert_event", {})
        tool_name = ""
        params = {}
        runbook_steps = state.get("runbook_steps", [])
        for step in runbook_steps:
            if step.get("level") == "L2":
                tool_name = step.get("tool", "")
                params = step.get("params", {})
                break

        request = self.approval.generate(
            tool_name=tool_name,
            params=params,
            requested_by="aiops-agent",
        )

        # In demo mode, auto-approve L2 actions
        if self.config.demo_mode:
            self.approval.approve(request["token"], approver_identity="demo-auto")
            return {
                "approval_token": request["token"],
                "approval_status": "approved",
                "approver_identity": "demo-auto",
            }

        return {
            "approval_token": request["token"],
            "approval_status": "pending",
            "approver_identity": "",
        }

    def execute_node(self, state: OpsAgentState) -> dict:
        """Execute: Run the remediation action via SDK or FunctionGraph."""
        runbook_steps = state.get("runbook_steps", [])
        results = []

        for step in runbook_steps:
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            level = step.get("level", "L1")

            if level in ("L0", "L1"):
                continue

            if level == "L3":
                results.append({"tool": tool_name, "result": "BLOCKED", "level": level})
                continue

            result = self.executor.execute(tool_name, params)
            results.append({"tool": tool_name, "result": result, "level": level})

        return {
            "execution_result": {"steps": results},
            "execution_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def verify_node(self, state: OpsAgentState) -> dict:
        """Verify: Check if remediation resolved the issue."""
        alert = state.get("alert_event", {})
        resource_type = alert.get("resource_type", "")
        resource_id = alert.get("resource_id", "")

        import time
        time.sleep(min(self.config.verification_delay_seconds, 5))

        health = self.monitor.assess_health(resource_type, resource_id)

        return {
            "verification_metrics": health.get("metrics", {}),
            "verification_status": health.get("status", "degraded"),
        }

    def report_node(self, state: OpsAgentState) -> dict:
        """Report: Generate incident report and persist to OBS/CSS."""
        alert = state.get("alert_event", {})
        now = datetime.now(tz=timezone.utc).isoformat()

        incident_report = {
            "incident_id": f"INC-{alert.get('alert_id', 'unknown')}-{int(time.time())}",
            "timestamp": now,
            "alert": alert,
            "root_cause": state.get("root_cause", ""),
            "confidence_score": state.get("confidence_score", 0.0),
            "recommended_action": state.get("recommended_action", ""),
            "action_level": state.get("action_level", ""),
            "approval_status": state.get("approval_status", ""),
            "execution_result": state.get("execution_result", {}),
            "verification_status": state.get("verification_status", ""),
            "agent_version": state.get("agent_version", ""),
            "trace_id": state.get("trace_id", ""),
        }

        doc_id = self.log_correlator.index_incident(incident_report)

        return {
            "incident_report": incident_report,
            "report_url": f"obs://{self.config.obs_bucket_name}/incidents/{incident_report['incident_id']}.json",
        }

    # ── Conditional routing ──

    def _route_after_approval(self, state: OpsAgentState) -> str:
        """Route after approval node based on action level and approval status."""
        action_level = state.get("action_level", "L1")
        approval_status = state.get("approval_status", "pending")

        if action_level in ("L0", "L1") and approval_status == "auto_approved":
            return "report"
        if action_level == "L3" and approval_status == "blocked":
            return "report"
        if action_level == "L2":
            if approval_status == "approved":
                return "execute"
            if approval_status in ("rejected", "expired", "blocked"):
                return "report"
            return "approve"  # pending: stay in approve (polling)

        return "report"

    def _route_after_verification(self, state: OpsAgentState) -> str:
        """Route after verification node based on health status."""
        verification_status = state.get("verification_status", "degraded")
        loop_count = state.get("loop_count", 0)

        if verification_status == "healthy":
            return "report"
        if verification_status == "degraded" and loop_count < self.config.max_rediagnosis_loops:
            return "observe"  # re-diagnose
        return "report"  # failed or max loops reached
