#!/usr/bin/env python3
"""Generate synthetic data for ChatBI demos — LATAM multi-country support.

Creates realistic datasets with country-specific business context:
- Vendors with risk scores and financial data
- Customers with KYC levels and limits
- Transactions with anomaly detection patterns
- Contract risk analysis results

Supported countries: mexico, colombia, argentina, chile, peru, brazil

Output: SQL seed files + JSON for direct loading.

Usage:
    python3 scripts/generate-chatbi-demo-data.py [--country mexico] [--domain financial] [--count N]
"""

import json
import random
import argparse
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════
# COUNTRY CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════

COUNTRIES = {
    "mexico": {
        "currency": "MXN",
        "tax_id_label": "RFC",
        "company_suffixes": ["SA de CV", "SAPI de CV", "SC", "AC"],
        "vendors": [
            "Transportes del Valle", "Suministros Industriales",
            "Constructora del Bajío", "Servicios Tecnológicos del Norte",
            "Distribuidora Nacional", "Grupo Logístico Centro",
            "Importaciones del Pacífico", "Manufacturas del Bajío",
            "Comercializadora del Sureste", "Alimentos Frescos",
            "Energías Renovables del Norte", "Consultoría Fiscal Centro",
            "Seguros y Fianzas del Bajío", "Minera del Sureste",
            "Agrícola del Valle", "Químicos Industriales",
            "Telecomunicaciones del Pacífico", "Turismo y Hospitalidad",
            "Metalúrgica del Norte", "Farmacéutica Nacional",
        ],
        "customers": [
            "Grupo Salinas", "FEMSA", "Banorte", "Bimbo", "Cemex",
            "América Móvil", "Walmex", "Liverpool", "Palacio de Hierro",
            "Televisa", "GAP", "Vitro", "Alfa", "IUSA", "Condumex",
        ],
        "regions": [
            "Ciudad de México", "Jalisco", "Nuevo León", "Estado de México",
            "Puebla", "Guanajuato", "Querétaro", "Veracruz", "Yucatán",
            "Chihuahua", "Sonora", "Coahuila", "Michoacán", "Guerrero",
        ],
        "cities": {
            "Ciudad de México": ["CDMX", "Ecatepec", "Nezahualcóyotl"],
            "Jalisco": ["Guadalajara", "Zapopan", "Tlaquepaque"],
            "Nuevo León": ["Monterrey", "San Nicolás", "Guadalupe"],
            "Estado de México": ["Toluca", "Naucalpan", "Tultitlán"],
            "Puebla": ["Puebla", "Tehuacán", "Atlixco"],
        },
        "amount_ranges": {
            "BAJO": (100_000, 500_000),
            "MEDIO": (500_000, 2_000_000),
            "ALTO": (2_000_000, 8_000_000),
            "CRITICO": (8_000_000, 25_000_000),
        },
        "revenue_multiplier": 1.0,
    },
    "colombia": {
        "currency": "COP",
        "tax_id_label": "NIT",
        "company_suffixes": ["SA", "S.A.S.", "S.R.L.", "LTDA"],
        "vendors": [
            "Transportes del Valle", "Suministros Industriales",
            "Constructora del Atlántico", "Servicios Tecnológicos Andinos",
            "Distribuidora Nacional", "Grupo Logístico Caribe",
            "Importaciones del Pacífico", "Manufacturas del Norte",
            "Comercializadora Andina", "Alimentos del Valle",
            "Energías Renovables Colombia", "Consultoría Fiscal Bogotá",
            "Seguros y Fianzas Andinos", "Minera del Chocó",
            "Agrícola del Tolima", "Químicos Industriales",
            "Telecomunicaciones del Caribe", "Turismo y Hospitalidad",
            "Metalúrgica Antioqueña", "Farmacéutica Nacional",
        ],
        "customers": [
            "Ecopetrol", "Bancolombia", "Éxito", "Claro Colombia",
            "Avianca", "Bavaria", "Carvajal", "Nutresa", "Grupo Nutresa",
            "ISA", "EPM", "ISA Intercolombia", "Cementos Argos",
            "Banco de Bogotá", "Davivienda",
        ],
        "regions": [
            "Bogotá D.C.", "Antioquia", "Valle del Cauca", "Atlántico",
            "Santander", "Bolívar", "Cundinamarca", "Boyacá",
            "Nariño", "Tolima", "Huila", "Norte de Santander",
        ],
        "cities": {
            "Bogotá D.C.": ["Bogotá", "Soacha", "Funza"],
            "Antioquia": ["Medellín", "Envigado", "Bello"],
            "Valle del Cauca": ["Cali", "Palmira", "Buenaventura"],
            "Atlántico": ["Barranquilla", "Soledad", "Malambo"],
        },
        "amount_ranges": {
            "BAJO": (2_000_000, 10_000_000),
            "MEDIO": (10_000_000, 50_000_000),
            "ALTO": (50_000_000, 200_000_000),
            "CRITICO": (200_000_000, 800_000_000),
        },
        "revenue_multiplier": 40.0,
    },
    "argentina": {
        "currency": "ARS",
        "tax_id_label": "CUIT",
        "company_suffixes": ["SA", "SRL", "SAS", "Cooperativa"],
        "vendors": [
            "Transportes del Sur", "Suministros Industriales",
            "Constructora del Litoral", "Servicios Tecnológicos",
            "Distribuidora Nacional", "Grupo Logístico Centro",
            "Importaciones del Paraná", "Manufacturas del Norte",
            "Comercializadora del Interior", "Alimentos del Pampa",
            "Energías Renovables Argentina", "Consultoría Fiscal porteña",
            "Seguros y Fianzas del Río", "Minera Patagónica",
            "Agrícola del Pampa Húmedo", "Químicos Industriales",
            "Telecomunicaciones del Litoral", "Turismo y Hospitalidad",
            "Metalúrgica del NOA", "Farmacéutica Nacional",
        ],
        "customers": [
            "YPF", "Mercado Libre", "Globant", "YPF", "Banco Galicia",
            "Banco Macro", "Telecom Argentina", "Pampa Energía",
            "Tenaris", "Arcor", "Molinos Río de la Plata", "San Miguel",
            "LA NACION", "Clarín", "Ledesma",
        ],
        "regions": [
            "Buenos Aires", "CABA", "Córdoba", "Santa Fe",
            "Mendoza", "Tucumán", "Entre Ríos", "Salta",
            "Chaco", "Misiones", "Corrientes", "San Juan",
        ],
        "cities": {
            "Buenos Aires": ["La Plata", "Mar del Plata", "Bahía Blanca"],
            "CABA": ["Buenos Aires", "Palermo", "San Telmo"],
            "Córdoba": ["Córdoba", "Villa Carlos Paz", "Río Cuarto"],
            "Santa Fe": ["Rosario", "Santa Fe", "Rafaela"],
        },
        "amount_ranges": {
            "BAJO": (50_000, 500_000),
            "MEDIO": (500_000, 3_000_000),
            "ALTO": (3_000_000, 15_000_000),
            "CRITICO": (15_000_000, 80_000_000),
        },
        "revenue_multiplier": 1.2,
    },
    "chile": {
        "currency": "CLP",
        "tax_id_label": "RUT",
        "company_suffixes": ["SpA", "SA", "EIRL", "Ltda"],
        "vendors": [
            "Transportes del Valle", "Suministros Industriales",
            "Constructora del Pacífico", "Servicios Tecnológicos",
            "Distribuidora Nacional", "Grupo Logístico Centro",
            "Importaciones del Norte", "Manufacturas del Sur",
            "Comercializadora Andina", "Alimentos del Valle Central",
            "Energías Renovables Chile", "Consultoría Fiscal Santiago",
            "Seguros y Fianzas Chile", "Minera del Norte Grande",
            "Agrícola del Valle Central", "Químicos Industriales",
            "Telecomunicaciones del Pacífico", "Turismo y Hospitalidad",
            "Metalúrgica del Norte", "Farmacéutica Nacional",
        ],
        "customers": [
            "Falabella", "CCU", "LAN Airlines", "BancoEstado",
            "Entel", "CMPC", "Copec", "Antofagasta Minerals",
            "SQM", "Enel Chile", "Colbún", "CAP",
            "Ripley", "Paris", "La Polar",
        ],
        "regions": [
            "Metropolitana", "Valparaíso", "Biobío", "Antofagasta",
            "Araucanía", "O'Higgins", "Maule", "Los Lagos",
            "Coquimbo", "Atacama", "Tarapacá", "Magallanes",
        ],
        "cities": {
            "Metropolitana": ["Santiago", "Providencia", "Las Condes"],
            "Valparaíso": ["Valparaíso", "Viña del Mar", "Quilpué"],
            "Biobío": ["Concepción", "Talcahuano", "Los Ángeles"],
        },
        "amount_ranges": {
            "BAJO": (100_000, 500_000),
            "MEDIO": (500_000, 3_000_000),
            "ALTO": (3_000_000, 15_000_000),
            "CRITICO": (15_000_000, 60_000_000),
        },
        "revenue_multiplier": 1.0,
    },
    "peru": {
        "currency": "PEN",
        "tax_id_label": "RUC",
        "company_suffixes": ["SA", "SAC", "EIRL", "S.A.C."],
        "vendors": [
            "Transportes del Valle", "Suministros Industriales",
            "Constructora del Pacífico", "Servicios Tecnológicos",
            "Distribuidora Nacional", "Grupo Logístico Centro",
            "Importaciones del Norte", "Manufacturas del Sur",
            "Comercializadora Andina", "Alimentos del Valle",
            "Energías Renovables Perú", "Consultoría Fiscal Lima",
            "Seguros y Fianzas Perú", "Minera del Sur",
            "Agrícola del Costa", "Químicos Industriales",
            "Telecomunicaciones del Pacífico", "Turismo y Hospitalidad",
            "Metalúrgica del Sur", "Farmacéutica Nacional",
        ],
        "customers": [
            "Southern Peru", "Banco de Crédito", "Interbank",
            "Alicorp", "Cervecería Backus", "InRetail",
            "Graña y Montero", "Viva Air", "Rimac Seguros",
            "Breca", "Cosapi", "Volcan Compañía Minera",
            "Honda", "Generales", "Polar",
        ],
        "regions": [
            "Lima", "Arequipa", "Trujillo", "Cusco",
            "Piura", "Chiclayo", "Ica", "Huancayo",
            "Puno", "Cajamarca", "Huaraz", "Tarapacá",
        ],
        "cities": {
            "Lima": ["Lima", "Miraflores", "San Isidro"],
            "Arequipa": ["Arequipa", "Cayma", "Cerro Colorado"],
            "Trujillo": ["Trujillo", "Huanchaco", "Laredo"],
        },
        "amount_ranges": {
            "BAJO": (50_000, 300_000),
            "MEDIO": (300_000, 1_500_000),
            "ALTO": (1_500_000, 8_000_000),
            "CRITICO": (8_000_000, 30_000_000),
        },
        "revenue_multiplier": 0.8,
    },
    "brazil": {
        "currency": "BRL",
        "tax_id_label": "CNPJ",
        "company_suffixes": ["Ltda.", "S.A.", "S/S", "ME", "EPP"],
        "vendors": [
            "Transportes do Vale", "Suministros Industriais",
            "Construtora do Atlântico", "Serviços Tecnológicos",
            "Distribuidora Nacional", "Grupo Logístico Centro",
            "Importações do Pacífico", "Manufaturas do Norte",
            "Comercializadora Andina", "Alimentos Frescos",
            "Energias Renováveis", "Consultoria Fiscal",
            "Seguros e Fianças", "Mineração do Sul",
            "Agrícola do Centro-Oeste", "Químicos Industriais",
            "Telecomunicações do Pacífico", "Turismo e Hospitalidade",
            "Metalúrgica do Norte", "Farmacêutica Nacional",
        ],
        "customers": [
            "Petrobras", "Itaú Unibanco", "Vale", "JBS",
            "Ambev", "B3", "WEG", "Eletrobras",
            "Suzano", "Klabin", "Raízen", "Cosan",
            "Gerdau", "Usiminas", "CBA",
        ],
        "regions": [
            "São Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia",
            "Paraná", "Rio Grande do Sul", "Pernambuco", "Ceará",
            "Pará", "Amazonas", "Goiás", "Distrito Federal",
        ],
        "cities": {
            "São Paulo": ["São Paulo", "Campinas", "Santos"],
            "Rio de Janeiro": ["Rio de Janeiro", "Niterói", "Volta Redonda"],
            "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Contagem"],
        },
        "amount_ranges": {
            "BAJO": (5_000, 50_000),
            "MEDIO": (50_000, 300_000),
            "ALTO": (300_000, 1_500_000),
            "CRITICO": (1_500_000, 5_000_000),
        },
        "revenue_multiplier": 5.0,
    },
}

