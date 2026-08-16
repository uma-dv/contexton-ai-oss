"""
Core graph data structure for ContextOn.AI OSS.

Implements a knowledge graph with confidence scoring and failure learning.
"""

import json
import hashlib
import os
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
from .confidence import ConfidenceEngine
from .failure_learning import FailureLearningEngine
from .quality import QualityBadges
from .text_utils import normalize, tokenize, utc_iso_now
from .entities import extract_entities, is_alias, resolve_alias
from .lifecycle import (
    STATE_NEW, STATE_TRUSTED, STATE_USED, STATE_SUCCESS, STATE_FAILURE,
    STATE_REINFORCED, STATE_SUSPECT, STATE_QUARANTINED, STATE_REVERIFIED,
    VALID_TRANSITIONS, can_transition, get_lifecycle_summary,
)
from .advanced import (
    confidence_weighted_bfs,
    find_high_confidence_paths,
    extract_facts_from_text,
    extract_entities_with_types,
    multi_hop_reasoning,
    ingest_from_enterprise_graph,
)


# Node types
NODE_FACT = "fact"
NODE_DECISION = "decision"
NODE_CONVERSATION = "conversation"
NODE_ENTITY = "entity"
NODE_PROCEDURE = "procedure"
NODE_TOOL = "tool"
NODE_OBSERVATION = "observation"

# Edge types
EDGE_CAUSED_BY = "caused_by"
EDGE_RELATED_TO = "related_to"
EDGE_DEPENDS_ON = "depends_on"
EDGE_LEARNED_FROM = "learned_from"
EDGE_CONTRADICTS = "contradicts"
EDGE_SUPPORTS = "supports"
EDGE_NEXT = "next"

# Confidence tags
TAG_EXTRACTED = "extracted"
TAG_INFERRED = "inferred"
TAG_AMBIGUOUS = "ambiguous"


