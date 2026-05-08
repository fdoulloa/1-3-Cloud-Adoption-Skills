#!/usr/bin/env python3
"""Generate synthetic risk analysis data for demos and testing.

Creates sample contract risk results with varying risk levels,
alert patterns, and recommendation sets. Useful for populating
dashboards and testing API endpoints without running the full pipeline.

Usage:
    python3 scripts/generate-risk-data.py [--count N] [--output FILE]

Output: JSON file with array of risk result objects.
"""

import json
import random
import argparse
from datetime import datetime, timedelta

# Risk templates by level
TEMPLATES = {
    "BAJO": {
        "score_range": (0, 3),
        "alert_pool": [
            "Sin anomalías detectadas",
            "Términos estándar del mercado",
            "Garantía adecuada",
        ],
        "recommend_pool": [
            "Aprobación estándar",
            "Sin observaciones",
            "Proceder con签约",
        ],
    },
    "MEDIO": {
        "score_range": (4, 6),
        "alert_pool": [
            "Monto requiere revisión",
            "Cláusula de terminación ambigua",
            "Condiciones de pago no estándar",
            "Penalización moderada",
        ],
        "recommend_pool": [
            "Revisión jurídica recomendada",
            "Negociar cláusula de terminación",
            "Solicitar garantía adicional",
        ],
    },
    "ALTO": {
        "score_range": (7, 8),
        "alert_pool": [
            "Monto superior a $2M MXN",
            "Garantía de cumplimiento insuficiente",
            "Penalización fuera de rango habitual",
            "Exención de responsabilidad excesiva",
            "Plazo de entrega inadecuado",
        ],
        "recommend_pool": [
            "Requiere aprobación del consejo",
            "Solicitar garantía bancaria",
            "Revisar cláusulas de force majeure",
            "Agregar seguro de cumplimiento",
        ],
    },
    "CRITICO": {
        "score_range": (9, 10),
        "alert_pool": [
            "Monto excepcional sin precedente",
            "Sin garantías de cumplimiento",
            "Penalización inexistente",
            "Exención total de responsabilidad",
            "Plazo de pago irreal",
            "Cláusulas de rescisión unilaterales",
        ],
        "recommend_pool": [
            "Requiere revisión legal externa",
            "Aprobación del CEO requerida",
            "Suspender proceso de签约",
            "Solicitar due diligence completo",
        ],
    },
}

CONTRACT_TYPES = [
    "Suministro de equipos",
    "Servicios de consultoría",
    "Contrato de mantenimiento",
    "Licenciamiento de software",
    "Servicios de nube",
    "Contrato de transporte",
    "Servicios profesionales",
]


def generate_result(contract_id, risk_level):
    template = TEMPLATES[risk_level]
    score = random.randint(*template["score_range"])

    num_alerts = random.randint(1, min(3, len(template["alert_pool"])))
    alerts = random.sample(template["alert_pool"], num_alerts)

    num_recs = random.randint(1, min(2, len(template["recommend_pool"])))
    recs = random.sample(template["recommend_pool"], num_recs)

    contract_type = random.choice(CONTRACT_TYPES)
    amount = random.randint(100_000, 15_000_000)

    return {
        "job_id": f"SYNTH-{contract_id:04d}",
        "contract_number": f"CTR-{random.randint(1000, 9999)}-{contract_type[:3].upper()}",
        "status": "completed",
        "result": {
            "contract_number": f"CTR-{random.randint(1000, 9999)}-{contract_type[:3].upper()}",
            "risk_score": score,
            "risk_level": risk_level,
            "alertas": alerts,
            "recomendaciones": recs,
            "resumen": f"Análisis de {contract_type.lower()}: {len(alerts)} alertas, score={score}/10.",
            "llm_provider": "synthetic-demo",
        },
        "created_at": (
            datetime.now() - timedelta(days=random.randint(0, 30))
        ).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic risk data")
    parser.add_argument("--count", type=int, default=20, help="Number of results")
    parser.add_argument("--output", type=str, default="synthetic-risk-data.json")
    args = parser.parse_args()

    random.seed(42)

    # Distribute across risk levels
    levels = ["BAJO", "MEDIO", "ALTO", "CRITICO"]
    weights = [0.25, 0.35, 0.25, 0.15]

    results = []
    for i in range(args.count):
        level = random.choices(levels, weights=weights, k=1)[0]
        results.append(generate_result(i + 1, level))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Print summary
    counts = {}
    for r in results:
        level = r["result"]["risk_level"]
        counts[level] = counts.get(level, 0) + 1

    print(f"Generated {args.count} synthetic risk results → {args.output}")
    for level in levels:
        print(f"  {level}: {counts.get(level, 0)}")


if __name__ == "__main__":
    main()