# ═══════════════════════════════════════════════════════════════
# SHARED CONSTANTS
# ═══════════════════════════════════════════════════════════════

RISK_LEVELS = ["BAJO", "MEDIO", "ALTO", "CRITICO"]

RISK_DISTRIBUTION = {"BAJO": 0.30, "MEDIO": 0.35, "ALTO": 0.25, "CRITICO": 0.10}

SECTORS = ["Tecnología", "Manufactura", "Servicios", "Comercio", "Construcción", "Salud", "Finanzas"]

ANOMALY_TYPES = ["Ninguna", "Monto inusual", "Frecuencia alta", "Ubicación sospechosa", "Duplicado"]

CONTRACT_TYPES = [
    "Suministro de equipos", "Servicios de consultoría", "Contrato de mantenimiento",
    "Licenciamiento de software", "Servicios de nube", "Contrato de transporte",
    "Servicios profesionales", "Construcción de infraestructura",
]


# ═══════════════════════════════════════════════════════════════
# TAX ID GENERATORS
# ═══════════════════════════════════════════════════════════════

def gen_rfc():
    """Mexico: 3 letters + 6 digits + 3 alphanumeric."""
    letters = "".join(random.choices("ABCDFGHJKLMNPRSTUVWXYZ", k=3))
    digits = f"{random.randint(10, 99)}{random.randint(1000, 9999)}"
    tail = "".join(random.choices("ABCDEF0123456789", k=3))
    return f"{letters}{digits}{tail}"

