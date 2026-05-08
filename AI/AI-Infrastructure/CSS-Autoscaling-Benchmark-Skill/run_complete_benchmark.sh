#!/bin/bash
# file: run_complete_benchmark.sh

set -e

#############################################
# CONFIGURACIÓN Y FUNCIONES AUXILIARES
#############################################

# Variables globales
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${HOME}/css-benchmark-env"
RESULTS_DIR="${SCRIPT_DIR}/results_$(date +%Y%m%d_%H%M%S)"

# Load configuration from .env file
if [ -f "${SCRIPT_DIR}/.env" ]; then
    # Export all variables from .env
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
else
    echo "❌ Archivo .env no encontrado en ${SCRIPT_DIR}"
    exit 1
fi

# Build LOCUST_HOST from .env variables (don't modify CSS_HOST - Python scripts need it without protocol/port)
LOCUST_HOST="https://${CSS_HOST}:${CSS_PORT}"

# Función para headers
print_header() {
    echo ""
    echo "================================================================="
    echo "  $1"
    echo "================================================================="
    echo ""
}

print_phase() {
    echo ""
    echo "─────────────────────────────────────────────────────────────────"
    echo "  FASE $1: $2"
    echo "─────────────────────────────────────────────────────────────────"
}

# Función para logs con timestamp
log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

# Verificar entorno virtual
ensure_venv() {
    if [ ! -d "${VENV_PATH}" ]; then
        echo "❌ Entorno virtual no encontrado en ${VENV_PATH}"
        echo "   Ejecuta: python3 -m venv ${VENV_PATH}"
        echo "   Luego: source ${VENV_PATH}/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    source "${VENV_PATH}/bin/activate"
    log "✅ Entorno virtual activado"
}

# Normalizar line endings
fix_line_endings() {
    log "🔧 Normalizando finales de línea..."
    find "${SCRIPT_DIR}" -maxdepth 1 -type f \( -name "*.sh" -o -name "*.py" \) -print0 | \
        while IFS= read -r -d '' f; do
            sed -i 's/\r$//' "$f" 2>/dev/null || true
        done
}

# Verificar dependencias críticas
check_dependencies() {
    log "🔍 Verificando dependencias..."
    
    # Verificar archivo .env
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        echo "❌ Archivo .env no encontrado"
        echo "   Crea el archivo .env con tus credenciales"
        exit 1
    fi
    
    # Verificar archivos Python esenciales
    local required_files=(
        "setup_css_index.py"
        "ingesta_benchmark.py"
        "evaluaciones_benchmark.py"
        "apis_test.py"
        "locustfile.py"
        "monitor_autoscaling.py"
        "phase5_controller.py"
        "css_monitor.py"
        "huawei_css_api.py"
        "scaling_engine.py"
        "generate_report.py"
        "run_performance_tests.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "${SCRIPT_DIR}/${file}" ]; then
            echo "❌ Archivo requerido no encontrado: ${file}"
            exit 1
        fi
    done
    
    # Verificar dependencias Python
    python3 -c "
import sys
modules = ['locust', 'opensearchpy', 'numpy', 'pandas', 'requests', 'tqdm', 'sklearn', 'tabulate']
missing = []
for mod in modules:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)
if missing:
    print('❌ Dependencias faltantes:', ', '.join(missing))
    sys.exit(1)
print('✅ Dependencias Python verificadas')
"
    
    log "✅ Verificación completa"
}

#############################################
# FUNCIÓN PRINCIPAL DE BENCHMARK
#############################################

