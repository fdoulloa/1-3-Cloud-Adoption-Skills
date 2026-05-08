#!/usr/bin/env python3
"""
Monitor para Fase 5 - Muestra estadísticas del autoscaler y stress test cada 10 segundos.
"""
import json
import time
import os
import sys
from datetime import datetime

# Archivos compartidos
AUTOSCALER_METRICS_FILE = '/tmp/css_autoscaler_metrics.json'
STRESS_TEST_METRICS_FILE = '/tmp/css_stress_test_metrics.json'
SCALING_EVENTS_FILE = '/tmp/css_scaling_events.json'

# Estado anterior para detectar cambios
last_data_nodes = None
last_scale_event = None

# Intentar abrir la terminal directamente para output visible
try:
    TTY = open('/dev/tty', 'w')
except:
    TTY = sys.stdout

def output(msg):
    """Escribe mensaje a la terminal."""
    print(msg, file=TTY, flush=True)

def read_autoscaler_metrics():
    """Lee métricas del autoscaler."""
    try:
        with open(AUTOSCALER_METRICS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def read_stress_metrics():
    """Lee métricas del stress test."""
    try:
        with open(STRESS_TEST_METRICS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def read_scaling_events():
    """Lee eventos de escalamiento."""
    try:
        with open(SCALING_EVENTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def print_stats():
    """Imprime estadísticas de ambos componentes."""
    global last_data_nodes, last_scale_event

    autoscaler = read_autoscaler_metrics()
    stress = read_stress_metrics()
    scaling_events = read_scaling_events()

    timestamp = datetime.now().strftime('%H:%M:%S')

    # Detectar evento de escalamiento
    if scaling_events and scaling_events != last_scale_event:
        last_scale_event = scaling_events
        event_type = scaling_events.get('type', '')
        reason = scaling_events.get('reason', '')
        nodes_from = scaling_events.get('from', '')
        nodes_to = scaling_events.get('to', '')
        if event_type:
            symbol = "🔼" if event_type == "SCALE_OUT" else "🔽"
            output(f"[{timestamp}] 🚨 {symbol} {event_type}: {nodes_from} → {nodes_to} data nodes | {reason}")

    # Detectar cambio en número de data nodes
    if autoscaler:
        current_nodes = autoscaler.get('data_nodes', 0)
        if last_data_nodes is not None and current_nodes != last_data_nodes:
            symbol = "🔼" if current_nodes > last_data_nodes else "🔽"
            output(f"[{timestamp}] {symbol} Data nodes cambiaron: {last_data_nodes} → {current_nodes}")
        last_data_nodes = current_nodes

    # Línea para autoscaler (compacta)
    if autoscaler:
        output(f"[{timestamp}] 🔧 Data Nodes:{autoscaler.get('data_nodes', 'N/A')} | "
               f"CPU:{autoscaler.get('avg_cpu', 0):.0f}%/{autoscaler.get('max_cpu', 0):.0f}% | "
               f"Heap:{autoscaler.get('avg_heap', 0):.0f}%/{autoscaler.get('max_heap', 0):.0f}% | "
               f"Disk:{autoscaler.get('avg_disk', 0):.0f}%/{autoscaler.get('max_disk', 0):.0f}%")
    else:
        output(f"[{timestamp}] 🔧 Autoscaler: esperando datos...")

    # Línea para stress test (compacta)
    if stress:
        output(f"[{timestamp}] 🔥 Users:{stress.get('current_users', 'N/A')} | "
               f"Reqs:{stress.get('requests_since_last', 0):,} | "
               f"RPS:{stress.get('rps', 0):.1f}/s | "
               f"Total:{stress.get('total_requests', 0):,}")
    else:
        output(f"[{timestamp}] 🔥 Stress: esperando datos...")

def main():
    """Loop principal del monitor."""
    try:
        while True:
            print_stats()
            time.sleep(10)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
