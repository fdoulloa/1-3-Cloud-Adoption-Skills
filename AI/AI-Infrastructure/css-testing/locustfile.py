# file: locustfile.py
#!/usr/bin/env python3
"""
Locust performance test file for CSS vector search.
Based on Phase 3 business queries + generic API monitoring.
All configuration loaded from .env via config module.
"""
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import urllib3
urllib3.disable_warnings()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from locust import HttpUser, task, constant, events
import json
import random
import numpy as np
from config import config

# Pre-generate query vectors for consistent testing
QUERY_VECTORS = []
for _ in range(1000):
    vector = np.random.randn(config.vector_dimension).astype(np.float32)
    vector = vector / np.linalg.norm(vector)
    QUERY_VECTORS.append(vector.tolist())

# Business data for Phase 3-style queries
CITIES = ["Ciudad de México", "Guadalajara", "Monterrey", "Cancún"]
PROPERTY_TYPES = ["casa", "departamento", "condominio", "villa"]
CITY_COORDS = {
    "Ciudad de México": (19.4326, -99.1332),
    "Guadalajara": (20.6597, -103.3496),
    "Monterrey": (25.6866, -100.3161),
    "Cancún": (21.1619, -86.8515)
}
PRICE_RANGES = [
    (1_000_000, 3_000_000),
    (3_000_000, 6_000_000),
    (6_000_000, 12_000_000)
]
TEXT_QUERIES = [
    "alberca terraza vista",
    "departamento nuevo Polanco",
    "casa jardín seguridad",
    "penthouse lujo panorámica"
]
AMENITY_COMBOS = [
    ["alberca", "gimnasio"],
    ["terraza", "vista panorámica"],
    ["estacionamiento", "seguridad"]
]
CONDITIONS = ["excelente", "nuevo", "remodelado"]