run_complete_benchmark() {
    print_header "🚀 CSS BENCHMARK COMPLETO CON AUTOESCALAMIENTO DE DATA NODES"
    
    # Preparación inicial
    cd "${SCRIPT_DIR}"
    ensure_venv
    fix_line_endings
    check_dependencies
    
    # Crear directorio de resultados
    mkdir -p "${RESULTS_DIR}"
    log "📁 Resultados se guardarán en: ${RESULTS_DIR}"
    
    # Configurar variables de entorno para Locust
    export LOCUST_HOST
    
    #############################################
    # FASE 1: CONFIGURACIÓN DEL ÍNDICE
    #############################################

    print_phase "1" "CONFIGURACIÓN DEL ÍNDICE VECTORIAL"
    log "Configurando índice CSS para OpenSearch 3.4.0..."

    python3 setup_css_index.py | tee "${RESULTS_DIR}/fase1_setup.log"

    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "❌ Error en configuración del índice"
        exit 1
    fi

    log "✅ Índice vectorial configurado correctamente"
    
    #############################################
    # FASE 2: INGESTA MASIVA
    #############################################

    print_phase "2" "INGESTA MASIVA (Replicando '100 millones en 12 hrs')"
    log "Iniciando benchmark de ingesta..."

    python3 ingesta_benchmark.py | tee "${RESULTS_DIR}/fase2_ingesta.log"

    # Copiar archivos CSV generados
    cp ingesta_metrics.csv "${RESULTS_DIR}/" 2>/dev/null || true

    log "✅ Ingesta completada"

    #############################################
    # FASE 3: EVALUACIONES DE CALIDAD
    #############################################

    print_phase "3" "EVALUACIONES DE CALIDAD (Recall@K y Latencias)"
    log "Ejecutando evaluaciones de recall y precisión..."

    python3 evaluaciones_benchmark.py | tee "${RESULTS_DIR}/fase3_evaluaciones.log"

    # Copiar resultados
    cp evaluaciones_results.csv "${RESULTS_DIR}/" 2>/dev/null || true

    log "✅ Evaluaciones completadas"

    #############################################
    # FASE 4: CROSS-QUERIES CSS + RDS
    #############################################
    print_phase "4" "CROSS-QUERIES CSS + RDS"
    log "Ejecutando benchmark de cross-queries (CSS vectores + RDS transaccional)..."
    log "Simulando: CSS (imagen+geo+metadatos) → RDS (precio+agente+disponibilidad)"

    python3 cross_query_benchmark.py | tee "${RESULTS_DIR}/fase4_cross_queries.log"

    # Copiar resultados
    cp cross_query_results.csv "${RESULTS_DIR}/" 2>/dev/null || true

    log "✅ Cross-queries completadas"

    #############################################
    # FASE 5: PERFORMANCE
    #############################################

    print_phase "5" "PRUEBAS DE PERFORMANCE"
    log "Ejecutando pruebas de performance con Locust..."

    # Ejecutar script de performance que toma parámetros del .env
    bash run_performance_tests.sh | tee "${RESULTS_DIR}/fase5_performance.log"

    # Copiar archivos de performance generados
    cp performance_*.html "${RESULTS_DIR}/" 2>/dev/null || true
    cp performance_*.csv "${RESULTS_DIR}/" 2>/dev/null || true

    log "✅ Pruebas de performance completadas"

    #############################################
    # FASE 6: AUTOESCALAMIENTO
    #############################################

    print_phase "6" "AUTOESCALAMIENTO DE DATA NODES"

    # Desactivar 'set -e' temporalmente para manejar posibles fallos
    set +e

    # Indicar que estamos en fase 5 (para manejo de SIGINT)
    IN_PHASE5=true

    # Iniciar autoscaler de data nodes en background
    # Usar un archivo de salida para capturar el PID del proceso Python
    python3 -u monitor_autoscaling.py > "${RESULTS_DIR}/data_node_autoscaler_output.log" 2>&1 &
    AUTOSCALER_PID=$!

    log "✅ Autoscaler de Data Nodes iniciado (PID: ${AUTOSCALER_PID})"

    log "🎯 Ejecutando estrategia agresiva de autoescalamiento..."

    python3 phase5_controller.py "${RESULTS_DIR}" 2>&1 | tee "${RESULTS_DIR}/phase5_controller.log"
    PHASE5_EXIT_CODE=$?

    # Ya no estamos en fase 5
    IN_PHASE5=false

    # Detener autoscaler con señal SIGINT para shutdown graceful
    log "🛑 Deteniendo autoscaler (PID: ${AUTOSCALER_PID})..."
    kill -SIGINT "${AUTOSCALER_PID}" 2>/dev/null || true

    # Esperar a que termine y genere su reporte CSV (con timeout)
    log "⏳ Esperando que el monitor termine..."
    wait "${AUTOSCALER_PID}" 2>/dev/null || true

    # Verificar que el proceso terminó
    if kill -0 "${AUTOSCALER_PID}" 2>/dev/null; then
        log "⚠️  Monitor no terminó gracefully, forzando terminación..."
        kill -SIGKILL "${AUTOSCALER_PID}" 2>/dev/null || true
        sleep 1
    fi

    # Reactivar strict mode
    set -e

    # Copiar archivo de reporte de autoscaling (los archivos phase5_burst ya se guardan en RESULTS_DIR)
    cp autoscaling_monitor.csv "${RESULTS_DIR}/" 2>/dev/null || true

    log "✅ Fase de autoescalamiento completada"

    #############################################
    # FASE 7: REPORTE FINAL CONSOLIDADO
    #############################################

    print_phase "7" "GENERACIÓN DE REPORTE FINAL"

    # Copiar todos los archivos de métricas al directorio de resultados
    cp *.csv "${RESULTS_DIR}/" 2>/dev/null || true
    cp *.html "${RESULTS_DIR}/" 2>/dev/null || true

    log "Generando reporte consolidado..."
    python3 generate_report.py | tee "${RESULTS_DIR}/fase7_reporte.log"

    # Copiar reporte final
    cp REPORTE_FINAL_CSS_BENCHMARK.txt "${RESULTS_DIR}/" 2>/dev/null || true
    
    #############################################
    # RESUMEN FINAL
    #############################################
    
    print_header "🎉 BENCHMARK COMPLETO FINALIZADO EXITOSAMENTE"
    
    echo "📊 RESUMEN DE ARCHIVOS GENERADOS:"
    echo "   Directorio principal: ${RESULTS_DIR}"
    echo ""
    echo "📈 INGESTA:"
    echo "   • fase2_ingesta.log - Log completo de ingesta"
    echo "   • ingesta_metrics.csv - Métricas detalladas por checkpoint"
    echo ""
    echo "📊 EVALUACIONES:"
    echo "   • fase3_evaluaciones.log - Log de evaluaciones"
    echo "   • evaluaciones_results.csv - Recall@K y latencias"
    echo ""
    echo "⚡ PERFORMANCE:"
    echo "   • fase4_performance.log - Log de pruebas de performance"
    echo "   • performance_*.html - Reportes interactivos de Locust"
    echo "   • performance_*_stats.csv - Estadísticas de performance"
    echo ""
    echo "🔄 AUTOESCALAMIENTO:"
    echo "   • data_node_autoscaler_output.log - Log del autoscaler de data nodes"
    echo "   • phase5_controller.log - Log del controlador de fase 5"
    echo "   • css_data_node_autoscaling_report.csv - Métricas y eventos de escalamiento"
    echo "   • phase5_burst_*.html - Reportes de pruebas de stress incremental"
    echo "   • phase5_burst_*_stats.csv - Estadísticas de cada burst"
    echo ""
    echo "📄 REPORTE CONSOLIDADO:"
    echo "   • REPORTE_FINAL_CSS_BENCHMARK.txt - Resumen ejecutivo"
    echo ""
    echo "🔗 Para revisar los resultados de performance, abre los archivos .html"
    echo "   en un navegador web para ver gráficos interactivos de Locust."
    echo ""
    echo "🔍 Para analizar el autoescalamiento, revisa:"
    echo "   css_data_node_autoscaling_report.csv"
    echo ""
    
    # Mostrar tiempo total
    local end_time=$(date +%s)
    local total_time=$((end_time - start_time))
    local hours=$((total_time / 3600))
    local minutes=$(((total_time % 3600) / 60))
    
    echo "⏱️  Tiempo total de ejecución: ${hours}h ${minutes}m"
    echo ""
    echo "================================================================="
}

