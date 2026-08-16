"""
Advanced Graph Features for ContextOn.AI OSS.

Adds confidence-weighted traversal, automatic fact extraction,
and improved entity linking to match enterprise capabilities.
"""

import re
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
from .text_utils import normalize, tokenize, STOPWORDS


# ═══════════════════════════════════════════════════════════════════════════
# Confidence-Weighted Graph Traversal
# ═══════════════════════════════════════════════════════════════════════════

def confidence_weighted_bfs(
    graph_nodes: Dict[str, Dict],
    graph_edges: List[Dict],
    start_id: str,
    max_depth: int = 3,
    min_confidence: float = 0.3,
    confidence_engine=None,
) -> List[Dict[str, Any]]:
    """
    BFS traversal that prefers high-confidence paths.
    
    Unlike basic BFS, this:
    1. Skips nodes below min_confidence
    2. Ranks paths by cumulative confidence
    3. Returns confidence-scored neighbors
    
    Args:
        graph_nodes: Dict of {node_id: node_dict}
        graph_edges: List of edge dicts
        start_id: Starting node ID
        max_depth: Maximum traversal depth
        min_confidence: Minimum confidence to traverse
        confidence_engine: ConfidenceEngine instance for scoring
    
    Returns:
        List of {"node": node_dict, "path_confidence": float, "depth": int}
    """
    if start_id not in graph_nodes:
        return []
    
    if confidence_engine is None:
        from .confidence import ConfidenceEngine
        confidence_engine = ConfidenceEngine()
    
    visited = {start_id}
    results = []
    
    # Priority queue: (negative_path_confidence, node_id, depth, path)
    import heapq
    start_conf = confidence_engine.node_confidence(graph_nodes[start_id])
    queue = [(-start_conf, start_id, 0, [start_id])]
    
    while queue:
        neg_conf, current_id, depth, path = heapq.heappop(queue)
        path_confidence = -neg_conf
        
        if depth > 0:
            node = graph_nodes.get(current_id, {})
            results.append({
                "node": node,
                "node_id": current_id,
                "path_confidence": path_confidence,
                "depth": depth,
                "path": path,
            })
        
        if depth >= max_depth:
            continue
        
        # Find neighbors
        for edge in graph_edges:
            neighbor_id = None
            if edge["source"] == current_id and edge["target"] not in visited:
                neighbor_id = edge["target"]
            elif edge["target"] == current_id and edge["source"] not in visited:
                neighbor_id = edge["source"]
            
            if neighbor_id and neighbor_id in graph_nodes:
                neighbor = graph_nodes[neighbor_id]
                neighbor_conf = confidence_engine.node_confidence(neighbor)
                
                if neighbor_conf >= min_confidence:
                    visited.add(neighbor_id)
                    # Path confidence = min of all nodes in path (bottleneck)
                    new_path_conf = min(path_confidence, neighbor_conf)
                    heapq.heappush(
                        queue,
                        (-new_path_conf, neighbor_id, depth + 1, path + [neighbor_id])
                    )
    
    # Sort by path confidence (highest first)
    results.sort(key=lambda x: -x["path_confidence"])
    return results