class PropertySearchUser(HttpUser):
    """Locust user simulating real business queries (Phase 3 patterns)
    combined with generic API monitoring.

    Task weights reflect realistic usage:
    - Business queries (Phase 3): highest weight
    - Generic API calls: low weight (monitoring/health)
    """

    host = config.css_full_url
    wait_time = constant(0)

    def on_start(self):
        self.client.auth = (config.css_username, config.css_password)
        self.client.verify = False

    # ========================================================================
    # BUSINESS QUERIES (Phase 3 patterns) - High weight
    # ========================================================================

    @task(20)
    def q1_pure_vector_search(self):
        """Q1: Búsqueda vectorial pura (baseline)"""
        query_vector = random.choice(QUERY_VECTORS)
        body = {
            "size": 10,
            "query": {
                "knn": {
                    "image_vector": {
                        "vector": query_vector,
                        "k": 10
                    }
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q1_Pure_Vector"
        )

    @task(15)
    def q2_vector_city_filter(self):
        """Q2: Vector + filtro exacto por ciudad"""
        query_vector = random.choice(QUERY_VECTORS)
        city = random.choice(CITIES)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [{
                        "knn": {
                            "image_vector": {
                                "vector": query_vector,
                                "k": 30
                            }
                        }
                    }],
                    "filter": [{"term": {"city": city}}]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q2_Vector_City"
        )

    @task(12)
    def q3_vector_geo_radius(self):
        """Q3: Vector + radio geográfico GPS"""
        query_vector = random.choice(QUERY_VECTORS)
        city = random.choice(CITIES)
        lat, lon = CITY_COORDS[city]
        lat += np.random.uniform(-0.02, 0.02)
        lon += np.random.uniform(-0.02, 0.02)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [{
                        "knn": {
                            "image_vector": {
                                "vector": query_vector,
                                "k": 40
                            }
                        }
                    }],
                    "filter": [{
                        "geo_distance": {
                            "distance": "10km",
                            "location": {"lat": lat, "lon": lon}
                        }
                    }]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q3_Vector_GPS"
        )

    @task(10)
    def q4_vector_price_range(self):
        """Q4: Vector + rango de precio"""
        query_vector = random.choice(QUERY_VECTORS)
        min_p, max_p = random.choice(PRICE_RANGES)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [{
                        "knn": {
                            "image_vector": {
                                "vector": query_vector,
                                "k": 30
                            }
                        }
                    }],
                    "filter": [{
                        "range": {
                            "base_price": {
                                "gte": min_p,
                                "lte": max_p
                            }
                        }
                    }]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q4_Vector_Price"
        )

    @task(8)
    def q5_vector_multi_filter(self):
        """Q5: Vector + múltiples filtros estrictos"""
        query_vector = random.choice(QUERY_VECTORS)
        city = random.choice(CITIES)
        ptype = random.choice(PROPERTY_TYPES)
        min_beds = random.randint(2, 4)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [{
                        "knn": {
                            "image_vector": {
                                "vector": query_vector,
                                "k": 50
                            }
                        }
                    }],
                    "filter": [
                        {"term": {"city": city}},
                        {"term": {"property_type": ptype}},
                        {"range": {"bedrooms": {"gte": min_beds}}}
                    ]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q5_Vector_MultiFilter"
        )

    @task(8)
    def q6_hybrid_text_vector(self):
        """Q6: Búsqueda híbrida (vector + texto)"""
        query_vector = random.choice(QUERY_VECTORS)
        text = random.choice(TEXT_QUERIES)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                "image_vector": {
                                    "vector": query_vector,
                                    "k": 30
                                }
                            }
                        },
                        {
                            "match": {
                                "description": {
                                    "query": text,
                                    "operator": "or"
                                }
                            }
                        }
                    ]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q6_Hybrid_TextVector"
        )

    @task(6)
    def q7_vector_amenities_condition(self):
        """Q7: Vector + amenidades específicas + condición"""
        query_vector = random.choice(QUERY_VECTORS)
        amenities = random.choice(AMENITY_COMBOS)
        condition = random.choice(CONDITIONS)
        body = {
            "size": 10,
            "query": {
                "bool": {
                    "must": [{
                        "knn": {
                            "image_vector": {
                                "vector": query_vector,
                                "k": 40
                            }
                        }
                    }],
                    "filter": [
                        {"terms": {"amenities": amenities}},
                        {"term": {"condition": condition}}
                    ]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Q7_Vector_Amenities"
        )

    # ========================================================================
    # GENERIC API QUERIES - Low weight (monitoring/health)
    # ========================================================================

    @task(3)
    def knn_search_k100(self):
        """Generic: K=100 vector search (medium load)"""
        query_vector = random.choice(QUERY_VECTORS)
        body = {
            "size": 100,
            "query": {
                "knn": {
                    "image_vector": {
                        "vector": query_vector,
                        "k": 100
                    }
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Generic_KNN_K100"
        )

    @task(2)
    def knn_search_k500(self):
        """Generic: K=500 vector search (heavy load)"""
        query_vector = random.choice(QUERY_VECTORS)
        body = {
            "size": 500,
            "query": {
                "knn": {
                    "image_vector": {
                        "vector": query_vector,
                        "k": 500
                    }
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Generic_KNN_K500"
        )

    @task(2)
    def multi_vector_search(self):
        """Generic: Multi-vector search (5 vectors in single request)"""
        vectors = random.sample(QUERY_VECTORS, 5)
        body = {
            "size": 50,
            "query": {
                "bool": {
                    "should": [
                        {
                            "knn": {
                                "image_vector": {
                                    "vector": v,
                                    "k": 50
                                }
                            }
                        }
                        for v in vectors
                    ]
                }
            }
        }
        self.client.post(
            f"/{config.index_name}/_search",
            data=json.dumps(body),
            headers={"Content-Type": "application/json"},
            name="Generic_MultiVector"
        )

    @task(1)
    def cluster_health(self):
        """API: Cluster health check"""
        self.client.get(
            "/_cluster/health",
            name="API_ClusterHealth"
        )

    @task(1)
    def node_stats(self):
        """API: Node stats"""
        self.client.get(
            "/_nodes/stats",
            name="API_NodeStats"
        )

    @task(1)
    def index_stats(self):
        """API: Index stats"""
        self.client.get(
            f"/{config.index_name}/_stats",
            name="API_IndexStats"
        )