def gen_nit():
    """Colombia: 8-10 digits + check digit."""
    base = str(random.randint(80000000, 9999999999))
    check = str(sum(int(d) * (i % 6 + 2) for i, d in enumerate(reversed(base))) % 11)
    return f"{base}-{check}"

def gen_cuit():
    """Argentina: 2 prefix + 8 digits + 1 check."""
    prefix = random.choice(["20", "23", "24", "27", "30", "33", "34"])
    body = f"{random.randint(0, 99999999):08d}"
    check = str((sum(int(d) * (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)[i] for i, d in enumerate(f"{prefix}{body}"))) % 11)
    return f"{prefix}-{body}-{check}"

def gen_rut():
    """Chile: 8 digits + verification digit."""
    base = random.randint(5000000, 25000000)
    chars = "0123456789K"
    mul = [2, 3, 4, 5, 6, 7]
    s, i = 0, 0
    for d in str(base)[::-1]:
        s += int(d) * mul[i % 6]
        i += 1
    ver = chars[(11 - s % 11) % 11]
    return f"{base}-{ver}"

def gen_ruc():
    """Peru: 11 digits."""
    return f"{random.randint(10000000000, 99999999999)}"

def gen_cnpj():
    """Brazil: 14 digits formatted XX.XXX.XXX/XXXX-XX."""
    n = [random.randint(0, 9) for _ in range(12)]
    # Simplified — not computing real check digits
    return f"{n[0]}{n[1]}.{n[2]}{n[3]}{n[4]}.{n[5]}{n[6]}{n[7]}/{n[8]}{n[9]}{n[10]}{n[11]}-{random.randint(10,99)}"

