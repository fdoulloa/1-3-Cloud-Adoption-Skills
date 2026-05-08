#!/usr/bin/env python3
"""
Wrapper para stress test con Locust - Reporta métricas cada 10 segundos.
"""
import json
import time
import os
import subprocess
import signal
import sys
from datetime import datetime

# Archivo compartido para métricas
STRESS_TEST_METRICS_FILE = '/tmp/css_stress_test_metrics.json'

# Variables globales
running = True
current_users = 0
spawn_rate = 0
duration = 0
start_time = None

def signal_handler(signum, frame):
    """Maneja señales de terminación."""
    global running
    running = False

def write_stress_metrics(requests_since_last=0, rps=0.0, total_requests=0):
    """Escribe métricas del stress test a archivo compartido."""
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'current_users': current_users,
            'spawn_rate': spawn_rate,
            'duration': duration,
            'requests_since_last': requests_since_last,
            'rps': rps,
            'total_requests': total_requests
        }
        with open(STRESS_TEST_METRICS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def monitor_locust_stats(csv_prefix, interval=10, output_dir=None):
    """
    Monitorea el archivo CSV de estadísticas de Locust y reporta métricas.
    Se ejecuta en un thread separado mientras Locust corre.
    """
    stats_file = os.path.join(output_dir, f"{csv_prefix}_stats.csv") if output_dir else f"{csv_prefix}_stats.csv"
    last_total = 0

    while running:
        try:
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        # La última línea tiene las estadísticas agregadas
                        last_line = lines[-1].strip()
                        if last_line:
                            parts = last_line.split(',')
                            if len(parts) >= 3:
                                total_requests = int(parts[2]) if parts[2].isdigit() else 0
                                requests_since_last = total_requests - last_total
                                rps = requests_since_last / interval if interval > 0 else 0

                                write_stress_metrics(
                                    requests_since_last=requests_since_last,
                                    rps=rps,
                                    total_requests=total_requests
                                )

                                last_total = total_requests
        except:
            pass

        time.sleep(interval)

def run_locust(users, spawn, duration_sec, csv_prefix, html_file, output_dir=None):
    """
    Ejecuta Locust y monitorea estadísticas en paralelo.

    Args:
        users: Número de usuarios concurrentes
        spawn: Tasa de spawn de usuarios
        duration_sec: Duración en segundos
        csv_prefix: Prefijo para archivos CSV
        html_file: Nombre del archivo HTML
        output_dir: Directorio donde guardar los resultados (opcional)
    """
    global current_users, spawn_rate, duration, running

    current_users = users
    spawn_rate = spawn
    duration = duration_sec

    # Escribir métricas iniciales
    write_stress_metrics(requests_since_last=0, rps=0.0, total_requests=0)

    # Determinar rutas de salida
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        html_path = os.path.join(output_dir, html_file)
        csv_path = os.path.join(output_dir, csv_prefix)
        stats_file = os.path.join(output_dir, f"{csv_prefix}_stats.csv")
    else:
        html_path = html_file
        csv_path = csv_prefix
        stats_file = f"{csv_prefix}_stats.csv"

    # Iniciar Locust
    cmd = [
        'locust', '-f', 'locustfile.py',
        '--headless',
        '-u', str(users),
        '-r', str(spawn),
        '-t', f'{duration_sec}s',
        '--html', html_path,
        '--csv', csv_path
    ]

    print(f"🚀 Iniciando Locust: {users} usuarios, {spawn}/s spawn, {duration_sec}s", flush=True)

    # Iniciar proceso Locust (salida visible en consola)
    proc = subprocess.Popen(cmd, stdout=None, stderr=None)

    # Monitorear estadísticas mientras Locust corre
    last_total = 0
    check_interval = 10
    elapsed = 0

    while proc.poll() is None and elapsed < duration_sec:
        time.sleep(check_interval)
        elapsed += check_interval

        try:
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:
                        last_line = lines[-1].strip()
                        if last_line:
                            parts = last_line.split(',')
                            if len(parts) >= 3:
                                total_requests = int(parts[2]) if parts[2].isdigit() else 0
                                requests_since_last = total_requests - last_total
                                rps = requests_since_last / check_interval if check_interval > 0 else 0

                                write_stress_metrics(
                                    requests_since_last=requests_since_last,
                                    rps=rps,
                                    total_requests=total_requests
                                )

                                last_total = total_requests
        except:
            pass

    # Esperar a que termine Locust
    proc.wait()

    # Leer estadísticas finales
    total_requests = 0
    failures = 0
    try:
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1].strip()
                    if last_line:
                        parts = last_line.split(',')
                        if len(parts) >= 3:
                            total_requests = int(parts[2]) if parts[2].isdigit() else 0
                        if len(parts) >= 4:
                            failures = int(parts[3]) if parts[3].isdigit() else 0
    except:
        pass

    return total_requests, failures

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Uso: stress_test_wrapper.py <users> <spawn_rate> <duration_sec> <csv_prefix> <html_file> [output_dir]")
        sys.exit(1)

    users = int(sys.argv[1])
    spawn = int(sys.argv[2])
    duration_sec = int(sys.argv[3])
    csv_prefix = sys.argv[4]
    html_file = sys.argv[5]
    output_dir = sys.argv[6] if len(sys.argv) > 6 else None

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    total, failures = run_locust(users, spawn, duration_sec, csv_prefix, html_file, output_dir)

    # Imprimir resultado para que el script principal lo capture
    print(f"RESULT: {total},{failures}", flush=True)
