"""Cross-service log correlation via CSS/OpenSearch for the AIOps Agent.

Queries across ops_logs, ops_alerts, ops_cts indices
to find related events for a given alert.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from opensearchpy import OpenSearch

from ops_agent_config import OpsAgentConfig


class CSSLogCorrelator:
    """Cross-service log correlation using CSS/OpenSearch."""

    DEFAULT_CORRELATION_FIELDS = ["resource_id", "region", "correlation_id"]

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._client = None
        if not config.demo_mode:
            try:
                self._client = self._build_client()
            except Exception:
                self._client = None

    def _build_client(self) -> OpenSearch:
        """Build OpenSearch client. Reuses css-testing pattern."""
        from urllib.parse import urlparse
        parsed = urlparse(self.config.css_endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 9200
        use_ssl = parsed.scheme == "https"
        return OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=(self.config.css_username, self.config.css_password),
            use_ssl=use_ssl,
            verify_certs=False,
            ssl_show_warn=False,
        )

    def query_recent_logs(self, resource_id: Optional[str] = None,
                          service: Optional[str] = None,
                          severity: Optional[str] = None,
                          minutes: int = 15,
                          index_pattern: str = "ops_logs-*") -> list[dict]:
        """Query recent logs from CSS ops_logs index."""
        if not self._client:
            return []

        now = datetime.now(tz=timezone.utc)
        from_time = now - timedelta(minutes=minutes)

        must = [
            {"range": {"timestamp": {"gte": from_time.isoformat(), "lte": now.isoformat()}}}
        ]
        if resource_id:
            must.append({"term": {"resource_id": resource_id}})
        if service:
            must.append({"term": {"source_service": service}})
        if severity:
            must.append({"term": {"severity": severity}})

        query = {"bool": {"must": must}}
        body = {
            "query": query,
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 100,
        }

        try:
            resp = self._client.search(index=index_pattern, body=body)
            return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
        except Exception:
            return []

    def correlate_events(self, alert: dict,
                         correlation_fields: Optional[list[str]] = None,
                         time_window_minutes: int = 15) -> list[dict]:
        """Find related events across logs, alerts, and CTS indices.

        Default correlation fields: resource_id, region, timestamp (within window).
        """
        if not self._client:
            return []

        fields = correlation_fields or self.DEFAULT_CORRELATION_FIELDS
        alert_time = alert.get("timestamp", "")
        if alert_time:
            alert_dt = datetime.fromisoformat(alert_time.replace("Z", "+00:00"))
        else:
            alert_dt = datetime.now(tz=timezone.utc)

        from_time = (alert_dt - timedelta(minutes=time_window_minutes)).isoformat()
        to_time = (alert_dt + timedelta(minutes=time_window_minutes)).isoformat()

        must = [{"range": {"timestamp": {"gte": from_time, "lte": to_time}}}]
        for field in fields:
            value = alert.get(field)
            if value:
                must.append({"term": {field: value}})

        query = {"bool": {"must": must}}
        body = {
            "query": query,
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 50,
        }

        indices = ["ops_logs-*", "ops_alerts-*", "ops_cts-*"]
        all_events = []
        for index in indices:
            try:
                resp = self._client.search(index=index, body=body)
                hits = resp.get("hits", {}).get("hits", [])
                for hit in hits:
                    event = hit["_source"]
                    event["_index"] = hit.get("_index", "")
                    event["_correlation_source"] = index
                    all_events.append(event)
            except Exception:
                continue

        all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return all_events[:100]

    def search_incident_history(self, root_cause_keywords: list[str],
                                limit: int = 5) -> list[dict]:
        """Search past incidents in ops_incidents index for similar root causes."""
        if not self._client:
            return []

        should = [{"match": {"root_cause": kw}} for kw in root_cause_keywords]
        query = {"bool": {"should": should, "minimum_should_match": 1}}
        body = {
            "query": query,
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": limit,
        }

        try:
            resp = self._client.search(index="ops_incidents-*", body=body)
            return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
        except Exception:
            return []

    def index_incident(self, incident: dict) -> str:
        """Index a completed incident record into ops_incidents.

        Returns document ID.
        """
        if not self._client:
            return ""

        index_name = f"ops_incidents-{datetime.now(tz=timezone.utc).strftime('%Y.%m')}"
        body = {
            **incident,
            "timestamp": incident.get("timestamp", datetime.now(tz=timezone.utc).isoformat()),
        }

        try:
            resp = self._client.index(index=index_name, body=body, refresh=True)
            return resp.get("_id", "")
        except Exception:
            return ""

    def bulk_ingest(self, index_name: str, documents: list[dict]) -> int:
        """Bulk ingest documents into CSS index.

        Returns count of successfully indexed documents.
        """
        if not self._client:
            return 0

        from opensearchpy.helpers import bulk

        actions = [
            {"_index": index_name, "_source": doc}
            for doc in documents
        ]

        try:
            success, errors = bulk(self._client, actions, raise_on_error=False)
            return success
        except Exception:
            return 0
