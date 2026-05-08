# file: evaluaciones_benchmark.py
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import urllib3
urllib3.disable_warnings()

import numpy as np
import time
from datetime import datetime
from opensearchpy import OpenSearch
from tqdm import tqdm
import pandas as pd
from tabulate import tabulate
from config import config

# Constantes derivadas de la configuración
INDEX_NAME = config.index_name
VECTOR_DIMENSION = config.vector_dimension
N_QUERIES = config.eval_n_queries

CITIES = ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga"]
CITY_COORDS = {
    "Bogotá": (4.7110, -74.0721),
    "Medellín": (6.2442, -75.5812),
    "Cali": (3.4516, -76.5320),
    "Barranquilla": (10.9685, -74.7813),
    "Cartagena": (10.3910, -75.4794),
    "Bucaramanga": (7.1193, -73.1227)
}

def create_css_client():
    os_config = config.get_opensearch_config()
    os_config['timeout'] = 120
    return OpenSearch(**os_config)

def gen_query_vector():
    v = np.random.randn(VECTOR_DIMENSION).astype(np.float32)
    return v / np.linalg.norm(v)

def run_query(client, body):
    """Ejecutar query y retornar (hits, latency_ms)"""
    start = time.time()
    response = client.search(index=INDEX_NAME, body=body)
    latency = (time.time() - start) * 1000
    hits = [h['_source'].get('rds_menu_id') for h in response['hits']['hits']]
    return hits, latency

# ─────────────────────────────────────────────────────────────────────────────
# LAS 7 MEJORES QUERIES ESTRICTAS PARA DELIVERY DE COMIDA
# ─────────────────────────────────────────────────────────────────────────────

def q1_visual_search_nearby(client, qv, lat, lon, radius_km=3.0):
    """
    Q1: Búsqueda visual + restaurante cercano (caso de uso principal).
    "Quiero este plato en un restaurante a menos de 3km de mí."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 50
                }}}],
                "filter": [{"geo_distance": {
                    "distance": f"{radius_km}km",
                    "restaurant_location": {"lat": lat, "lon": lon}
                }}]
            }
        },
        "sort": [{"popularity_score": "desc"}, "_score"]
    }
    return run_query(client, body)

def q2_visual_category_rating(client, qv, category, min_rating=4.0):
    """
    Q2: Búsqueda visual + categoría + valoración mínima.
    "Quiero una sopa similar a esta foto, pero solo de restaurantes bien valorados."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 60
                }}}],
                "filter": [
                    {"term": {"food_category": category}},
                    {"range": {"avg_rating": {"gte": min_rating}}}
                ]
            }
        },
        "sort": [{"avg_rating": "desc"}, "_score"]
    }
    return run_query(client, body)

def q3_visual_budget_city(client, qv, city, max_price_cop):
    """
    Q3: Búsqueda visual + ciudad + presupuesto máximo.
    "Quiero algo similar a esta foto en Medellín por menos de $20.000."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 60
                }}}],
                "filter": [
                    {"term": {"city": city}},
                    {"range": {"base_price_cop": {"lte": max_price_cop}}}
                ]
            }
        },
        "sort": [{"base_price_cop": "asc"}, "_score"]
    }
    return run_query(client, body)

def q4_dietary_restrictions_geo(client, qv, lat, lon, radius_km=5.0):
    """
    Q4: Búsqueda visual + vegetariano + radio GPS.
    "Quiero opciones vegetarianas similares a esta foto cerca de mí."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 50
                }}}],
                "filter": [
                    {"term": {"is_vegetarian": True}},
                    {"geo_distance": {
                        "distance": f"{radius_km}km",
                        "restaurant_location": {"lat": lat, "lon": lon}
                    }}
                ]
            }
        }
    }
    return run_query(client, body)