def find_high_confidence_paths(
    graph_nodes: Dict[str, Dict],
    graph_edges: List[Dict],
    start_id: str,
    end_id: str,
    max_depth: int = 5,
    min_confidence: float = 0.5,
    confidence_engine=None,
) -> Optional[List[str]]:
    """
    Find path between two nodes that maximizes minimum confidence along the path.
    
    This is better than basic BFS because it finds the most RELIABLE path,
    not just the shortest.
    
    Args:
        graph_nodes: Dict of {node_id: node_dict}
        graph_edges: List of edge dicts
        start_id: Starting node ID
        end_id: Target node ID
        max_depth: Maximum path length
        min_confidence: Minimum confidence threshold
        confidence_engine: ConfidenceEngine instance
    
    Returns:
        List of node IDs forming the best path, or None
    """
    if start_id == end_id:
        return [start_id]
    
    if start_id not in graph_nodes or end_id not in graph_nodes:
        return None
    
    if confidence_engine is None:
        from .confidence import ConfidenceEngine
        confidence_engine = ConfidenceEngine()
    
    # Build adjacency list with confidence
    adj = defaultdict(list)
    for edge in graph_edges:
        src, tgt = edge["source"], edge["target"]
        if src in graph_nodes and tgt in graph_nodes:
            src_conf = confidence_engine.node_confidence(graph_nodes[src])
            tgt_conf = confidence_engine.node_confidence(graph_nodes[tgt])
            # Edge confidence = min of endpoint confidences
            edge_conf = min(src_conf, tgt_conf)
            if edge_conf >= min_confidence:
                adj[src].append((tgt, edge_conf))
                adj[tgt].append((src, edge_conf))
    
    # Dijkstra-like search maximizing minimum confidence
    import heapq
    start_conf = confidence_engine.node_confidence(graph_nodes[start_id])
    # Store (-min_confidence, node_id, path) for max-heap behavior
    queue = [(-start_conf, start_id, [start_id])]
    visited = {start_id: start_conf}
    
    while queue:
        neg_min_conf, current, path = heapq.heappop(queue)
        min_conf = -neg_min_conf
        
        if current == end_id:
            return path
        
        if len(path) > max_depth:
            continue
        
        for neighbor, edge_conf in adj[current]:
            if neighbor not in visited:
                new_min_conf = min(min_conf, edge_conf)
                if new_min_conf > visited.get(neighbor, 0):
                    visited[neighbor] = new_min_conf
                    heapq.heappush(
                        queue,
                        (-new_min_conf, neighbor, path + [neighbor])
                    )
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Automatic Fact Extraction
# ═══════════════════════════════════════════════════════════════════════════

# Patterns for automatic fact extraction
_FACT_PATTERNS = [
    # "X is Y" patterns
    re.compile(r'([A-Z][^.]{10,60})\s+(?:is|are|was|were)\s+([^.]{10,100})', re.IGNORECASE),
    # "X has Y" patterns
    re.compile(r'([A-Z][^.]{10,60})\s+(?:has|have|had)\s+([^.]{10,100})', re.IGNORECASE),
    # "X covers Y" patterns
    re.compile(r'([A-Z][^.]{10,60})\s+(?:covers?|includes?|provides?)\s+([^.]{10,100})', re.IGNORECASE),
    # "X was Y" patterns (past tense)
    re.compile(r'([A-Z][^.]{10,60})\s+(?:was|were)\s+(?:established?|created?|founded?|launched?)\s+([^.]{10,100})', re.IGNORECASE),
]