class ContextGraph:
    """
    A knowledge graph with confidence scoring and failure learning.
    
    Unlike simple knowledge graphs, ContextOn.AI OSS:
    - Tracks confidence for every node and edge
    - Learns from failures (marks unreliable paths)
    - Suggests questions the graph can answer
    - Shows quality badges (🟢🟡🔴)
    
    Example:
        graph = ContextGraph()
        
        # Ingest knowledge
        graph.ingest("What is PM-JAY?", "Health insurance for poor families")
        
        # Query with confidence ranking
        results = graph.query("PM-JAY coverage")
        
        # Record failure (agent gave wrong answer)
        graph.record_failure(
            query="What is PM-JAY?",
            answer="It's a housing scheme",
            reason="Incorrect - it's health insurance"
        )
        
        # Get suggestions
        suggestions = graph.suggest_questions()
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the context graph.
        
        Args:
            data_dir: Directory to persist graph data. If None, uses in-memory only.
        """
        self.data_dir = data_dir
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self.metadata = {
            "created_at": utc_iso_now(),
            "updated_at": utc_iso_now(),
            "node_count": 0,
            "edge_count": 0,
        }
        
        # Initialize engines
        self.confidence_engine = ConfidenceEngine()
        self.failure_engine = FailureLearningEngine(self)
        self.quality_badges = QualityBadges()
        
        # Entity resolution index: normalized name -> canonical entity node id
        self.entity_index: Dict[str, str] = {}
        # Canonical entity name -> list of aliases
        self.entity_aliases: Dict[str, List[str]] = {}
        # Tool registry: tool name -> node id
        self.tools: Dict[str, str] = {}
        
        # Performance: dirty flag for batch saving
        self._dirty = False
        
        # Load existing data if available
        if data_dir:
            self._load()
    
    def _generate_id(self, content: str, node_type: str) -> str:
        """Generate a unique ID for a node."""
        return hashlib.sha256(f"{node_type}:{content[:200]}".encode()).hexdigest()[:12]
    
    def _load(self):
        """Load graph from disk."""
        path = os.path.join(self.data_dir, "graph.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
                    self.metadata = data.get("metadata", self.metadata)
                    self.entity_index = data.get("entity_index", {})
                    self.entity_aliases = data.get("entity_aliases", {})
                    self.tools = data.get("tools", {})
            except (json.JSONDecodeError, IOError):
                pass
        
        # Rebuild entity index if it was missing (e.g. older saves)
        if not self.entity_index:
            for nid, node in self.nodes.items():
                if node.get("type") == NODE_ENTITY:
                    self.entity_index[normalize(node.get("content", ""))] = nid
        
        # Rebuild tool registry if it was missing (e.g. older saves)
        if not self.tools:
            for nid, node in self.nodes.items():
                if node.get("type") == NODE_TOOL:
                    self.tools[node.get("content", "")] = nid
    
    def _save(self):
        """Save graph to disk (only if dirty)."""
        if not self.data_dir:
            return
        if not self._dirty:
            return
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.metadata["updated_at"] = utc_iso_now()
        self.metadata["node_count"] = len(self.nodes)
        self.metadata["edge_count"] = len(self.edges)
        
        path = os.path.join(self.data_dir, "graph.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "nodes": self.nodes,
                "edges": self.edges,
                "metadata": self.metadata,
                "entity_index": self.entity_index,
                "entity_aliases": self.entity_aliases,
                "tools": self.tools,
            }, f, indent=2, ensure_ascii=False)
        
        self._dirty = False
    
    def save(self):
        """Force save graph to disk (clears dirty flag)."""
        self._dirty = True
        self._save()
    
    def add_node(
        self,
        content: str,
        node_type: str = NODE_FACT,
        source: str = "",
        confidence: float = 1.0,
        tag: str = TAG_EXTRACTED,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Add a node to the graph.
        
        Args:
            content: The knowledge content
            node_type: Type of node (fact, entity, conversation, etc.)
            source: Where this knowledge came from
            confidence: Initial confidence score (0.0-1.0)
            tag: Whether this was EXTRACTED or INFERRED
            metadata: Additional metadata
        
        Returns:
            Node ID
        """
        nid = self._generate_id(content, node_type)
        now = utc_iso_now()
        
        if nid in self.nodes:
            # Node exists - update it
            self.nodes[nid]["mentions"] += 1
            self.nodes[nid]["last_seen"] = now
            self.nodes[nid]["last_verified"] = now
        else:
            # Create new node
            self.nodes[nid] = {
                "id": nid,
                "type": node_type,
                "content": content[:2000],
                "content_lower": normalize(content[:2000]),
                "source": source,
                "confidence": confidence,
                "original_confidence": confidence,  # Ceiling for bounded recovery
                "tag": tag,
                "mentions": 1,
                "created_at": now,
                "last_seen": now,
                "last_verified": now,
                "failure_count": 0,
                "success_count": 0,
                "query_count": 0,
                "state": STATE_TRUSTED,  # Trust lifecycle state
            }
            if metadata:
                self.nodes[nid]["metadata"] = metadata
        
        self._dirty = True
        return nid
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str = EDGE_RELATED_TO,
        weight: float = 1.0,
        tag: str = TAG_EXTRACTED,
        rationale: str = "",
    ) -> None:
        """
        Add an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of relationship
            weight: Edge weight (0.0-1.0)
            tag: EXTRACTED or INFERRED
            rationale: WHY this connection exists (human-readable)
        """
        # Check for duplicate
        for e in self.edges:
            if e["source"] == source_id and e["target"] == target_id and e["type"] == edge_type:
                # Update existing edge
                e["weight"] = min(1.0, e["weight"] + 0.1)
                e["mentions"] = e.get("mentions", 1) + 1
                e["last_seen"] = utc_iso_now()
                self._dirty = True
                return
        
        # Create new edge
        now = utc_iso_now()
        self.edges.append({
            "source": source_id,
            "target": target_id,
            "type": edge_type,
            "weight": weight,
            "confidence": weight,  # Initial confidence = weight
            "tag": tag,
            "rationale": rationale,
            "verified": False,
            "failure_count": 0,
            "success_count": 0,
            "last_outcome": None,
            "created_at": now,
            "last_seen": now,
        })
        self._dirty = True
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def transition_state(self, node_id: str, new_state: str) -> Dict[str, Any]:
        """
        Transition a node to a new trust lifecycle state.
        
        Enforces valid transitions per paper Section IV.E:
            NEW → TRUSTED → USED → SUCCESS/FAILURE → REINFORCED/SUSPECT → QUARANTINED → REVERIFIED
        
        Args:
            node_id: Node to transition
            new_state: Target state
        
        Returns:
            Dict with transition result
        """
        node = self.nodes.get(node_id)
        if not node:
            return {"status": "error", "message": f"Node {node_id} not found"}
        
        current = node.get("state", STATE_TRUSTED)
        valid = VALID_TRANSITIONS.get(current, set())
        
        if new_state not in valid:
            return {
                "status": "error",
                "message": f"Invalid transition: {current} → {new_state}. Valid: {valid}",
            }
        
        node["state"] = new_state
        node["last_seen"] = utc_iso_now()
        self._dirty = True
        self._save()
        
        return {
            "status": "transitioned",
            "node_id": node_id,
            "from": current,
            "to": new_state,
        }
    
    def get_lifecycle_summary(self) -> Dict[str, Any]:
        """
        Get summary of all nodes by trust lifecycle state.
        
        Returns:
            Dict with state counts and lists
        """
        by_state: Dict[str, List[Dict]] = {}
        for nid, node in self.nodes.items():
            state = node.get("state", STATE_TRUSTED)
            by_state.setdefault(state, []).append({
                "id": nid,
                "content": node.get("content", "")[:100],
                "confidence": round(self.confidence_engine.node_confidence(node), 3),
            })
        
        return {
            "state_counts": {s: len(nodes) for s, nodes in by_state.items()},
            "by_state": by_state,
            "quarantined_count": len(by_state.get(STATE_QUARANTINED, [])),
            "total_nodes": len(self.nodes),
        }
    
    def quarantine_low_confidence(self, threshold: float = 0.3) -> Dict[str, Any]:
        """
        Auto-quarantine nodes below confidence threshold.
        
        Paper Section IV.E: "Memories below a configurable confidence
        threshold are excluded from retrieval, implementing automatic
        quarantine of unreliable knowledge."
        
        Args:
            threshold: Confidence threshold (default 0.3)
        
        Returns:
            Dict with quarantine results
        """
        quarantined = []
        for nid, node in self.nodes.items():
            # Skip observation/bookkeeping nodes
            if node.get("type") == NODE_OBSERVATION:
                continue
            # Skip already quarantined nodes
            if node.get("state") == STATE_QUARANTINED:
                continue
            
            confidence = self.confidence_engine.node_confidence(node)
            if confidence < threshold:
                node["state"] = STATE_QUARANTINED
                node["last_seen"] = utc_iso_now()
                quarantined.append({
                    "id": nid,
                    "content": node.get("content", "")[:100],
                    "confidence": round(confidence, 3),
                })
        
        if quarantined:
            self._dirty = True
            self._save()
        
        return {
            "quarantined": len(quarantined),
            "threshold": threshold,
            "nodes": quarantined,
        }
    
    def unreinstate_quarantined(self, node_id: str) -> Dict[str, Any]:
        """
        Manually reinstate a quarantined node after re-verification.
        
        Args:
            node_id: Quarantined node to reinstate
        
        Returns:
            Dict with reinstatement result
        """
        node = self.nodes.get(node_id)
        if not node:
            return {"status": "error", "message": f"Node {node_id} not found"}
        
        if node.get("state") != STATE_QUARANTINED:
            return {"status": "error", "message": f"Node is not quarantined (state: {node.get('state')})"}
        
        node["state"] = STATE_REVERIFIED
        node["last_verified"] = utc_iso_now()
        node["last_seen"] = utc_iso_now()
        self._dirty = True
        self._save()
        
        return {
            "status": "reinstated",
            "node_id": node_id,
            "state": STATE_REVERIFIED,
        }
    
    def get_edge(self, source_id: str, target_id: str, edge_type: str) -> Optional[Dict]:
        """Get an edge by source, target, and type."""
        for e in self.edges:
            if e["source"] == source_id and e["target"] == target_id and e["type"] == edge_type:
                return e
        return None
    
    def get_neighbors(self, node_id: str, depth: int = 1) -> Dict[str, Dict]:
        """
        Get neighbors of a node up to given depth.
        
        Returns dict of {node_id: {"node": node_dict, "edge": edge_dict, "depth": int}}
        """
        if node_id not in self.nodes:
            return {}
        
        visited = {node_id}
        current = {node_id}
        result = {}
        
        for d in range(depth):
            next_level = set()
            for nid in current:
                for e in self.edges:
                    neighbor = None
                    if e["source"] == nid and e["target"] not in visited:
                        neighbor = e["target"]
                    elif e["target"] == nid and e["source"] not in visited:
                        neighbor = e["source"]
                    
                    if neighbor:
                        next_level.add(neighbor)
                        visited.add(neighbor)
                        result[neighbor] = {
                            "node": self.nodes.get(neighbor, {}),
                            "edge": e,
                            "depth": d + 1,
                        }
            current = next_level
        
        return result
    
    def find_path(self, start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[str]]:
        """
        Find shortest path between two nodes using BFS.
        
        Returns list of node IDs forming the path, or None if no path exists.
        """
        if start_id == end_id:
            return [start_id]
        
        if start_id not in self.nodes or end_id not in self.nodes:
            return None
        
        visited = {start_id}
        queue = [(start_id, [start_id])]
        
        for _ in range(max_depth):
            next_queue = []
            for nid, path in queue:
                for e in self.edges:
                    neighbor = None
                    if e["source"] == nid:
                        neighbor = e["target"]
                    elif e["target"] == nid:
                        neighbor = e["source"]
                    
                    if neighbor and neighbor not in visited:
                        new_path = path + [neighbor]
                        if neighbor == end_id:
                            return new_path
                        visited.add(neighbor)
                        next_queue.append((neighbor, new_path))
            
            queue = next_queue
            if not queue:
                break
        
        return None
    
    def god_nodes(self, top_n: int = 5) -> List[Dict]:
        """
        Find the most-connected nodes (highest degree).
        
        These are the "god nodes" - concepts that everything connects through.
        """
        degree = defaultdict(int)
        for e in self.edges:
            degree[e["source"]] += 1
            degree[e["target"]] += 1
        
        ranked = sorted(degree.items(), key=lambda x: -x[1])[:top_n]
        return [{"node": self.nodes.get(nid, {}), "degree": deg} for nid, deg in ranked if nid in self.nodes]
    
    def detect_communities(self) -> Dict[str, List[str]]:
        """
        Detect communities using connected components.
        
        Returns dict of {community_id: [node_ids]}
        """
        # Build adjacency list
        adj = defaultdict(set)
        for e in self.edges:
            adj[e["source"]].add(e["target"])
            adj[e["target"]].add(e["source"])
        
        # BFS to find connected components
        visited = set()
        communities = {}
        comp_id = 0
        
        for nid in self.nodes:
            if nid in visited:
                continue
            
            component = []
            queue = [nid]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in adj[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            if component:
                communities[f"community_{comp_id}"] = component
                comp_id += 1
        
        return communities
    
    def ingest(
        self,
        query: str,
        answer: str,
        agent_id: str = "",
        confidence: float = 0.8,
        session_id: str = "",
    ) -> Dict[str, Any]:
        """
        Ingest a conversation turn into the graph.
        
        This is the main entry point for adding knowledge.
        
        Args:
            query: The user's question
            answer: The agent's answer
            agent_id: Which agent provided this answer (used for per-agent scoping)
            confidence: Agent's confidence in the answer (0.0-1.0)
            session_id: Optional session/thread identifier for context injection
        
        Returns:
            Dict with ingestion results
        """
        # Add conversation node
        conv_content = f"Q: {query[:500]} A: {answer[:500]}"
        conv_meta = {"query": query[:500], "answer": answer[:500]}
        if session_id:
            conv_meta["session_id"] = session_id
        conv_id = self.add_node(
            content=conv_content,
            node_type=NODE_CONVERSATION,
            source=agent_id or "user",
            confidence=confidence,
            tag=TAG_EXTRACTED,
            metadata=conv_meta
        )
        if agent_id:
            self.nodes[conv_id]["agent_id"] = agent_id
        
        # Extract entities from query and answer, resolving aliases
        # so duplicates like "PM-JAY" and "Pradhan Mantri Jan Arogya
        # Yojana" map to the same node.
        query_entities = self._extract_entities(query)
        answer_entities = self._extract_entities(answer)
        
        entity_ids = []
        for entity, etype in query_entities + answer_entities:
            eid, canonical = self._get_or_create_entity(entity, etype)
            entity_ids.append(eid)
            if agent_id:
                self.nodes[eid].setdefault("agent_id", agent_id)
            self.add_edge(
                source_id=conv_id,
                target_id=eid,
                edge_type=EDGE_RELATED_TO,
                weight=0.8,
                rationale=f"conversation mentions {canonical}"
            )
        
        # Add facts from answer
        sentences = [s.strip() for s in answer.replace(".", "!").replace("?", "!").split("!") if len(s.strip()) > 20]
        fact_ids = []
        for sentence in sentences[:5]:
            fid = self.add_node(
                content=sentence,
                node_type=NODE_FACT,
                source="extraction",
                tag=TAG_EXTRACTED
            )
            if agent_id:
                self.nodes[fid]["agent_id"] = agent_id
            fact_ids.append(fid)
            self.add_edge(
                source_id=conv_id,
                target_id=fid,
                edge_type=EDGE_LEARNED_FROM,
                weight=0.9,
                rationale="fact from answer"
            )
        
        # Link facts to entities
        for fid in fact_ids:
            for eid in entity_ids[:5]:
                self.add_edge(
                    source_id=fid,
                    target_id=eid,
                    edge_type=EDGE_RELATED_TO,
                    weight=0.6
                )
        
        # Temporal link to previous conversation
        conv_nodes = [(nid, n) for nid, n in self.nodes.items()
                      if n.get("type") == NODE_CONVERSATION and nid != conv_id]
        if conv_nodes:
            latest = max(conv_nodes, key=lambda x: x[1].get("last_seen", ""))
            self.add_edge(
                source_id=latest[0],
                target_id=conv_id,
                edge_type=EDGE_NEXT,
                weight=1.0,
                tag=TAG_EXTRACTED,
                rationale="temporal sequence"
            )
        
        return {
            "conversation_id": conv_id,
            "entities_added": len(entity_ids),
            "facts_added": len(fact_ids),
            "confidence": confidence,
        }
    
    def _extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """Extract named entities from text."""
        return extract_entities(text)
    
    def _get_or_create_entity(self, entity: str, etype: str) -> Tuple[str, str]:
        """
        Return the node id for an entity, creating it if unknown and
        resolving aliases to existing canonical entity nodes.
        
        Returns:
            (node_id, canonical_name)
        """
        key = normalize(entity)
        if key in self.entity_index:
            return self.entity_index[key], entity
        
        # Alias match against known entities (acronyms, initials, containment)
        for known_key, existing_id in self.entity_index.items():
            existing_name = self.nodes.get(existing_id, {}).get("content", "")
            if existing_name and is_alias(entity, existing_name):
                self.entity_aliases.setdefault(existing_name, []).append(entity)
                return existing_id, existing_name
        
        eid = self.add_node(
            content=entity,
            node_type=NODE_ENTITY,
            source="extraction",
            tag=TAG_EXTRACTED,
            metadata={"entity_type": etype}
        )
        self.entity_index[key] = eid
        return eid, entity
    
    def get_aliases(self, entity: str = "") -> Dict[str, List[str]]:
        """
        Get alias mappings. If entity is given, only its aliases are
        returned; otherwise all aliases are returned.
        """
        if entity:
            return {entity: self.entity_aliases.get(entity, [])}
        return dict(self.entity_aliases)
    
    def resolve_aliases(self) -> Dict[str, Any]:
        """
        Scan the graph for duplicate entity nodes and merge them into
        canonical nodes (re-pointing edges, merging mentions and
        aliases). Returns a summary of what was merged.
        """
        # Group entity nodes by canonical name
        canonical_by_id: Dict[str, str] = {}
        groups: Dict[str, List[str]] = {}
        
        entity_nodes = [
            (nid, n) for nid, n in self.nodes.items()
            if n.get("type") == NODE_ENTITY
        ]
        
        for nid, node in entity_nodes:
            name = node.get("content", "")
            canonical = resolve_alias(name, list(canonical_by_id.values()))
            canonical_by_id[nid] = canonical
            groups.setdefault(canonical, []).append(nid)
        
        merged = 0
        for canonical, ids in groups.items():
            if len(ids) <= 1:
                continue
            # Keep the first node as canonical, merge the rest into it
            keep_id = ids[0]
            for dup_id in ids[1:]:
                dup = self.nodes[dup_id]
                keep = self.nodes[keep_id]
                keep["mentions"] = keep.get("mentions", 1) + dup.get("mentions", 1)
                keep["failure_count"] = keep.get("failure_count", 0) + dup.get("failure_count", 0)
                # Re-point all edges from the duplicate to the canonical node
                for edge in self.edges:
                    if edge["source"] == dup_id:
                        edge["source"] = keep_id
                    if edge["target"] == dup_id:
                        edge["target"] = keep_id
                # Record the duplicate name as an alias
                dup_name = dup.get("content", "")
                if dup_name and dup_name != canonical:
                    self.entity_aliases.setdefault(canonical, []).append(dup_name)
                del self.nodes[dup_id]
                merged += 1
            
            # Rebuild the index for the canonical name
            self.entity_index[normalize(canonical)] = keep_id
        
        self._dirty = True
        self._save()
        return {
            "merged_nodes": merged,
            "entity_count": len([n for n in self.nodes.values() if n.get("type") == NODE_ENTITY]),
            "aliases": dict(self.entity_aliases),
        }
    
    def query(
        self,
        query: str,
        min_confidence: float = 0.0,
        max_results: int = 5,
        node_type: str = "",
        agent_id: str = "",
        include_quarantined: bool = False,
    ) -> List[Dict]:
        """
        Query the graph with confidence-ranked retrieval.
        
        Unlike simple keyword search, this:
        1. Finds relevant nodes (punctuation-insensitive token matching)
        2. Ranks by confidence (not just relevance)
        3. Never returns failure/observation bookkeeping nodes
        4. Excludes quarantined nodes (paper Section IV.E)
        5. Returns quality badges
        
        Args:
            query: Search query
            min_confidence: Minimum confidence threshold
            max_results: Maximum results to return
            node_type: Optional filter (e.g. "procedure", "tool", "entity")
            agent_id: Optional per-agent scope filter (transparency, not enforcement)
            include_quarantined: If True, include quarantined nodes in results
        
        Returns:
            List of matching nodes with confidence scores
        """
        query_words = set(tokenize(query))
        
        # Score each node
        scored = []
        for nid, node in self.nodes.items():
            # Skip failure observations - they are bookkeeping, not knowledge
            if node.get("type") == NODE_OBSERVATION and \
                    node.get("metadata", {}).get("type") == "failure":
                continue
            
            # Skip quarantined nodes unless explicitly requested (paper Section IV.E)
            if not include_quarantined and node.get("state") == STATE_QUARANTINED:
                continue
            
            # Node type filter
            if node_type and node.get("type") != node_type:
                continue
            
            # Per-agent scope filter (transparency, not enforcement)
            if agent_id and node.get("agent_id") != agent_id:
                continue
            
            content_words = set(tokenize(node.get("content", "")))
            
            # Calculate relevance (token overlap)
            overlap = len(query_words & content_words) / max(len(query_words), 1)
            
            # Get confidence (single source of truth)
            confidence = self.confidence_engine.node_confidence(node)
            
            # Combined score (relevance + confidence)
            score = overlap * 0.6 + confidence * 0.4
            
            if score > 0.1 and confidence >= min_confidence:
                scored.append({
                    "node": node,
                    "score": score,
                    "confidence": confidence,
                    "badge": self.quality_badges.get_badge(confidence),
                    "state": node.get("state", STATE_TRUSTED),
                })
                node["query_count"] = node.get("query_count", 0) + 1
        
        # Sort by score
        scored.sort(key=lambda x: -x["score"])
        
        return scored[:max_results]
    
    def record_failure(
        self,
        query: str,
        answer: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Record that an agent gave a wrong answer.
        
        This is the KEY DIFFERENTIATOR - no other tool learns from failures.
        
        Args:
            query: The original question
            answer: The wrong answer that was given
            reason: Why it was wrong
        
        Returns:
            Dict with failure recording results
        """
        return self.failure_engine.record_failure(query, answer, reason)
    
    def record_success(
        self,
        query: str,
        answer: str,
    ) -> Dict[str, Any]:
        """
        Record that an agent gave a correct answer.
        
        This increases confidence in the knowledge path.
        
        Args:
            query: The question
            answer: The correct answer
        
        Returns:
            Dict with success recording results
        """
        return self.failure_engine.record_success(query, answer)
    
    # ------------------------------------------------------------------
    # Agent capabilities: skills, tools, context, hygiene, scoping
    # ------------------------------------------------------------------
    
    def ingest_procedure(
        self,
        name: str,
        steps: List[str],
        agent_id: str = "",
        confidence: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Ingest a reusable skill/procedure ("how to" knowledge).
        
        Creates a PROCEDURE node (a skill) with each step stored as a
        linked fact node so the procedure is retrievable and its steps
        are individually traceable.
        
        Args:
            name: The skill/procedure name (e.g. "Reset password")
            steps: Ordered list of step descriptions
            agent_id: Which agent provided this skill
            confidence: Initial confidence (0.0-1.0)
        
        Returns:
            Dict with procedure_id and steps_added
        """
        pid = self.add_node(
            content=name[:500],
            node_type=NODE_PROCEDURE,
            source=agent_id or "user",
            confidence=confidence,
            tag=TAG_EXTRACTED,
            metadata={"steps": steps[:20], "skill_type": "procedure"}
        )
        if agent_id:
            self.nodes[pid]["agent_id"] = agent_id
        
        step_ids = []
        prev_id = None
        for step in steps[:20]:
            sid = self.add_node(
                content=step[:500],
                node_type=NODE_FACT,
                source="procedure_extraction",
                confidence=confidence,
                tag=TAG_EXTRACTED,
                metadata={"step_of": pid, "skill_type": "procedure"}
            )
            if agent_id:
                self.nodes[sid]["agent_id"] = agent_id
            step_ids.append(sid)
            self.add_edge(
                source_id=pid,
                target_id=sid,
                edge_type=EDGE_DEPENDS_ON,
                weight=0.9,
                rationale=f"step of procedure {name}"
            )
            if prev_id:
                self.add_edge(
                    source_id=prev_id,
                    target_id=sid,
                    edge_type=EDGE_NEXT,
                    weight=1.0,
                    rationale="next step in procedure"
                )
            prev_id = sid
        
        self._dirty = True
        self._save()
        return {
            "procedure_id": pid,
            "steps_added": len(step_ids),
            "message": f"Ingested procedure: {name}",
        }
    
    def get_procedure(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a procedure by name, with its ordered steps.
        
        Returns a dict with name, steps, and confidence, or None.
        """
        for nid, node in self.nodes.items():
            if node.get("type") == NODE_PROCEDURE and node.get("content") == name:
                step_ids = [
                    e["target"] for e in self.edges
                    if e["source"] == nid and e["type"] == EDGE_DEPENDS_ON
                ]
                steps = [self.nodes[s].get("content", "") for s in step_ids if s in self.nodes]
                return {
                    "procedure_id": nid,
                    "name": name,
                    "steps": steps,
                    "confidence": self.confidence_engine.node_confidence(node),
                    "badge": self.quality_badges.get_badge(
                        self.confidence_engine.node_confidence(node)),
                }
        return None
    
    def register_tool(
        self,
        name: str,
        description: str = "",
        agent_id: str = "",
    ) -> str:
        """
        Register a tool in the graph's tool registry memory.
        
        Tools become TOOL nodes, so they carry confidence, appear in
        query results, and can be penalized by failure learning.
        
        Args:
            name: Tool name
            description: What the tool does
            agent_id: Which agent owns/uses this tool
        
        Returns:
            Tool node id
        """
        nid = self.add_node(
            content=name[:200],
            node_type=NODE_TOOL,
            source=agent_id or "registry",
            confidence=1.0,
            tag=TAG_EXTRACTED,
            metadata={"description": description[:1000], "tool_type": "tool"}
        )
        if agent_id:
            self.nodes[nid]["agent_id"] = agent_id
        self.tools[name] = nid
        self._dirty = True
        return nid
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with their status."""
        tools = []
        for name, nid in self.tools.items():
            node = self.nodes.get(nid, {})
            confidence = self.confidence_engine.node_confidence(node)
            tools.append({
                "name": name,
                "description": node.get("metadata", {}).get("description", ""),
                "confidence": round(confidence, 3),
                "badge": self.quality_badges.get_badge(confidence),
                "failure_count": node.get("failure_count", 0),
                "success_count": node.get("success_count", 0),
            })
        return sorted(tools, key=lambda t: -t["confidence"])
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool's registry entry by name."""
        nid = self.tools.get(name)
        if not nid or nid not in self.nodes:
            return None
        node = self.nodes[nid]
        return {
            "name": name,
            "description": node.get("metadata", {}).get("description", ""),
            "confidence": round(self.confidence_engine.node_confidence(node), 3),
            "failure_count": node.get("failure_count", 0),
            "success_count": node.get("success_count", 0),
        }
    
    def record_tool_outcome(self, name: str, success: bool, error: str = "") -> Dict[str, Any]:
        """
        Record whether a tool call succeeded or failed.
        
        Failures penalize the tool node (lowering its confidence) via the
        failure learning engine; successes verify it.
        
        Args:
            name: Tool name
            success: Whether the call succeeded
            error: Error message on failure
        
        Returns:
            Dict with tool status
        """
        nid = self.tools.get(name)
        if not nid or nid not in self.nodes:
            return {"status": "error", "message": f"unknown tool: {name}"}
        node = self.nodes[nid]
        if success:
            node["success_count"] = node.get("success_count", 0) + 1
            node["last_verified"] = utc_iso_now()
            if node.get("failure_count", 0) > 0:
                node["failure_count"] = max(0, node["failure_count"] - 1)
        else:
            node["failure_count"] = node.get("failure_count", 0) + 1
            node["confidence"] = max(
                self.failure_engine.MIN_CONFIDENCE_AFTER_FAILURE,
                node["confidence"] * self.failure_engine.FAILURE_CONFIDENCE_MULTIPLIER
            )
            node.setdefault("errors", []).append(error[:200])
        self._dirty = True
        self._save()
        return {
            "status": "recorded",
            "tool": name,
            "success": success,
            "confidence": round(self.confidence_engine.node_confidence(node), 3),
            "badge": self.quality_badges.get_badge(self.confidence_engine.node_confidence(node)),
        }
    
    def get_context(
        self,
        query: str,
        session_id: str = "",
        max_tokens: int = 2000,
        min_confidence: float = 0.5,
        max_items: int = 10,
    ) -> Dict[str, Any]:
        """
        Assemble confident, badge-annotated context for an agent.
        
        This is the "auto-context injection" layer: instead of raw query
        results, an agent gets a ready-to-use context pack containing
        relevant entities, facts, and procedures - deduplicated, filtered
        by minimum confidence, and packed to a token budget.
        
        Args:
            query: The agent's current task/question
            session_id: Optional session; restricts context to that session's knowledge
            max_tokens: Rough token budget (chars/4) for the assembled text
            min_confidence: Only include knowledge at/above this confidence
            max_items: Maximum number of context items
        
        Returns:
            Dict with items, context_text, session_id, and stats
        """
        # Gather candidates: entities, facts, procedures, tools
        candidates = []
        for nid, node in self.nodes.items():
            if node.get("type") in (NODE_OBSERVATION,):
                continue
            # Session scoping (transparency, not enforcement)
            if session_id:
                node_session = node.get("metadata", {}).get("session_id", "")
                if node.get("type") != NODE_CONVERSATION or node_session != session_id:
                    continue
            confidence = self.confidence_engine.node_confidence(node)
            if confidence < min_confidence:
                continue
            # Skip conversation nodes unless session-scoped (they carry
            # the full Q/A, usually too verbose for context packs)
            if node.get("type") == NODE_CONVERSATION and not session_id:
                continue
            candidates.append((nid, node, confidence))
        
        # Rank: token overlap with query (relevance) then confidence
        query_tokens = set(tokenize(query))
        ranked = []
        for nid, node, confidence in candidates:
            content = node.get("content", "")
            overlap = len(query_tokens & set(tokenize(content))) / max(len(query_tokens), 1)
            ranked.append((overlap, confidence, nid, node))
        ranked.sort(key=lambda x: (-x[0], -x[1]))
        
        # Assemble items and text within the token budget
        items = []
        parts = []
        used_chars = 0
        budget = max_tokens * 4
        for overlap, confidence, nid, node in ranked[:max_items]:
            content = node.get("content", "")
            if node.get("type") == NODE_PROCEDURE:
                content = self._procedure_text(nid)
            entry = f"{self.quality_badges.get_badge(confidence)} [{node.get('type','')}] {content}"
            if used_chars + len(entry) > budget and parts:
                break
            items.append({
                "node_id": nid,
                "content": content[:500],
                "node_type": node.get("type"),
                "confidence": round(confidence, 3),
                "badge": self.quality_badges.get_badge(confidence),
            })
            parts.append(entry)
            used_chars += len(entry)
        
        return {
            "session_id": session_id,
            "query": query[:200],
            "items": items,
            "context_text": "\n".join(parts),
            "item_count": len(items),
            "truncated": used_chars >= budget,
        }
    
    def _procedure_text(self, pid: str) -> str:
        """Render a procedure node as readable skill text."""
        node = self.nodes.get(pid, {})
        steps = node.get("metadata", {}).get("steps", [])
        text = node.get("content", "")
        if steps:
            text += "\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        return text
    
    def get_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """
        Return all knowledge owned by a specific agent.
        
        Transparency/scoping helper - lists what an agent has stored,
        grouped by node type. This is a read filter, not enforcement.
        
        Args:
            agent_id: The agent to scope to
        
        Returns:
            Dict with agent_id and grouped node summaries
        """
        owned = [n for n in self.nodes.values() if n.get("agent_id") == agent_id]
        grouped: Dict[str, List[Dict]] = {}
        for node in owned:
            conf = self.confidence_engine.node_confidence(node)
            grouped.setdefault(node.get("type", "unknown"), []).append({
                "content": node.get("content", "")[:200],
                "confidence": round(conf, 3),
                "badge": self.quality_badges.get_badge(conf),
            })
        return {
            "agent_id": agent_id,
            "node_count": len(owned),
            "by_type": grouped,
        }
    
    def hygiene_sweep(
        self,
        max_age_days: int = 30,
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Memory hygiene report: find stale and low-confidence knowledge.
        
        This is the maintenance/schedule dimension - run it periodically
        (e.g. nightly) to keep the graph trustworthy.
        
        Args:
            max_age_days: Knowledge older than this needs re-verification
            min_confidence: Knowledge below this needs attention
        
        Returns:
            Dict with stale nodes, low-confidence nodes, and totals
        """
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        stale = []
        low_conf = []
        for nid, node in self.nodes.items():
            if node.get("type") == NODE_OBSERVATION:
                continue
            confidence = self.confidence_engine.node_confidence(node)
            if confidence < min_confidence:
                low_conf.append({
                    "node_id": nid,
                    "content": node.get("content", "")[:150],
                    "confidence": round(confidence, 3),
                    "badge": self.quality_badges.get_badge(confidence),
                })
            last_verified = node.get("last_verified")
            age_days = None
            if last_verified:
                try:
                    verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
                    age_days = max(0, (now - verified_dt).days)
                except (ValueError, TypeError):
                    age_days = None
            if age_days is not None and age_days > max_age_days:
                stale.append({
                    "node_id": nid,
                    "content": node.get("content", "")[:150],
                    "age_days": age_days,
                })
        
        return {
            "checked_nodes": len(self.nodes),
            "stale_count": len(stale),
            "low_confidence_count": len(low_conf),
            "stale_nodes": stale[:50],
            "low_confidence_nodes": low_conf[:50],
            "recommendation": (
                "Re-verify stale knowledge or record_success to refresh it."
                if stale or low_conf else "Graph is healthy."
            ),
        }
    
    def needs_reverification(
        self,
        max_age_days: int = 30,
        min_confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Return a list of nodes that need re-verification."""
        report = self.hygiene_sweep(max_age_days=max_age_days, min_confidence=min_confidence)
        return report["stale_nodes"] + report["low_confidence_nodes"]
    
    def prune(
        self,
        max_age_days: int = 90,
        min_confidence: float = 0.2,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Remove old, low-confidence knowledge (opt-in, conservative).
        
        Only observation nodes and facts below the confidence floor and
        older than max_age_days are candidates. Entities, procedures,
        tools, and recent knowledge are never pruned. Set dry_run=False
        to actually delete.
        
        Args:
            max_age_days: Minimum age to be considered
            min_confidence: Maximum confidence to be considered
            dry_run: If True, report only (no deletion)
        
        Returns:
            Dict with candidates and whether they were pruned
        """
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        candidates = []
        for nid, node in self.nodes.items():
            if node.get("type") not in (NODE_OBSERVATION, NODE_FACT):
                continue
            confidence = self.confidence_engine.node_confidence(node)
            if confidence > min_confidence:
                continue
            last_verified = node.get("last_verified")
            if not last_verified:
                continue
            try:
                verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            age_days = max(0, (now - verified_dt).days)
            if age_days >= max_age_days:
                candidates.append(nid)
        
        if not dry_run:
            for nid in candidates:
                self.edges = [e for e in self.edges if e["source"] != nid and e["target"] != nid]
                del self.nodes[nid]
            self._dirty = True
            self._save()
        
        return {
            "dry_run": dry_run,
            "candidates": len(candidates),
            "pruned": 0 if dry_run else len(candidates),
            "message": (
                f"Would prune {len(candidates)} old, low-confidence nodes."
                if dry_run else f"Pruned {len(candidates)} old, low-confidence nodes."
            ),
        }
    
    def suggest_questions(self, top_n: int = 5) -> List[Dict]:
        """
        Suggest questions the graph can answer.
        
        This helps users discover what knowledge is available.
        
        Args:
            top_n: Number of suggestions to return
        
        Returns:
            List of suggested questions with reasons
        """
        suggestions = []
        
        # 1. High-confidence entities that are rarely asked about
        for nid, node in self.nodes.items():
            if node.get("type") != NODE_ENTITY:
                continue
            confidence = self.confidence_engine.node_confidence(node)
            if node.get("query_count", 0) < 3 and confidence >= 0.7:
                content = node.get("content", "")[:100]
                suggestions.append({
                    "question": f"What is {content}?",
                    "reason": "High-confidence entity, rarely asked about",
                    "confidence": confidence,
                    "badge": self.quality_badges.get_badge(confidence),
                })
        
        # 2. High-confidence facts that mention a known entity
        entity_names = {n.get("content", "").lower() for n in self.nodes.values()
                        if n.get("type") == NODE_ENTITY}
        for nid, node in self.nodes.items():
            if node.get("type") != NODE_FACT:
                continue
            confidence = self.confidence_engine.node_confidence(node)
            if node.get("query_count", 0) < 3 and confidence >= 0.7:
                tokens = set(tokenize(node.get("content", "")))
                hits = [e for e in entity_names if any(t in e.split() for t in tokens)]
                if hits:
                    entity = max(hits, key=len)
                    suggestions.append({
                        "question": f"Tell me more about {entity.title()}",
                        "reason": "Related fact is high-confidence and rarely asked",
                        "confidence": confidence,
                        "badge": self.quality_badges.get_badge(confidence),
                    })
        
        # 3. Underexplored communities (fallback)
        communities = self.detect_communities()
        for comm_id, node_ids in communities.items():
            if len(node_ids) < 3:
                first_node = self.nodes.get(node_ids[0], {})
                if first_node.get("type") == NODE_ENTITY:
                    content = first_node.get("content", "")[:100]
                    suggestions.append({
                        "question": f"What is {content}?",
                        "reason": "Underexplored community",
                        "confidence": 0.7,
                        "badge": "🟡",
                    })
        
        # Sort by confidence, dedupe
        suggestions.sort(key=lambda x: -x["confidence"])
        seen = set()
        unique = []
        for s in suggestions:
            if s["question"] not in seen:
                seen.add(s["question"])
                unique.append(s)
        
        return unique[:top_n]
    
    def visualize(self, output_path: str = "graph.html") -> str:
        """
        Generate an interactive HTML visualization of the graph.
        
        Args:
            output_path: Path to save the HTML file
        
        Returns:
            Path to the generated file
        """
        from .visualization import generate_graph_html
        return generate_graph_html(self, output_path)
    
    # ------------------------------------------------------------------
    # Advanced Features: Confidence-Weighted Traversal, Auto-Extraction
    # ------------------------------------------------------------------
    
    def traverse_confident(
        self,
        start_id: str,
        max_depth: int = 3,
        min_confidence: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Confidence-weighted BFS traversal.
        
        Unlike basic traversal, this prefers high-confidence paths
        and skips unreliable nodes.
        
        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            min_confidence: Minimum confidence to traverse
        
        Returns:
            List of {"node": node_dict, "path_confidence": float, "depth": int}
        """
        return confidence_weighted_bfs(
            self.nodes, self.edges, start_id,
            max_depth=max_depth,
            min_confidence=min_confidence,
            confidence_engine=self.confidence_engine,
        )
    
    def find_best_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
        min_confidence: float = 0.5,
    ) -> Optional[List[str]]:
        """
        Find most reliable path between two nodes.
        
        Uses confidence-weighted search to find the path that
        maximizes minimum confidence along the way.
        
        Args:
            start_id: Starting node ID
            end_id: Target node ID
            max_depth: Maximum path length
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of node IDs forming the best path, or None
        """
        return find_high_confidence_paths(
            self.nodes, self.edges, start_id, end_id,
            max_depth=max_depth,
            min_confidence=min_confidence,
            confidence_engine=self.confidence_engine,
        )
    
    def ingest_text(
        self,
        text: str,
        source: str = "auto_extraction",
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """
        Automatically extract and ingest facts from unstructured text.
        
        Uses pattern matching to find factual statements:
        - "X is Y"
        - "X has Y"
        - "X covers Y"
        
        Args:
            text: Unstructured text to extract facts from
            source: Source identifier
            agent_id: Optional agent ID
        
        Returns:
            Dict with extraction results
        """
        # Extract facts
        facts = extract_facts_from_text(text)
        
        # Extract entities
        entities = extract_entities_with_types(text)
        
        ingested_facts = 0
        ingested_entities = 0
        
        # Ingest facts
        for fact in facts:
            content = fact.get("full_text", f"{fact['subject']} {fact.get('predicate', '')} {fact.get('object', '')}")
            if len(content) > 10:
                self.add_node(
                    content=content[:500],
                    node_type=NODE_FACT,
                    source=source,
                    confidence=fact.get("confidence", 0.7),
                    tag=TAG_EXTRACTED,
                    metadata={"extraction_method": fact.get("method", "pattern"), "auto_extracted": True}
                )
                ingested_facts += 1
        
        # Ingest entities
        for entity, etype in entities:
            eid, canonical = self._get_or_create_entity(entity, etype)
            if agent_id:
                self.nodes[eid].setdefault("agent_id", agent_id)
            ingested_entities += 1
        
        self._dirty = True
        self._save()
        
        return {
            "facts_extracted": ingested_facts,
            "entities_extracted": ingested_entities,
            "source": source,
            "message": f"Extracted {ingested_facts} facts and {ingested_entities} entities from text",
        }
    
    def multi_hop_query(
        self,
        query: str,
        max_hops: int = 3,
        min_confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Answer a query by traversing multiple hops in the graph.
        
        Example: "What is the coverage of PM-JAY?"
        Hop 1: Find PM-JAY entity
        Hop 2: Find facts about PM-JAY
        Hop 3: Find coverage details
        
        Args:
            query: The question to answer
            max_hops: Maximum number of hops
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of reasoning paths with confidence scores
        """
        return multi_hop_reasoning(
            self.nodes, self.edges, query,
            max_hops=max_hops,
            min_confidence=min_confidence,
            confidence_engine=self.confidence_engine,
        )
    
    def ingest_enterprise_graph(
        self,
        enterprise_graph: Dict[str, Any],
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """
        Ingest knowledge from enterprise graph format.
        
        Allows the OSS to work with existing enterprise applications
        that store knowledge in graph format.
        
        Args:
            enterprise_graph: Enterprise graph dict with nodes and edges
            agent_id: Optional agent ID
        
        Returns:
            Dict with ingestion summary
        """
        return ingest_from_enterprise_graph(self, enterprise_graph, agent_id)
    
    def get_entity_graph(
        self,
        entity: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get the subgraph around an entity with all relationships.
        
        Useful for understanding what's connected to a specific entity.
        
        Args:
            entity: Entity name to find
            depth: How many hops to include
        
        Returns:
            Dict with entity node, neighbors, and relationships
        """
        # Find entity node
        entity_key = normalize(entity)
        entity_id = self.entity_index.get(entity_key)
        
        if not entity_id:
            # Try to find by content match
            for nid, node in self.nodes.items():
                if node.get("type") == NODE_ENTITY:
                    if normalize(node.get("content", "")) == entity_key:
                        entity_id = nid
                        break
        
        if not entity_id:
            return {"error": f"Entity '{entity}' not found"}
        
        # Get neighbors
        neighbors = self.get_neighbors(entity_id, depth=depth)
        
        # Get entity info
        entity_node = self.nodes[entity_id]
        confidence = self.confidence_engine.node_confidence(entity_node)
        
        return {
            "entity": {
                "id": entity_id,
                "content": entity_node.get("content", ""),
                "confidence": confidence,
                "badge": self.quality_badges.get_badge(confidence),
                "aliases": self.entity_aliases.get(entity_node.get("content", ""), []),
            },
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics.
        
        Confidence numbers use the same engine-computed values as query
        results, so stats always agree with what retrieval reports.
        """
        confidences = [self.confidence_engine.node_confidence(n) for n in self.nodes.values()]
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "high_confidence_nodes": sum(1 for c in confidences if c >= 0.8),
            "medium_confidence_nodes": sum(1 for c in confidences if 0.5 <= c < 0.8),
            "low_confidence_nodes": sum(1 for c in confidences if c < 0.5),
            "communities": len(self.detect_communities()),
            "god_nodes": len(self.god_nodes(3)),
        }
