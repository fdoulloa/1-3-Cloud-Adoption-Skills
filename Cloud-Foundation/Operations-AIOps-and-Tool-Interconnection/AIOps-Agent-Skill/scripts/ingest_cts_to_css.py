"""CTS trace events -> CSS index ingestion pipeline.

Queries CTS SDK for recent trace events, transforms to ops_cts common schema,
bulk-ingests into CSS via opensearch-py.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from ops_agent_config import OpsAgentConfig


STATE_FILE = Path(__file__).parent / ".cts_last_ingest"


def transform_cts_event(event: dict) -> dict:
    """Transform CTS trace event to ops_cts common schema."""
    return {
        "timestamp": event.get("time", datetime.now(tz=timezone.utc).isoformat()),
        "trace_id": event.get("id", ""),
        "trace_name": event.get("trace_name", ""),
        "trace_type": event.get("trace_type", ""),
        "trace_status": event.get("trace_status", ""),
        "resource_id": event.get("resource_id", ""),
        "resource_type": event.get("resource_type", ""),
        "resource_name": event.get("resource_name", ""),
        "region": event.get("region", ""),
        "user_name": event.get("user", {}).get("name", ""),
        "user_domain": event.get("user", {}).get("domain", ""),
        "api_version": event.get("api_version", ""),
        "code": event.get("code", 0),
        "correlation_id": event.get("correlation_id", ""),
    }


def get_last_ingest_time() -> str:
    """Get the timestamp of the last ingested CTS event."""
    if STATE_FILE.exists():
        return STATE_FILE.read_text().strip()
    # Default: 1 hour ago
    return (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()


def save_last_ingest_time(ts: str) -> None:
    """Save the timestamp of the last ingested CTS event."""
    STATE_FILE.write_text(ts)


def ingest_cts_to_css(config: OpsAgentConfig, minutes: int = 5) -> int:
    """Ingest CTS traces into CSS ops_cts index."""
    css = OpenSearch(
        hosts=[{"host": config.css_endpoint.replace("https://", "").replace("http://", ""),
                "port": 9200}],
        http_auth=(config.css_username, config.css_password),
        use_ssl=True, verify_certs=False, ssl_show_warn=False,
    )

    from huaweicloudsdkcts.v3 import CtsClient, ListTracesRequest
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.http.http_config import HttpConfig

    credentials = BasicCredentials(ak=config.hwc_ak, sk=config.hwc_sk,
                                   project_id=config.hwc_project_id)
    http_config = HttpConfig.get_default_config()
    cts_client = (
        CtsClient.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(CtsClient.region.value_of(config.hwc_region))
        .build()
    )

    now = int(time.time() * 1000)
    from_time = now - minutes * 60 * 1000

    req = ListTracesRequest(tracker_name=config.cts_tracker_name)
    req.from_time = from_time
    req.to_time = now

    resp = cts_client.list_traces(req)
    traces = resp.traces or []

    if not traces:
        print("No new CTS traces to ingest")
        return 0

    index_name = f"ops_cts-{datetime.now(tz=timezone.utc).strftime('%Y.%m.%d')}"
    actions = []
    for trace in traces:
        event = trace if isinstance(trace, dict) else vars(trace)
        doc = transform_cts_event(event)
        actions.append({"_index": index_name, "_source": doc})

    success, errors = bulk(css, actions, raise_on_error=False)
    print(f"Ingested {success} CTS traces into {index_name}")

    # Save last ingest time
    save_last_ingest_time(datetime.now(tz=timezone.utc).isoformat())
    return success


def main():
    config = OpsAgentConfig.from_env()
    errors = config.validate()
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    count = ingest_cts_to_css(config)
    print(f"Total ingested: {count}")


if __name__ == "__main__":
    main()
