"""LlamaIndex knowledge base for O&M runbooks and past incidents.

Uses CSS/OpenSearch as vector store. Reuses enterprise-rag-agent pattern.
Falls back to CSS direct query when LlamaIndex is not installed.
"""

from typing import Optional

from ops_agent_config import OpsAgentConfig

try:
    from llama_index.core import VectorStoreIndex, StorageContext, Settings
    from llama_index.vector_stores.opensearch import OpenSearchVectorStore
    HAS_LLAMAINDEX = True
except ImportError:
    HAS_LLAMAINDEX = False


class OpsKnowledgeBase:
    """Knowledge base for O&M runbooks and past incidents.

    Uses LlamaIndex + CSS/OpenSearch for hybrid keyword + vector search.
    Falls back to direct CSS query when LlamaIndex is not installed.
    """

    def __init__(self, config: OpsAgentConfig):
        self.config = config
        self._index = None
        if HAS_LLAMAINDEX:
            self._vector_store = self._build_vector_store()

    def _build_vector_store(self):
        return OpenSearchVectorStore(
            endpoint=self.config.css_endpoint,
            index="ops_knowledge",
            dim=1536,
            embedding_field="embedding",
            text_field="content",
            http_auth=(self.config.css_username, self.config.css_password),
            use_ssl=True,
            verify_certs=False,
        )

    def _get_index(self):
        if self._index is None:
            storage_context = StorageContext.from_defaults(
                vector_store=self._vector_store,
            )
            self._index = VectorStoreIndex.from_documents(
                [], storage_context=storage_context,
            )
        return self._index

    def search_runbooks(self, alert_type: str, root_cause: str) -> list[dict]:
        """Search for matching runbooks given alert type and root cause."""
        if not HAS_LLAMAINDEX:
            return self._search_runbooks_css(alert_type, root_cause)

        query = f"runbook for {alert_type}: {root_cause}"
        index = self._get_index()
        query_engine = index.as_query_engine(similarity_top_k=5)

        try:
            response = query_engine.query(query)
            results = []
            for node in response.source_nodes:
                results.append({
                    "node_id": node.node_id,
                    "score": node.score,
                    "content": node.text[:500],
                    "metadata": node.metadata,
                })
            return results
        except Exception:
            return []

    def _search_runbooks_css(self, alert_type: str, root_cause: str) -> list[dict]:
        """Fallback: search runbooks via direct CSS query."""
        try:
            from opensearchpy import OpenSearch
            client = OpenSearch(
                hosts=[{"host": self.config.css_endpoint.replace("http://", "").replace("https://", "").split(":")[0],
                        "port": int(self.config.css_endpoint.rstrip("/").split(":")[-1])}],
                http_auth=(self.config.css_username, self.config.css_password),
                use_ssl=False,
                verify_certs=False,
            )
            query = {
                "size": 5,
                "query": {
                    "multi_match": {
                        "query": f"{alert_type} {root_cause}",
                        "fields": ["content", "title", "alert_type"],
                    },
                },
            }
            resp = client.search(index="ops_knowledge", body=query)
            return [
                {"node_id": h["_id"], "score": h["_score"], "content": h["_source"].get("content", "")[:500], "metadata": h["_source"]}
                for h in resp.get("hits", {}).get("hits", [])
            ]
        except Exception:
            return []

    def search_past_incidents(self, description: str, limit: int = 5) -> list[dict]:
        """Search for similar past incidents."""
        if not HAS_LLAMAINDEX:
            return []

        query = f"past incident similar to: {description}"
        index = self._get_index()
        query_engine = index.as_query_engine(similarity_top_k=limit)

        try:
            response = query_engine.query(query)
            results = []
            for node in response.source_nodes:
                results.append({
                    "node_id": node.node_id,
                    "score": node.score,
                    "content": node.text[:500],
                    "metadata": node.metadata,
                })
            return results
        except Exception:
            return []

    def index_runbook(self, runbook_path: str) -> str:
        """Index a runbook document into the knowledge base."""
        if not HAS_LLAMAINDEX:
            return ""

        from llama_index.core import Document

        try:
            with open(runbook_path) as f:
                content = f.read()

            doc = Document(
                text=content,
                metadata={
                    "type": "runbook",
                    "source": runbook_path,
                },
            )
            index = self._get_index()
            index.insert(doc)
            return doc.doc_id
        except Exception:
            return ""

    def index_incident_record(self, incident: dict) -> str:
        """Index a completed incident record for future retrieval."""
        if not HAS_LLAMAINDEX:
            return ""

        from llama_index.core import Document

        doc = Document(
            text=incident.get("root_cause", ""),
            metadata={
                "type": "incident",
                "alert_type": incident.get("alert_type", ""),
                "action_taken": incident.get("action_taken", ""),
                "outcome": incident.get("outcome", ""),
            },
        )
        index = self._get_index()
        index.insert(doc)
        return doc.doc_id
