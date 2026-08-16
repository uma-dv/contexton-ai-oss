"""
Failure Learning Engine for ContextOn.AI OSS.

THE CORE DIFFERENTIATOR: No other knowledge graph tool learns from failures.

When an agent gives a wrong answer:
1. Mark all edges in the path as failed
2. Reduce confidence of involved nodes
3. Add failure metadata for analysis

This ensures future queries avoid unreliable paths.

Example:
    engine = FailureLearningEngine(graph)
    
    # Agent gives wrong answer
    engine.record_failure(
        query="What is PM-JAY?",
        answer="It's a housing scheme",
        reason="Incorrect - it's health insurance"
    )
    
    # Next query avoids this path
    results = graph.query("PM-JAY")
    # Returns paths with higher confidence, avoiding the failed one
"""

from typing import Dict, List, Any, Optional, Set

from .text_utils import tokenize, token_overlap, shared_tokens, utc_iso_now
from .lifecycle import (
    STATE_USED, STATE_FAILURE, STATE_SUSPECT, STATE_QUARANTINED,
    STATE_SUCCESS, STATE_REINFORCED, STATE_TRUSTED, STATE_REVERIFIED,
    QUARANTINE_THRESHOLD,
)


class FailureLearningEngine:
    """
    Learns from agent failures to improve future retrieval.
    
    This is UNIQUE to ContextOn.AI OSS:
    - Graphify: No failure learning
    - Graphiti: No failure learning
    - Mem0: No failure learning
    
    How it works:
    1. When agent fails, mark the knowledge path as unreliable
    2. Reduce confidence of all nodes/edges in that path
    3. Future queries prefer paths that haven't failed
    
    This creates a self-improving system where:
    - Good knowledge gets reinforced
    - Bad knowledge gets filtered out
    - Agents automatically use more reliable information
    """
    
    # Confidence reduction factor on failure
    FAILURE_CONFIDENCE_MULTIPLIER = 0.5
    
    # Confidence boost on success
    SUCCESS_CONFIDENCE_MULTIPLIER = 1.1
    
    # Minimum confidence after failure
    MIN_CONFIDENCE_AFTER_FAILURE = 0.1
    
    def __init__(self, graph):
        """
        Initialize the failure learning engine.
        
        Args:
            graph: The ContextGraph instance to modify
        """
        self.graph = graph
    
    def record_failure(
        self,
        query: str,
        answer: str,
        reason: str = "",
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """
        Record that an agent gave a wrong answer.
        
        This is the KEY METHOD - no other tool has this.
        
        What happens:
        1. Find all edges that led to this answer
        2. Mark them as failed
        3. Reduce their confidence
        4. Add an observation node about the failure
        
        Args:
            query: The original question
            answer: The wrong answer that was given
            reason: Why it was wrong (optional)
            agent_id: Which agent failed (optional)
        
        Returns:
            Dict with failure recording results
        """
        now = utc_iso_now()
        
        # Find nodes related to the failed answer using token overlap
        # Match on ANSWER, not query — this is the wrong content
        related = self._find_related_nodes(query, answer)
        
        # Only affect nodes that DIRECTLY match the answer
        # Do NOT cascade penalties through edges to connected nodes
        affected_edges = []
        affected_nodes = set()
        
        # Mark directly related nodes as failed
        for node_id in related:
            node = self.graph.nodes.get(node_id)
            if node:
                node["failure_count"] = node.get("failure_count", 0) + 1
                affected_nodes.add(node_id)
                # Trust lifecycle: USED → FAILURE → SUSPECT
                current_state = node.get("state", STATE_TRUSTED)
                if current_state in (STATE_TRUSTED, STATE_USED, STATE_SUCCESS, STATE_REINFORCED):
                    node["state"] = STATE_FAILURE
                elif current_state == STATE_FAILURE:
                    node["state"] = STATE_SUSPECT
                # Auto-quarantine if confidence drops below threshold
                from .confidence import ConfidenceEngine
                eng = ConfidenceEngine()
                if eng.node_confidence(node) < QUARANTINE_THRESHOLD:
                    node["state"] = STATE_QUARANTINED
        
        # Mark edges that CONNECT failed nodes to other nodes
        # Only penalize edges where BOTH source and target are in the failed set
        for edge in self.graph.edges:
            if edge["source"] in related and edge["target"] in related:
                edge["failure_count"] = edge.get("failure_count", 0) + 1
                edge["last_outcome"] = "failure"
                affected_edges.append(edge)
        
        # Add observation node about the failure
        failure_content = f"FAILED: {query[:100]} → {answer[:100]}"
        if reason:
            failure_content += f" (Reason: {reason[:100]})"
        
        failure_node_id = self.graph.add_node(
            content=failure_content,
            node_type="observation",
            source=agent_id or "failure_learning",
            confidence=0.3,  # Low confidence for failure observations
            tag="inferred",
            metadata={
                "type": "failure",
                "query": query[:500],
                "answer": answer[:500],
                "reason": reason[:500],
                "timestamp": now,
            }
        )
        
        # Save changes
        self.graph._dirty = True
        self.graph._save()
        
        return {
            "status": "recorded",
            "failure_node_id": failure_node_id,
            "affected_edges": len(affected_edges),
            "affected_nodes": len(affected_nodes),
            "message": f"Recorded failure: {reason or 'No reason provided'}",
        }
    
    def record_success(
        self,
        query: str,
        answer: str,
        agent_id: str = "",
    ) -> Dict[str, Any]:
        """
        Record that an agent gave a correct answer.
        
        This INCREASES confidence in the knowledge path.
        
        What happens:
        1. Find all edges that led to this answer
        2. Mark them as successful
        3. Increase their confidence
        4. Verify the nodes are still valid
        
        Args:
            query: The question
            answer: The correct answer
            agent_id: Which agent succeeded (optional)
        
        Returns:
            Dict with success recording results
        """
        now = utc_iso_now()
        
        # Find nodes related to the successful answer using token overlap
        # Match on ANSWER content, not query (same as record_failure)
        related = self._find_related_nodes(query, answer)
        
        # Only affect nodes that DIRECTLY match the answer
        # Do NOT cascade bonuses through edges to connected nodes
        affected_edges = []
        affected_nodes = set()
        
        # Mark directly related nodes as successful
        for node_id in related:
            node = self.graph.nodes.get(node_id)
            if node:
                node["mentions"] = node.get("mentions", 0) + 1
                node["last_verified"] = now
                affected_nodes.add(node_id)
                # Trust lifecycle: FAILURE/SUSPECT → REINFORCED; QUARANTINED → REVERIFIED
                current_state = node.get("state", STATE_TRUSTED)
                if current_state == STATE_QUARANTINED:
                    node["state"] = STATE_REVERIFIED
                elif current_state in (STATE_FAILURE, STATE_SUSPECT):
                    node["state"] = STATE_REINFORCED
                elif current_state in (STATE_TRUSTED, STATE_USED, STATE_SUCCESS):
                    node["state"] = STATE_SUCCESS
        
        # Mark edges that CONNECT successful nodes
        # Only boost edges where BOTH source and target are in the successful set
        for edge in self.graph.edges:
            if edge["source"] in related and edge["target"] in related:
                edge["success_count"] = edge.get("success_count", 0) + 1
                edge["last_outcome"] = "success"
                edge["verified"] = True
                affected_edges.append(edge)
        
        # Increase confidence of affected nodes - a verified success undoes
        # the damage of a prior failure, so confidence is actually restored
        for node_id in affected_nodes:
            node = self.graph.nodes.get(node_id)
            if node:
                node["success_count"] = node.get("success_count", 0) + 1
                node["last_verified"] = now
                # Undo failure damage: decrement failure_count (min 0)
                fc = node.get("failure_count", 0)
                if fc > 0:
                    node["failure_count"] = fc - 1
                # Bounded additive restoration: cap at original_confidence, not 1.0
                ceiling = node.get("original_confidence", node["confidence"])
                node["confidence"] = min(ceiling, node["confidence"] + 0.3)
        
        # Save changes
        self.graph._dirty = True
        self.graph._save()
        
        return {
            "status": "recorded",
            "affected_edges": len(affected_edges),
            "affected_nodes": len(affected_nodes),
            "message": "Success recorded - confidence increased",
        }
    
    def _find_related_nodes(self, query: str, answer: str) -> Set[str]:
        """
        Find graph nodes related to a FAILED answer using meaningful
        token overlap (punctuation-insensitive, stopword-filtered).
        
        IMPORTANT: We match primarily on the ANSWER (the wrong content),
        not the query. The query touches the entity node which connects
        to ALL facts about that entity — matching on query would cause
        collateral damage to correct facts.
        
        A node is related when it shares at least 3 meaningful tokens
        with the failed answer, or has strong Jaccard overlap with the
        answer. Bookkeeping/observation nodes are never matched.
        
        We require 3+ shared tokens (not 2) to prevent false positives
        where unrelated facts share common words like "poor" or "families".
        """
        # Match on ANSWER, not query — this is the wrong content
        answer_tokens = set(tokenize(answer))
        if not answer_tokens:
            return set()
        
        related = set()
        for nid, node in self.graph.nodes.items():
            # Never match bookkeeping nodes (e.g. prior failure observations)
            if node.get("type") == "observation":
                continue
            # Never match entity nodes — they represent concepts, not specific facts
            # A failure about a wrong answer should only affect the fact, not the entity
            if node.get("type") == "entity":
                continue
            content = node.get("content", "")
            node_tokens = set(tokenize(content))
            if not node_tokens:
                continue
            shared = len(answer_tokens & node_tokens)
            # Require BOTH 3+ shared tokens AND >= 0.4 Jaccard overlap
            # This ensures only facts with substantial content overlap are penalized
            if shared >= 3 and token_overlap(answer, content) >= 0.4:
                related.add(nid)
        
        return related
    
    def get_reliable_paths(
        self,
        query: str,
        top_k: int = 5,
        min_reliability: float = 0.3,
    ) -> List[Dict]:
        """
        Retrieve paths ranked by RELIABILITY, not just relevance.
        
        Reliability = confidence * (1 - failure_rate)
        
        This is the KEY DIFFERENTIATOR:
        - Regular search: Returns whatever matches
        - ContextOn.AI OSS: Returns only reliable, verified knowledge
        
        Args:
            query: Search query
            top_k: Maximum results
            min_reliability: Minimum reliability threshold
        
        Returns:
            List of reliable paths sorted by reliability
        """
        # Get basic query results
        basic_results = self.graph.query(query, max_results=top_k * 2)
        
        # Enhance with reliability scoring
        reliable_paths = []
        for result in basic_results:
            node = result["node"]
            
            # Find paths through this node
            paths = self._find_paths_through(node["id"])
            
            for path in paths:
                reliability = self._calculate_path_reliability(path)
                if reliability >= min_reliability:
                    reliable_paths.append({
                        "node": node,
                        "path": path,
                        "reliability": reliability,
                        "badge": "🟢" if reliability >= 0.8 else ("🟡" if reliability >= 0.5 else "🔴"),
                    })
        
        # Sort by reliability
        reliable_paths.sort(key=lambda x: -x["reliability"])
        
        return reliable_paths[:top_k]
    
    def _find_paths_through(self, node_id: str, max_depth: int = 2) -> List[List[str]]:
        """Find paths that go through a specific node."""
        paths = []
        
        # Get incoming edges
        incoming = [e for e in self.graph.edges if e["target"] == node_id]
        # Get outgoing edges
        outgoing = [e for e in self.graph.edges if e["source"] == node_id]
        
        # Simple paths: incoming -> node -> outgoing
        for in_edge in incoming[:3]:  # Limit to 3
            for out_edge in outgoing[:3]:
                path = [in_edge["source"], node_id, out_edge["target"]]
                paths.append(path)
        
        return paths[:5]  # Limit paths
    
    def _calculate_path_reliability(self, path: List[str]) -> float:
        """Calculate reliability of a specific path."""
        if len(path) < 2:
            return 0.5
        
        # Get nodes and edges in path
        nodes = []
        edges = []
        
        for i, node_id in enumerate(path):
            node = self.graph.nodes.get(node_id)
            if node:
                nodes.append(node)
            
            if i < len(path) - 1:
                # Find edge between this node and next
                for edge in self.graph.edges:
                    if edge["source"] == node_id and edge["target"] == path[i + 1]:
                        edges.append(edge)
                        break
        
        if not nodes:
            return 0.5
        
        # Calculate reliability
        from .confidence import ConfidenceEngine
        engine = ConfidenceEngine()
        return engine.calculate_reliability({"nodes": nodes, "edges": edges})
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """
        Analyze all failures in the graph.
        
        Useful for understanding what knowledge is unreliable.
        
        Returns:
            Dict with failure statistics
        """
        failure_nodes = [
            n for n in self.graph.nodes.values()
            if n.get("type") == "observation" and 
            n.get("metadata", {}).get("type") == "failure"
        ]
        
        failed_edges = [
            e for e in self.graph.edges
            if e.get("failure_count", 0) > 0
        ]
        
        return {
            "total_failures": len(failure_nodes),
            "failed_edges": len(failed_edges),
            "avg_failure_count": sum(e.get("failure_count", 0) for e in failed_edges) / max(len(failed_edges), 1),
            "most_failed_nodes": self._get_most_failed_nodes(5),
            "failure_reasons": self._get_failure_reasons(),
        }
    
    def _get_most_failed_nodes(self, top_n: int = 5) -> List[Dict]:
        """Get nodes with most failures."""
        failed_nodes = [
            {"node": n, "failures": n.get("failure_count", 0)}
            for n in self.graph.nodes.values()
            if n.get("failure_count", 0) > 0
        ]
        failed_nodes.sort(key=lambda x: -x["failures"])
        return failed_nodes[:top_n]
    
    def _get_failure_reasons(self) -> List[Dict]:
        """Extract failure reasons from observation nodes."""
        reasons = []
        for node in self.graph.nodes.values():
            if node.get("type") == "observation" and node.get("metadata", {}).get("type") == "failure":
                reason = node.get("metadata", {}).get("reason", "")
                if reason:
                    reasons.append({
                        "reason": reason,
                        "query": node.get("metadata", {}).get("query", ""),
                        "timestamp": node.get("metadata", {}).get("timestamp", ""),
                    })
        return reasons[:10]  # Return top 10