def q5_cuisine_neighborhood_popular(client, qv, city, neighborhood, min_reviews=100):
    """
    Q5: Búsqueda visual + cocina + barrio + popularidad mínima.
    "Quiero comida colombiana tradicional similar a esta en Chapinero con muchas reseñas."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 70
                }}}],
                "filter": [
                    {"term": {"city": city}},
                    {"term": {"neighborhood": neighborhood}},
                    {"range": {"total_reviews": {"gte": min_reviews}}}
                ]
            }
        },
        "sort": [{"popularity_score": "desc"}]
    }
    return run_query(client, body)

def q6_allergen_safe_geo(client, qv, excluded_allergens, lat, lon, radius_km=4.0):
    """
    Q6: Búsqueda visual + sin alérgenos específicos + radio GPS.
    "Quiero algo similar pero sin gluten ni lácteos, cerca de mí."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 60
                }}}],
                "filter": [
                    {"geo_distance": {
                        "distance": f"{radius_km}km",
                        "restaurant_location": {"lat": lat, "lon": lon}
                    }}
                ],
                "must_not": [
                    {"terms": {"allergens": excluded_allergens}}
                ]
            }
        }
    }
    return run_query(client, body)

def q7_hybrid_text_visual_spice(client, qv, text_query, spice_level, city):
    """
    Q7: Búsqueda híbrida (imagen + texto) + nivel de picante + ciudad.
    "Quiero algo como bandeja paisa pero sin tanto picante en Bogotá."
    """
    body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [
                    {"knn": {"image_vector": {
                        "vector": qv.tolist(), "k": 50
                    }}},
                    {"match": {"description": {
                        "query": text_query, "operator": "or", "boost": 0.5
                    }}}
                ],
                "filter": [
                    {"term": {"spice_level": spice_level}},
                    {"term": {"city": city}}
                ]
            }
        }
    }
    return run_query(client, body)