TAX_ID_GENERATORS = {
    "mexico": gen_rfc, "colombia": gen_nit, "argentina": gen_cuit,
    "chile": gen_rut, "peru": gen_ruc, "brazil": gen_cnpj,
}


# ═══════════════════════════════════════════════════════════════
# DATA GENERATORS
# ═══════════════════════════════════════════════════════════════

def get_config(country):
    if country not in COUNTRIES:
        raise ValueError(f"Country '{country}' not supported. Options: {list(COUNTRIES.keys())}")
    return COUNTRIES[country]

def generate_vendors(country, count=50, seed=42):
    cfg = get_config(country)
    random.seed(seed)
    vendors = []
    gen_tax = TAX_ID_GENERATORS[country]

    for i in range(count):
        name = random.choice(cfg["vendors"]) + f" #{i+1:03d}"
        region = random.choice(cfg["regions"])
        city = random.choice(cfg["cities"].get(region, ["Capital"]))
        sector = random.choice(SECTORS)

        risk_level = random.choices(
            RISK_LEVELS, weights=[0.30, 0.35, 0.25, 0.10], k=1
        )[0]
        risk_score = {
            "BAJO": random.uniform(0, 3),
            "MEDIO": random.uniform(4, 6),
            "ALTO": random.uniform(7, 8),
            "CRITICO": random.uniform(9, 10),
        }[risk_level]

        ranges = cfg["amount_ranges"][risk_level]
        annual_revenue = random.randint(ranges[0] * 10, ranges[1] * 50)

        suffix = random.choice(cfg["company_suffixes"])
        tax_id = gen_tax()

        vendors.append({
            "vendor_id": f"VND-{i+1:04d}",
            "name": f"{name} {suffix}",
            "tax_id": tax_id,
            "tax_id_type": cfg["tax_id_label"],
            "country": country,
            "currency": cfg["currency"],
            "sector": sector,
            "region": region,
            "city": city,
            "risk_level": risk_level,
            "risk_score": round(risk_score, 1),
            "annual_revenue": annual_revenue,
            "debt_ratio": round(random.uniform(0.1, 0.8), 2),
            "contract_count": random.randint(1, 20),
            "employee_count": random.randint(10, 500),
        })

    return vendors

