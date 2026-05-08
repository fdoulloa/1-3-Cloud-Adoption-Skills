#!/usr/bin/env python3
"""
Scaling Engine - Decision logic for data node autoscaling.
All configuration loaded from .env via config module.
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from config import config
from css_monitor import DataNodeMetrics


class ScalingAction(Enum):
    """Possible scaling actions"""
    NONE = "none"
    SCALE_OUT = "scale_out"
    SCALE_IN = "scale_in"


@dataclass
class ScalingDecision:
    """Container for scaling decision"""
    action: ScalingAction
    current_data_nodes: int
    target_data_nodes: int
    reason: str
    timestamp: str


@dataclass
class ScalingEvent:
    """Record of a scaling event"""
    action: ScalingAction
    current_data_nodes: int
    target_data_nodes: int
    reason: str
    timestamp: str


class DataNodeScalingEngine:
    """
    Decision engine for data node autoscaling.

    Implements hysteresis-based scaling with:
    - Scale OUT: When ANY metric exceeds its threshold
    - Scale IN: When ALL metrics are below their thresholds

    Includes cooldown periods to prevent thrashing.
    """

    def __init__(self):
        # Load thresholds from config
        self.scale_out_cpu = config.scale_out_cpu
        self.scale_out_heap = config.scale_out_heap
        self.scale_out_disk = config.scale_out_disk

        self.scale_in_cpu = config.scale_in_cpu
        self.scale_in_heap = config.scale_in_heap
        self.scale_in_disk = config.scale_in_disk

        self.min_nodes = config.min_data_nodes
        self.max_nodes = config.max_data_nodes

        self.scale_out_cooldown = timedelta(seconds=config.scale_out_cooldown)
        self.scale_in_cooldown = timedelta(seconds=config.scale_in_cooldown)

        # State tracking
        self.last_scale_out: Optional[datetime] = None
        self.last_scale_in: Optional[datetime] = None
        self.decision_history: List[ScalingEvent] = []

    def _can_scale_out(self) -> tuple[bool, str]:
        """Check if scale out is allowed (cooldown expired)"""
        if self.last_scale_out is None:
            return True, "No previous scale out"

        elapsed = datetime.now() - self.last_scale_out
        remaining = self.scale_out_cooldown - elapsed

        if remaining.total_seconds() > 0:
            return False, f"Cooldown: {remaining.total_seconds():.0f}s remaining"

        return True, "Cooldown expired"

    def _can_scale_in(self) -> tuple[bool, str]:
        """Check if scale in is allowed (cooldown expired)"""
        if self.last_scale_in is None:
            return True, "No previous scale in"

        elapsed = datetime.now() - self.last_scale_in
        remaining = self.scale_in_cooldown - elapsed

        if remaining.total_seconds() > 0:
            return False, f"Cooldown: {remaining.total_seconds():.0f}s remaining"

        return True, "Cooldown expired"

    def _evaluate_scale_out(self, metrics: DataNodeMetrics) -> tuple[bool, str]:
        """
        Evaluate if scale out is needed.
        Scale OUT if ANY metric exceeds its threshold.
        """
        reasons = []

        # Check CPU
        if metrics.max_cpu_percent >= self.scale_out_cpu:
            reasons.append(f"CPU {metrics.max_cpu_percent:.1f}% >= {self.scale_out_cpu}%")

        # Check Heap
        if metrics.max_heap_percent >= self.scale_out_heap:
            reasons.append(f"Heap {metrics.max_heap_percent:.1f}% >= {self.scale_out_heap}%")

        # Check Disk
        if metrics.max_disk_percent >= self.scale_out_disk:
            reasons.append(f"Disk {metrics.max_disk_percent:.1f}% >= {self.scale_out_disk}%")

        if reasons:
            return True, " | ".join(reasons)

        return False, "All metrics below scale-out thresholds"

    def _evaluate_scale_in(self, metrics: DataNodeMetrics) -> tuple[bool, str]:
        """
        Evaluate if scale in is needed.
        Scale IN only if ALL metrics are below their thresholds.
        """
        reasons = []

        # Check CPU
        if metrics.avg_cpu_percent <= self.scale_in_cpu:
            reasons.append(f"CPU {metrics.avg_cpu_percent:.1f}% <= {self.scale_in_cpu}%")
        else:
            return False, f"CPU {metrics.avg_cpu_percent:.1f}% > {self.scale_in_cpu}%"

        # Check Heap
        if metrics.avg_heap_percent <= self.scale_in_heap:
            reasons.append(f"Heap {metrics.avg_heap_percent:.1f}% <= {self.scale_in_heap}%")
        else:
            return False, f"Heap {metrics.avg_heap_percent:.1f}% > {self.scale_in_heap}%"

        # Check Disk
        if metrics.avg_disk_percent <= self.scale_in_disk:
            reasons.append(f"Disk {metrics.avg_disk_percent:.1f}% <= {self.scale_in_disk}%")
        else:
            return False, f"Disk {metrics.avg_disk_percent:.1f}% > {self.scale_in_disk}%"

        return True, " & ".join(reasons)

    def make_scaling_decision(self, metrics: DataNodeMetrics) -> ScalingDecision:
        """
        Make scaling decision based on current metrics.

        Priority:
        1. Scale OUT if needed (high load)
        2. Scale IN if needed (low load)
        3. No action
        """
        current_nodes = metrics.total_data_nodes
        timestamp = datetime.now().isoformat()

        # Check for scale out
        should_scale_out, out_reason = self._evaluate_scale_out(metrics)

        if should_scale_out:
            can_scale, cooldown_reason = self._can_scale_out()

            if can_scale and current_nodes < self.max_nodes:
                target_nodes = min(current_nodes + 1, self.max_nodes)
                reason = f"Scale OUT: {out_reason}"

                decision = ScalingDecision(
                    action=ScalingAction.SCALE_OUT,
                    current_data_nodes=current_nodes,
                    target_data_nodes=target_nodes,
                    reason=reason,
                    timestamp=timestamp
                )

                self._record_decision(decision)
                self.last_scale_out = datetime.now()
                return decision

            elif not can_scale:
                return ScalingDecision(
                    action=ScalingAction.NONE,
                    current_data_nodes=current_nodes,
                    target_data_nodes=current_nodes,
                    reason=f"Scale OUT needed but {cooldown_reason}",
                    timestamp=timestamp
                )

            else:
                return ScalingDecision(
                    action=ScalingAction.NONE,
                    current_data_nodes=current_nodes,
                    target_data_nodes=current_nodes,
                    reason=f"Scale OUT needed but at max nodes ({self.max_nodes})",
                    timestamp=timestamp
                )

        # Check for scale in
        should_scale_in, in_reason = self._evaluate_scale_in(metrics)

        if should_scale_in:
            can_scale, cooldown_reason = self._can_scale_in()

            if can_scale and current_nodes > self.min_nodes:
                target_nodes = max(current_nodes - 1, self.min_nodes)
                reason = f"Scale IN: {in_reason}"

                decision = ScalingDecision(
                    action=ScalingAction.SCALE_IN,
                    current_data_nodes=current_nodes,
                    target_data_nodes=target_nodes,
                    reason=reason,
                    timestamp=timestamp
                )

                self._record_decision(decision)
                self.last_scale_in = datetime.now()
                return decision

            elif not can_scale:
                return ScalingDecision(
                    action=ScalingAction.NONE,
                    current_data_nodes=current_nodes,
                    target_data_nodes=current_nodes,
                    reason=f"Scale IN possible but {cooldown_reason}",
                    timestamp=timestamp
                )

            else:
                return ScalingDecision(
                    action=ScalingAction.NONE,
                    current_data_nodes=current_nodes,
                    target_data_nodes=current_nodes,
                    reason=f"Scale IN possible but at min nodes ({self.min_nodes})",
                    timestamp=timestamp
                )

        # No scaling needed
        return ScalingDecision(
            action=ScalingAction.NONE,
            current_data_nodes=current_nodes,
            target_data_nodes=current_nodes,
            reason="Metrics within normal range",
            timestamp=timestamp
        )

    def _record_decision(self, decision: ScalingDecision):
        """Record a scaling decision in history"""
        event = ScalingEvent(
            action=decision.action,
            current_data_nodes=decision.current_data_nodes,
            target_data_nodes=decision.target_data_nodes,
            reason=decision.reason,
            timestamp=decision.timestamp
        )
        self.decision_history.append(event)

    def print_scaling_decision(self, decision: ScalingDecision):
        """Print scaling decision only when action is needed"""
        if decision.action == ScalingAction.SCALE_OUT:
            print(f"🔼 SCALE OUT: {decision.current_data_nodes} → {decision.target_data_nodes} data nodes | {decision.reason}", flush=True)
        elif decision.action == ScalingAction.SCALE_IN:
            print(f"🔽 SCALE IN: {decision.current_data_nodes} → {decision.target_data_nodes} data nodes | {decision.reason}", flush=True)


if __name__ == "__main__":
    # Test the scaling engine
    print("🚀 Testing Scaling Engine...", flush=True)

    engine = DataNodeScalingEngine()

    # Create test metrics
    test_metrics = DataNodeMetrics(
        timestamp=datetime.now().isoformat(),
        total_data_nodes=3,
        cluster_status="green",
        avg_cpu_percent=85.0,  # High CPU - should trigger scale out
        max_cpu_percent=90.0,
        avg_heap_percent=70.0,
        max_heap_percent=75.0,
        avg_disk_percent=50.0,
        max_disk_percent=55.0,
        total_docs=100000,
        total_size_gb=10.0
    )

    print("\nTest 1: High CPU (should scale out)", flush=True)
    decision = engine.make_scaling_decision(test_metrics)
    engine.print_scaling_decision(decision)

    test_metrics.avg_cpu_percent = 20.0
    test_metrics.max_cpu_percent = 25.0
    test_metrics.avg_heap_percent = 30.0
    test_metrics.max_heap_percent = 35.0
    test_metrics.avg_disk_percent = 25.0
    test_metrics.max_disk_percent = 30.0

    print("\nTest 2: Low metrics (should scale in)", flush=True)
    decision = engine.make_scaling_decision(test_metrics)
    engine.print_scaling_decision(decision)
