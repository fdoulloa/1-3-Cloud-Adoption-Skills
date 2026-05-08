# file: setup_css_index.py
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import urllib3
urllib3.disable_warnings()

from opensearchpy import OpenSearch
from config import config

def create_css_client():
    os_config = config.get_opensearch_config()
    os_config['timeout'] = 300
    return OpenSearch(**os_config)

def create_food_delivery_index():
    """
    Crear índice CSS optimizado para búsqueda visual de comida colombiana.
    Incluye soporte para embeddings de imágenes, geolocalización y texto en español.
    """
    client = create_css_client()

    if client.indices.exists(index=config.index_name):
        client.indices.delete(index=config.index_name)
        print(f"   Índice existente '{config.index_name}' eliminado")

    index_config = {
        "settings": {
            "index": {
                "number_of_shards": 3,
                "number_of_replicas": 1,
                "refresh_interval": "30s",
                "knn": True
            },
            "analysis": {
                "analyzer": {
                    "spanish_food": {
                        "type": "standard",
                        "stopwords": "_spanish_"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # ─── VECTOR EMBEDDING DE IMAGEN ──────────────────────────
                "image_vector": {
                    "type": "knn_vector",
                    "dimension": config.vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                        "parameters": {
                            "ef_construction": 256,
                            "m": 16
                        }
                    }
                },

                # ─── IDs DE REFERENCIA ───────────────────────────────────
                "dish_id": {"type": "long"},
                "restaurant_id": {"type": "long"},
                "rds_menu_id": {"type": "long"},  # FK hacia RDS

                # ─── INFORMACIÓN DEL PLATO ───────────────────────────────
                "dish_name": {
                    "type": "text",
                    "analyzer": "spanish_food",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "description": {
                    "type": "text",
                    "analyzer": "spanish_food"
                },
                "food_category": {"type": "keyword"},
                "cuisine_type": {"type": "keyword"},
                "ingredients": {"type": "keyword"},
                "allergens": {"type": "keyword"},
                "is_vegetarian": {"type": "boolean"},
                "is_vegan": {"type": "boolean"},
                "spice_level": {"type": "keyword"},

                # ─── INFORMACIÓN DEL RESTAURANTE ─────────────────────────
                "restaurant_name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}}
                },
                "restaurant_location": {"type": "geo_point"},
                "city": {"type": "keyword"},
                "neighborhood": {"type": "keyword"},

                # ─── VALORACIONES ────────────────────────────────────────
                "avg_rating": {"type": "float"},
                "total_reviews": {"type": "integer"},
                "popularity_score": {"type": "float"},

                # ─── PRECIO BASE ─────────────────────────────────────────
                "base_price_cop": {"type": "double"},
                "price_tier": {"type": "keyword"},

                # ─── METADATA ────────────────────────────────────────────
                "image_url": {"type": "keyword", "index": False},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        }
    }

    try:
        client.indices.create(index=config.index_name, body=index_config)
        print(f"✅ Índice '{config.index_name}' creado exitosamente")
        print(f"   Engine: Lucene | Algorithm: HNSW | Space: Cosine")
        print(f"   Dimensiones: {config.vector_dimension}")
        print(f"   Soporte: geo_point, texto español, knn_vector")
        return True
    except Exception as e:
        print(f"❌ Error creando índice: {e}")
        return False

if __name__ == "__main__":
    print("=" * 65)
    print("CSS INDEX SETUP - ColombiaEats Food Delivery Platform")
    print("=" * 65)
    create_food_delivery_index()
