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
        
        # Find nodes related to the failed query/answer using token overlap
        related = self._find_related_nodes(query, answer)
        
        # Mark related edges as failed
        affected_edges = []
        affected_nodes = set()
        
        for edge in self.graph.edges:
            if edge["source"] in related or edge["target"] in related:
                # Mark as failed
                edge["failure_count"] = edge.get("failure_count", 0) + 1
                edge["last_outcome"] = "failure"
                edge["confidence"] = max(
                    self.MIN_CONFIDENCE_AFTER_FAILURE,
                    edge["confidence"] * self.FAILURE_CONFIDENCE_MULTIPLIER
                )
                
                affected_edges.append(edge)
                affected_nodes.add(edge["source"])
                affected_nodes.add(edge["target"])
        
        # Reduce confidence of affected nodes
        for node_id in affected_nodes:
            node = self.graph.nodes.get(node_id)
            if node:
                node["failure_count"] = node.get("failure_count", 0) + 1
                node["confidence"] = max(
                    self.MIN_CONFIDENCE_AFTER_FAILURE,
                    node["confidence"] * self.FAILURE_CONFIDENCE_MULTIPLIER
                )
        
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
        
        # Find nodes related to the successful query/answer using token overlap
        related = self._find_related_nodes(query, answer)
        
        # Mark related edges as successful
        affected_edges = []
        affected_nodes = set()
        
        for edge in self.graph.edges:
            if edge["source"] in related or edge["target"] in related:
                # Mark as successful
                edge["success_count"] = edge.get("success_count", 0) + 1
                edge["last_outcome"] = "success"
                edge["verified"] = True
                
                # Undo failure damage if the edge had failed before
                if edge.get("failure_count", 0) > 0:
                    edge["failure_count"] = max(0, edge["failure_count"] - 1)
                    edge["confidence"] = min(
                        1.0,
                        edge["confidence"] / self.FAILURE_CONFIDENCE_MULTIPLIER
                    )
                else:
                    edge["confidence"] = min(
                        1.0,
                        edge["confidence"] * self.SUCCESS_CONFIDENCE_MULTIPLIER
                    )
                
                affected_edges.append(edge)
                affected_nodes.add(edge["source"])
                affected_nodes.add(edge["target"])
        
        # Increase confidence of affected nodes - a verified success undoes
        # the damage of a prior failure, so confidence is actually restored
        for node_id in affected_nodes:
            node = self.graph.nodes.get(node_id)
            if node:
                node["mentions"] = node.get("mentions", 0) + 1
                node["last_verified"] = now
                if node.get("failure_count", 0) > 0:
                    node["failure_count"] = max(0, node["failure_count"] - 1)
                    node["confidence"] = min(
                        1.0,
                        node["confidence"] / self.FAILURE_CONFIDENCE_MULTIPLIER
                    )
                else:
                    node["confidence"] = min(
                        1.0,
                        node["confidence"] * self.SUCCESS_CONFIDENCE_MULTIPLIER
                    )
        
        # Save changes
        self.graph._save()
        
        return {
            "status": "recorded",
            "affected_edges": len(affected_edges),
            "affected_nodes": len(affected_nodes),
            "message": "Success recorded - confidence increased",
        }
    
    def _find_related_nodes(self, query: str, answer: str) -> Set[str]:
        """
        Find graph nodes related to a query/answer pair using meaningful
        token overlap (punctuation-insensitive, stopword-filtered).
        
        A node is related when it shares at least 2 meaningful tokens
        with the combined query+answer text, or has strong Jaccard
        overlap. Bookkeeping/observation nodes are never matched.
        """
        combined = f"{query} {answer}"
        combined_tokens = set(tokenize(combined))
        if not combined_tokens:
            return set()
        
        related = set()
        for nid, node in self.graph.nodes.items():
            # Never match bookkeeping nodes (e.g. prior failure observations)
            if node.get("type") == "observation":
                continue
            content = node.get("content", "")
            node_tokens = set(tokenize(content))
            if not node_tokens:
                continue
            shared = len(combined_tokens & node_tokens)
            if shared >= 2:
                related.add(nid)
            elif token_overlap(combined, content) >= 0.25:
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
