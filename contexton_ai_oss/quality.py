"""
Quality Badge System for ContextOn.AI OSS.

Visual quality indicators for graph nodes:
- 🟢 High: confidence >= 0.8 (verified, reliable)
- 🟡 Medium: 0.5 <= confidence < 0.8 (needs verification)
- 🔴 Low: confidence < 0.5 (unreliable, verify before using)

This is a NOVEL feature not found in other knowledge graph tools.
"""

from typing import Dict, Any, List


class QualityBadges:
    """
    Visual quality indicators for graph nodes.
    
    This is UNIQUE to ContextOn.AI OSS:
    - Graphify: No quality badges
    - Graphiti: No quality badges
    - Mem0: No quality badges
    
    The badges make it immediately clear which knowledge is trustworthy:
    - 🟢 Safe to use, verified multiple times
    - 🟡 Use with caution, needs verification
    - 🔴 Do not trust without verification
    """
    
    # Thresholds
    HIGH_THRESHOLD = 0.8
    MEDIUM_THRESHOLD = 0.5
    
    # Badge symbols
    BADGE_HIGH = "🟢"
    BADGE_MEDIUM = "🟡"
    BADGE_LOW = "🔴"
    
    def get_badge(self, confidence: float) -> str:
        """
        Get visual badge based on confidence score.
        
        Args:
            confidence: Confidence score (0.0-1.0)
        
        Returns:
            Badge emoji: 🟢, 🟡, or 🔴
        """
        if confidence >= self.HIGH_THRESHOLD:
            return self.BADGE_HIGH
        elif confidence >= self.MEDIUM_THRESHOLD:
            return self.BADGE_MEDIUM
        else:
            return self.BADGE_LOW
    
    def get_quality_summary(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get comprehensive quality info for a node.
        
        Confidence comes from the ConfidenceEngine (the single source
        of truth), so it always agrees with query results and stats.
        
        Args:
            node: Node dict
        
        Returns:
            Dict with badge, confidence, status, and recommendations
        """
        from .confidence import ConfidenceEngine
        confidence = ConfidenceEngine().node_confidence(node)
        badge = self.get_badge(confidence)
        
        return {
            "badge": badge,
            "confidence": confidence,
            "confidence_percent": f"{confidence * 100:.1f}%",
            "mentions": node.get("mentions", 0),
            "last_verified": node.get("last_verified"),
            "failure_count": node.get("failure_count", 0),
            "status": self.get_status(node),
            "recommendation": self.get_recommendation(node),
        }
    
    def get_status(self, node: Dict[str, Any]) -> str:
        """
        Get human-readable status for a node.
        
        Args:
            node: Node dict
        
        Returns:
            Status string
        """
        confidence = node.get("confidence", 0)
        failure_count = node.get("failure_count", 0)
        
        if confidence >= self.HIGH_THRESHOLD:
            if failure_count == 0:
                return "Verified and reliable"
            else:
                return "Verified but has had failures"
        elif confidence >= self.MEDIUM_THRESHOLD:
            return "Needs verification"
        elif failure_count > 2:
            return "Frequently fails - verify before using"
        else:
            return "Low confidence - use with caution"
    
    def get_recommendation(self, node: Dict[str, Any]) -> str:
        """
        Get actionable recommendation for a node.
        
        Args:
            node: Node dict
        
        Returns:
            Recommendation string
        """
        confidence = node.get("confidence", 0)
        failure_count = node.get("failure_count", 0)
        
        if confidence >= self.HIGH_THRESHOLD:
            return "Safe to use in responses"
        elif confidence >= self.MEDIUM_THRESHOLD:
            return "Verify before using in critical responses"
        elif failure_count > 2:
            return "Do not use without manual verification"
        else:
            return "Use with caution, cross-reference with other sources"
    
    def get_badge_color(self, confidence: float) -> str:
        """
        Get CSS color for the badge.
        
        Useful for visualization.
        
        Args:
            confidence: Confidence score
        
        Returns:
            CSS color string
        """
        if confidence >= self.HIGH_THRESHOLD:
            return "#22c55e"  # Green
        elif confidence >= self.MEDIUM_THRESHOLD:
            return "#eab308"  # Yellow
        else:
            return "#ef4444"  # Red
    
    def format_node_with_badge(self, node: Dict[str, Any], include_details: bool = False) -> str:
        """
        Format a node with its quality badge.
        
        Args:
            node: Node dict
            include_details: Whether to include detailed info
        
        Returns:
            Formatted string with badge
        """
        badge = self.get_badge(node.get("confidence", 0))
        content = node.get("content", "")[:100]
        
        if include_details:
            summary = self.get_quality_summary(node)
            return (
                f"{badge} {content}\n"
                f"   Confidence: {summary['confidence_percent']} | "
                f"Status: {summary['status']}"
            )
        else:
            return f"{badge} {content}"
    
    def format_edge_with_badge(self, edge: Dict[str, Any]) -> str:
        """
        Format an edge with its quality badge.
        
        Args:
            edge: Edge dict
        
        Returns:
            Formatted string with badge
        """
        from .confidence import ConfidenceEngine
        engine = ConfidenceEngine()
        confidence = engine.edge_confidence(edge)
        badge = self.get_badge(confidence)
        
        source = edge.get("source", "")[:8]
        target = edge.get("target", "")[:8]
        edge_type = edge.get("type", "")
        
        return f"{badge} {source} --[{edge_type}]--> {target}"
    
    def get_quality_report(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a quality report for a list of nodes.
        
        Args:
            nodes: List of node dicts
        
        Returns:
            Dict with quality statistics
        """
        if not nodes:
            return {"total": 0, "high": 0, "medium": 0, "low": 0}
        
        confidences = [n.get("confidence", 0) for n in nodes]
        
        return {
            "total": len(nodes),
            "high": sum(1 for c in confidences if c >= self.HIGH_THRESHOLD),
            "medium": sum(1 for c in confidences if self.MEDIUM_THRESHOLD <= c < self.HIGH_THRESHOLD),
            "low": sum(1 for c in confidences if c < self.MEDIUM_THRESHOLD),
            "avg_confidence": sum(confidences) / len(confidences),
            "high_percent": f"{sum(1 for c in confidences if c >= self.HIGH_THRESHOLD) / len(nodes) * 100:.1f}%",
            "medium_percent": f"{sum(1 for c in confidences if self.MEDIUM_THRESHOLD <= c < self.HIGH_THRESHOLD) / len(nodes) * 100:.1f}%",
            "low_percent": f"{sum(1 for c in confidences if c < self.MEDIUM_THRESHOLD) / len(nodes) * 100:.1f}%",
        }
