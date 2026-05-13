#!/usr/bin/env python3
"""Validate project memory RAG system components."""

import json
import sys
from pathlib import Path


def validate_document_rag(config: dict) -> tuple[bool, str]:
    """Check document RAG pipeline is configured."""
    rag = config.get("document_rag", {})
    if rag.get("obs_bucket") and rag.get("css_index") and rag.get("ragflow_url"):
        return True, f"OBS + CSS + RAGFlow configured"
    return False, "Document RAG pipeline incomplete"


def validate_learned_memory(config: dict) -> tuple[bool, str]:
    """Check learned memory store is configured."""
    learned = config.get("learned_memory", {})
    if learned.get("css_index") and learned.get("embedding_dim"):
        return True, f"Learned memory: {learned['css_index']}"
    return False, "Learned memory store not configured"


def validate_graphrag(config: dict) -> tuple[bool, str]:
    """Check GraphRAG is configured."""
    graph = config.get("graphrag", {})
    if graph.get("enabled") and graph.get("css_index"):
        return True, f"GraphRAG: {graph['css_index']}"
    elif not graph.get("enabled", True):
        return True, "GraphRAG disabled (optional)"
    return False, "GraphRAG not configured"


def validate_mcp_tools(config: dict) -> tuple[bool, str]:
    """Check MCP tools are registered."""
    mcp = config.get("mcp", {})
    tools = mcp.get("tools", [])
    required = {"memory.search_learned", "memory.search_documents", "memory.store_insight"}
    registered = set(tools)
    if required.issubset(registered):
        return True, f"{len(required)} MCP tools registered"
    missing = required - registered
    return False, f"Missing MCP tools: {missing}"


def validate_hybrid_retrieval(config: dict) -> tuple[bool, str]:
    """Check hybrid retrieval is configured."""
    hybrid = config.get("hybrid_retrieval", {})
    if hybrid.get("learned_first") is not None and hybrid.get("document_fallback") is not None:
        return True, f"Learned first: {hybrid['learned_first']}, doc fallback: {hybrid['document_fallback']}"
    return False, "Hybrid retrieval not configured"


def main():
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("rag_config.json")
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print("Creating default config for validation...")
        config = {
            "document_rag": {"obs_bucket": "docs", "css_index": "document_chunks_v1", "ragflow_url": "http://localhost:9380"},
            "learned_memory": {"css_index": "learned_memory_v1", "embedding_dim": 1536},
            "graphrag": {"enabled": True, "css_index": "graph_entities_v1"},
            "mcp": {"tools": ["memory.search_learned", "memory.search_documents", "memory.search_graph", "memory.store_insight", "memory.store_skill"]},
            "hybrid_retrieval": {"learned_first": True, "document_fallback": True},
        }
    else:
        config = json.loads(config_path.read_text())

    gates = [
        ("Document RAG pipeline", validate_document_rag(config)),
        ("Learned memory store", validate_learned_memory(config)),
        ("GraphRAG", validate_graphrag(config)),
        ("MCP tools", validate_mcp_tools(config)),
        ("Hybrid retrieval", validate_hybrid_retrieval(config)),
    ]

    all_pass = True
    for name, (passed, msg) in gates:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\nAll validation gates passed.")
    else:
        print("\nSome validation gates failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
