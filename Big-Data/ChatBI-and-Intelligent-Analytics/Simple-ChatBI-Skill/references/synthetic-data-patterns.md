# Synthetic Data Patterns for ChatBI Demos

## Why Synthetic Data

- Real customer data is sensitive and can't be used in demos.
- Synthetic data must look realistic to be convincing.
- LATAM business context makes demos relatable for regional audiences.
- Support multiple countries: Mexico, Colombia, Argentina, Chile, Peru, Brazil.

## Data Generation Principles

1. **Reproducibility**: Use fixed random seeds for consistent demo data.
2. **Realism**: Country-specific company names, currencies, tax IDs, and regions.
3. **Distribution**: Follow real-world distributions (most vendors are low-risk, few are critical).
4. **Relationships**: Foreign keys must match (vendors exist in both dim_vendor and fact_transaction).
5. **Edge cases**: Include some outliers (very high amounts, very low scores) for interesting queries.

## Multi-Country Support

Use `--country` flag to select the business context. Each country has its own:

| Country | Currency | Tax ID Format | Company Suffixes | Capital |
|---------|----------|---------------|------------------|---------|
| Mexico | MXN | RFC (3-4 letters + 6 digits + 3 chars) | SA de CV, SAPI de CV, SC | Ciudad de México |
| Colombia | COP | NIT (8-10 digits + check digit) | SA, S.A.S., S.R.L. | Bogotá |
| Argentina | ARS | CUIT (2 digits + 8 digits + 1 digit) | SA, SRL, SAS | Buenos Aires |
| Chile | CLP | RUT (8 digits + verification digit) | SpA, SA, EIRL | Santiago |
| Peru | PEN | RUC (11 digits) | SA, SAC, EIRL | Lima |
| Brazil | BRL | CNPJ (14 digits) | Ltda., S.A., ME/EPP | São Paulo |

## Domain Templates

### Financial Services (Risk Analysis)

```python
VENDOR_NAMES = {
    "mexico": [
        "Transportes del Valle", "Suministros Industriales",
        "Constructora del Bajío", "Servicios Tecnológicos",
        "Distribuidora Nacional", "Grupo Logístico Centro",
        "Importaciones del Pacífico", "Manufacturas del Norte",
    ],
    "colombia": [
        "Transportes del Valle", "Suministros Industriales",
        "Constructora del Atlántico", "Servicios Tecnológicos",
        "Distribuidora Nacional", "Grupo Logístico Centro",
        "Importaciones del Pacífico", "Manufacturas del Norte",
    ],
    "argentina": [
        "Transportes del Sur", "Suministros Industriales",
        "Constructora del Litoral", "Servicios Tecnológicos",
        "Distribuidora Nacional", "Grupo Logístico Centro",
        "Importaciones del Paraná", "Manufacturas del Norte",
    ],
}

RISK_DISTRIBUTION = {"BAJO": 0.30, "MEDIO": 0.35, "ALTO": 0.25, "CRITICO": 0.10}

# Amounts in local currency — adjust ranges per country
AMOUNT_RANGES = {
    "mexico": {"BAJO": (100_000, 500_000), "MEDIO": (500_000, 2_000_000), "ALTO": (2_000_000, 8_000_000), "CRITICO": (8_000_000, 25_000_000)},
    "colombia": {"BAJO": (2_000_000, 10_000_000), "MEDIO": (10_000_000, 50_000_000), "ALTO": (50_000_000, 200_000_000), "CRITICO": (200_000_000, 800_000_000)},
    "argentina": {"BAJO": (50_000, 500_000), "MEDIO": (500_000, 3_000_000), "ALTO": (3_000_000, 15_000_000), "CRITICO": (15_000_000, 80_000_000)},
    "chile": {"BAJO": (100_000, 500_000), "MEDIO": (500_000, 3_000_000), "ALTO": (3_000_000, 15_000_000), "CRITICO": (15_000_000, 60_000_000)},
    "peru": {"BAJO": (50_000, 300_000), "MEDIO": (300_000, 1_500_000), "ALTO": (1_500_000, 8_000_000), "CRITICO": (8_000_000, 30_000_000)},
    "brazil": {"BAJO": (5_000, 50_000), "MEDIO": (50_000, 300_000), "ALTO": (300_000, 1_500_000), "CRITICO": (1_500_000, 5_000_000)},
}
```

### Retail / E-commerce

```python
PRODUCT_CATEGORIES = [
    "Electrónicos", "Ropa", "Hogar", "Deportes",
    "Alimentos", "Salud", "Automotriz", "Oficina",
]

# Regions are auto-selected based on --country
REGIONS_BY_COUNTRY = {
    "mexico": ["CDMX", "Jalisco", "Nuevo León", "Estado de México", "Puebla", "Guanajuato"],
    "colombia": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga"],
    "argentina": ["Buenos Aires", "Córdoba", "Rosario", "Mendoza", "Tucumán", "La Plata"],
    "chile": ["Santiago", "Valparaíso", "Concepción", "Antofagasta", "Temuco", "Rancagua"],
    "peru": ["Lima", "Arequipa", "Trujillo", "Cusco", "Piura", "Chiclayo"],
    "brazil": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza", "Belo Horizonte"],
}
```

### Healthcare

```python
HOSPITAL_TYPES = ["General", "Especializado", "Urgencias", "Laboratorio"]
PROCEDURE_CATEGORIES = ["Cirugía", "Diagnóstico", "Terapia", "Prevención"]
```

## Country-Specific Business Context

### Mexico
- **Tax ID (RFC)**: 3-4 letters + 6 digits + 3 characters (e.g., `TDE850101XYZ`)
- **Currency**: MXN
- **Company suffixes**: SA de CV, SAPI de CV, SC, AC
- **Regions**: 32 states (CDMX, Jalisco, Nuevo León, etc.)

### Colombia
- **Tax ID (NIT)**: 8-10 digits + hyphen + check digit (e.g., `900123456-7`)
- **Currency**: COP
- **Company suffixes**: SA, S.A.S., S.R.L., LTDA
- **Regions**: 32 departments (Bogotá, Antioquia, Valle del Cauca, etc.)

### Argentina
- **Tax ID (CUIT)**: 2 digits + 8 digits + hyphen + 1 digit (e.g., `30-71234567-9`)
- **Currency**: ARS
- **Company suffixes**: SA, SRL, SAS, Cooperativa
- **Regions**: 23 provinces + CABA (Buenos Aires, Córdoba, Santa Fe, etc.)

### Chile
- **Tax ID (RUT)**: 8 digits + hyphen + verification digit (e.g., `12.345.678-K`)
- **Currency**: CLP
- **Company suffixes**: SpA, SA, EIRL, Ltda
- **Regions**: 16 regions (Metropolitana, Valparaíso, Biobío, etc.)

### Peru
- **Tax ID (RUC)**: 11 digits (same as DNI for natural persons)
- **Currency**: PEN (Sol)
- **Company suffixes**: SA, SAC, EIRL, S.A.C.
- **Regions**: 25 regions (Lima, Arequipa, Cusco, etc.)

### Brazil
- **Tax ID (CNPJ)**: 14 digits formatted as XX.XXX.XXX/XXXX-XX
- **Currency**: BRL (Real)
- **Company suffixes**: Ltda., S.A., S/S, ME, EPP
- **Regions**: 26 states + DF (São Paulo, Rio de Janeiro, Minas Gerais, etc.)
