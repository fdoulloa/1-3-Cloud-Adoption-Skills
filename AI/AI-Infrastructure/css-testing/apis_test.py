#!/usr/bin/env python3
"""
CSS API Tests - Comprehensive API functionality tests.
All configuration loaded from .env via config module.
"""
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import urllib3
urllib3.disable_warnings()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
from tabulate import tabulate

# Load configuration from .env
from config import config


def create_session_with_retries(total_retries=3, backoff_factor=0.5):
    """
    Create a requests session with retry strategy for SSL/connection errors.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "PUT", "POST", "DELETE"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# Global session with retries
_api_session = None


def get_api_session():
    """Get or create the global session with retries"""
    global _api_session
    if _api_session is None:
        _api_session = create_session_with_retries(total_retries=3, backoff_factor=0.5)
    return _api_session


def test_api_endpoint(name, method, endpoint, body=None, expected_status=200, max_retries=3):
    """Test individual API endpoint with timing, error handling and retries"""
    url = f"{config.css_full_url}/{endpoint}"
    auth = (config.css_username, config.css_password)
    headers = {"Content-Type": "application/json"}
    session = get_api_session()

    start_time = time.time()
    last_error = None

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = session.get(url, auth=auth, verify=False, timeout=(10, 30))
            elif method == "POST":
                response = session.post(
                    url, auth=auth, verify=False,
                    headers=headers, data=json.dumps(body), timeout=(10, 30)
                )

            latency = (time.time() - start_time) * 1000
            status = "✅ PASS" if response.status_code == expected_status else f"❌ FAIL ({response.status_code})"

            return {
                "api": name,
                "status": status,
                "latency_ms": f"{latency:.1f}",
                "status_code": response.status_code
            }

        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 1.0 * (2 ** attempt)
                time.sleep(wait_time)
            continue

        except Exception as e:
            last_error = e
            break

    latency = (time.time() - start_time) * 1000
    error_msg = str(last_error)[:50] if last_error else "Unknown error"
    return {
        "api": name,
        "status": f"❌ ERROR: {error_msg}...",
        "latency_ms": f"{latency:.1f}",
        "status_code": 0
    }


def run_api_tests():
    """Execute comprehensive API functionality test suite"""
    print(f"{'='*60}")
    print("CSS API COMPREHENSIVE TEST SUITE")
    print(f"{'='*60}")
    print(f"Configuration:")
    print(f"   CSS Host: {config.css_host}:{config.css_port}")
    print(f"   Index: {config.index_name}")
    print(f"{'='*60}")

    results = []

    # Core cluster APIs
    results.append(test_api_endpoint("Cluster Health", "GET", "_cluster/health"))
    results.append(test_api_endpoint("Cluster Stats", "GET", "_cluster/stats"))
    results.append(test_api_endpoint("Node Information", "GET", "_nodes"))
    results.append(test_api_endpoint("Node Statistics", "GET", "_nodes/stats"))

    # Index management APIs
    results.append(test_api_endpoint("Index Statistics", "GET", f"{config.index_name}/_stats"))
    results.append(test_api_endpoint("Index Mapping", "GET", f"{config.index_name}/_mapping"))
    results.append(test_api_endpoint("Document Count", "GET", f"{config.index_name}/_count"))

    # Vector search APIs
    sample_vector = [0.1] * config.vector_dimension  # Simple test vector
    knn_query = {
        "size": 10,
        "query": {"knn": {"vector": {"vector": sample_vector, "k": 10}}}
    }
    results.append(test_api_endpoint("KNN Vector Search", "POST", f"{config.index_name}/_search", knn_query))

    # Display comprehensive results
    print(f"\n{'='*60}")
    print("API TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    table_data = [[r["api"], r["status"], r["latency_ms"]] for r in results]
    headers = ["API Endpoint", "Status", "Latency (ms)"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Summary statistics
    passed = sum(1 for r in results if "PASS" in r["status"])
    print(f"\n📊 API Test Summary: {passed}/{len(results)} endpoints functioning correctly")

    return results


if __name__ == "__main__":
    run_api_tests()
