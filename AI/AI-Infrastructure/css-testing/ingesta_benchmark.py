# file: ingesta_benchmark.py
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import urllib3
urllib3.disable_warnings()

import io
import base64
import numpy as np
import time
import threading
from datetime import datetime, timedelta
from opensearchpy import OpenSearch, helpers
from tqdm import tqdm
import pandas as pd
from faker import Faker
from PIL import Image, ImageDraw, ImageFilter
from config import config

# Constantes derivadas de la configuración
INDEX_NAME = config.index_name
VECTOR_DIMENSION = config.vector_dimension
TOTAL_VECTORS = config.ingestion_total_vectors
BATCH_SIZE = config.ingestion_batch_size

# ─────────────────────────────────────────────────────────────────────────────
# DATOS MAESTROS - COLOMBIA
# ─────────────────────────────────────────────────────────────────────────────

COLOMBIAN_CITIES = {
    "Bogotá": {
        "lat_range": (4.48, 4.83),
        "lon_range": (-74.22, -73.98),
        "neighborhoods": [
            "Chapinero", "Usaquén", "Zona Rosa", "La Candelaria",
            "Teusaquillo", "Suba", "Kennedy", "Engativá"
        ],
        "weight": 0.35
    },
    "Medellín": {
        "lat_range": (6.15, 6.35),
        "lon_range": (-75.65, -75.52),
        "neighborhoods": [
            "El Poblado", "Laureles", "Envigado", "Sabaneta",
            "Belén", "Robledo"
        ],
        "weight": 0.25
    },
    "Cali": {
        "lat_range": (3.30, 3.55),
        "lon_range": (-76.60, -76.45),
        "neighborhoods": [
            "Granada", "San Antonio", "Ciudad Jardín", "El Peñón",
            "Versalles", "Chipichape"
        ],
        "weight": 0.15
    },
    "Barranquilla": {
        "lat_range": (10.92, 11.05),
        "lon_range": (-74.88, -74.74),
        "neighborhoods": [
            "El Prado", "Riomar", "Ciudad Jardín", "Bello Horizonte"
        ],
        "weight": 0.10
    },
    "Cartagena": {
        "lat_range": (10.37, 10.45),
        "lon_range": (-75.55, -75.48),
        "neighborhoods": [
            "Ciudad Amurallada", "Bocagrande", "Manga", "Getsemaní"
        ],
        "weight": 0.08
    },
    "Bucaramanga": {
        "lat_range": (7.07, 7.15),
        "lon_range": (-73.14, -73.08),
        "neighborhoods": [
            "Cabecera", "La Ciudadela", "El Poblado", "Provenza"
        ],
        "weight": 0.07
    }
}

