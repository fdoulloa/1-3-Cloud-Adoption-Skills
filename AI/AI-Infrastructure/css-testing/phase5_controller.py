#!/usr/bin/env python3
"""
Controlador de Fase 5 - Estrategia agresiva para forzar scale out/in.
Monitrea el cluster y ajusta la carga dinámicamente.
"""
import json
import time
import subprocess
import sys
import os
import signal
from datetime import datetime

from config import config

# Lista global de procesos Locust activos para cleanup
active_locust_processes = []
shutdown_requested = False

# Archivos compartidos
AUTOSCALER_METRICS_FILE = '/tmp/css_autoscaler_metrics.json'
STRESS_TEST_METRICS_FILE = '/tmp/css_stress_test_metrics.json'
SCALING_EVENTS_FILE = '/tmp/css_scaling_events.json'

def output(msg):
    """Escribe mensaje a la terminal."""
    print(msg, flush=True)

def handle_shutdown(signum, frame):
    """Manejador de señales para shutdown graceful."""
    global shutdown_requested
    output(f"\n⛔ Señal de apagado recibida (SIGINT/SIGTERM)")
    output("🧹 Terminando procesos Locust activos...")

    # Terminar todos los procesos Locust activos
    for proc in active_locust_processes:
        try:
            if proc.poll() is None:  # Proceso aún corriendo
                proc.terminate()  # SIGTERM primero
                try:
                    proc.wait(timeout=5)  # Esperar hasta 5s
                except subprocess.TimeoutExpired:
                    proc.kill()  # SIGKILL si no termina
                    output(f"   ⚠️ Proceso {proc.pid} terminado forzosamente")
                else:
                    output(f"   ✅ Proceso {proc.pid} terminado gracefully")
        except Exception as e:
            output(f"   ⚠️ Error terminando proceso: {e}")

    # También matar cualquier proceso locust residual
    try:
        subprocess.run(['pkill', '-TERM', '-f', 'locust'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
    except:
        pass

    output("✅ Todos los procesos Locust terminados")
    shutdown_requested = True

def read_autoscaler_metrics():
    """Lee métricas del autoscaler."""
    try:
        with open(AUTOSCALER_METRICS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def write_stress_metrics(users, requests, rps, total):
    """Escribe métricas del stress test."""
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'current_users': users,
            'requests_since_last': requests,
            'rps': rps,
            'total_requests': total
        }
        with open(STRESS_TEST_METRICS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def run_locust_burst(users, duration_sec, csv_prefix, output_dir=None, workers=4):
    """
    Ejecuta un burst de carga con Locust en modo distribuido (master + workers).
    Retorna (total_requests, failures)

    Args:
        users: Número de usuarios concurrentes
        duration_sec: Duración en segundos
        csv_prefix: Prefijo para los archivos de salida
        output_dir: Directorio donde guardar los resultados (opcional)
        workers: Número de workers paralelos (default: 4)
    """
    global shutdown_requested

    # Si ya se solicitó shutdown, no iniciar nuevos procesos
    if shutdown_requested:
        return 0, 0

    # Si hay directorio de salida, usar rutas completas
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        html_file = os.path.join(output_dir, f"{csv_prefix}.html")
        csv_path = os.path.join(output_dir, csv_prefix)
    else:
        html_file = f"{csv_prefix}.html"
        csv_path = csv_prefix

    # Spawn rate agresivo: alcanzar todos los usuarios en 1 segundo máximo
    spawn_rate = max(users, 100)

    # Puerto base para el master (usar puerto aleatorio para evitar conflictos)
    import random
    master_port = random.randint(5557, 5999)

    # Comando para el master
    master_cmd = [
        'locust', '-f', 'locustfile.py',
        '--headless',
        '--master',
        '--master-bind-port', str(master_port),
        '--expect-workers', str(workers),
        '-u', str(users),
        '-r', str(spawn_rate),
        '-t', f'{duration_sec}s',
        '--html', html_file,
        '--csv', csv_path,
    ]

    # Comando para los workers
    worker_cmd = [
        'locust', '-f', 'locustfile.py',
        '--headless',
        '--worker',
        '--master-port', str(master_port),
    ]

    # Iniciar master
    master_proc = subprocess.Popen(master_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    active_locust_processes.append(master_proc)

    # Pequeña pausa para que el master esté listo
    time.sleep(0.5)

    # Iniciar workers
    worker_procs = []
    for _ in range(workers):
        worker_proc = subprocess.Popen(worker_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        worker_procs.append(worker_proc)
        active_locust_processes.append(worker_proc)

    try:
        # Esperar a que termine el master
        master_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        # Terminar todos los workers
        for worker_proc in worker_procs:
            try:
                if worker_proc.poll() is None:
                    worker_proc.terminate()
                    worker_proc.wait(timeout=2)
            except:
                try:
                    worker_proc.kill()
                except:
                    pass

    # Leer estadísticas del CSV
    stats_file = os.path.join(output_dir, f"{csv_prefix}_stats.csv") if output_dir else f"{csv_prefix}_stats.csv"
    total_requests = 0
    failures = 0
    try:
        with open(stats_file, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                parts = lines[-1].strip().split(',')
                if len(parts) >= 3:
                    total_requests = int(parts[2]) if parts[2].isdigit() else 0
                if len(parts) >= 4:
                    failures = int(parts[3]) if parts[3].isdigit() else 0
    except:
        pass

    return total_requests, failures

def check_scaling_event():
    """Verifica si hubo un evento de escalamiento."""
    try:
        with open(SCALING_EVENTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def main(output_dir=None):
    """
    Ejecuta la fase 5 de autoescalamiento.

    Args:
        output_dir: Directorio donde guardar los resultados de Locust (opcional)
    """
    global shutdown_requested

    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    output("="*60)
    output("🎯 FASE 5: AUTOESCALAMIENTO")
    if output_dir:
        output(f"📁 Resultados en: {output_dir}")
    output("="*60)

    total_requests = 0
    last_requests = 0
    current_users = 0
    scale_out_detected = False
    scale_in_detected = False
    phase = "RAMP_UP"  # RAMP_UP -> SCALE_OUT_WAIT -> COOLDOWN -> SCALE_IN_WAIT -> DONE

    iteration = 0
    phase_start_time = time.time()

    # Variables para detectar escalamiento por comparación de data nodes y estado del cluster
    initial_data_nodes = None
    last_data_nodes = None
    initial_cluster_status = None
    last_cluster_status = None
    scale_out_target_nodes = None  # Número objetivo después de scale out
    scale_out_retries = 0  # Contador de reintentos de scale out

    while True:
        # Verificar si se solicitó shutdown
        if shutdown_requested:
            output(f"[{now}] 🛑 Shutdown solicitado, terminando fase 5...")
            break

        # Seguridad: límite máximo de iteraciones
        if iteration > config.phase5_max_total_iterations:
            output(f"[{now}] ⚠️ Límite de iteraciones alcanzado")
            break
        iteration += 1
        now = datetime.now().strftime('%H:%M:%S')

        # Leer métricas del cluster
        metrics = read_autoscaler_metrics()
        scaling_event = check_scaling_event()

        if not metrics:
            output(f"[{now}] ⏳ Esperando métricas...")
            time.sleep(config.phase5_check_interval)
            continue

        # Extraer métricas
        data_nodes = metrics.get('data_nodes', 0)
        avg_cpu = metrics.get('avg_cpu', 0)
        max_cpu = metrics.get('max_cpu', 0)
        avg_heap = metrics.get('avg_heap', 0)
        max_heap = metrics.get('max_heap', 0)
        cluster_status = metrics.get('cluster_status', 'unknown')

        # Función auxiliar para detectar si el estado es de escalamiento
        def is_scaling_state(status):
            """Detecta si el estado indica escalamiento en progreso.
            Maneja estados como 'Processing', 'Processing (Creating)', etc.
            """
            scaling_keywords = ['Processing', 'Scaling', 'Resizing', 'Creating',
                               'Starting', 'Restarting', 'Upgrading', 'Checking', 'Configuring']
            return any(keyword in status for keyword in scaling_keywords)

        # Inicializar conteo de data nodes y estado del cluster si es la primera vez
        if initial_data_nodes is None:
            initial_data_nodes = data_nodes
            last_data_nodes = data_nodes
            initial_cluster_status = cluster_status
            last_cluster_status = cluster_status
            output(f"[{now}] 📊 Data nodes iniciales: {initial_data_nodes}, Estado: {initial_cluster_status}")

        # Calcular requests desde última lectura
        requests_since_last = total_requests - last_requests
        rps = requests_since_last / config.phase5_check_interval if config.phase5_check_interval > 0 else 0
        last_requests = total_requests

        # Mostrar estado compacto con icono según estado del cluster (Huawei Cloud CSS)
        status_icons = {
            # Estados normales
            'Active': '🟢',
            'Available': '🟢',
            # Estados de transición/escalamiento
            'Processing': '🔵',
            'Scaling': '🔵',
            'Resizing': '🔵',
            'Creating': '🔵',
            'Starting': '🔵',
            'Restarting': '🔵',
            'Upgrading': '🔵',
            'Checking': '🔵',
            'Configuring': '🔵',
            # Estados de advertencia
            'Unavailable': '🟡',
            'Stopping': '🟡',
            'Stopped': '🟡',
            'Frozen': '🟡',
            # Estados de error
            'Error': '🔴',
            'Deleting': '🔴',
            'Deleted': '🔴',
            # Desconocido
            'unknown': '⚪',
        }
        # Obtener icono: si el estado contiene "Processing" usar icono de escalamiento
        if is_scaling_state(cluster_status):
            status_icon = '🔵'
        else:
            status_icon = status_icons.get(cluster_status, '⚪')
        output(f"[{now}] 👤 {current_users} users | 📊 {rps:.0f} RPS | 📈 {total_requests:,} total | 🖥️ {data_nodes} nodes | {status_icon} {cluster_status}")

        # Detectar scale out CONFIRMADO: estado volvió a Active Y data_nodes aumentaron
        # Esta detección solo aplica cuando ya estamos en SCALE_OUT_WAIT
        if phase == "SCALE_OUT_WAIT" and not scale_out_detected:
            # Scale out confirmado cuando:
            # 1. Estado del cluster volvió a Active, Y
            # 2. Data nodes aumentaron respecto al inicial
            if cluster_status == 'Active' and data_nodes > initial_data_nodes:
                scale_out_detected = True
                scale_out_target_nodes = data_nodes
                output(f"[{now}] ✅ SCALE OUT confirmado: {initial_data_nodes} → {data_nodes} nodes (estado: {cluster_status})")
                phase = "COOLDOWN"
                phase_start_time = time.time()
            # También detectar por evento explícito
            elif scaling_event and scaling_event.get('type') == 'SCALE_OUT':
                scale_out_detected = True
                scale_out_target_nodes = scaling_event.get('to', data_nodes)
                output(f"[{now}] ✅ SCALE OUT por evento: {scaling_event.get('from')} → {scaling_event.get('to')} nodes")
                phase = "COOLDOWN"
                phase_start_time = time.time()

        # Actualizar último conteo de data nodes y estado del cluster
        last_data_nodes = data_nodes
        last_cluster_status = cluster_status

        # Detectar scale in por evento O por comparación de data nodes
        if not scale_in_detected and scale_out_detected:
            # Método 1: Por evento en archivo
            if scaling_event and scaling_event.get('type') == 'SCALE_IN':
                scale_in_detected = True
                output(f"[{now}] 🔽 SCALE IN: {scaling_event.get('from')} → {scaling_event.get('to')} nodes")
            # Método 2: Por comparación de data nodes
            elif data_nodes < last_data_nodes:
                scale_in_detected = True
                output(f"[{now}] 🔽 SCALE IN: {last_data_nodes} → {data_nodes} nodes")

        # Lógica de fases
        elapsed = time.time() - phase_start_time

        if phase == "RAMP_UP":
            # Incremento agresivo de usuarios - CONTINUAR ESCALANDO
            if current_users < 200:
                current_users = 200  # Carga inicial alta
            elif current_users < 500:
                current_users += 100
            elif current_users < 1000:
                current_users += 200
            else:
                current_users += 300

            # Indicar umbrales alcanzados (solo informativo)
            threshold_status = " 🎯 Umbrales alcanzados" if (max_cpu >= config.scale_out_cpu or max_heap >= config.scale_out_heap) else ""

            # Cambiar a SCALE_OUT_WAIT cuando se detecte escalamiento en progreso
            # (estado Processing o data_nodes cambiando)
            cluster_scaling = False
            if is_scaling_state(cluster_status):
                cluster_scaling = True
                output(f"[{now}] 📊 Escalamiento iniciado: {cluster_status}")
            elif data_nodes != initial_data_nodes:
                cluster_scaling = True
                output(f"[{now}] 📊 Cambio de nodos detectado: {initial_data_nodes} → {data_nodes} nodes")

            if cluster_scaling:
                phase = "SCALE_OUT_WAIT"
                phase_start_time = time.time()

            # Ejecutar burst de carga
            output(f"[{now}] ⬆️ Users: {current_users} (CPU:{max_cpu}% Heap:{max_heap}%){threshold_status}")
            req, _ = run_locust_burst(current_users, config.phase5_check_interval, f"phase5_burst_{iteration}", output_dir, config.phase5_locust_processes)
            total_requests += req
            write_stress_metrics(current_users, req, req/config.phase5_check_interval, total_requests)

        elif phase == "SCALE_OUT_WAIT":
            # MANTENER carga fija esperando scale out real, pero seguir enviando peticiones
            if scale_out_detected:
                output(f"[{now}] ✅ Scale out confirmado")
                phase = "COOLDOWN"
                phase_start_time = time.time()
            elif elapsed > config.phase5_scale_out_target_time:
                # Verificar si ya hubo escalamiento por comparación de data nodes
                if data_nodes > initial_data_nodes:
                    scale_out_detected = True
                    scale_out_target_nodes = data_nodes
                    output(f"[{now}] 🔼 SCALE OUT: {initial_data_nodes} → {data_nodes} nodes")
                    phase = "COOLDOWN"
                    phase_start_time = time.time()
                else:
                    scale_out_retries += 1
                    if scale_out_retries > config.phase5_max_scale_out_retries:
                        output(f"[{now}] ⚠️ Max reintentos, asumiendo scale out")
                        scale_out_detected = True
                        phase = "COOLDOWN"
                        phase_start_time = time.time()
                    else:
                        # Timeout alcanzado - escalar carga más para forzar scale out
                        output(f"[{now}] ⬆️ Escalando carga (retry {scale_out_retries}/{config.phase5_max_scale_out_retries})")
                        if current_users < 500:
                            current_users += 100
                        elif current_users < 1000:
                            current_users += 200
                        else:
                            current_users += 300
                        # Reset timer para dar más tiempo
                        phase_start_time = time.time()

            # Mantener carga fija, seguir enviando peticiones
            output(f"[{now}] ⏳ Esperando scale out | Users: {current_users} (CPU:{max_cpu}% Heap:{max_heap}%)")
            req, _ = run_locust_burst(current_users, config.phase5_check_interval, f"phase5_burst_{iteration}", output_dir, config.phase5_locust_processes)
            total_requests += req
            write_stress_metrics(current_users, req, req/config.phase5_check_interval, total_requests)

        elif phase == "COOLDOWN":
            # Período de cooldown después de scale out
            if elapsed > config.phase5_cooldown_time:
                output(f"[{now}] ⬇️ Iniciando reducción de carga")
                phase = "SCALE_IN_WAIT"
                phase_start_time = time.time()
            else:
                # Mantener carga media durante cooldown
                current_users = max(50, current_users // 2)
                output(f"[{now}] ⏳ Cooldown: {int(elapsed)}s/{config.phase5_cooldown_time}s")
                req, _ = run_locust_burst(current_users, config.phase5_check_interval, f"phase5_burst_{iteration}", output_dir, config.phase5_locust_processes)
                total_requests += req
                write_stress_metrics(current_users, req, req/config.phase5_check_interval, total_requests)

        elif phase == "SCALE_IN_WAIT":
            # Reducir carga para forzar scale in
            if scale_in_detected:
                output(f"[{now}] ✅ Scale in confirmado")
                phase = "DONE"
            elif elapsed > config.phase5_scale_in_target_time:
                output(f"[{now}] ⚠️ Scale in no detectado")
                phase = "DONE"
            else:
                # Reducir usuarios gradualmente
                if max_cpu > config.scale_in_cpu + 10 or max_heap > config.scale_in_heap + 10:
                    # Aún hay carga, reducir más
                    current_users = max(5, current_users - 20)
                else:
                    # Carga ya baja, mantener mínima
                    current_users = max(5, current_users // 2)

                output(f"[{now}] ⬇️ Users: {current_users}")
                req, _ = run_locust_burst(current_users, config.phase5_check_interval, f"phase5_burst_{iteration}", output_dir, config.phase5_locust_processes)
                total_requests += req
                write_stress_metrics(current_users, req, req/config.phase5_check_interval, total_requests)

        elif phase == "DONE":
            output(f"[{now}] ✅ Fase 5 completada")
            break

        time.sleep(1)  # Pequeña pausa entre iteraciones

if __name__ == "__main__":
    # Permitir pasar directorio de salida como argumento
    output_dir = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        main(output_dir)
        output("\n✅ Fase 5 completada exitosamente")
        sys.exit(0)
    except KeyboardInterrupt:
        output("\n⛔ Interrupción detectada, ejecutando cleanup...")
        handle_shutdown(None, None)
        sys.exit(0)  # Exit code 0 para que el script principal continúe
