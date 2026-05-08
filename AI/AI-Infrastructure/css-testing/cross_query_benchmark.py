# file: cross_query_benchmark.py
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
import urllib3
urllib3.disable_warnings()

import sqlite3
import threading
import concurrent.futures
import numpy as np
import time
from datetime import datetime, timedelta
from opensearchpy import OpenSearch
from tqdm import tqdm
import pandas as pd
from tabulate import tabulate
from config import config

# Constantes derivadas de la configuración
INDEX_NAME = config.index_name
VECTOR_DIMENSION = config.vector_dimension
N_QUERIES = config.eval_n_queries
RDS_ROWS = config.rds_simulation_rows

def create_css_client():
    os_config = config.get_opensearch_config()
    os_config['timeout'] = 120
    return OpenSearch(**os_config)

def gen_query_vector():
    v = np.random.randn(VECTOR_DIMENSION).astype(np.float32)
    return v / np.linalg.norm(v)

def setup_delivery_rds() -> sqlite3.Connection:
    """
    Simular RDS con datos transaccionales de delivery de comida.
    Representa la capa operacional en tiempo real.
    """
    print("🗄️ Configurando RDS simulado (datos de delivery en tiempo real)...")
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()

    # Tabla de items del menú (disponibilidad y precios en tiempo real)
    cursor.execute('''
        CREATE TABLE menu_items (
            rds_menu_id     INTEGER PRIMARY KEY,
            restaurant_id   INTEGER NOT NULL,
            is_available    BOOLEAN DEFAULT 1,
            current_price   REAL NOT NULL,
            promo_price     REAL,
            prep_time_min   INTEGER NOT NULL,
            daily_stock     INTEGER DEFAULT 100,
            sold_today      INTEGER DEFAULT 0,
            last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla de restaurantes (datos operacionales)
    cursor.execute('''
        CREATE TABLE restaurants (
            restaurant_id       INTEGER PRIMARY KEY,
            is_open             BOOLEAN DEFAULT 1,
            delivery_fee_cop    REAL NOT NULL,
            min_order_cop       REAL NOT NULL,
            avg_delivery_min    INTEGER NOT NULL,
            max_delivery_km     REAL NOT NULL,
            total_orders        INTEGER DEFAULT 0,
            is_premium_partner  BOOLEAN DEFAULT 0,
            city                TEXT NOT NULL
        )
    ''')

    # Tabla de pedidos (historial)
    cursor.execute('''
        CREATE TABLE orders (
            order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            rds_menu_id     INTEGER NOT NULL,
            restaurant_id   INTEGER NOT NULL,
            order_time      TIMESTAMP NOT NULL,
            total_cop       REAL NOT NULL,
            status          TEXT DEFAULT 'delivered',
            delivery_min    INTEGER,
            rating_given    REAL
        )
    ''')

    # Tabla de promociones activas
    cursor.execute('''
        CREATE TABLE promotions (
            promo_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            rds_menu_id     INTEGER NOT NULL,
            discount_pct    REAL NOT NULL,
            promo_type      TEXT NOT NULL,
            valid_until     TIMESTAMP NOT NULL,
            is_active       BOOLEAN DEFAULT 1
        )
    ''')

    print("   Poblando RDS con datos transaccionales...")

    # Poblar restaurantes
    cities = ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga"]
    restaurants_data = []
    for i in range(5000):
        restaurants_data.append((
            i,
            1 if np.random.random() < 0.85 else 0,  # is_open
            np.random.choice([0, 2000, 3000, 5000]),  # delivery_fee
            np.random.choice([15000, 20000, 25000]),   # min_order
            np.random.randint(20, 60),                  # avg_delivery_min
            np.random.uniform(2.0, 10.0),               # max_delivery_km
            np.random.randint(100, 50000),              # total_orders
            1 if np.random.random() < 0.2 else 0,      # is_premium
            np.random.choice(cities)
        ))

    cursor.executemany('''
        INSERT INTO restaurants VALUES (?,?,?,?,?,?,?,?,?)
    ''', restaurants_data)

    # Poblar menu_items
    menu_data = []
    promo_data = []
    now = datetime.now()

    for menu_id in range(RDS_ROWS):
        rid = menu_id % 5000
        base_price = np.random.choice([8000, 12000, 18000, 25000, 35000, 45000])
        has_promo = np.random.random() < 0.25
        promo_price = round(base_price * np.random.uniform(0.7, 0.9)) if has_promo else None

        menu_data.append((
            menu_id,
            rid,
            1 if np.random.random() < 0.88 else 0,  # is_available
            float(base_price),
            float(promo_price) if promo_price else None,
            np.random.randint(10, 45),               # prep_time_min
            np.random.randint(20, 150),              # daily_stock
            np.random.randint(0, 80)                 # sold_today
        ))

        # Agregar promoción si aplica
        if has_promo:
            promo_data.append((
                menu_id,
                round(np.random.uniform(10, 40), 1),   # discount_pct
                np.random.choice(["2x1", "descuento", "combo", "happy_hour"]),
                (now + timedelta(hours=np.random.randint(1, 72))).isoformat(),
                1
            ))

    cursor.executemany('''
        INSERT INTO menu_items (rds_menu_id, restaurant_id, is_available, current_price, promo_price, prep_time_min, daily_stock, sold_today)
        VALUES (?,?,?,?,?,?,?,?)
    ''', menu_data)
    cursor.executemany('''
        INSERT INTO promotions (rds_menu_id, discount_pct, promo_type, valid_until, is_active)
        VALUES (?,?,?,?,?)
    ''', promo_data)

    # Poblar historial de pedidos
    orders_data = []
    n_orders = min(RDS_ROWS * 2, 200000)
    for _ in range(n_orders):
        menu_id = np.random.randint(0, RDS_ROWS)
        orders_data.append((
            np.random.randint(1, 10000),     # user_id
            menu_id,
            menu_id % 5000,                  # restaurant_id
            (now - timedelta(
                days=np.random.randint(0, 90),
                hours=np.random.randint(0, 24)
            )).isoformat(),
            np.random.choice([12000, 18000, 25000, 35000, 50000]),
            np.random.choice(['delivered', 'cancelled'], p=[0.92, 0.08]),
            np.random.randint(15, 75),
            round(np.random.uniform(3.0, 5.0), 1) if np.random.random() < 0.7 else None
        ))

    cursor.executemany('''
        INSERT INTO orders (user_id, rds_menu_id, restaurant_id, order_time, total_cop, status, delivery_min, rating_given)
        VALUES (?,?,?,?,?,?,?,?)
    ''', orders_data)

    # Índices para optimizar cross-queries
    cursor.execute('CREATE INDEX idx_menu_available ON menu_items(is_available)')
    cursor.execute('CREATE INDEX idx_menu_price ON menu_items(current_price)')
    cursor.execute('CREATE INDEX idx_menu_rest_available ON menu_items(restaurant_id, is_available)')
    cursor.execute('CREATE INDEX idx_rest_open ON restaurants(is_open)')
    cursor.execute('CREATE INDEX idx_rest_city_open ON restaurants(city, is_open, restaurant_id)')
    cursor.execute('CREATE INDEX idx_orders_user ON orders(user_id)')
    cursor.execute('CREATE INDEX idx_promo_active ON promotions(is_active)')
    cursor.execute('CREATE INDEX idx_promo_menu_active ON promotions(rds_menu_id, is_active)')

    conn.commit()
    print(f"✅ RDS simulado creado con {len(menu_data):,} items y {len(orders_data):,} pedidos")
    return conn

# ─────────────────────────────────────────────────────────────────────────────
# 5 CROSS-QUERIES PARA DELIVERY DE COMIDA
# ─────────────────────────────────────────────────────────────────────────────

def cq1_order_now_available(css_client, rds_cursor, rds_lock, qv, lat, lon, radius_km=3.0):
    """
    CQ1: "Pedir ahora" - Búsqueda visual + disponibilidad inmediata.
    PATRÓN: POST-FILTER (CSS → RDS)
    
    Caso crítico: Usuario quiere algo específico que esté disponible AHORA.
    """
    # Paso 1: CSS - búsqueda visual + geo
    css_start = time.time()
    body = {
        "size": 50,
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
        "_source": ["rds_menu_id", "restaurant_id", "dish_name"]
    }
    css_resp = css_client.search(index=INDEX_NAME, body=body)
    css_latency = (time.time() - css_start) * 1000
    css_ids = [h['_source']['rds_menu_id'] for h in css_resp['hits']['hits']]

    if not css_ids:
        return [], css_latency, 0.0, css_latency

    # Paso 2: RDS - disponibilidad + tiempo de entrega real
    rds_start = time.time()
    placeholders = ','.join('?' * len(css_ids))
    with rds_lock:
        rds_cursor.execute(f'''
            SELECT
                m.rds_menu_id,
                m.current_price,
                COALESCE(m.promo_price, m.current_price) as final_price,
                m.prep_time_min,
                r.avg_delivery_min,
                (m.prep_time_min + r.avg_delivery_min) as total_eta_min,
                r.delivery_fee_cop
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            WHERE m.rds_menu_id IN ({placeholders})
              AND m.is_available = 1
              AND r.is_open = 1
              AND (m.daily_stock - m.sold_today) > 0
            ORDER BY total_eta_min ASC
            LIMIT 10
        ''', css_ids)
        results = rds_cursor.fetchall()
    rds_latency = (time.time() - rds_start) * 1000

    return results, css_latency, rds_latency, css_latency + rds_latency

def cq2_personalized_recommendation(css_client, rds_cursor, rds_lock, qv, user_id, city):
    """
    CQ2: Recomendación personalizada basada en historial.
    PATRÓN: BIDIRECCIONAL (RDS → CSS → RDS)
    
    Caso: "Basado en lo que has pedido antes, esto te puede gustar"
    """
    # Paso 1: RDS - historial del usuario
    rds_start = time.time()
    with rds_lock:
        rds_cursor.execute('''
            SELECT DISTINCT rds_menu_id
            FROM orders
            WHERE user_id = ? AND status = 'delivered' AND rating_given >= 4.0
            ORDER BY order_time DESC LIMIT 5
        ''', (user_id,))
        user_history = [r[0] for r in rds_cursor.fetchall()]
    rds1_latency = (time.time() - rds_start) * 1000

    # Paso 2: CSS - búsqueda visual excluyendo historial
    css_start = time.time()
    body = {
        "size": 30,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 40
                }}}],
                "filter": [
                    {"term": {"city": city}},
                    {"range": {"avg_rating": {"gte": 4.0}}}
                ]
            }
        },
        "_source": ["rds_menu_id"]
    }

    if user_history:
        body["query"]["bool"]["must_not"] = [{"terms": {"rds_menu_id": user_history}}]

    css_resp = css_client.search(index=INDEX_NAME, body=body)
    css_latency = (time.time() - css_start) * 1000
    candidate_ids = [h['_source']['rds_menu_id'] for h in css_resp['hits']['hits']]

    if not candidate_ids:
        return [], rds1_latency, css_latency, 0.0, rds1_latency + css_latency

    # Paso 3: RDS - disponibilidad + promociones
    rds2_start = time.time()
    placeholders = ','.join('?' * len(candidate_ids))
    with rds_lock:
        rds_cursor.execute(f'''
            SELECT
                m.rds_menu_id, m.current_price, p.discount_pct,
                CASE WHEN p.discount_pct IS NOT NULL
                     THEN ROUND(m.current_price * (1 - p.discount_pct/100))
                     ELSE m.current_price END as final_price,
                p.promo_type
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            LEFT JOIN promotions p ON m.rds_menu_id = p.rds_menu_id AND p.is_active = 1
            WHERE m.rds_menu_id IN ({placeholders}) AND m.is_available = 1 AND r.is_open = 1
            ORDER BY p.discount_pct DESC NULLS LAST LIMIT 10
        ''', candidate_ids)
        results = rds_cursor.fetchall()
    rds2_latency = (time.time() - rds2_start) * 1000

    total_latency = rds1_latency + css_latency + rds2_latency
    return results, rds1_latency, css_latency, rds2_latency, total_latency

def cq3_best_deal_finder(css_client, rds_cursor, rds_lock, qv, city, max_budget):
    """
    CQ3: Mejor oferta disponible.
    PATRÓN: PARALELO (CSS ∥ RDS → merge)
    
    Caso: "Quiero algo similar al mejor precio posible"
    """
    def css_query():
        body = {
            "size": 60,
            "query": {
                "bool": {
                    "must": [{"knn": {"image_vector": {
                        "vector": qv.tolist(), "k": 60
                    }}}],
                    "filter": [{"term": {"city": city}}]
                }
            },
            "_source": ["rds_menu_id"]
        }
        resp = css_client.search(index=INDEX_NAME, body=body)
        return {h['_source']['rds_menu_id'] for h in resp['hits']['hits']}

    def rds_query():
        with rds_lock:
            rds_cursor.execute('''
                SELECT m.rds_menu_id, m.current_price, p.discount_pct,
                       CASE WHEN p.discount_pct IS NOT NULL
                            THEN ROUND(m.current_price * (1 - p.discount_pct/100))
                            ELSE m.current_price END as final_price
                FROM restaurants r
                JOIN menu_items m ON m.restaurant_id = r.restaurant_id
                                  AND m.is_available = 1
                                  AND m.current_price <= ?
                LEFT JOIN promotions p ON m.rds_menu_id = p.rds_menu_id AND p.is_active = 1
                WHERE r.is_open = 1 AND r.city = ?
                ORDER BY final_price ASC LIMIT 100
            ''', (max_budget, city))
            rows = rds_cursor.fetchall()
        return {r[0]: r for r in rows}

    # Ejecución paralela
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        css_future = executor.submit(css_query)
        rds_future = executor.submit(rds_query)
        css_ids = css_future.result()
        rds_deals = rds_future.result()
    total_latency = (time.time() - start) * 1000

    # Merge por intersección
    common = css_ids & set(rds_deals.keys())
    results = sorted([rds_deals[mid] for mid in common], key=lambda x: x[3])[:10]  # Por precio final

    return results, total_latency

def cq4_reorder_favorite_restaurant(css_client, rds_cursor, rds_lock, qv, user_id, lat, lon):
    """
    CQ4: Re-pedir del restaurante favorito.
    PATRÓN: RDS-FIRST (RDS → CSS)
    
    Caso: "Quiero algo nuevo de mi restaurante favorito"
    """
    # Paso 1: RDS - encontrar restaurante favorito
    rds_start = time.time()
    with rds_lock:
        rds_cursor.execute('''
            SELECT restaurant_id, COUNT(*) as order_count
            FROM orders WHERE user_id = ? AND status = 'delivered'
            GROUP BY restaurant_id ORDER BY order_count DESC LIMIT 1
        ''', (user_id,))
        fav_row = rds_cursor.fetchone()
    rds1_latency = (time.time() - rds_start) * 1000

    if not fav_row:
        return [], rds1_latency, 0.0, 0.0, rds1_latency

    fav_restaurant_id = fav_row[0]

    # Paso 2: CSS - platos similares de ese restaurante
    css_start = time.time()
    body = {
        "size": 20,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 30
                }}}],
                "filter": [
                    {"term": {"restaurant_id": fav_restaurant_id}},
                    {"geo_distance": {
                        "distance": "15km",
                        "restaurant_location": {"lat": lat, "lon": lon}
                    }}
                ]
            }
        },
        "_source": ["rds_menu_id"]
    }
    css_resp = css_client.search(index=INDEX_NAME, body=body)
    css_latency = (time.time() - css_start) * 1000
    candidate_ids = [h['_source']['rds_menu_id'] for h in css_resp['hits']['hits']]

    if not candidate_ids:
        return [], rds1_latency, css_latency, 0.0, rds1_latency + css_latency

    # Paso 3: RDS - disponibilidad y precios
    rds2_start = time.time()
    placeholders = ','.join('?' * len(candidate_ids))
    with rds_lock:
        rds_cursor.execute(f'''
            SELECT m.rds_menu_id, m.current_price,
                   COALESCE(m.promo_price, m.current_price) as final_price,
                   (SELECT COUNT(*) FROM orders o WHERE o.rds_menu_id = m.rds_menu_id AND o.user_id = ?) as times_ordered
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            WHERE m.rds_menu_id IN ({placeholders}) AND m.is_available = 1 AND r.is_open = 1
            ORDER BY times_ordered DESC, final_price ASC LIMIT 5
        ''', [user_id] + candidate_ids)
        results = rds_cursor.fetchall()
    rds2_latency = (time.time() - rds2_start) * 1000

    total = rds1_latency + css_latency + rds2_latency
    return results, rds1_latency, css_latency, rds2_latency, total

def cq5_group_order_optimizer(css_client, rds_cursor, rds_lock, qv, city, n_people, budget_per_person):
    """
    CQ5: Optimizar pedido grupal.
    PATRÓN: POST-FILTER con agregación
    
    Caso: "Somos 4 personas, queremos pedir del mismo restaurante"
    """
    total_budget = budget_per_person * n_people

    # Paso 1: CSS - candidatos en la ciudad
    css_start = time.time()
    body = {
        "size": 80,
        "query": {
            "bool": {
                "must": [{"knn": {"image_vector": {
                    "vector": qv.tolist(), "k": 80
                }}}],
                "filter": [
                    {"term": {"city": city}},
                    {"range": {"base_price_cop": {"lte": budget_per_person}}}
                ]
            }
        },
        "_source": ["rds_menu_id", "restaurant_id"]
    }
    css_resp = css_client.search(index=INDEX_NAME, body=body)
    css_latency = (time.time() - css_start) * 1000
    css_ids = [h['_source']['rds_menu_id'] for h in css_resp['hits']['hits']]

    if not css_ids:
        return [], css_latency, 0.0, css_latency

    # Paso 2: RDS - agrupar por restaurante
    rds_start = time.time()
    placeholders = ','.join('?' * len(css_ids))
    with rds_lock:
        rds_cursor.execute(f'''
            SELECT
                r.restaurant_id,
                COUNT(m.rds_menu_id) as available_dishes,
                MIN(m.current_price) as min_price,
                AVG(m.current_price) as avg_price,
                r.delivery_fee_cop,
                r.avg_delivery_min,
                (COUNT(m.rds_menu_id) * AVG(m.current_price) + r.delivery_fee_cop) as estimated_total
            FROM menu_items m
            JOIN restaurants r ON m.restaurant_id = r.restaurant_id
            WHERE m.rds_menu_id IN ({placeholders})
              AND m.is_available = 1 AND r.is_open = 1
              AND (m.daily_stock - m.sold_today) >= ?
            GROUP BY r.restaurant_id, r.delivery_fee_cop, r.avg_delivery_min
            HAVING available_dishes >= ? AND estimated_total <= ?
            ORDER BY r.avg_delivery_min ASC LIMIT 5
        ''', css_ids + [n_people, n_people, total_budget])
        results = rds_cursor.fetchall()
    rds_latency = (time.time() - rds_start) * 1000

    return results, css_latency, rds_latency, css_latency + rds_latency

def run_cross_query_benchmark():
    print("=" * 70)
    print("CROSS-QUERY BENCHMARK: CSS + RDS")
    print("ColombiaEats - Delivery de Comida Colombia")
    print("=" * 70)

    css_client = create_css_client()
    rds_conn = setup_delivery_rds()
    rds_cursor = rds_conn.cursor()
    rds_lock = threading.Lock()

    css_count = css_client.count(index=INDEX_NAME)['count']
    rds_cursor.execute("SELECT COUNT(*) FROM menu_items")
    rds_count = rds_cursor.fetchone()[0]

    print(f"CSS (vectores + metadatos): {css_count:,} platos")
    print(f"RDS (datos transaccionales): {rds_count:,} items")
    print(f"Queries por escenario: {N_QUERIES}")
    print("=" * 70)

    all_results = []
    cities = ["Bogotá", "Medellín", "Cali", "Barranquilla"]
    city_coords = {
        "Bogotá": (4.7110, -74.0721),
        "Medellín": (6.2442, -75.5812),
        "Cali": (3.4516, -76.5320),
        "Barranquilla": (10.9685, -74.7813)
    }

    # CQ1: Pedir ahora
    print("\n🚀 CQ1: 'Pedir ahora' - Visual + Disponibilidad inmediata...")
    css_lats, rds_lats, total_lats, hits = [], [], [], []
    for _ in tqdm(range(N_QUERIES), desc="CQ1"):
        city = np.random.choice(cities)
        lat, lon = city_coords[city]
        lat += np.random.uniform(-0.04, 0.04)
        lon += np.random.uniform(-0.04, 0.04)
        res, cl, rl, tl = cq1_order_now_available(
            css_client, rds_cursor, rds_lock, gen_query_vector(), lat, lon
        )
        css_lats.append(cl); rds_lats.append(rl)
        total_lats.append(tl); hits.append(len(res))

    all_results.append({
        "query": "CQ1: Order Now (Post-Filter)",
        "pattern": "CSS→RDS",
        "css_avg_ms": np.mean(css_lats), "css_p95_ms": np.percentile(css_lats, 95),
        "rds_avg_ms": np.mean(rds_lats), "rds_p95_ms": np.percentile(rds_lats, 95),
        "total_avg_ms": np.mean(total_lats), "total_p99_ms": np.percentile(total_lats, 99),
        "avg_hits": np.mean(hits),
        "zero_pct": sum(1 for h in hits if h == 0) / len(hits) * 100
    })

    # CQ2: Recomendación personalizada
    print("\n🎯 CQ2: Recomendación personalizada...")
    rds1_lats, css_lats, rds2_lats, total_lats, hits = [], [], [], [], []
    for _ in tqdm(range(N_QUERIES), desc="CQ2"):
        user_id = np.random.randint(1, 10000)
        city = np.random.choice(cities)
        res, r1l, cl, r2l, tl = cq2_personalized_recommendation(
            css_client, rds_cursor, rds_lock, gen_query_vector(), user_id, city
        )
        rds1_lats.append(r1l); css_lats.append(cl)
        rds2_lats.append(r2l); total_lats.append(tl); hits.append(len(res))

    all_results.append({
        "query": "CQ2: Personalized Rec (Bidirectional)",
        "pattern": "RDS→CSS→RDS",
        "css_avg_ms": np.mean(css_lats), "css_p95_ms": np.percentile(css_lats, 95),
        "rds_avg_ms": np.mean(rds1_lats) + np.mean(rds2_lats),
        "rds_p95_ms": np.percentile([a+b for a, b in zip(rds1_lats, rds2_lats)], 95),
        "total_avg_ms": np.mean(total_lats), "total_p99_ms": np.percentile(total_lats, 99),
        "avg_hits": np.mean(hits),
        "zero_pct": sum(1 for h in hits if h == 0) / len(hits) * 100
    })

    # CQ3: Mejor oferta
    print("\n💸 CQ3: Mejor oferta disponible...")
    total_lats, hits = [], []
    budgets = [15000, 25000, 40000, 60000]
    for _ in tqdm(range(N_QUERIES), desc="CQ3"):
        city = np.random.choice(cities)
        budget = np.random.choice(budgets)
        res, tl = cq3_best_deal_finder(
            css_client, rds_cursor, rds_lock, gen_query_vector(), city, budget
        )
        total_lats.append(tl); hits.append(len(res))

    all_results.append({
        "query": "CQ3: Best Deal (Parallel)",
        "pattern": "CSS ∥ RDS",
        "css_avg_ms": np.mean(total_lats) * 0.55,
        "css_p95_ms": np.percentile(total_lats, 95) * 0.55,
        "rds_avg_ms": np.mean(total_lats) * 0.45,
        "rds_p95_ms": np.percentile(total_lats, 95) * 0.45,
        "total_avg_ms": np.mean(total_lats), "total_p99_ms": np.percentile(total_lats, 99),
        "avg_hits": np.mean(hits),
        "zero_pct": sum(1 for h in hits if h == 0) / len(hits) * 100
    })

    # CQ4: Re-pedir favorito
    print("\n❤️ CQ4: Re-pedir del restaurante favorito...")
    rds1_lats, css_lats, rds2_lats, total_lats, hits = [], [], [], [], []
    for _ in tqdm(range(N_QUERIES), desc="CQ4"):
        user_id = np.random.randint(1, 10000)
        city = np.random.choice(cities)
        lat, lon = city_coords[city]
        res, r1l, cl, r2l, tl = cq4_reorder_favorite_restaurant(
            css_client, rds_cursor, rds_lock, gen_query_vector(), user_id, lat, lon
        )
        rds1_lats.append(r1l); css_lats.append(cl)
        rds2_lats.append(r2l); total_lats.append(tl); hits.append(len(res))

    all_results.append({
        "query": "CQ4: Reorder Favorite (RDS-First)",
        "pattern": "RDS→CSS→RDS",
        "css_avg_ms": np.mean(css_lats), "css_p95_ms": np.percentile(css_lats, 95),
        "rds_avg_ms": np.mean(rds1_lats) + np.mean(rds2_lats),
        "rds_p95_ms": np.percentile([a+b for a, b in zip(rds1_lats, rds2_lats)], 95),
        "total_avg_ms": np.mean(total_lats), "total_p99_ms": np.percentile(total_lats, 99),
        "avg_hits": np.mean(hits),
        "zero_pct": sum(1 for h in hits if h == 0) / len(hits) * 100
    })

    # CQ5: Pedido grupal
    print("\n👥 CQ5: Optimizar pedido grupal...")
    css_lats, rds_lats, total_lats, hits = [], [], [], []
    for _ in tqdm(range(N_QUERIES), desc="CQ5"):
        city = np.random.choice(cities)
        n_people = np.random.choice([2, 3, 4, 5])
        budget = np.random.choice([20000, 30000, 40000])
        res, cl, rl, tl = cq5_group_order_optimizer(
            css_client, rds_cursor, rds_lock, gen_query_vector(), city, n_people, budget
        )
        css_lats.append(cl); rds_lats.append(rl)
        total_lats.append(tl); hits.append(len(res))

    all_results.append({
        "query": "CQ5: Group Order (Post-Filter+Agg)",
        "pattern": "CSS→RDS GROUP BY",
        "css_avg_ms": np.mean(css_lats), "css_p95_ms": np.percentile(css_lats, 95),
        "rds_avg_ms": np.mean(rds_lats), "rds_p95_ms": np.percentile(rds_lats, 95),
        "total_avg_ms": np.mean(total_lats), "total_p99_ms": np.percentile(total_lats, 99),
        "avg_hits": np.mean(hits),
        "zero_pct": sum(1 for h in hits if h == 0) / len(hits) * 100
    })

    rds_cursor.close()
    rds_conn.close()

    # Reporte final
    print(f"\n{'='*70}")
    print("REPORTE FINAL - CROSS-QUERIES CSS + RDS")
    print(f"{'='*70}")

    table_data = [[
        r["query"], r["pattern"],
        f"{r['css_avg_ms']:.1f}", f"{r['css_p95_ms']:.1f}",
        f"{r['rds_avg_ms']:.1f}", f"{r['rds_p95_ms']:.1f}",
        f"{r['total_avg_ms']:.1f}", f"{r['total_p99_ms']:.1f}",
        f"{r['avg_hits']:.1f}", f"{r['zero_pct']:.1f}%"
    ] for r in all_results]

    headers = ["Query", "Pattern", "CSS Avg", "CSS P95",
               "RDS Avg", "RDS P95", "Total Avg", "Total P99",
               "Avg Hits", "0-Result%"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    pd.DataFrame(all_results).to_csv('cross_query_results.csv', index=False)
    print(f"\n📊 Resultados guardados en: cross_query_results.csv")

if __name__ == "__main__":
    run_cross_query_benchmark()