# Platos colombianos auténticos con características visuales
COLOMBIAN_DISHES = {
    "Bandeja Paisa": {
        "category": "plato_principal",
        "cuisine": "colombiana_tradicional",
        "base_colors": [(210, 160, 80), (180, 100, 50), (220, 200, 150)],
        "accent_colors": [(50, 120, 50), (200, 50, 50)],
        "description": "Bandeja paisa tradicional antioqueña con frijoles, arroz, chicharrón, carne molida, chorizo, morcilla, huevo frito, aguacate y arepa.",
        "ingredients": ["frijoles", "arroz", "chicharrón", "carne molida", "chorizo", "morcilla", "huevo", "aguacate", "arepa"],
        "allergens": ["gluten", "huevo"],
        "price_range": (28000, 45000),
        "is_vegetarian": False,
        "spice_level": "suave"
    },
    "Ajiaco Bogotano": {
        "category": "sopa",
        "cuisine": "colombiana_tradicional",
        "base_colors": [(220, 190, 120), (200, 170, 100), (180, 150, 80)],
        "accent_colors": [(200, 200, 180), (50, 150, 50)],
        "description": "Sopa bogotana tradicional con tres tipos de papa, pollo, guascas y mazorca. Servida con crema de leche, alcaparras y aguacate.",
        "ingredients": ["papa criolla", "papa pastusa", "papa sabanera", "pollo", "guascas", "mazorca", "crema de leche"],
        "allergens": ["lacteos"],
        "price_range": (22000, 38000),
        "is_vegetarian": False,
        "spice_level": "suave"
    },
    "Arepa con Todo": {
        "category": "comida_rapida",
        "cuisine": "colombiana_callejera",
        "base_colors": [(240, 210, 130), (220, 190, 110), (200, 170, 90)],
        "accent_colors": [(200, 50, 50), (50, 150, 50), (220, 220, 180)],
        "description": "Arepa de chócolo con queso costeño, hogao, carne desmechada y aguacate. Clásico de las calles colombianas.",
        "ingredients": ["arepa chócolo", "queso costeño", "hogao", "carne desmechada", "aguacate"],
        "allergens": ["lacteos", "gluten"],
        "price_range": (8000, 18000),
        "is_vegetarian": False,
        "spice_level": "suave"
    },
    "Empanadas Colombianas": {
        "category": "snack",
        "cuisine": "colombiana_callejera",
        "base_colors": [(230, 180, 80), (210, 160, 60), (190, 140, 40)],
        "accent_colors": [(200, 100, 50), (50, 130, 50)],
        "description": "Empanadas de pipián con papa y carne, fritas en aceite. Servidas con ají de maní.",
        "ingredients": ["masa de maíz", "papa", "carne", "ají de maní"],
        "allergens": ["maní"],
        "price_range": (3000, 8000),
        "is_vegetarian": False,
        "spice_level": "medio"
    },
    "Cazuela de Mariscos": {
        "category": "plato_principal",
        "cuisine": "costeña",
        "base_colors": [(220, 150, 80), (200, 130, 60), (180, 110, 50)],
        "accent_colors": [(200, 180, 150), (50, 120, 180)],
        "description": "Cazuela costeña con camarones, langostinos, calamares y pescado en crema de coco con ají dulce.",
        "ingredients": ["camarones", "langostinos", "calamares", "pescado", "coco", "ají dulce"],
        "allergens": ["mariscos", "lacteos"],
        "price_range": (35000, 65000),
        "is_vegetarian": False,
        "spice_level": "medio"
    },
    "Sushi Fusión": {
        "category": "internacional",
        "cuisine": "fusión_colombiana",
        "base_colors": [(250, 245, 230), (220, 180, 140), (180, 60, 60)],
        "accent_colors": [(50, 150, 80), (220, 180, 50)],
        "description": "Rolls de sushi con toque colombiano: aguacate, mango biche y ají amarillo.",
        "ingredients": ["arroz sushi", "nori", "aguacate", "mango", "ají amarillo", "salmón"],
        "allergens": ["mariscos", "gluten", "soya"],
        "price_range": (25000, 55000),
        "is_vegetarian": False,
        "spice_level": "medio"
    }
}

FOOD_CATEGORIES = list(set(d["category"] for d in COLOMBIAN_DISHES.values()))
CUISINE_TYPES = list(set(d["cuisine"] for d in COLOMBIAN_DISHES.values()))

class IngestMetrics:
    def __init__(self):
        self.total_docs = 0
        self.failed_docs = 0
        self.start_time = None
        self.checkpoints = []
        self.lock = threading.Lock()

    def record_batch(self, success, failed, batch_time):
        with self.lock:
            self.total_docs += success
            self.failed_docs += failed
            elapsed_total = time.time() - self.start_time

            self.checkpoints.append({
                'timestamp': datetime.now().isoformat(),
                'total_docs': self.total_docs,
                'failed_docs': self.failed_docs,
                'docs_per_second': success / batch_time if batch_time > 0 else 0,
                'elapsed_minutes': elapsed_total / 60,
                'cumulative_rate': self.total_docs / elapsed_total if elapsed_total > 0 else 0
            })

