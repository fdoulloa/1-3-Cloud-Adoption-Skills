"""LTS log group -> CSS index ingestion pipeline.

Queries LTS SDK for log records, transforms to ops_logs common schema,
bulk-ingests into CSS via opensearch-py.

Reuses css-log-assistant/scripts/upload_to_es.py bulk ingest pattern.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

from ops_agent_config import OpsAgentConfig


def transform_lts_record(record: dict) -> dict:
    """Transform LTS log record to ops_logs common schema."""
    return {
        "timestamp": record.get("time", datetime.now(tz=timezone.utc).isoformat()),
        "source_service": record.get("service", "unknown"),
        "source_type": "lts",
        "resource_id": record.get("resource_id", ""),
        "resource_type": record.get("resource_type", ""),
        "resource_name": record.get("resource_name", ""),
        "region": record.get("region", ""),
        "severity": record.get("severity", "info"),
        "log_level": record.get("level", "INFO"),
        "message": record.get("content", ""),
        "error_code": record.get("error_code", ""),
        "trace_id": record.get("trace_id", ""),
        "correlation_id": record.get("correlation_id", ""),
        "host": record.get("host", ""),
        "app": record.get("app", ""),
    }


def ingest_lts_to_css(config: OpsAgentConfig,
                       log_group_id: str, log_topic_id: str,
                       minutes: int = 5) -> int:
    """Ingest LTS logs into CSS ops_logs index."""
    css = OpenSearch(
        hosts=[{"host": config.css_endpoint.replace("https://", "").replace("http://", ""),
                "port": 9200}],
        http_auth=(config.css_username, config.css_password),
        use_ssl=True, verify_certs=False, ssl_show_warn=False,
    )

    # Query LTS SDK for recent logs
    from huaweicloudsdklts.v2 import LtsClient, ListLogsRequest
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.http.http_config import HttpConfig

    credentials = BasicCredentials(ak=config.hwc_ak, sk=config.hwc_sk,
                                   project_id=config.hwc_project_id)
    http_config = HttpConfig.get_default_config()
    lts_client = (
        LtsClient.new_builder()
        .with_http_config(http_config)
        .with_credentials(credentials)
        .with_region(LtsClient.region.value_of(config.hwc_region))
        .build()
    )

    now = int(time.time() * 1000)
    from_time = now - minutes * 60 * 1000

    req = ListLogsRequest(log_group_id=log_group_id, log_topic_id=log_topic_id)
    resp = lts_client.list_logs(req)

    logs = resp.logs or []
    if not logs:
        print("No new LTS logs to ingest")
        return 0

    # Transform and bulk ingest
    index_name = f"ops_logs-{datetime.now(tz=timezone.utc).strftime('%Y.%m.%d')}"
    actions = []
    for log in logs:
        doc = transform_lts_record(log if isinstance(log, dict) else vars(log))
        actions.append({"_index": index_name, "_source": doc})

    success, errors = bulk(css, actions, raise_on_error=False)
    print(f"Ingested {success} LTS logs into {index_name}")
    return success


def main():
    config = OpsAgentConfig.from_env()
    errors = config.validate()
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    log_group_id = config.lts_log_group_id
    log_topic_id = config.lts_log_topic_id
    if not log_group_id or not log_topic_id:
        print("ERROR: Set LTS_LOG_GROUP_ID and LTS_LOG_TOPIC_ID")
        sys.exit(1)

    count = ingest_lts_to_css(config, log_group_id, log_topic_id)
    print(f"Total ingested: {count}")


if __name__ == "__main__":
    main()
