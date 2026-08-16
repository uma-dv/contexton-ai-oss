"""
Bridge between Understand-Anything knowledge graphs and ContextOn.AI OSS.

Converts Understand-Anything code analysis output into ContextOn's
knowledge graph format, adding confidence scoring and failure learning
to codebase knowledge.

Understand-Anything creates:
  - .ua/knowledge-graph.json (structure + semantic summaries)
  - Code understanding via tree-sitter + LLM pipeline

ContextOn.AI OSS adds:
  - Confidence tracking (🟢🟡🔴) for every fact
  - Failure learning (wrong summaries penalized)
  - Developer correction → confidence improvement

Usage:
    graph = ContextGraph(data_dir="./codebase_memory")
    result = ingest_from_ua(graph, ".ua/knowledge-graph.json")
"""

import json
from typing import Dict, Any, List, Tuple
from .text_utils import utc_iso_now


# Node type mapping: Understand-Anything → ContextOn
_UA_TYPE_MAP = {
    "file": "fact",
    "function": "fact",
    "class": "fact",
    "interface": "fact",
    "module": "fact",
    "variable": "fact",
    "type": "fact",
    "enum": "fact",
    "constant": "fact",
    "directory": "entity",
}

# Edge type mapping: Understand-Anything → ContextOn
_UA_EDGE_MAP = {
    "contains": "depends_on",
    "defines": "depends_on",
    "imports": "related_to",
    "uses": "related_to",
    "extends": "supports",
    "implements": "supports",
    "calls": "depends_on",
    "reads": "related_to",
    "writes": "related_to",
    "configures": "related_to",
}


def _ua_node_content(node: Dict[str, Any]) -> str:
    """Build a human-readable content string from a UA node."""
    node_id = node.get("id", "")
    node_type = node.get("type", "")
    summary = node.get("summary", "")

    if summary:
        return f"[{node_type}] {node_id}: {summary}"
    return f"[{node_type}] {node_id}"


def _ua_node_metadata(node: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata fields from a UA node."""
    meta = node.get("metadata", {})
    return {
        "ua_id": node.get("id", ""),
        "ua_type": node.get("type", ""),
        "language": meta.get("language", ""),
        "path": meta.get("path", ""),
        "start_line": meta.get("start_line", 0),
        "end_line": meta.get("end_line", 0),
        "imported_from": "understand-anything",
    }


def ingest_from_ua(
    context_graph,
    ua_graph_path: str,
    agent_id: str = "understand-anything",
) -> Dict[str, Any]:
    """
    Ingest an Understand-Anything knowledge graph into ContextOn.AI OSS.

    Reads the `.ua/knowledge-graph.json` file produced by Understand-Anything,
    converts nodes and edges to ContextOn's format, and stores them with
    initial confidence scores.

    Args:
        context_graph: ContextGraph instance to ingest into
        ua_graph_path: Path to the `.ua/knowledge-graph.json` file
        agent_id: Agent ID to tag imported knowledge with

    Returns:
        Dict with ingestion summary
    """
    with open(ua_graph_path, "r", encoding="utf-8") as f:
        ua_graph = json.load(f)

    ua_nodes = ua_graph.get("nodes", [])
    ua_edges = ua_graph.get("edges", [])

    # Map UA node IDs → ContextOn node IDs
    ua_to_co: Dict[str, str] = {}

    ingested_nodes = 0
    skipped_nodes = 0

    # Ingest nodes
    for ua_node in ua_nodes:
        content = _ua_node_content(ua_node)
        if len(content) < 5:
            skipped_nodes += 1
            continue

        ua_type = ua_node.get("type", "")
        co_type = _UA_TYPE_MAP.get(ua_type, "fact")

        # Code summaries start at 0.7 confidence (needs developer verification)
        confidence = 0.7

        # Summaries with very short text may be less reliable
        summary = ua_node.get("summary", "")
        if len(summary) < 10:
            confidence = 0.5

        nid = context_graph.add_node(
            content=content,
            node_type=co_type,
            source=agent_id,
            confidence=confidence,
            tag="extracted",
            metadata=_ua_node_metadata(ua_node),
        )
        ua_to_co[ua_node.get("id", "")] = nid
        ingested_nodes += 1

    ingested_edges = 0

    # Ingest edges
    for ua_edge in ua_edges:
        src_ua = ua_edge.get("source", "")
        tgt_ua = ua_edge.get("target", "")

        src_co = ua_to_co.get(src_ua)
        tgt_co = ua_to_co.get(tgt_ua)

        if src_co and tgt_co:
            ua_edge_type = ua_edge.get("type", "")
            co_edge_type = _UA_EDGE_MAP.get(ua_edge_type, "related_to")
            weight = ua_edge.get("confidence", 0.8)

            context_graph.add_edge(
                source_id=src_co,
                target_id=tgt_co,
                edge_type=co_edge_type,
                weight=weight,
                tag="extracted",
                rationale=f"imported from Understand-Anything: {ua_edge_type}",
            )
            ingested_edges += 1

    context_graph._dirty = True
    context_graph._save()

    return {
        "nodes_ingested": ingested_nodes,
        "edges_ingested": ingested_edges,
        "nodes_skipped": skipped_nodes,
        "ua_nodes_total": len(ua_nodes),
        "ua_edges_total": len(ua_edges),
        "message": (
            f"Ingested {ingested_nodes} code knowledge nodes and "
            f"{ingested_edges} relationships from Understand-Anything. "
            f"Run record_success/record_failure to refine confidence."
        ),
    }


def query_code(
    context_graph,
    query: str,
    min_confidence: float = 0.3,
    max_results: int = 5,
) -> List[Dict]:
    """
    Query code knowledge with confidence-ranked results.

    Filters out low-confidence summaries and ranks by both relevance
    and confidence. Shows 🟢🟡🔴 badges for each result.

    Args:
        context_graph: ContextGraph instance
        query: Search query
        min_confidence: Minimum confidence threshold
        max_results: Maximum results to return

    Returns:
        List of matching code facts with confidence scores
    """
    results = context_graph.query(
        query=query,
        min_confidence=min_confidence,
        max_results=max_results,
    )

    # Enrich with code-specific metadata
    enriched = []
    for r in results:
        node = r["node"]
        meta = node.get("metadata", {})
        enriched.append({
            "content": node.get("content", ""),
            "confidence": r["confidence"],
            "badge": r["badge"],
            "path": meta.get("path", ""),
            "language": meta.get("language", ""),
            "lines": f"{meta.get('start_line', 0)}-{meta.get('end_line', 0)}",
        })

    return enriched
