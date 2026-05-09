# LangGraph State Machine Design

## State Flow

```
Observe → Diagnose → Recommend → Preview → Approve → Execute → Verify → Report
                                                        │              │
                                            L0/L1 ─────► Report       │
                                            L2+approved ─► Execute    │
                                            L2+rejected ──► Report    │
                                            L3 ──────────► Report    │
                                                                       │
                                            healthy ─────► Report     │
                                            degraded ────► Observe    │
                                                           (max 2)   │
                                            failed ──────► Report     │
```

## 8 States

| State | Purpose | Key Outputs |
|-------|---------|-------------|
| Observe | Collect metrics, logs, CTS events | `observed_metrics`, `observed_logs`, `observed_cts_events`, `observation_summary` |
| Diagnose | Identify root cause via LLM + knowledge | `root_cause`, `related_incidents`, `confidence_score` |
| Recommend | Find runbook, determine action level | `recommended_action`, `runbook_id`, `runbook_steps`, `action_level` |
| Preview | Dry-run recommended action | `preview_result`, `preview_summary` |
| Approve | Handle L2 approval or auto-approve L0/L1 | `approval_token`, `approval_status`, `approver_identity` |
| Execute | Run remediation via SDK/FunctionGraph | `execution_result`, `execution_timestamp` |
| Verify | Check if remediation resolved the issue | `verification_metrics`, `verification_status` |
| Report | Generate and persist incident report | `incident_report`, `report_url` |

## OpsAgentState TypedDict

```python
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
```

## Conditional Routing

### After Approve

```python
def _route_after_approval(state) -> str:
    if action_level in ("L0", "L1") and approval_status == "auto_approved":
        return "report"
    if action_level == "L3" and approval_status == "blocked":
        return "report"
    if action_level == "L2":
        if approval_status == "approved":
            return "execute"
        if approval_status in ("rejected", "expired", "blocked"):
            return "report"
        return "approve"  # pending: stay and poll
    return "report"
```

### After Verify

```python
def _route_after_verification(state) -> str:
    if verification_status == "healthy":
        return "report"
    if verification_status == "degraded" and loop_count < max_rediagnosis_loops:
        return "observe"  # re-diagnose (max 2 loops)
    return "report"  # failed or max loops reached
```

## Graph Construction

```python
graph = StateGraph(OpsAgentState)
for name in ["observe","diagnose","recommend","preview","approve","execute","verify","report"]:
    graph.add_node(name, getattr(self, f"{name}_node"))

graph.add_edge("observe", "diagnose")
graph.add_edge("diagnose", "recommend")
graph.add_edge("recommend", "preview")
graph.add_edge("preview", "approve")
graph.add_conditional_edges("approve", self._route_after_approval)
graph.add_edge("execute", "verify")
graph.add_conditional_edges("verify", self._route_after_verification)
graph.add_edge("report", END)
graph.set_entry_point("observe")
```

## State Persistence

LangGraph uses `SqliteSaver` checkpointer for durable state across approval wait periods. Each alert runs in its own thread:

```python
compiled_graph = graph.compile(
    checkpointer=SqliteSaver.from_conn_string("aiops_checkpoints.db")
)
config = {"configurable": {"thread_id": thread_id}}
result = compiled_graph.invoke(initial_state, config)
```

Enables the agent to pause at Approve, wait for human approval, and resume without losing state.
