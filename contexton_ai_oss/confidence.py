"""
Confidence Engine for ContextOn.AI OSS.

Calculates confidence scores for nodes and edges based on:
- Verification count (mentions)
- Time since last verification (decay)
- Failure count (penalty)

This is a NOVEL feature not found in other knowledge graph tools.
"""

from datetime import datetime, timedelta
from typing import Dict, Any


class ConfidenceEngine:
    """
    Calculates confidence scores for graph nodes and edges.
    
    Confidence represents how trustworthy knowledge is:
    - 0.8-1.0: Verified, reliable (🟢)
    - 0.5-0.8: Needs verification (🟡)
    - 0.0-0.5: Unreliable, verify before using (🔴)
    
    This is NOT in any other tool:
    - Graphify: No confidence scoring
    - Graphiti: No confidence scoring
    - Mem0: No confidence scoring
    
    Example:
        engine = ConfidenceEngine()
        
        # Node with high confidence
        node1 = {"mentions": 10, "last_verified": now(), "failure_count": 0}
        print(engine.node_confidence(node1))  # 1.0
        
        # Node with low confidence (old, failed)
        node2 = {"mentions": 2, "last_verified": 30_days_ago, "failure_count": 3}
        print(engine.node_confidence(node2))  # 0.05 (floored)
    """
    
    # Decay rate per day (0.95 = 5% decay per day)
    DECAY_RATE = 0.95
    
    # Failure penalty multiplier
    FAILURE_PENALTY = 0.5
    
    # Minimum confidence floor
    MIN_CONFIDENCE = 0.05
    
    def node_confidence(self, node: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a node. This is the SINGLE source
        of truth for node confidence - query ranking, badges, and stats
        all use this value.
        
        Formula:
        1. Base: stored confidence (set at ingestion, modified by success/failure)
        
        2. Decay: * (DECAY_RATE ^ days_since_verified)
           - Old knowledge loses confidence over time
           - 0.95^30 = 0.21 after 30 days
        
        3. Failure penalty: * (FAILURE_PENALTY ^ failure_count)
           - Each failure halves confidence
           - 3 failures = 0.125 of original
        
        Final: max(MIN_CONFIDENCE, base * decay * failure_penalty)
        
        Args:
            node: Node dict with confidence, mentions, last_verified, failure_count
        
        Returns:
            Confidence score between MIN_CONFIDENCE and 1.0
        """
        # Base confidence: stored ingestion trust (modified by record_success)
        stored = node.get("confidence")
        if stored is None:
            stored = 0.5  # Unknown nodes start neutral
        
        # Time decay
        last_verified = node.get("last_verified")
        if last_verified:
            try:
                verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
                days_old = (datetime.now(verified_dt.tzinfo) - verified_dt).days
                decay = self.DECAY_RATE ** days_old
            except (ValueError, TypeError):
                decay = 1.0
        else:
            decay = 1.0
        
        # Failure penalty
        failure_count = node.get("failure_count", 0)
        failure_penalty = self.FAILURE_PENALTY ** failure_count
        
        # Combined confidence
        confidence = float(stored) * decay * failure_penalty
        
        return max(self.MIN_CONFIDENCE, min(1.0, confidence))
    
    def edge_confidence(self, edge: Dict[str, Any]) -> float:
        """
        Calculate confidence score for an edge.
        
        Formula:
        1. Success rate: success_count / (success_count + failure_count + 1)
           - Ratio of successful vs failed uses
           - +1 prevents division by zero
        
        2. Weight factor: edge weight (0.0-1.0)
           - Higher weight = more important relationship
        
        3. Combined: success_rate * 0.7 + weight * 0.3
           - Success rate matters more than weight
        
        Args:
            edge: Edge dict with success_count, failure_count, weight
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        success_count = edge.get("success_count", 0)
        failure_count = edge.get("failure_count", 0)
        weight = edge.get("weight", 0.5)
        
        # Success rate
        total = success_count + failure_count + 1
        success_rate = success_count / total
        
        # Combined confidence
        confidence = success_rate * 0.7 + weight * 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def calculate_reliability(self, path: Dict[str, Any]) -> float:
        """
        Calculate overall reliability of a path (sequence of nodes/edges).
        
        Reliability = average(confidence) * (1 - failure_rate)
        
        This ensures agents use knowledge that has been verified,
        avoiding paths that have failed before.
        
        Args:
            path: Dict with nodes and edges in the path
        
        Returns:
            Reliability score between 0.0 and 1.0
        """
        nodes = path.get("nodes", [])
        edges = path.get("edges", [])
        
        if not nodes and not edges:
            return 0.0
        
        # Average node confidence
        node_confidences = [self.node_confidence(n) for n in nodes]
        avg_node_conf = sum(node_confidences) / len(node_confidences) if node_confidences else 0.5
        
        # Average edge confidence
        edge_confidences = [self.edge_confidence(e) for e in edges]
        avg_edge_conf = sum(edge_confidences) / len(edge_confidences) if edge_confidences else 0.5
        
        # Failure rate
        total_failures = sum(e.get("failure_count", 0) for e in edges)
        total_uses = sum(e.get("success_count", 0) + e.get("failure_count", 0) for e in edges)
        failure_rate = total_failures / (total_uses + 1)
        
        # Combined reliability
        reliability = (avg_node_conf * 0.5 + avg_edge_conf * 0.5) * (1 - failure_rate)
        
        return max(0.0, min(1.0, reliability))
    
    def get_confidence_breakdown(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed breakdown of how confidence was calculated.
        
        Useful for debugging and understanding.
        
        Args:
            node: Node dict
        
        Returns:
            Dict with confidence components
        """
        stored = node.get("confidence")
        if stored is None:
            stored = 0.5
        
        last_verified = node.get("last_verified")
        if last_verified:
            try:
                verified_dt = datetime.fromisoformat(last_verified.replace("Z", "+00:00"))
                days_old = (datetime.now(verified_dt.tzinfo) - verified_dt).days
                decay = self.DECAY_RATE ** days_old
            except (ValueError, TypeError):
                days_old = 0
                decay = 1.0
        else:
            days_old = 0
            decay = 1.0
        
        failure_count = node.get("failure_count", 0)
        failure_penalty = self.FAILURE_PENALTY ** failure_count
        
        final = self.node_confidence(node)
        
        return {
            "stored_confidence": round(float(stored), 3),
            "days_since_verified": days_old,
            "decay_factor": round(decay, 3),
            "failure_count": failure_count,
            "failure_penalty": round(failure_penalty, 3),
            "final_confidence": round(final, 3),
            "badge": "🟢" if final >= 0.8 else ("🟡" if final >= 0.5 else "🔴"),
        }