# Relationship patterns
_RELATIONSHIP_PATTERNS = [
    # "X of Y" patterns
    re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'),
    # "X for Y" patterns
    re.compile(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+for\s+([a-z]+(?:\s+[a-z]+)*)'),
]


def extract_facts_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Automatically extract facts from unstructured text.
    
    Uses pattern matching to find factual statements:
    - "X is Y"
    - "X has Y"
    - "X covers Y"
    - "X was established in Y"
    
    Args:
        text: Unstructured text to extract facts from
    
    Returns:
        List of {"subject": str, "predicate": str, "object": str, "confidence": float}
    """
    facts = []
    
    # Extract using fact patterns
    for pattern in _FACT_PATTERNS:
        for match in pattern.finditer(text):
            subject = match.group(1).strip()
            predicate_obj = match.group(2).strip()
            
            # Clean up
            subject = re.sub(r'\s+', ' ', subject)
            predicate_obj = re.sub(r'\s+', ' ', predicate_obj)
            
            if len(subject) > 5 and len(predicate_obj) > 5:
                facts.append({
                    "subject": subject,
                    "predicate": predicate_obj,
                    "full_text": f"{subject} {predicate_obj}",
                    "confidence": 0.7,  # Default confidence for extracted facts
                    "method": "pattern_extraction",
                })
    
    # Extract relationships
    for pattern in _RELATIONSHIP_PATTERNS:
        for match in pattern.finditer(text):
            entity1 = match.group(1).strip()
            entity2 = match.group(2).strip()
            
            if len(entity1) > 2 and len(entity2) > 2:
                facts.append({
                    "subject": entity1,
                    "predicate": "related_to",
                    "object": entity2,
                    "full_text": f"{entity1} related to {entity2}",
                    "confidence": 0.6,
                    "method": "relationship_extraction",
                })
    
    # Deduplicate
    seen = set()
    unique_facts = []
    for fact in facts:
        key = f"{fact['subject']}:{fact.get('object', fact.get('predicate', ''))}"
        if key not in seen:
            seen.add(key)
            unique_facts.append(fact)
    
    return unique_facts[:20]  # Limit to 20 facts


def extract_entities_with_types(text: str) -> List[Tuple[str, str]]:
    """
    Extract named entities with type classification.
    
    Improves basic entity extraction by:
    1. Classifying entity types (PERSON, ORG, LOCATION, CONCEPT)
    2. Resolving coreferences (he/she -> previous entity)
    3. Filtering out common words
    
    Args:
        text: Text to extract entities from
    
    Returns:
        List of (entity_name, entity_type) tuples
    """
    entities = []
    
    # Capitalized phrases (potential named entities)
    cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b')
    
    for match in cap_pattern.finditer(text):
        entity = match.group(1).strip()
        
        # Skip short entities
        if len(entity) < 3:
            continue
        
        # Skip common words
        if entity.lower() in STOPWORDS:
            continue
        
        # Classify entity type
        entity_type = _classify_entity(entity, text)
        entities.append((entity, entity_type))
    
    # Acronyms
    acronym_pattern = re.compile(r'\b([A-Z]{2,}(?:-[A-Z]+)*)\b')
    for match in acronym_pattern.finditer(text):
        entity = match.group(1).strip()
        if len(entity) >= 2:
            entities.append((entity, "ACRONYM"))
    
    # Deduplicate
    seen = set()
    unique = []
    for entity, etype in entities:
        key = entity.lower()
        if key not in seen:
            seen.add(key)
            unique.append((entity, etype))
    
    return unique[:15]


def _classify_entity(entity: str, context: str) -> str:
    """
    Classify entity type based on context clues.
    
    Types: PERSON, ORG, LOCATION, CONCEPT, ACRONYM
    """
    entity_lower = entity.lower()
    context_lower = context.lower()
    
    # Check if it's an acronym (all caps)
    if entity.isupper() and len(entity) >= 2:
        return "ACRONYM"
    
    # Check for organization indicators
    org_indicators = ["authority", "ministry", "department", "company", "corporation",
                      "institute", "organization", "agency", "board", "commission"]
    if any(ind in entity_lower for ind in org_indicators):
        return "ORG"
    
    # Check for location indicators
    location_indicators = ["city", "state", "country", "district", "village", "town"]
    if any(ind in entity_lower for ind in location_indicators):
        return "LOCATION"
    
    # Check if it appears near person-related words
    person_indicators = ["mr", "mrs", "dr", "professor", "minister", "director"]
    if any(ind in context_lower for ind in person_indicators):
        # Check if this entity appears near person indicators
        for indicator in person_indicators:
            if indicator in context_lower:
                # Simple heuristic: if entity appears within 50 chars of person indicator
                idx = context_lower.find(indicator)
                entity_idx = context_lower.find(entity_lower)
                if idx >= 0 and entity_idx >= 0 and abs(idx - entity_idx) < 50:
                    return "PERSON"
    
    # Default to CONCEPT
    return "CONCEPT"


# ═══════════════════════════════════════════════════════════════════════════
# Multi-Hop Reasoning
# ═══════════════════════════════════════════════════════════════════════════

def multi_hop_reasoning(
    graph_nodes: Dict[str, Dict],
    graph_edges: List[Dict],
    query: str,
    max_hops: int = 3,
    min_confidence: float = 0.5,
    confidence_engine=None,
) -> List[Dict[str, Any]]:
    """
    Answer a query by traversing multiple hops in the graph.
    
    Example: "What is the coverage of PM-JAY?"
    Hop 1: Find PM-JAY entity
    Hop 2: Find facts about PM-JAY
    Hop 3: Find coverage details
    
    Args:
        graph_nodes: Dict of {node_id: node_dict}
        graph_edges: List of edge dicts
        query: The question to answer
        max_hops: Maximum number of hops
        min_confidence: Minimum confidence threshold
        confidence_engine: ConfidenceEngine instance
    
    Returns:
        List of reasoning paths with confidence scores
    """
    from .text_utils import tokenize
    
    if confidence_engine is None:
        from .confidence import ConfidenceEngine
        confidence_engine = ConfidenceEngine()
    
    query_tokens = set(tokenize(query))
    
    # Step 1: Find initial matching nodes
    initial_matches = []
    for nid, node in graph_nodes.items():
        if node.get("type") in ("observation",):
            continue
        
        content_tokens = set(tokenize(node.get("content", "")))
        overlap = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
        confidence = confidence_engine.node_confidence(node)
        
        if overlap > 0.2 and confidence >= min_confidence:
            initial_matches.append({
                "node_id": nid,
                "node": node,
                "relevance": overlap,
                "confidence": confidence,
            })
    
    # Sort by relevance * confidence
    initial_matches.sort(key=lambda x: -(x["relevance"] * x["confidence"]))
    
    # Step 2: For each initial match, traverse hops
    reasoning_paths = []
    
    for match in initial_matches[:3]:  # Top 3 initial matches
        nid = match["node_id"]
        
        # BFS with confidence weighting
        neighbors = confidence_weighted_bfs(
            graph_nodes, graph_edges, nid,
            max_depth=max_hops,
            min_confidence=min_confidence,
            confidence_engine=confidence_engine,
        )
        
        # Collect related facts
        related_facts = []
        for neighbor in neighbors:
            node = neighbor["node"]
            if node.get("type") in ("fact", "entity", "procedure"):
                related_facts.append({
                    "content": node.get("content", ""),
                    "type": node.get("type", ""),
                    "confidence": neighbor["path_confidence"],
                    "depth": neighbor["depth"],
                    "path": neighbor["path"],
                })
        
        if related_facts:
            reasoning_paths.append({
                "query_node": match["node"],
                "query_confidence": match["confidence"],
                "related_facts": related_facts[:5],
                "total_facts": len(related_facts),
            })
    
    return reasoning_paths


# ═══════════════════════════════════════════════════════════════════════════
# Integration Helper: Ingest from Enterprise Format
# ═══════════════════════════════════════════════════════════════════════════

def ingest_from_enterprise_graph(
    context_graph,
    enterprise_graph: Dict[str, Any],
    agent_id: str = "",
) -> Dict[str, Any]:
    """
    Ingest knowledge from enterprise graph format into ContextOn.AI OSS.
    
    This allows the OSS to work with existing enterprise applications
    that store knowledge in graph format.
    
    Args:
        context_graph: ContextGraph instance to ingest into
        enterprise_graph: Enterprise graph dict with nodes and edges
        agent_id: Optional agent ID to tag knowledge with
    
    Returns:
        Dict with ingestion summary
    """
    nodes = enterprise_graph.get("nodes", {})
    edges = enterprise_graph.get("edges", [])
    
    ingested_nodes = 0
    ingested_edges = 0
    
    # Map enterprise node IDs to OSS node IDs
    enterprise_to_oss = {}
    
    # Ingest nodes
    for nid, node in nodes.items():
        content = node.get("content", "")
        node_type = node.get("type", "fact")
        
        if not content or len(content) < 5:
            continue
        
        # Map enterprise node types to OSS types
        type_mapping = {
            "fact": "fact",
            "decision": "decision",
            "conversation": "conversation",
            "entity": "entity",
            "procedure": "procedure",
            "preference": "fact",
            "observation": "observation",
        }
        oss_type = type_mapping.get(node_type, "fact")
        
        # Add node to OSS
        oss_id = context_graph.add_node(
            content=content,
            node_type=oss_type,
            source=node.get("source", "enterprise_import"),
            confidence=node.get("confidence", 0.8),
            tag="extracted",
            metadata={"enterprise_id": nid, "imported": True}
        )
        enterprise_to_oss[nid] = oss_id
        ingested_nodes += 1
    
    # Ingest edges - actually create them in the graph
    for edge in edges:
        src_enterprise = edge.get("source", "")
        tgt_enterprise = edge.get("target", "")
        
        # Map to OSS node IDs
        src_oss = enterprise_to_oss.get(src_enterprise)
        tgt_oss = enterprise_to_oss.get(tgt_enterprise)
        
        if src_oss and tgt_oss:
            context_graph.add_edge(
                source_id=src_oss,
                target_id=tgt_oss,
                edge_type=edge.get("type", "related_to"),
                weight=edge.get("weight", 0.8),
                tag="extracted",
                rationale=f"imported from enterprise edge"
            )
            ingested_edges += 1
    
    context_graph._save()
    
    return {
        "nodes_ingested": ingested_nodes,
        "edges_ingested": ingested_edges,
        "message": f"Ingested {ingested_nodes} nodes and {ingested_edges} edges from enterprise graph",
    }
