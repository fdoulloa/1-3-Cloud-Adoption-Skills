# file: data_node_autoscaler.py
#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import urllib3
urllib3.disable_warnings()

import time
import signal
import sys
from datetime import datetime
import pandas as pd

from config import config
from css_monitor import CSSDataNodeMonitor
from huawei_css_api import HuaweiCSSDataNodeAPI
from scaling_engine import DataNodeScalingEngine, ScalingAction

# Archivos compartidos para métricas y eventos
AUTOSCALER_METRICS_FILE = '/tmp/css_autoscaler_metrics.json'
SCALING_EVENTS_FILE = '/tmp/css_scaling_events.json'

def write_autoscaler_metrics(metrics):
    """
    Escribe métricas del autoscaler a archivo compartido para monitoreo en tiempo real.
    """
    import json
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'data_nodes': metrics.total_data_nodes,
            'avg_cpu': metrics.avg_cpu_percent,
            'max_cpu': metrics.max_cpu_percent,
            'avg_heap': metrics.avg_heap_percent,
            'max_heap': metrics.max_heap_percent,
            'avg_disk': metrics.avg_disk_percent,
            'max_disk': metrics.max_disk_percent,
            'cluster_status': metrics.cluster_status
        }
        with open(AUTOSCALER_METRICS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

def write_scaling_event(event_type, nodes_from, nodes_to, reason):
    """
    Escribe evento de escalamiento a archivo compartido.
    """
    import json
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'from': nodes_from,
            'to': nodes_to,
            'reason': reason
        }
        with open(SCALING_EVENTS_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass


class CSSDataNodeAutoscaler:
    """
    ORQUESTADOR PRINCIPAL DEL AUTOESCALAMIENTO DE DATA NODES

    Basado en: robin-tech-blog.vercel.app/posts/css-ces-autoscaling-end-to-end
    MODIFICACIÓN CLAVE: Escala DATA NODES (ess) en lugar de CLIENT NODES (ess-client)

    Funcionalidad:
    1. Monitorea métricas de data nodes cada 30s
    2. Aplica lógica de decisión con cooldowns
    3. Ejecuta escalamiento via API de Huawei Cloud
    4. Genera reportes de actividad
    """

    def __init__(self):
        self.monitor = CSSDataNodeMonitor()
        self.api = HuaweiCSSDataNodeAPI()
        self.engine = DataNodeScalingEngine()

        self.running = False
        self.start_time = datetime.now()
        self.metrics_log = []

        # Manejar señales de sistema
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Apagado graceful del autoscaler"""
        print(f"\n\n⛔ Señal de apagado recibida", flush=True)
        self.running = False
        self._generate_final_report()
        print(f"👋 Autoscaler detenido correctamente", flush=True)
        sys.exit(0)
    
    def validate_configuration(self) -> bool:
        """Validar configuración antes de iniciar"""
        print("🔍 Validando configuración del autoscaler...", flush=True)

        errors = []

        # Validar configuración CSS
        if not config.css_host:
            errors.append("CSS_HOST no configurado")
        if not config.css_cluster_id:
            errors.append("CSS_CLUSTER_ID no configurado")

        # Validar credenciales Huawei Cloud
        if not config.hw_access_key:
            errors.append("HW_ACCESS_KEY no configurado")
        if not config.hw_secret_key:
            errors.append("HW_SECRET_KEY no configurado")
        if not config.hw_project_id:
            errors.append("HW_PROJECT_ID no configurado")

        # Validar límites lógicos
        if config.min_data_nodes < 1:
            errors.append("MIN_DATA_NODES debe ser >= 1")
        if config.max_data_nodes <= config.min_data_nodes:
            errors.append("MAX_DATA_NODES debe ser > MIN_DATA_NODES")

        if errors:
            print("❌ Errores de configuración encontrados:", flush=True)
            for error in errors:
                print(f"   • {error}", flush=True)
            return False

        print("✅ Configuración válida", flush=True)
        return True
    
    def print_startup_banner(self):
        """Banner informativo al iniciar"""
        print(f"\n{'='*75}", flush=True)
        print(f"  🚀 CSS DATA NODE HORIZONTAL AUTOSCALER", flush=True)
        print(f"  Modificación del CSS CES Autoscaling Test Harness", flush=True)
        print(f"  CAMBIO CLAVE: Escala DATA NODES (ess) no CLIENT NODES", flush=True)
        print(f"{'='*75}", flush=True)
        print(f"  CSS Cluster:    {config.css_host}:{config.css_port}", flush=True)
        print(f"  Cluster ID:     {config.css_cluster_id}", flush=True)
        print(f"  Huawei Region:  {config.hw_region}", flush=True)
        print(f"{'─'*75}", flush=True)
        print(f"  UMBRALES DE ESCALAMIENTO:", flush=True)
        print(f"    Scale OUT (agregar data nodes):", flush=True)
        print(f"      CPU  >= {config.scale_out_cpu}% | "
              f"Heap >= {config.scale_out_heap}% | "
              f"Disk >= {config.scale_out_disk}%", flush=True)
        print(f"    Scale IN (remover data nodes):", flush=True)
        print(f"      CPU  <= {config.scale_in_cpu}% & "
              f"Heap <= {config.scale_in_heap}% & "
              f"Disk <= {config.scale_in_disk}%", flush=True)
        print(f"{'─'*75}", flush=True)
        print(f"  LÍMITES DE DATA NODES:", flush=True)
        print(f"    Mínimo: {config.min_data_nodes} | "
              f"Máximo: {config.max_data_nodes}", flush=True)
        print(f"  COOLDOWNS:", flush=True)
        print(f"    Scale Out: {config.scale_out_cooldown}s | "
              f"Scale In: {config.scale_in_cooldown}s", flush=True)
        print(f"  INTERVALO: {config.monitor_interval}s", flush=True)
        print(f"{'─'*75}", flush=True)
        print(f"  Iniciado: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"  Presiona Ctrl+C para detener gracefully", flush=True)
        print(f"{'='*75}\n", flush=True)
    
    def execute_scaling_operation(self, decision) -> bool:
        """
        Ejecutar la operación de escalamiento via API de Huawei Cloud.
        CLAVE: Solo opera sobre DATA NODES (type: ess).
        """
        if decision.action == ScalingAction.SCALE_OUT:
            nodes_to_add = decision.target_data_nodes - decision.current_data_nodes
            success = self.api.scale_out_data_nodes(nodes_to_add)
            
        elif decision.action == ScalingAction.SCALE_IN:
            nodes_to_remove = decision.current_data_nodes - decision.target_data_nodes
            success = self.api.scale_in_data_nodes(nodes_to_remove)
            
        else:
            return True  # No action needed
        
        if success:
            print(f"\n⏳ Esperando completar escalamiento de data nodes...", flush=True)

            # Esperar a que la operación se complete
            scaling_completed = self.api.wait_for_scaling_completion(timeout_seconds=600)

            if scaling_completed:
                print(f"✅ Escalamiento de data nodes completado exitosamente", flush=True)
                print(f"   Data nodes: {decision.current_data_nodes} → {decision.target_data_nodes}", flush=True)

                # Pausa adicional para estabilización
                stabilization_time = 60
                print(f"   Esperando estabilización ({stabilization_time}s)...", flush=True)
                time.sleep(stabilization_time)
            else:
                print(f"⚠️  Timeout esperando escalamiento, pero operación puede continuar", flush=True)
        
        return success
    
    def _log_metrics(self, metrics, decision):
        """Registrar métricas para reporte final"""
        self.metrics_log.append({
            'timestamp': metrics.timestamp,
            'data_nodes': metrics.total_data_nodes,
            'cluster_status': metrics.cluster_status,
            'avg_cpu': metrics.avg_cpu_percent,
            'max_cpu': metrics.max_cpu_percent,
            'avg_heap': metrics.avg_heap_percent,
            'max_heap': metrics.max_heap_percent,
            'avg_disk': metrics.avg_disk_percent,
            'max_disk': metrics.max_disk_percent,
            'total_docs': metrics.total_docs,
            'scaling_action': decision.action.value,
            'scaling_reason': decision.reason
        })
    
    def _generate_final_report(self):
        """Generar reporte final de actividad"""
        if not self.metrics_log:
            print("📊 No hay datos para reporte", flush=True)
            return

        print(f"\n📊 Generando reporte final...", flush=True)

        # Guardar CSV con métricas
        df = pd.DataFrame(self.metrics_log)
        df.to_csv('css_data_node_autoscaling_report.csv', index=False)

        # Estadísticas de escalamiento
        scaling_events = [
            d for d in self.engine.decision_history
            if d.action != ScalingAction.NONE
        ]

        duration_minutes = (datetime.now() - self.start_time).total_seconds() / 60

        print(f"\n{'='*75}", flush=True)
        print(f"REPORTE FINAL - CSS DATA NODE AUTOSCALER", flush=True)
        print(f"{'='*75}", flush=True)
        print(f"Duración total:        {duration_minutes:.1f} minutos", flush=True)
        print(f"Total de mediciones:   {len(self.metrics_log)}", flush=True)
        print(f"Eventos de escalamiento: {len(scaling_events)}", flush=True)

        if scaling_events:
            print(f"\nHistorial de escalamiento de data nodes:", flush=True)
            for event in scaling_events:
                action_symbol = "🔼" if event.action == ScalingAction.SCALE_OUT else "🔽"
                print(f"  {action_symbol} [{event.timestamp[:19]}] "
                      f"{event.action.value.upper()}: "
                      f"{event.current_data_nodes} → {event.target_data_nodes} data nodes", flush=True)
                print(f"     Razón: {event.reason}", flush=True)

        # Estadísticas de métricas
        if self.metrics_log:
            df = pd.DataFrame(self.metrics_log)
            print(f"\nEstadísticas de data nodes:", flush=True)
            print(f"  CPU promedio:    {df['avg_cpu'].mean():.1f}% "
                  f"(max: {df['max_cpu'].max():.1f}%)", flush=True)
            print(f"  Heap promedio:   {df['avg_heap'].mean():.1f}% "
                  f"(max: {df['max_heap'].max():.1f}%)", flush=True)
            print(f"  Disco promedio:  {df['avg_disk'].mean():.1f}% "
                  f"(max: {df['max_disk'].max():.1f}%)", flush=True)
            print(f"  Data nodes rango: {df['data_nodes'].min()} - {df['data_nodes'].max()}", flush=True)

        print(f"\n📄 Datos completos guardados en: css_data_node_autoscaling_report.csv", flush=True)
        print(f"{'='*75}", flush=True)
    
    def run(self):
        """
        LOOP PRINCIPAL DEL AUTOSCALER DE DATA NODES
        
        Flujo:
        1. Validar configuración
        2. Mostrar banner informativo  
        3. Loop infinito:
           - Recopilar métricas de data nodes
           - Evaluar condiciones de escalamiento
           - Ejecutar escalamiento si es necesario
           - Esperar intervalo configurado
        4. Generar reporte final al terminar
        """
        # Validación inicial
        if not self.validate_configuration():
            print("❌ Configuración inválida. Abortando.", flush=True)
            sys.exit(1)

        self.print_startup_banner()
        self.running = True

        print("🔄 Iniciando loop de monitoreo de data nodes...\n", flush=True)
        
        iteration = 0
        
        while self.running:
            iteration += 1
            loop_start_time = time.time()

            try:
                # 1. Recopilar métricas específicas de data nodes
                metrics = self.monitor.collect_data_node_metrics()

                if not metrics:
                    time.sleep(10)
                    continue

                # 1.5 Escribir métricas a archivo compartido para monitoreo en tiempo real
                write_autoscaler_metrics(metrics)

                # 2. Mostrar métricas de data nodes
                self.monitor.print_data_node_metrics(metrics)
                
                # 3. Evaluar necesidad de escalamiento
                decision = self.engine.make_scaling_decision(metrics)
                self.engine.print_scaling_decision(decision)
                
                # 4. Ejecutar escalamiento de data nodes si es necesario
                if decision.action != ScalingAction.NONE:
                    metrics.scale_reason = (
                        f"{decision.action.value}: "
                        f"{decision.current_data_nodes}→{decision.target_data_nodes} data nodes"
                    )

                    # Escribir evento de escalamiento para el monitor
                    write_scaling_event(
                        decision.action.value,
                        decision.current_data_nodes,
                        decision.target_data_nodes,
                        decision.reason
                    )

                    scaling_success = self.execute_scaling_operation(decision)
                    if scaling_success:
                        print(f"✅ Escalamiento de data nodes ejecutado correctamente", flush=True)
                    else:
                        print(f"❌ Error en escalamiento de data nodes", flush=True)

                # 5. Registrar métricas
                self._log_metrics(metrics, decision)

                # 6. Esperar hasta próxima iteración
                elapsed_time = time.time() - loop_start_time
                sleep_time = max(0, config.monitor_interval - elapsed_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error en loop principal: {e}", flush=True)
                time.sleep(30)
        
        # Generar reporte final
        self._generate_final_report()

if __name__ == "__main__":
    print("🚀 Iniciando CSS Data Node Autoscaler...", flush=True)
    autoscaler = CSSDataNodeAutoscaler()
    autoscaler.run()
