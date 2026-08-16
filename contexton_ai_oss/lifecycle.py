"""
Trust Lifecycle for ContextOn.AI OSS.

Defines the state machine for memory reliability per paper Section IV.E:

    NEW → TRUSTED → USED → SUCCESS/FAILURE
                         ↓           ↓
                    REINFORCED    SUSPECT
                         ↓           ↓
                    TRUSTED    QUARANTINED
                                   ↓
                              REVERIFIED → TRUSTED

Memories below a configurable confidence threshold are excluded from
retrieval, implementing automatic quarantine of unreliable knowledge.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Trust lifecycle states
STATE_NEW = "new"
STATE_TRUSTED = "trusted"
STATE_USED = "used"
STATE_SUCCESS = "success"
STATE_FAILURE = "failure"
STATE_REINFORCED = "reinforced"
STATE_SUSPECT = "suspect"
STATE_QUARANTINED = "quarantined"
STATE_REVERIFIED = "reverified"

# Valid state transitions
VALID_TRANSITIONS = {
    STATE_NEW: {STATE_TRUSTED},
    STATE_TRUSTED: {STATE_USED},
    STATE_USED: {STATE_SUCCESS, STATE_FAILURE},
    STATE_SUCCESS: {STATE_REINFORCED, STATE_USED},
    STATE_FAILURE: {STATE_SUSPECT, STATE_USED},
    STATE_REINFORCED: {STATE_TRUSTED, STATE_USED},
    STATE_SUSPECT: {STATE_QUARANTINED, STATE_USED, STATE_TRUSTED},
    STATE_QUARANTINED: {STATE_REVERIFIED, STATE_TRUSTED},
    STATE_REVERIFIED: {STATE_TRUSTED, STATE_USED},
}

# Default confidence threshold for quarantine
QUARANTINE_THRESHOLD = 0.3


def can_transition(current_state: str, new_state: str) -> bool:
    """Check if a state transition is valid."""
    return new_state in VALID_TRANSITIONS.get(current_state, set())


def transition(node: Dict[str, Any], new_state: str) -> Dict[str, Any]:
    """
    Attempt to transition a node to a new state.
    
    Returns:
        Dict with status, from, to on success; error on failure
    """
    current = node.get("state", STATE_TRUSTED)
    if not can_transition(current, new_state):
        valid = VALID_TRANSITIONS.get(current, set())
        return {
            "status": "error",
            "message": f"Invalid transition: {current} → {new_state}. Valid: {valid}",
        }
    node["state"] = new_state
    return {"status": "transitioned", "from": current, "to": new_state}


def classify_state(confidence: float, failure_count: int, success_count: int) -> str:
    """
    Classify what state a node should be in based on its metrics.
    
    Used for bootstrapping legacy nodes that lack a state field.
    """
    if confidence < QUARANTINE_THRESHOLD:
        return STATE_QUARANTINED
    if failure_count > 0 and failure_count > success_count:
        return STATE_SUSPECT
    if success_count > failure_count and success_count > 0:
        return STATE_REINFORCED
    if failure_count > 0:
        return STATE_FAILURE
    if success_count > 0:
        return STATE_SUCCESS
    return STATE_TRUSTED


def get_lifecycle_summary(nodes: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Summarize all nodes by trust lifecycle state.
    
    Args:
        nodes: Dict of {node_id: node_dict}
    
    Returns:
        Dict with state_counts, by_state details, quarantined_count
    """
    by_state: Dict[str, List[Dict]] = {}
    for nid, node in nodes.items():
        state = node.get("state", STATE_TRUSTED)
        by_state.setdefault(state, []).append({
            "id": nid,
            "content": node.get("content", "")[:100],
            "state": state,
        })
    
    return {
        "state_counts": {s: len(items) for s, items in by_state.items()},
        "by_state": by_state,
        "quarantined_count": len(by_state.get(STATE_QUARANTINED, [])),
        "total_nodes": len(nodes),
    }