def run_evaluaciones_benchmark():
    client = create_css_client()

    print("=" * 70)
    print("EVALUACIONES - ColombiaEats Strict Query Benchmark")
    print("=" * 70)
    count_resp = client.count(index=INDEX_NAME)
    print(f"Documentos en CSS: {count_resp['count']:,}")
    print(f"Queries por escenario: {N_QUERIES}")
    print("=" * 70)

    all_results = []

    # Q1: Visual + Cercano
    print("\n📍 Q1: Visual + Restaurante cercano (<3km)...")
    lats, hits_list = [], []
    for _ in tqdm(range(N_QUERIES), desc="Q1"):
        city = np.random.choice(CITIES)
        base_lat, base_lon = CITY_COORDS[city]
        lat = base_lat + np.random.uniform(-0.03, 0.03)
        lon = base_lon + np.random.uniform(-0.03, 0.03)
        h, l = q1_visual_search_nearby(client, gen_query_vector(), lat, lon)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q1: Visual + Nearby (<3km)",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q2: Visual + Categoría + Rating
    print("\n⭐ Q2: Visual + Categoría + Rating >= 4.0...")
    categories = ["plato_principal", "sopa", "comida_rapida", "snack"]
    lats, hits_list = [], []
    for _ in tqdm(range(N_QUERIES), desc="Q2"):
        cat = np.random.choice(categories)
        h, l = q2_visual_category_rating(client, gen_query_vector(), cat)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q2: Visual + Category + Rating≥4",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q3: Visual + Ciudad + Presupuesto
    print("\n💰 Q3: Visual + Ciudad + Presupuesto máximo...")
    lats, hits_list = [], []
    budgets = [10000, 20000, 35000, 50000]
    for _ in tqdm(range(N_QUERIES), desc="Q3"):
        city = np.random.choice(CITIES)
        budget = np.random.choice(budgets)
        h, l = q3_visual_budget_city(client, gen_query_vector(), city, budget)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q3: Visual + City + Budget",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q4: Visual + Vegetariano + GPS
    print("\n🥗 Q4: Visual + Vegetariano + GPS...")
    lats, hits_list = [], []
    for _ in tqdm(range(N_QUERIES), desc="Q4"):
        city = np.random.choice(CITIES)
        base_lat, base_lon = CITY_COORDS[city]
        lat = base_lat + np.random.uniform(-0.04, 0.04)
        lon = base_lon + np.random.uniform(-0.04, 0.04)
        h, l = q4_dietary_restrictions_geo(client, gen_query_vector(), lat, lon)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q4: Visual + Vegetarian + GPS",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q5: Visual + Barrio + Popularidad
    print("\n🏘️ Q5: Visual + Barrio + Popularidad...")
    lats, hits_list = [], []
    city_hoods = {
        "Bogotá": ["Chapinero", "Usaquén", "Zona Rosa"],
        "Medellín": ["El Poblado", "Laureles", "Envigado"]
    }
    for _ in tqdm(range(N_QUERIES), desc="Q5"):
        city = np.random.choice(list(city_hoods.keys()))
        hood = np.random.choice(city_hoods[city])
        h, l = q5_cuisine_neighborhood_popular(client, gen_query_vector(), city, hood)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q5: Visual + Neighborhood + Popularity",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q6: Visual + Sin alérgenos + GPS
    print("\n🚫 Q6: Visual + Sin alérgenos + GPS...")
    lats, hits_list = [], []
    allergen_combos = [["gluten"], ["lacteos"], ["mariscos"], ["gluten", "lacteos"]]
    for _ in tqdm(range(N_QUERIES), desc="Q6"):
        city = np.random.choice(CITIES)
        base_lat, base_lon = CITY_COORDS[city]
        lat = base_lat + np.random.uniform(-0.03, 0.03)
        lon = base_lon + np.random.uniform(-0.03, 0.03)
        allergens = allergen_combos[np.random.randint(len(allergen_combos))]
        h, l = q6_allergen_safe_geo(client, gen_query_vector(), allergens, lat, lon)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q6: Visual + No Allergens + GPS",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Q7: Híbrida (visual + texto) + Picante + Ciudad
    print("\n💬 Q7: Híbrida (visual + texto) + Picante + Ciudad...")
    lats, hits_list = [], []
    text_queries = [
        "bandeja paisa frijoles arepa",
        "sopa caliente pollo papa",
        "empanadas fritas crujientes",
        "cazuela mariscos coco"
    ]
    spice_levels = ["suave", "medio", "picante"]
    for _ in tqdm(range(N_QUERIES), desc="Q7"):
        city = np.random.choice(CITIES)
        spice = np.random.choice(spice_levels)
        text = np.random.choice(text_queries)
        h, l = q7_hybrid_text_visual_spice(client, gen_query_vector(), text, spice, city)
        lats.append(l); hits_list.append(len(h))
    
    all_results.append({
        "query": "Q7: Hybrid Text+Visual + Spice + City",
        "avg_ms": np.mean(lats), "p95_ms": np.percentile(lats, 95),
        "p99_ms": np.percentile(lats, 99), "avg_hits": np.mean(hits_list),
        "zero_pct": sum(1 for h in hits_list if h == 0) / len(hits_list) * 100
    })

    # Reporte final
    print(f"\n{'='*70}")
    print("REPORTE FINAL DE EVALUACIONES")
    print(f"{'='*70}")
    
    table_data = [[r["query"], f"{r['avg_ms']:.1f}", f"{r['p95_ms']:.1f}",
                   f"{r['p99_ms']:.1f}", f"{r['avg_hits']:.1f}", f"{r['zero_pct']:.1f}%"]
                  for r in all_results]
    headers = ["Query", "Avg(ms)", "P95(ms)", "P99(ms)", "Avg Hits", "0-Result%"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    pd.DataFrame(all_results).to_csv('evaluaciones_results.csv', index=False)
    print(f"\n📊 Resultados guardados en: evaluaciones_results.csv")

if __name__ == "__main__":
    run_evaluaciones_benchmark()