def generate_food_image_embedding(dish_name: str, dish_data: dict) -> np.ndarray:
    """
    Generar embedding visual sofisticado para platos colombianos.
    Cada tipo de plato tiene características visuales únicas basadas en:
    - Colores dominantes del plato
    - Colores de acento (ingredientes visibles)
    - Complejidad visual (número de componentes)
    """
    width, height = 128, 128
    base_colors = dish_data["base_colors"]
    accent_colors = dish_data["accent_colors"]

    # Crear imagen base con gradiente
    img_array = np.zeros((height, width, 3), dtype=np.float32)
    primary_color = np.array(base_colors[0], dtype=np.float32)
    img_array[:, :] = primary_color

    # Agregar variación de color para textura
    if len(base_colors) > 1:
        secondary = np.array(base_colors[1], dtype=np.float32)
        blend_mask = np.random.random((height, width, 1))
        img_array = img_array * (1 - blend_mask * 0.4) + secondary * blend_mask * 0.4

    # Simular componentes del plato
    img_pil = Image.fromarray(img_array.astype(np.uint8))
    draw = ImageDraw.Draw(img_pil)

    n_components = 5 if dish_data["category"] == "plato_principal" else 3
    for i in range(n_components):
        color = accent_colors[i % len(accent_colors)]
        cx = np.random.randint(15, width - 15)
        cy = np.random.randint(15, height - 15)
        radius = np.random.randint(8, 20)

        # Diferentes formas según el ingrediente
        if i % 3 == 0:  # Circular
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
        elif i % 3 == 1:  # Rectangular
            draw.rectangle([cx - radius, cy - radius//2, cx + radius, cy + radius//2], fill=color)
        else:  # Irregular
            points = [(cx + radius * np.cos(a), cy + radius * np.sin(a))
                      for a in np.linspace(0, 2*np.pi, 6)]
            draw.polygon(points, fill=color)

    # Aplicar blur y ruido
    img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=1.0))
    img_final = np.array(img_pil, dtype=np.float32)
    noise = np.random.randn(height, width, 3) * 8
    img_final = np.clip(img_final + noise, 0, 255)

    # Generar embedding
    flat = img_final.flatten()
    chunk = len(flat) // VECTOR_DIMENSION
    embedding = np.array([
        flat[i * chunk:(i + 1) * chunk].mean() +
        np.random.randn() * 2
        for i in range(VECTOR_DIMENSION)
    ], dtype=np.float32)

    # Normalizar L2
    norm = np.linalg.norm(embedding)
    return embedding / (norm + 1e-8)

