#!/usr/bin/env python3
"""
CSS Autoscaling Monitor - Monitors cluster metrics during load tests.
All configuration loaded from .env via config module.
"""
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import urllib3
urllib3.disable_warnings()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import signal
import sys
import json
from datetime import datetime
import pandas as pd

# Load configuration from .env
from config import config

# Archivo compartido para métricas del autoscaler
AUTOSCALER_METRICS_FILE = '/tmp/css_autoscaler_metrics.json'
SCALING_EVENTS_FILE = '/tmp/css_scaling_events.json'

# Global flag for graceful shutdown
running = True

def create_session_with_retries(total_retries=5, backoff_factor=1.0):
    """
    Create a requests session with retry strategy for SSL/connection errors.

    Args:
        total_retries: Maximum number of retries
        backoff_factor: Wait backoff_factor * (2 ** (retry - 1)) seconds between retries

    Returns:
        requests.Session with retry adapter mounted
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "POST", "DELETE"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

# Global session with retries
_session = None


def get_session():
    """Get or create the global session with retries"""
    global _session
    if _session is None:
        _session = create_session_with_retries(total_retries=5, backoff_factor=1.0)
    return _session


def get_cluster_health_status():
    """Obtiene el estado real del cluster desde Huawei Cloud CSS API.

    Verifica tanto el estado del cluster como el estado de las instancias individuales.
    Si alguna instancia está en proceso de escalamiento, retorna 'Processing'.
    """
    try:
        from huawei_css_api import HuaweiCSSDataNodeAPI
        api = HuaweiCSSDataNodeAPI()

        # Obtener info completa del cluster
        info = api.get_cluster_info()
        cluster_status = info.get('status', 'unknown')
        instances = info.get('instances', [])

        # Mapear códigos de estado a nombres descriptivos
        status_map = {
            '200': 'Active',
            '303': 'Processing',
            '400': 'Error',
            '500': 'Error',
            '100': 'Creating',
            '102': 'Starting',
            '103': 'Available',
            '104': 'Unavailable',
            '105': 'Stopping',
            '106': 'Stopped',
            '107': 'Deleting',
            '108': 'Deleted',
            '109': 'Scaling',
            '110': 'Resizing',
            '111': 'Restarting',
            '112': 'Upgrading',
            '113': 'Rollback',
            '114': 'Patch',
            '115': 'Checking',
            '116': 'Frozen',
            '117': 'Restoring',
            '118': 'Backup',
            '119': 'Configuring',
            '120': 'Download',
            '121': 'Upload',
            '122': 'Log',
            '123': 'Monitor',
            '124': 'Alarm',
            '125': 'Template',
            '126': 'Policy',
            '127': 'Rule',
            '128': 'Action',
            '129': 'Task',
            '130': 'Job',
        }

        # Estados que indican procesamiento/escalamiento
        processing_states = ['100', '102', '109', '110', '111', '112', '115', '119']

        # Verificar si alguna instancia (especialmente data nodes) está en proceso
        for instance in instances:
            inst_status = instance.get('status', '')
            inst_type = instance.get('type', '')
            # Solo verificar data nodes (ess)
            if inst_type == 'ess' and inst_status in processing_states:
                return f"Processing ({status_map.get(inst_status, inst_status)})"

        # Si no hay instancias en proceso, retornar estado del cluster
        return status_map.get(cluster_status, f'Status_{cluster_status}')
    except Exception as e:
        return 'unknown'


def write_autoscaler_metrics(metrics):
    """Escribe métricas del autoscaler a archivo compartido para monitoreo en tiempo real."""
    try:
        # Obtener estado real del cluster
        cluster_status = get_cluster_health_status()

        data = {
            'timestamp': metrics.get('timestamp', datetime.now().isoformat()),
            'data_nodes': metrics.get('data_node_count', 0),
            'avg_cpu': metrics.get('avg_cpu_percent', 0),
            'max_cpu': metrics.get('max_cpu_percent', 0),
            'avg_heap': metrics.get('avg_heap_percent', 0),
            'max_heap': metrics.get('max_heap_percent', 0),
            'avg_disk': 0,
            'max_disk': 0,
            'cluster_status': cluster_status
        }
        with open(AUTOSCALER_METRICS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"⚠️ Error escribiendo métricas: {e}", flush=True)


def write_scaling_event(event_type, nodes_from, nodes_to):
    """Escribe evento de escalamiento a archivo compartido."""
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'from': nodes_from,
            'to': nodes_to
        }
        with open(SCALING_EVENTS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\n🛑 Recibida señal de terminación. Finalizando monitor...", flush=True)
    running = False


def interruptible_sleep(seconds):
    """Sleep que puede ser interrumpido verificando la variable global 'running'."""
    global running
    end_time = time.time() + seconds
    while running and time.time() < end_time:
        time.sleep(min(0.5, end_time - time.time()))


def get_cluster_metrics(max_retries=5, retry_delay=2.0):
    """
    Collect comprehensive cluster performance metrics (DATA NODES ONLY)

    Args:
        max_retries: Maximum number of retry attempts for connection errors
        retry_delay: Base delay between retries (exponential backoff applied)

    Returns:
        dict with cluster metrics or None if all retries fail
    """
    global running
    base_url = config.css_full_url
    auth = (config.css_username, config.css_password)
    session = get_session()

    last_error = None
    for attempt in range(max_retries):
        if not running:
            return None  # Terminación solicitada

        try:
            nodes_response = session.get(
                f"{base_url}/_nodes/stats",
                auth=auth,
                verify=False,
                timeout=(10, 30)  # (connect timeout, read timeout)
            )
            nodes_response.raise_for_status()
            nodes_stats = nodes_response.json()
            break  # Success, exit retry loop

        except requests.exceptions.SSLError as e:
            last_error = f"SSL Error (attempt {attempt + 1}/{max_retries}): {e}"
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️  {last_error}, retrying in {wait_time:.1f}s...", flush=True)
                interruptible_sleep(wait_time)
            continue

        except requests.exceptions.ConnectionError as e:
            last_error = f"Connection Error (attempt {attempt + 1}/{max_retries}): {e}"
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️  {last_error}, retrying in {wait_time:.1f}s...", flush=True)
                interruptible_sleep(wait_time)
            continue

        except requests.exceptions.Timeout as e:
            last_error = f"Timeout Error (attempt {attempt + 1}/{max_retries}): {e}"
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️  {last_error}, retrying in {wait_time:.1f}s...", flush=True)
                interruptible_sleep(wait_time)
            continue

        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP Error (attempt {attempt + 1}/{max_retries}): {e}"
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"⚠️  {last_error}, retrying in {wait_time:.1f}s...", flush=True)
                interruptible_sleep(wait_time)
            continue

    else:
        # All retries exhausted
        print(f"❌ Error retrieving cluster metrics after {max_retries} attempts: {last_error}", flush=True)
        return None

    try:

        # Filter only HOT DATA nodes (exclude cold/warm/frozen data nodes)
        # In OpenSearch/CSS: data nodes can have specific roles:
        # - data_hot: stores recent/time-series data (HOT)
        # - data_cold: stores old/rarely accessed data (COLD)
        # - data_warm: stores moderately recent data (WARM)
        # - data_frozen: stores very old data (FROZEN)
        # - data: generic data node (treated as hot by default)
        #
        # Some clusters don't use explicit data_hot/data_cold roles but name nodes
        # with patterns like: "css-test-ess-cold-esn-1-1" for cold nodes
        data_nodes = {}
        for node_id, node_data in nodes_stats['nodes'].items():
            roles = node_data.get('roles', [])
            node_name = node_data.get('name', '').lower()

            # Skip cluster_manager/master nodes
            is_cluster_manager = 'cluster_manager' in roles or 'master' in roles
            if is_cluster_manager:
                continue

            # Check for specific data tier roles
            is_data_hot = 'data_hot' in roles
            is_data_cold = 'data_cold' in roles
            is_data_warm = 'data_warm' in roles
            is_data_frozen = 'data_frozen' in roles
            is_generic_data = 'data' in roles

            # Also check node name for cold/warm/frozen indicators
            # (for clusters that don't use explicit tier roles)
            is_cold_by_name = 'cold' in node_name
            is_warm_by_name = 'warm' in node_name
            is_frozen_by_name = 'frozen' in node_name

            # Combine role-based and name-based detection
            is_cold = is_data_cold or is_cold_by_name
            is_warm = is_data_warm or is_warm_by_name
            is_frozen = is_data_frozen or is_frozen_by_name

            # Include node if:
            # 1. It has explicit 'data_hot' role, OR
            # 2. It has generic 'data' role but is NOT cold/warm/frozen (by role or name)
            if is_data_hot or (is_generic_data and not is_cold and not is_warm and not is_frozen):
                data_nodes[node_id] = node_data

        # If no hot data nodes found with roles, try alternative detection
        if not data_nodes:
            for node_id, node_data in nodes_stats['nodes'].items():
                roles = node_data.get('roles', [])
                node_name = node_data.get('name', '').lower()
                # Alternative: nodes that are NOT cluster_manager and NOT cold data
                is_cluster_manager = 'cluster_manager' in roles or 'master' in roles
                is_data_cold = 'data_cold' in roles or 'cold' in node_name
                if not is_cluster_manager and not is_data_cold:
                    data_nodes[node_id] = node_data

        data_node_count = len(data_nodes)

        # Calculate per-data-node resource utilization
        cpu_percentages = []
        heap_usage_gb = []
        total_docs = 0
        total_store_bytes = 0

        for node_id, node_data in data_nodes.items():
            cpu_percentages.append(node_data['os']['cpu']['percent'])
            heap_usage_gb.append(node_data['jvm']['mem']['heap_used_in_bytes'] / (1024**3))
            # Get docs and store from indices if available
            if 'indices' in node_data:
                total_docs += node_data['indices'].get('docs', {}).get('count', 0)
                total_store_bytes += node_data['indices'].get('store', {}).get('size_in_bytes', 0)

        store_size_gb = total_store_bytes / (1024**3)

        return {
            'timestamp': datetime.now().isoformat(),
            'data_node_count': data_node_count,
            'total_documents': total_docs,
            'store_size_gb': store_size_gb,
            'avg_cpu_percent': sum(cpu_percentages) / len(cpu_percentages) if cpu_percentages else 0,
            'max_cpu_percent': max(cpu_percentages) if cpu_percentages else 0,
            'avg_heap_gb': sum(heap_usage_gb) / len(heap_usage_gb) if heap_usage_gb else 0,
            'max_heap_gb': max(heap_usage_gb) if heap_usage_gb else 0
        }
    except Exception as e:
        print(f"Error retrieving cluster metrics: {e}", flush=True)
        return None


def stabilize_load():
    """
    Señalizar que se debe estabilizar la carga de pruebas.
    Escribe a un archivo de control que Locust u otros componentes pueden leer.
    """
    stabilize_file = '/tmp/css_stabilize_load.txt'
    try:
        with open(stabilize_file, 'w') as f:
            f.write(f"STABILIZE:{datetime.now().isoformat()}\n")
    except:
        pass


def monitor_cluster(interval_seconds=10):
    """Monitor cluster metrics until shutdown signal is received"""
    global running

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"{'='*60}", flush=True)
    print("CSS HOT DATA NODES AUTOSCALING MONITOR", flush=True)
    print("(Excludes cold/warm/frozen data nodes)", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Configuration:", flush=True)
    print(f"   CSS Host: {config.css_host}:{config.css_port}", flush=True)
    print(f"   Interval: {interval_seconds} seconds", flush=True)
    print(f"   Running until shutdown signal (Ctrl+C)", flush=True)
    print(f"{'='*60}", flush=True)
    print("Execute load tests in parallel to observe autoscaling behavior", flush=True)

    metrics_history = []
    last_total_requests = 0
    initial_node_count = None  # Track initial node count
    autoscaling_detected = False  # Flag for autoscaling detection
    autoscaling_notified = False  # Flag to avoid repeated notifications

    # Try to read requests from shared file
    requests_file = '/tmp/css_benchmark_requests.txt'

    while running:
        metrics = get_cluster_metrics()
        if metrics:
            # Initialize initial node count on first measurement
            if initial_node_count is None:
                initial_node_count = metrics['data_node_count']
                print(f"\n📌 Número inicial de HOT data nodes: {initial_node_count}", flush=True)

            # REAL-TIME AUTOSCALING DETECTION
            current_node_count = metrics['data_node_count']
            if current_node_count != initial_node_count and not autoscaling_detected:
                autoscaling_detected = True
                autoscaling_notified = True

                # Determine scaling direction
                if current_node_count > initial_node_count:
                    scaling_type = "SCALE_OUT"
                    scaling_symbol = "🔼"
                else:
                    scaling_type = "SCALE_IN"
                    scaling_symbol = "🔽"

                # Escribir evento de escalamiento para el controller
                write_scaling_event(scaling_type, initial_node_count, current_node_count)

                # PROMINENT NOTIFICATION
                print(f"\n", flush=True)
                print(f"{'!'*60}", flush=True)
                print(f"🚨🚨🚨 AUTOSCALING DETECTADO EN TIEMPO REAL 🚨🚨🚨", flush=True)
                print(f"{'!'*60}", flush=True)
                print(f"   {scaling_symbol} Tipo: {scaling_type}", flush=True)
                print(f"   📊 Hot Data Nodes: {initial_node_count} → {current_node_count}", flush=True)
                print(f"   ⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                print(f"{'!'*60}", flush=True)
                print(f"", flush=True)

                # Signal load stabilization
                stabilize_load()

            # Read current requests count from shared file
            current_requests = 0
            try:
                with open(requests_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        current_requests = int(content)
            except:
                pass

            # Calculate requests since last check
            requests_since_last = current_requests - last_total_requests
            requests_per_sec = requests_since_last / interval_seconds if interval_seconds > 0 else 0
            last_total_requests = current_requests

            metrics['total_requests'] = current_requests
            metrics['requests_since_last'] = requests_since_last
            metrics['requests_per_sec'] = requests_per_sec
            metrics['autoscaling_detected'] = autoscaling_detected

            # Escribir métricas a archivo compartido para el controller
            write_autoscaler_metrics(metrics)

            metrics_history.append(metrics)

            # Status indicator shows if autoscaling was detected
            status_indicator = "🔄" if autoscaling_detected else "📊"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"{status_indicator} Hot Data Nodes: {metrics['data_node_count']} | "
                  f"CPU: {metrics['avg_cpu_percent']:.1f}% (max: {metrics['max_cpu_percent']:.1f}%) | "
                  f"Heap: {metrics['avg_heap_gb']:.1f}GB", flush=True)

        # Sleep interrumpible
        interruptible_sleep(interval_seconds)

    # Save monitoring data
    if metrics_history:
        df = pd.DataFrame(metrics_history)
        df.to_csv('autoscaling_monitor.csv', index=False)
        print(f"\n📊 Monitoring data saved to: autoscaling_monitor.csv", flush=True)

        # Detect autoscaling events
        initial_nodes = metrics_history[0]['data_node_count']
        final_nodes = metrics_history[-1]['data_node_count']

        # Verificar si hubo escalamiento durante la ejecución (no solo al final)
        autoscaling_happened = any(m.get('autoscaling_detected', False) for m in metrics_history)

        if autoscaling_happened:
            print(f"🔄 Autoscaling detectado durante la prueba", flush=True)
            if final_nodes != initial_nodes:
                print(f"   Resultado final: {initial_nodes} → {final_nodes} hot data nodes", flush=True)
            else:
                print(f"   Hot data nodes regresaron al valor inicial: {initial_nodes}", flush=True)
        elif final_nodes != initial_nodes:
            print(f"🔄 Autoscaling confirmado: {initial_nodes} → {final_nodes} hot data nodes", flush=True)
        else:
            print(f"ℹ️  No autoscaling detectado (hot data nodes remained at {initial_nodes})", flush=True)

    return metrics_history


if __name__ == "__main__":
    print("Configuration loaded from .env:", flush=True)
    print(f"   CSS Host: {config.css_host}:{config.css_port}", flush=True)
    print(flush=True)

    # Run until shutdown signal
    monitor_cluster(interval_seconds=10)