def generate_customers(country, count=30, seed=42):
    cfg = get_config(country)
    random.seed(seed + 1)
    customers = []
    gen_tax = TAX_ID_GENERATORS[country]

    for i in range(count):
        name = random.choice(cfg["customers"]) + f" #{i+1:03d}"
        region = random.choice(cfg["regions"])
        city = random.choice(cfg["cities"].get(region, ["Capital"]))
        kyc_level = random.choices(["Básico", "Medio", "Avanzado"], weights=[0.3, 0.5, 0.2], k=1)[0]

        base_amount = cfg["amount_ranges"]["BAJO"][0]
        monthly_limit = {
            "Básico": random.randint(base_amount, base_amount * 5),
            "Medio": random.randint(base_amount * 5, base_amount * 20),
            "Avanzado": random.randint(base_amount * 20, base_amount * 100),
        }[kyc_level]

        suffix = random.choice(cfg["company_suffixes"])

        customers.append({
            "customer_id": f"CUST-{i+1:04d}",
            "name": f"{name} {suffix}",
            "tax_id": gen_tax(),
            "tax_id_type": cfg["tax_id_label"],
            "country": country,
            "currency": cfg["currency"],
            "kyc_level": kyc_level,
            "monthly_limit": monthly_limit,
            "risk_score": round(random.uniform(0, 8), 1),
            "city": city,
            "region": region,
            "account_age_days": random.randint(30, 3650),
        })

    return customers

def generate_transactions(vendors, customers, count=500, seed=42):
    random.seed(seed + 2)
    transactions = []

    for i in range(count):
        vendor = random.choice(vendors)
        customer = random.choice(customers)

        base_amount = vendor["annual_revenue"] / 12
        amount = round(random.uniform(0.1, 3.0) * base_amount, 2)

        anomaly_type = random.choices(
            ANOMALY_TYPES, weights=[0.85, 0.05, 0.04, 0.03, 0.03], k=1
        )[0]

        tx_date = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 450))

        transactions.append({
            "tx_id": f"TX-{i+1:06d}",
            "vendor_id": vendor["vendor_id"],
            "customer_id": customer["customer_id"],
            "amount": amount,
            "currency": vendor["currency"],
            "country": vendor["country"],
            "anomaly_type": anomaly_type,
            "timestamp": tx_date.strftime("%Y-%m-%d %H:%M:%S"),
            "city_from": vendor["city"],
            "city_to": customer["city"],
        })

    return transactions