def generate_food_document(doc_id: int) -> dict:
    """Generar documento completo de plato colombiano"""
    
    # Seleccionar ciudad con distribución realista
    cities = list(COLOMBIAN_CITIES.keys())
    weights = [COLOMBIAN_CITIES[c]["weight"] for c in cities]
    city_name = np.random.choice(cities, p=weights)
    city_data = COLOMBIAN_CITIES[city_name]
    neighborhood = np.random.choice(city_data["neighborhoods"])

    # Seleccionar plato
    dish_name = np.random.choice(list(COLOMBIAN_DISHES.keys()))
    dish_data = COLOMBIAN_DISHES[dish_name]

    # Generar embedding
    image_vector = generate_food_image_embedding(dish_name, dish_data)

    # Precio con variación
    min_price, max_price = dish_data["price_range"]
    base_price = np.random.uniform(min_price, max_price)
    base_price = round(base_price / 1000) * 1000  # Redondear a miles

    # Coordenadas GPS
    lat = np.random.uniform(*city_data["lat_range"])
    lon = np.random.uniform(*city_data["lon_range"])

    # Valoraciones
    avg_rating = np.clip(np.random.normal(4.1, 0.5), 1.0, 5.0)
    total_reviews = int(np.random.lognormal(mean=4.5, sigma=1.2))
    total_reviews = max(5, min(50000, total_reviews))

    # Score de popularidad
    popularity_score = (
        (avg_rating / 5.0) * 0.5 +
        (min(total_reviews, 10000) / 10000) * 0.3 +
        np.random.uniform(0, 0.2)
    )

    # Nombre del restaurante
    restaurant_prefixes = ["Sabores de", "La Cocina de", "El Rincón de", "Casa", "Restaurante"]
    restaurant_suffixes = ["Colombia", "la Abuela", "Antioquia", "la Costa", "Bogotá"]
    restaurant_name = f"{np.random.choice(restaurant_prefixes)} {np.random.choice(restaurant_suffixes)}"

    return {
        "_index": INDEX_NAME,
        "_id": doc_id,
        "_source": {
            # Vector de imagen
            "image_vector": image_vector.tolist(),

            # IDs
            "dish_id": doc_id,
            "restaurant_id": doc_id % 5000,
            "rds_menu_id": doc_id,

            # Información del plato
            "dish_name": dish_name,
            "description": dish_data["description"],
            "food_category": dish_data["category"],
            "cuisine_type": dish_data["cuisine"],
            "ingredients": dish_data["ingredients"],
            "allergens": dish_data.get("allergens", []),
            "is_vegetarian": dish_data.get("is_vegetarian", False),
            "is_vegan": False,
            "spice_level": dish_data.get("spice_level", "suave"),

            # Restaurante
            "restaurant_name": restaurant_name,
            "restaurant_location": {
                "lat": round(lat, 6),
                "lon": round(lon, 6)
            },
            "city": city_name,
            "neighborhood": neighborhood,

            # Valoraciones
            "avg_rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "popularity_score": round(popularity_score, 4),

            # Precio
            "base_price_cop": base_price,
            "price_tier": "económico" if base_price < 15000 else "moderado" if base_price < 35000 else "premium",

            # Metadata
            "image_url": f"https://cdn.colombiaeats.co/dishes/{doc_id:08d}.jpg",
            "created_at": (datetime.now() - timedelta(days=np.random.randint(0, 730))).isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    }

def create_css_client():
    os_config = config.get_opensearch_config()
    os_config['timeout'] = 300
    return OpenSearch(**os_config)

def run_ingesta_benchmark():
    client = create_css_client()
    metrics = IngestMetrics()
    metrics.start_time = time.time()

    print("=" * 70)
    print("BENCHMARK DE INGESTA - ColombiaEats Food Delivery")
    print("=" * 70)
    print(f"Target: {TOTAL_VECTORS:,} platos colombianos")
    print(f"Platos disponibles: {len(COLOMBIAN_DISHES)}")
    print(f"Ciudades: {len(COLOMBIAN_CITIES)}")
    print(f"Vector dimension: {VECTOR_DIMENSION}")
    print("=" * 70)

    pbar = tqdm(total=TOTAL_VECTORS, desc="Ingesta platos", unit="platos")
    processed = 0

    while processed < TOTAL_VECTORS:
        chunk_size = min(BATCH_SIZE, TOTAL_VECTORS - processed)
        batch_docs = [generate_food_document(processed + i) for i in range(chunk_size)]

        batch_start = time.time()
        try:
            success, failed = helpers.bulk(
                client,
                batch_docs,
                chunk_size=BATCH_SIZE,
                request_timeout=120,
                raise_on_error=False,
                stats_only=True
            )
            batch_elapsed = time.time() - batch_start
            metrics.record_batch(success, failed, batch_elapsed)
            pbar.update(success + failed)
            processed += chunk_size
        except Exception as e:
            print(f"\n❌ Error en batch: {e}")
            break

    pbar.close()
    total_time = time.time() - metrics.start_time

    print(f"\n{'='*70}")
    print("REPORTE FINAL DE INGESTA")
    print(f"{'='*70}")
    print(f"Platos ingestados:      {metrics.total_docs:>15,}")
    print(f"Tiempo total:           {total_time/3600:>14.2f} horas")
    print(f"Throughput promedio:    {metrics.total_docs/total_time:>12.0f} platos/seg")

    if metrics.total_docs > 0:
        time_for_100M = (100_000_000 / metrics.total_docs) * total_time
        print(f"Tiempo estimado 100M:   {time_for_100M/3600:>14.1f} horas")

    pd.DataFrame(metrics.checkpoints).to_csv('ingesta_metrics.csv', index=False)
    print(f"\n📊 Métricas guardadas en: ingesta_metrics.csv")

if __name__ == "__main__":
    run_ingesta_benchmark()