# Variable para indicar si estamos en la fase 5
IN_PHASE5=false

# Función para cleanup en caso de interrupción o salida
cleanup() {
    echo ""
    echo "🛑 Limpiando procesos en background..."

    # Matar monitor de estadísticas
    if [ ! -z "$PHASE5_MONITOR_PID" ]; then
        kill -SIGINT "$PHASE5_MONITOR_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$PHASE5_MONITOR_PID" 2>/dev/null || true
        echo "   Monitor de estadísticas detenido"
    fi

    # Matar autoescalador
    if [ ! -z "$AUTOSCALER_PID" ]; then
        kill -SIGINT "$AUTOSCALER_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$AUTOSCALER_PID" 2>/dev/null || true
        echo "   Autoescalador detenido"
    fi

    # Matar cualquier proceso locust residual
    pkill -9 -f "locust" 2>/dev/null || true
    pkill -9 -f "stress_test_wrapper" 2>/dev/null || true

    # Limpiar archivos temporales
    rm -f /tmp/css_autoscaler_metrics.json 2>/dev/null
    rm -f /tmp/css_stress_test_metrics.json 2>/dev/null
    rm -f /tmp/css_scaling_events.json 2>/dev/null
    rm -f /tmp/css_stabilize_load.txt 2>/dev/null

    echo "✅ Cleanup completado"
}

# Función para cleanup por interrupción (Ctrl+C)
cleanup_interrupt() {
    # Si estamos en fase 5, solo terminamos phase5_controller y dejamos que continue
    if [ "$IN_PHASE5" = true ]; then
        echo ""
        echo "🛑 Interrupción durante Fase 5 - Terminando procesos Locust..."
        # Matar procesos locust pero NO el autoscaler todavía
        pkill -TERM -f "locust" 2>/dev/null || true
        sleep 2
        pkill -9 -f "locust" 2>/dev/null || true
        echo "✅ Procesos Locust terminados, continuando con Fase 6..."
        # No hacer exit, dejar que el script continue
        return
    fi

    # Si no estamos en fase 5, hacer cleanup completo y salir
    cleanup
    exit 1
}

# Configurar trap para cleanup en interrupciones y salida normal
trap cleanup_interrupt SIGINT SIGTERM
trap cleanup EXIT

#############################################
# PUNTO DE ENTRADA PRINCIPAL
#############################################

# Verificar argumentos
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Uso: $0 [--dry-run]"
    echo ""
    echo "Ejecuta el benchmark completo de CSS con autoescalamiento."
    echo ""
    echo "Opciones:"
    echo "  --dry-run    Solo verifica dependencias sin ejecutar pruebas"
    echo "  --help       Muestra esta ayuda"
    exit 0
fi

if [ "$1" = "--dry-run" ]; then
    echo "🔍 Modo dry-run: Solo verificando dependencias..."
    ensure_venv
    fix_line_endings
    check_dependencies
    echo "✅ Verificación completada. El sistema está listo para ejecutar."
    exit 0
fi

# Ejecutar benchmark completo
start_time=$(date +%s)
run_complete_benchmark
