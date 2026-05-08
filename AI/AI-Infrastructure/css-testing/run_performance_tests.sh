#!/bin/bash
# file: run_performance_tests.sh
# Ejecuta pruebas de performance con Locust
# Los parámetros se leen desde el archivo .env

set -e

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cargar configuración desde .env
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
else
    echo "❌ Archivo .env no encontrado en ${SCRIPT_DIR}"
    exit 1
fi

# Construir LOCUST_HOST desde las variables de .env
LOCUST_HOST="https://${CSS_HOST}:${CSS_PORT}"
export LOCUST_HOST

# Directorio de resultados
RESULTS_DIR="${SCRIPT_DIR}/results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${RESULTS_DIR}"

echo "=== STARTING COMPREHENSIVE PERFORMANCE TESTS ==="
echo "   Host: ${LOCUST_HOST}"
echo "   Resultados en: ${RESULTS_DIR}"

# Prueba 1: Carga baja
echo ""
echo "📊 Prueba 1: Carga baja (20 usuarios, 30 segundos)"
locust -f "${SCRIPT_DIR}/locustfile.py" \
    --headless \
    --only-summary \
    -u 20 -r 2 -t 30s \
    --html "${RESULTS_DIR}/performance_20users.html" \
    --csv "${RESULTS_DIR}/performance_20users"

# Prueba 2: Carga media
echo ""
echo "📊 Prueba 2: Carga media (100 usuarios, 30 segundos)"
locust -f "${SCRIPT_DIR}/locustfile.py" \
    --headless \
    --only-summary \
    -u 100 -r 5 -t 30s \
    --html "${RESULTS_DIR}/performance_100users.html" \
    --csv "${RESULTS_DIR}/performance_100users"

# Prueba 3: Carga alta
echo ""
echo "📊 Prueba 3: Carga alta (200 usuarios, 30 segundos)"
locust -f "${SCRIPT_DIR}/locustfile.py" \
    --headless \
    --only-summary \
    -u 200 -r 10 -t 30s \
    --html "${RESULTS_DIR}/performance_200users.html" \
    --csv "${RESULTS_DIR}/performance_200users"

echo ""
echo "=== PERFORMANCE TESTS COMPLETED ==="
echo "📁 Resultados guardados en: ${RESULTS_DIR}"
echo "📊 Revisa los archivos HTML generados para métricas detalladas de performance"
