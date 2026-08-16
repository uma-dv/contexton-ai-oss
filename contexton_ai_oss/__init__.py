"""
ContextOn.AI OSS - Knowledge Graph Engine for AI Agents

A confidence-aware, failure-learning knowledge graph that helps AI agents
remember and learn from conversations.

Open-source version by ODEFTO AI Labs.
Enterprise version: https://contexton.ai
"""

__version__ = "0.1.0"

from .graph import ContextGraph
from .confidence import ConfidenceEngine
from .failure_learning import FailureLearningEngine
from .quality import QualityBadges
from .entities import extract_entities, is_alias, resolve_alias
from .advanced import (
    confidence_weighted_bfs,
    find_high_confidence_paths,
    extract_facts_from_text,
    extract_entities_with_types,
    multi_hop_reasoning,
    ingest_from_enterprise_graph,
)

__all__ = [
    "ContextGraph",
    "ConfidenceEngine", 
    "FailureLearningEngine",
    "QualityBadges",
    "extract_entities",
    "is_alias",
    "resolve_alias",
    "confidence_weighted_bfs",
    "find_high_confidence_paths",
    "extract_facts_from_text",
    "extract_entities_with_types",
    "multi_hop_reasoning",
    "ingest_from_enterprise_graph",
]