def generate_risk_results(vendors, count=20, seed=42):
    random.seed(seed + 3)
    results = []

    alert_pools = {
        "BAJO": ["Sin anomalías detectadas", "Términos estándar"],
        "MEDIO": ["Monto requiere revisión", "Cláusula ambigua"],
        "ALTO": ["Garantía insuficiente", "Penalización fuera de rango"],
        "CRITICO": ["Sin garantías", "Exención total de responsabilidad"],
    }

    for i in range(count):
        vendor = random.choice(vendors)
        risk_level = vendor["risk_level"]
        score = vendor["risk_score"]
        ranges = get_config(vendor["country"])["amount_ranges"][risk_level]
        amount = random.randint(ranges[0], ranges[1])
        contract_type = random.choice(CONTRACT_TYPES)

        alerts = random.sample(alert_pools[risk_level], k=min(2, len(alert_pools[risk_level])))

        results.append({
            "contract_number": f"CTR-{random.randint(1000, 9999)}",
            "vendor_name": vendor["name"],
            "country": vendor["country"],
            "currency": vendor["currency"],
            "monto_total": amount,
            "plazo_dias": random.choice([30, 60, 90, 180, 365]),
            "penalizacion_pct": round(random.uniform(0, 15), 1),
            "garantia_pct": round(random.uniform(0, 30), 1),
            "risk_score": round(score, 1),
            "risk_level": risk_level,
            "alertas": json.dumps(alerts, ensure_ascii=False),
            "recomendaciones": json.dumps([f"Revisión de {contract_type.lower()}"], ensure_ascii=False),
            "resumen": f"Análisis de {contract_type.lower()}: {len(alerts)} alertas.",
            "llm_provider": "synthetic-demo",
            "analyzed_at": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d %H:%M:%S"),
        })

    return results


# ═══════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════

def to_sql(table_name, records, schema="public"):
    if not records:
        return ""
    columns = list(records[0].keys())
    lines = [f"-- Synthetic data for {schema}.{table_name}"]
    lines.append(f"TRUNCATE TABLE {schema}.{table_name};")

    for record in records:
        values = []
        for col in columns:
            val = record[col]
            if val is None:
                values.append("NULL")
            elif isinstance(val, (int, float)):
                values.append(str(val))
            elif isinstance(val, str):
                escaped = val.replace("'", "''")
                values.append(f"'{escaped}'")
            else:
                values.append(f"'{str(val)}'")
        lines.append(
            f"INSERT INTO {schema}.{table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic ChatBI demo data — LATAM multi-country")
    parser.add_argument("--country", choices=list(COUNTRIES.keys()), default="mexico",
                        help="Country context for data generation (default: mexico)")
    parser.add_argument("--domain", choices=["financial", "retail", "healthcare"], default="financial")
    parser.add_argument("--count", type=int, default=50, help="Number of vendors/customers")
    parser.add_argument("--output-dir", type=str, default=".")
    args = parser.parse_args()

    cfg = get_config(args.country)

    vendors = generate_vendors(args.country, args.count)
    customers = generate_customers(args.country, args.count // 2)
    transactions = generate_transactions(vendors, customers, args.count * 10)
    risk_results = generate_risk_results(vendors, args.count // 3)

    # Write SQL seed file
    sql_path = f"{args.output_dir}/chatbi-demo-seed-{args.country}.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(f"-- ChatBI Demo Data — {args.country.upper()}\n")
        f.write(f"-- Currency: {cfg['currency']}\n")
        f.write(f"-- Tax ID: {cfg['tax_id_label']}\n")
        f.write(f"-- Generated by generate-chatbi-demo-data.py\n\n")
        f.write(to_sql("vendors", vendors) + "\n\n")
        f.write(to_sql("customers", customers) + "\n\n")
        f.write(to_sql("transactions", transactions) + "\n\n")
        f.write(to_sql("risk_results", risk_results) + "\n")

    # Write JSON for API loading
    json_path = f"{args.output_dir}/chatbi-demo-data-{args.country}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "country": args.country,
            "currency": cfg["currency"],
            "tax_id_type": cfg["tax_id_label"],
            "vendors": vendors,
            "customers": customers,
            "transactions": transactions,
            "risk_results": risk_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"Generated synthetic data for {args.country.upper()}:")
    print(f"  Currency:    {cfg['currency']}")
    print(f"  Tax ID:      {cfg['tax_id_label']}")
    print(f"  Vendors:     {len(vendors)}")
    print(f"  Customers:   {len(customers)}")
    print(f"  Transactions:{len(transactions)}")
    print(f"  Risk results:{len(risk_results)}")
    print(f"  SQL seed:    {sql_path}")
    print(f"  JSON data:   {json_path}")


if __name__ == "__main__":
    main()
