#!/usr/bin/env python3
"""Load generator for CSS cluster to trigger autoscaling."""

import argparse
import random
import threading
import time
import urllib3
from datetime import datetime

urllib3.disable_warnings()

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    exit(1)


def generate_vector(dim: int) -> list:
    """Generate a random vector."""
    return [random.random() for _ in range(dim)]


def index_documents(args, thread_id: int, stop_event: threading.Event):
    """Index documents continuously."""
    url = f"https://{args.host}:{args.port}/{args.index}/_bulk"
    auth = (args.username, args.password)

    count = 0
    while not stop_event.is_set():
        # Create bulk request
        bulk_lines = []
        for i in range(args.batch_size):
            doc = {
                "vector": generate_vector(args.dimension),
                "timestamp": datetime.utcnow().isoformat(),
                "thread_id": thread_id,
                "doc_id": count + i,
            }
            bulk_lines.append('{"index": {}}')
            bulk_lines.append(str(doc).replace("'", '"'))

        bulk_body = "\n".join(bulk_lines) + "\n"

        try:
            resp = requests.post(
                url,
                auth=auth,
                data=bulk_body,
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=30,
            )
            if resp.status_code == 200:
                count += args.batch_size
                if count % 1000 == 0:
                    print(f"[Thread {thread_id}] Indexed {count} documents")
        except Exception as e:
            print(f"[Thread {thread_id}] Index error: {e}")

        time.sleep(args.index_delay)


def search_queries(args, thread_id: int, stop_event: threading.Event):
    """Run search queries continuously."""
    search_url = f"https://{args.host}:{args.port}/{args.index}/_search"
    knn_url = f"https://{args.host}:{args.port}/{args.index}/_knn_search"
    auth = (args.username, args.password)

    count = 0
    while not stop_event.is_set():
        # Regular search
        query = {
            "size": 100,
            "query": {
                "bool": {
                    "must": [
                        {"match_all": {}}
                    ]
                }
            }
        }

        try:
            resp = requests.post(
                search_url,
                auth=auth,
                json=query,
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=30,
            )
            if resp.status_code == 200:
                count += 1
        except Exception as e:
            print(f"[Thread {thread_id}] Search error: {e}")

        # KNN search (vector search - more CPU intensive)
        if args.knn_search:
            knn_query = {
                "size": args.knn_k,
                "query": {
                    "knn": {
                        "vector": {
                            "vector": generate_vector(args.dimension),
                            "k": args.knn_k
                        }
                    }
                }
            }
            try:
                resp = requests.post(
                    knn_url,
                    auth=auth,
                    json=knn_query,
                    headers={"Content-Type": "application/json"},
                    verify=False,
                    timeout=30,
                )
            except Exception:
                pass

        time.sleep(args.search_delay)

    print(f"[Thread {thread_id}] Completed {count} searches")


def main():
    parser = argparse.ArgumentParser(description="CSS Load Generator")
    parser.add_argument("--host", default="101.44.24.182", help="CSS host")
    parser.add_argument("--port", type=int, default=9200, help="CSS port")
    parser.add_argument("--username", default="admin", help="Username")
    parser.add_argument("--password", default="Andrea1980$", help="Password")
    parser.add_argument("--index", default="benchmark_vectors", help="Index name")
    parser.add_argument("--dimension", type=int, default=128, help="Vector dimension")
    parser.add_argument("--batch-size", type=int, default=100, help="Bulk batch size")
    parser.add_argument("--index-threads", type=int, default=4, help="Indexing threads")
    parser.add_argument("--search-threads", type=int, default=8, help="Search threads")
    parser.add_argument("--index-delay", type=float, default=0.01, help="Delay between index ops")
    parser.add_argument("--search-delay", type=float, default=0.001, help="Delay between searches")
    parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    parser.add_argument("--knn-search", action="store_true", help="Enable KNN vector search")
    parser.add_argument("--knn-k", type=int, default=10, help="KNN k value")
    args = parser.parse_args()

    print(f"CSS Load Generator")
    print(f"  Host: {args.host}:{args.port}")
    print(f"  Index: {args.index}")
    print(f"  Duration: {args.duration}s")
    print(f"  Index threads: {args.index_threads}")
    print(f"  Search threads: {args.search_threads}")
    print(f"  KNN search: {args.knn_search}")
    print()

    stop_event = threading.Event()
    threads = []

    # Start indexing threads
    for i in range(args.index_threads):
        t = threading.Thread(target=index_documents, args=(args, i, stop_event))
        t.daemon = True
        t.start()
        threads.append(t)

    # Start search threads
    for i in range(args.search_threads):
        t = threading.Thread(target=search_queries, args=(args, i, stop_event))
        t.daemon = True
        t.start()
        threads.append(t)

    print(f"Started {len(threads)} threads. Press Ctrl+C to stop.")

    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_event.set()
        time.sleep(1)
        print("Done.")


if __name__ == "__main__":
    main()
