#!/usr/bin/env python3
"""
CSS Data Node Monitor - Collects metrics from CSS cluster data nodes.
All configuration loaded from .env via config module.
"""
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

import urllib3
urllib3.disable_warnings()

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

from opensearchpy import OpenSearch
from config import config


@dataclass
class DataNodeMetrics:
    """Container for data node metrics"""
    timestamp: str
    total_data_nodes: int
    cluster_status: str
    avg_cpu_percent: float
    max_cpu_percent: float
    avg_heap_percent: float
    max_heap_percent: float
    avg_disk_percent: float
    max_disk_percent: float
    total_docs: int
    total_size_gb: float
    node_details: List[dict] = field(default_factory=list)
    scale_reason: str = ""


class CSSDataNodeMonitor:
    """
    Monitors CSS cluster data nodes and collects metrics for autoscaling decisions.
    Focuses specifically on DATA NODES (type: ess), not client or master nodes.
    """

    def __init__(self):
        self.client = OpenSearch(
            **config.get_opensearch_config(),
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        self._verify_connection()

    def _verify_connection(self):
        """Verify connection to CSS cluster"""
        try:
            info = self.client.info()
            print(f"✅ Connected to CSS cluster: {info.get('cluster_name', 'unknown')}", flush=True)
            print(f"   Version: {info.get('version', {}).get('number', 'unknown')}", flush=True)
        except Exception as e:
            print(f"⚠️  Warning: Could not verify CSS connection: {e}", flush=True)

    def get_cluster_health(self) -> dict:
        """Get cluster health status"""
        try:
            return self.client.cluster.health()
        except Exception as e:
            print(f"❌ Error getting cluster health: {e}", flush=True)
            return {}

    def get_cluster_stats(self) -> dict:
        """Get cluster-level statistics"""
        try:
            return self.client.cluster.stats()
        except Exception as e:
            print(f"❌ Error getting cluster stats: {e}", flush=True)
            return {}

    def get_nodes_stats(self) -> dict:
        """Get statistics for all nodes"""
        try:
            return self.client.nodes.stats()
        except Exception as e:
            print(f"❌ Error getting node stats: {e}", flush=True)
            return {}

    def get_nodes_info(self) -> dict:
        """Get information about all nodes"""
        try:
            return self.client.nodes.info()
        except Exception as e:
            print(f"❌ Error getting node info: {e}", flush=True)
            return {}

    def identify_data_nodes(self) -> List[dict]:
        """
        Identify HOT data nodes in the cluster.
        Solo cuenta data nodes activos (hot), excluye:
        - Master/cluster_manager nodes
        - Cold/frozen data nodes (box_type=cold)
        - Client nodes
        """
        nodes_info = self.get_nodes_info()

        data_nodes = []
        for node_id, node_data in nodes_info.get('nodes', {}).items():
            roles = node_data.get('roles', [])
            attributes = node_data.get('attributes', {})
            box_type = attributes.get('box_type', 'hot')  # Default to hot if not specified

            # Excluir nodos que NO son data nodes hot
            is_cluster_manager = 'cluster_manager' in roles or 'master' in roles
            is_cold = box_type == 'cold' or box_type == 'frozen' or 'cold' in roles
            is_client = 'client' in roles and 'data' not in roles
            is_data = 'data' in roles

            # Solo incluir si es un data node hot (no master, no cold, no client)
            if is_data and not is_cluster_manager and not is_cold and not is_client:
                data_nodes.append({
                    'node_id': node_id,
                    'name': node_data.get('name', 'unknown'),
                    'host': node_data.get('host', 'unknown'),
                    'roles': roles,
                    'ip': node_data.get('ip', 'unknown'),
                    'box_type': box_type
                })

        return data_nodes

    def collect_data_node_metrics(self) -> Optional[DataNodeMetrics]:
        """
        Collect comprehensive metrics from data nodes.
        This is the main method called by the autoscaler.
        """
        try:
            # Get all required data
            cluster_health = self.get_cluster_health()
            nodes_stats = self.get_nodes_stats()
            data_nodes = self.identify_data_nodes()

            if not data_nodes:
                print("⚠️  No data nodes found in cluster", flush=True)
                return None

            # Initialize aggregation variables
            cpu_values = []
            heap_values = []
            disk_values = []
            total_docs = 0
            total_size_bytes = 0
            node_details = []

            # Collect metrics from each data node
            for dn in data_nodes:
                node_id = dn['node_id']
                node_stats = nodes_stats.get('nodes', {}).get(node_id, {})

                if not node_stats:
                    continue

                # CPU usage (process CPU percent)
                process = node_stats.get('process', {})
                cpu_percent = process.get('cpu', {}).get('percent', 0)
                cpu_values.append(cpu_percent)

                # Heap usage
                jvm = node_stats.get('jvm', {})
                heap_used = jvm.get('mem', {}).get('heap_used_in_bytes', 0)
                heap_max = jvm.get('mem', {}).get('heap_max_in_bytes', 1)
                heap_percent = (heap_used / heap_max * 100) if heap_max > 0 else 0
                heap_values.append(heap_percent)

                # Disk usage
                fs = node_stats.get('fs', {})
                total_disk = fs.get('total', {}).get('total_in_bytes', 1)
                available_disk = fs.get('total', {}).get('available_in_bytes', 0)
                used_disk = total_disk - available_disk
                disk_percent = (used_disk / total_disk * 100) if total_disk > 0 else 0
                disk_values.append(disk_percent)

                # Document count
                indices = node_stats.get('indices', {})
                docs = indices.get('docs', {}).get('count', 0)
                total_docs += docs

                # Store size
                store = indices.get('store', {}).get('size_in_bytes', 0)
                total_size_bytes += store

                # Store node details
                node_details.append({
                    'name': dn['name'],
                    'cpu': round(cpu_percent, 1),
                    'heap': round(heap_percent, 1),
                    'disk': round(disk_percent, 1),
                    'docs': docs
                })

            # Calculate averages and maxes
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            max_cpu = max(cpu_values) if cpu_values else 0
            avg_heap = sum(heap_values) / len(heap_values) if heap_values else 0
            max_heap = max(heap_values) if heap_values else 0
            avg_disk = sum(disk_values) / len(disk_values) if disk_values else 0
            max_disk = max(disk_values) if disk_values else 0

            # Convert size to GB
            total_size_gb = total_size_bytes / (1024 ** 3)

            return DataNodeMetrics(
                timestamp=datetime.now().isoformat(),
                total_data_nodes=len(data_nodes),
                cluster_status=cluster_health.get('status', 'unknown'),
                avg_cpu_percent=round(avg_cpu, 1),
                max_cpu_percent=round(max_cpu, 1),
                avg_heap_percent=round(avg_heap, 1),
                max_heap_percent=round(max_heap, 1),
                avg_disk_percent=round(avg_disk, 1),
                max_disk_percent=round(max_disk, 1),
                total_docs=total_docs,
                total_size_gb=round(total_size_gb, 2),
                node_details=node_details
            )

        except Exception as e:
            print(f"❌ Error collecting data node metrics: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return None

    def print_data_node_metrics(self, metrics: DataNodeMetrics):
        """Print data node metrics in a single compact line"""
        import sys
        # Intentar escribir directamente a la terminal
        try:
            tty = open('/dev/tty', 'w')
            output = lambda msg: print(msg, file=tty, flush=True)
        except:
            output = lambda msg: print(msg, flush=True)

        output(f"[{metrics.timestamp[11:19]}] 📊 DataNodes:{metrics.total_data_nodes} | "
               f"Docs:{metrics.total_docs:,} | "
               f"CPU:{metrics.avg_cpu_percent:.0f}%/{metrics.max_cpu_percent:.0f}% | "
               f"Heap:{metrics.avg_heap_percent:.0f}%/{metrics.max_heap_percent:.0f}% | "
               f"Disk:{metrics.avg_disk_percent:.0f}%/{metrics.max_disk_percent:.0f}% | "
               f"Status:{metrics.cluster_status.upper()}")


if __name__ == "__main__":
    # Test the monitor
    print("🚀 Testing CSS Data Node Monitor...", flush=True)

    monitor = CSSDataNodeMonitor()
    metrics = monitor.collect_data_node_metrics()

    if metrics:
        monitor.print_data_node_metrics(metrics)
    else:
        print("❌ Failed to collect metrics", flush=True)
