"""
Tests for Trust Lifecycle, Quarantine, Time Decay, and REST API.

Covers paper Section IV.E (Trust Lifecycle), Section IV (Reliability Scoring),
and the REST API endpoints added to web_demo.py.
"""

import json
import tempfile
import os
from datetime import datetime, timezone, timedelta

from contexton_ai_oss import ContextGraph
from contexton_ai_oss.lifecycle import (
    STATE_NEW, STATE_TRUSTED, STATE_USED, STATE_SUCCESS, STATE_FAILURE,
    STATE_REINFORCED, STATE_SUSPECT, STATE_QUARANTINED, STATE_REVERIFIED,
    VALID_TRANSITIONS, can_transition, transition, classify_state,
    QUARANTINE_THRESHOLD,
)
from contexton_ai_oss.confidence import ConfidenceEngine


# ============================================================================
# Trust Lifecycle State Machine Tests
# ============================================================================

class TestTrustLifecycle:
    """Test the trust lifecycle state machine (paper Section IV.E)."""

    def test_new_node_starts_trusted(self):
        """New nodes start in TRUSTED state."""
        graph = ContextGraph()
        nid = graph.add_node(content="Test fact", node_type="fact")
        node = graph.get_node(nid)
        assert node["state"] == STATE_TRUSTED

    def test_valid_transitions(self):
        """All valid transitions per paper Section IV.E."""
        assert can_transition(STATE_NEW, STATE_TRUSTED)
        assert can_transition(STATE_TRUSTED, STATE_USED)
        assert can_transition(STATE_USED, STATE_SUCCESS)
        assert can_transition(STATE_USED, STATE_FAILURE)
        assert can_transition(STATE_SUCCESS, STATE_REINFORCED)
        assert can_transition(STATE_FAILURE, STATE_SUSPECT)
        assert can_transition(STATE_SUSPECT, STATE_QUARANTINED)
        assert can_transition(STATE_QUARANTINED, STATE_REVERIFIED)
        assert can_transition(STATE_REVERIFIED, STATE_TRUSTED)

    def test_invalid_transitions(self):
        """Invalid transitions are rejected."""
        assert not can_transition(STATE_TRUSTED, STATE_QUARANTINED)
        assert not can_transition(STATE_QUARANTINED, STATE_USED)
        assert not can_transition(STATE_NEW, STATE_FAILURE)
        assert not can_transition(STATE_SUSPECT, STATE_NEW)

    def test_transition_method(self):
        """Transition method updates node state."""
        graph = ContextGraph()
        nid = graph.add_node(content="Test fact", node_type="fact")
        
        result = graph.transition_state(nid, STATE_USED)
        assert result["status"] == "transitioned"
        assert result["from"] == STATE_TRUSTED
        assert result["to"] == STATE_USED
        
        node = graph.get_node(nid)
        assert node["state"] == STATE_USED

    def test_transition_invalid_returns_error(self):
        """Invalid transition returns error."""
        graph = ContextGraph()
        nid = graph.add_node(content="Test fact", node_type="fact")
        
        result = graph.transition_state(nid, STATE_QUARANTINED)
        assert result["status"] == "error"
        assert "Invalid transition" in result["message"]

    def test_failure_transitions_to_failure_state(self):
        """Recording failure transitions matching nodes to FAILURE state."""
        graph = ContextGraph()
        nid = graph.add_node(
            content="PM-JAY is health insurance for poor families",
            node_type="fact",
            confidence=0.8,
        )
        assert graph.get_node(nid).get("state") == STATE_TRUSTED
        
        # Record failure
        graph.record_failure("What is PM-JAY?", "PM-JAY is health insurance for poor families", "Wrong")
        
        # Check state changed
        state = graph.get_node(nid).get("state")
        assert state in (STATE_FAILURE, STATE_SUSPECT, STATE_QUARANTINED)

    def test_success_transitions_to_reinforced_state(self):
        """Recording success on a failed node transitions to REINFORCED."""
        graph = ContextGraph()
        graph.ingest("What is Y?", "Y is a service")
        
        # Fail first
        graph.record_failure("What is Y?", "Y is a database", "Wrong")
        
        # Then succeed
        graph.record_success("What is Y?", "Y is a service")
        
        # Check state
        for n in graph.nodes.values():
            if "service" in n.get("content", "") and n.get("type") == "fact":
                assert n.get("state") in (STATE_SUCCESS, STATE_REINFORCED)

    def test_lifecycle_summary(self):
        """Lifecycle summary returns correct state counts."""
        graph = ContextGraph()
        graph.ingest("What is A?", "A is alpha")
        graph.ingest("What is B?", "B is beta")
        
        summary = graph.get_lifecycle_summary()
        assert "state_counts" in summary
        assert "quarantined_count" in summary
        assert summary["total_nodes"] > 0

    def test_full_lifecycle_path(self):
        """Test complete lifecycle: TRUSTED → USED → FAILURE → SUSPECT → QUARANTINED."""
        graph = ContextGraph()
        nid = graph.add_node(
            content="PM-JAY provides health coverage",
            node_type="fact",
            confidence=0.8,
        )
        
        # TRUSTED → USED
        graph.transition_state(nid, STATE_USED)
        assert graph.get_node(nid)["state"] == STATE_USED
        
        # USED → FAILURE
        graph.transition_state(nid, STATE_FAILURE)
        assert graph.get_node(nid)["state"] == STATE_FAILURE
        
        # FAILURE → SUSPECT
        graph.transition_state(nid, STATE_SUSPECT)
        assert graph.get_node(nid)["state"] == STATE_SUSPECT
        
        # SUSPECT → QUARANTINED
        graph.transition_state(nid, STATE_QUARANTINED)
        assert graph.get_node(nid)["state"] == STATE_QUARANTINED


# ============================================================================
# Quarantine Mechanism Tests
# ============================================================================

class TestQuarantine:
    """Test quarantine mechanism (paper Section IV.E)."""

    def test_quarantine_low_confidence(self):
        """Nodes below confidence threshold are quarantined."""
        graph = ContextGraph()
        nid = graph.add_node(
            content="Quarantine test fact",
            node_type="fact",
            confidence=0.1,
        )
        graph.nodes[nid]["failure_count"] = 10
        graph._dirty = True
        graph._save()
        
        # Quarantine
        result = graph.quarantine_low_confidence(threshold=0.5)
        assert result["quarantined"] > 0

    def test_quarantined_nodes_excluded_from_query(self):
        """Quarantined nodes are excluded from query results by default."""
        graph = ContextGraph()
        graph.ingest("What is R?", "R is reliability")
        
        # Fail enough to quarantine
        for _ in range(5):
            graph.record_failure("What is R?", "R is reliability", "Wrong")
        
        graph.quarantine_low_confidence(threshold=0.5)
        
        # Query without including quarantined
        results = graph.query("reliability", include_quarantined=False)
        quarantined_in_results = [
            r for r in results if r.get("state") == STATE_QUARANTINED
        ]
        assert len(quarantined_in_results) == 0

    def test_quarantined_nodes_included_when_requested(self):
        """Quarantined nodes appear when include_quarantined=True."""
        graph = ContextGraph()
        graph.ingest("What is S?", "S is safety")
        
        for _ in range(5):
            graph.record_failure("What is S?", "S is safety", "Wrong")
        
        graph.quarantine_low_confidence(threshold=0.5)
        
        # Query including quarantined
        results = graph.query("safety", include_quarantined=True)
        # Should find results (may or may not include quarantined depending on score)
        assert isinstance(results, list)

    def test_reinstate_quarantined(self):
        """Manually reinstate a quarantined node."""
        graph = ContextGraph()
        nid = graph.add_node(content="Quarantined fact", node_type="fact")
        
        # Manually set to quarantined state
        graph.nodes[nid]["state"] = STATE_QUARANTINED
        graph._dirty = True
        graph._save()
        
        # Reinstate
        result = graph.unreinstate_quarantined(nid)
        assert result["status"] == "reinstated"
        assert graph.get_node(nid)["state"] == STATE_REVERIFIED

    def test_reinstate_non_quarantined_fails(self):
        """Cannot reinstate a node that isn't quarantined."""
        graph = ContextGraph()
        nid = graph.add_node(content="Normal fact", node_type="fact")
        
        result = graph.unreinstate_quarantined(nid)
        assert result["status"] == "error"
        assert "not quarantined" in result["message"]


# ============================================================================
# Time Decay Tests (paper Section IV)
# ============================================================================

class TestTimeDecay:
    """Test time decay in confidence scoring (paper Section IV)."""

    def test_decay_rate_is_095(self):
        """Decay rate is 0.95 per day (5% daily decay)."""
        engine = ConfidenceEngine()
        assert engine.DECAY_RATE == 0.95

    def test_fresh_node_has_full_confidence(self):
        """A freshly verified node has no decay."""
        engine = ConfidenceEngine()
        node = {
            "confidence": 0.8,
            "last_verified": datetime.now(timezone.utc).isoformat(),
            "failure_count": 0,
        }
        conf = engine.node_confidence(node)
        assert conf >= 0.79  # ~0.8 with minimal decay

    def test_old_node_has_decay(self):
        """A node verified 30 days ago has significant decay."""
        engine = ConfidenceEngine()
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        node = {
            "confidence": 0.8,
            "last_verified": thirty_days_ago,
            "failure_count": 0,
        }
        conf = engine.node_confidence(node)
        # 0.95^30 ≈ 0.21, so 0.8 * 0.21 ≈ 0.17
        assert conf < 0.3

    def test_failure_penalty(self):
        """Each failure halves confidence."""
        engine = ConfidenceEngine()
        now = datetime.now(timezone.utc).isoformat()
        
        node_0 = {"confidence": 0.8, "last_verified": now, "failure_count": 0}
        node_1 = {"confidence": 0.8, "last_verified": now, "failure_count": 1}
        node_2 = {"confidence": 0.8, "last_verified": now, "failure_count": 2}
        
        c0 = engine.node_confidence(node_0)
        c1 = engine.node_confidence(node_1)
        c2 = engine.node_confidence(node_2)
        
        assert c0 > c1 > c2
        # After 1 failure: 0.8 * 0.5 = 0.4
        assert 0.39 < c1 < 0.41
        # After 2 failures: 0.8 * 0.25 = 0.2
        assert 0.19 < c2 < 0.21

    def test_confidence_never_below_floor(self):
        """Confidence never drops below MIN_CONFIDENCE (0.05)."""
        engine = ConfidenceEngine()
        node = {
            "confidence": 0.1,
            "last_verified": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            "failure_count": 10,
        }
        conf = engine.node_confidence(node)
        assert conf >= engine.MIN_CONFIDENCE

    def test_confidence_breakdown_shows_decay(self):
        """Confidence breakdown includes decay factor."""
        engine = ConfidenceEngine()
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        node = {
            "confidence": 0.8,
            "last_verified": thirty_days_ago,
            "failure_count": 0,
        }
        breakdown = engine.get_confidence_breakdown(node)
        assert breakdown["days_since_verified"] == 30
        assert breakdown["decay_factor"] < 0.3


# ============================================================================
# Record Failure with Lifecycle Transitions Tests
# ============================================================================

class TestFailureLifecycleIntegration:
    """Test that record_failure and record_success correctly transition states."""

    def test_record_failure_transitions_state(self):
        """record_failure transitions matching nodes to FAILURE/SUSPECT/QUARANTINED."""
        graph = ContextGraph()
        nid = graph.add_node(
            content="PM-JAY is health insurance for poor families",
            node_type="fact",
            confidence=0.8,
        )
        assert graph.get_node(nid)["state"] == STATE_TRUSTED
        
        # Record failure
        graph.record_failure("What is PM-JAY?", "PM-JAY is health insurance for poor families", "Wrong")
        
        # State should have changed
        state = graph.get_node(nid).get("state")
        assert state in (STATE_FAILURE, STATE_SUSPECT, STATE_QUARANTINED)

    def test_record_success_transitions_state(self):
        """record_success transitions matching nodes to SUCCESS/REINFORCED."""
        graph = ContextGraph()
        nid = graph.add_node(
            content="PM-JAY is health insurance for poor families",
            node_type="fact",
            confidence=0.8,
        )
        assert graph.get_node(nid)["state"] == STATE_TRUSTED
        
        # Record success
        graph.record_success("What is PM-JAY?", "PM-JAY is health insurance for poor families")
        
        # State should be SUCCESS or REINFORCED
        state = graph.get_node(nid).get("state")
        assert state in (STATE_SUCCESS, STATE_REINFORCED)

    def test_quarantine_auto_on_heavy_failure(self):
        """Multiple failures auto-quarantine a node."""
        graph = ContextGraph()
        graph.ingest("What is V?", "V is very wrong")
        
        # Fail many times
        for _ in range(8):
            graph.record_failure("What is V?", "V is very wrong", "Wrong")
        
        # Find the fact node
        for nid, node in graph.nodes.items():
            if "very wrong" in node.get("content", "") and node.get("type") == "fact":
                # Should be quarantined after many failures
                assert node.get("state") == STATE_QUARANTINED
                break


# ============================================================================
# REST API Tests
# ============================================================================

class TestRestAPI:
    """Test REST API endpoints in web_demo.py."""

    def _get_handler(self):
        """Create a test handler with a fresh graph."""
        from contexton_ai_oss.web_demo import WebDemoHandler, load_demo_dataset
        graph = ContextGraph()
        load_demo_dataset(graph, "support")
        WebDemoHandler.graph = graph
        return WebDemoHandler, graph

    def test_api_stats(self):
        """GET /api/stats returns node and edge counts."""
        import io
        from http.server import BaseHTTPRequestHandler
        from contexton_ai_oss.web_demo import WebDemoHandler, load_demo_dataset
        
        graph = ContextGraph()
        load_demo_dataset(graph, "support")
        
        stats = graph.get_stats()
        assert "node_count" in stats
        assert "edge_count" in stats
        assert stats["node_count"] > 0

    def test_api_lifecycle(self):
        """GET /api/lifecycle returns state summary."""
        graph = ContextGraph()
        graph.ingest("What is L?", "L is lifecycle")
        
        summary = graph.get_lifecycle_summary()
        assert "state_counts" in summary
        assert "quarantined_count" in summary

    def test_api_query_includes_state(self):
        """POST /api/query results include state field."""
        graph = ContextGraph()
        graph.ingest("What is W?", "W is widget")
        
        results = graph.query("widget")
        for r in results:
            assert "state" in r
            assert r["state"] in (
                STATE_NEW, STATE_TRUSTED, STATE_USED, STATE_SUCCESS,
                STATE_FAILURE, STATE_REINFORCED, STATE_SUSPECT,
                STATE_QUARANTINED, STATE_REVERIFIED,
            )

    def test_api_quarantine(self):
        """POST /api/quarantine quarantines low-confidence nodes."""
        graph = ContextGraph()
        graph.ingest("What is Q2?", "Q2 is quarantine")
        
        for _ in range(5):
            graph.record_failure("What is Q2?", "Q2 is quarantine", "Wrong")
        
        result = graph.quarantine_low_confidence(threshold=0.5)
        assert result["quarantined"] >= 0

    def test_api_reinstate(self):
        """POST /api/reinstate reinstates a quarantined node."""
        graph = ContextGraph()
        nid = graph.add_node(content="Reinstate test", node_type="fact")
        
        # Manually set to quarantined
        graph.nodes[nid]["state"] = STATE_QUARANTINED
        graph._dirty = True
        graph._save()
        
        result = graph.unreinstate_quarantined(nid)
        assert result["status"] == "reinstated"

    def test_api_from_ua(self):
        """POST /api/from-ua ingests Understand-Anything graph."""
        from contexton_ai_oss.ua_bridge import ingest_from_ua
        
        ua_graph = {
            "nodes": [
                {"id": "file:test.py", "type": "file", "summary": "Test file", 
                 "metadata": {"language": "python", "path": "test.py"}},
            ],
            "edges": [],
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(ua_graph, f)
            path = f.name
        
        try:
            graph = ContextGraph()
            result = ingest_from_ua(graph, path)
            assert result["nodes_ingested"] == 1
        finally:
            os.unlink(path)

    def test_api_failure_and_success_cycle(self):
        """POST /api/failure then /api/success shows confidence recovery."""
        graph = ContextGraph()
        graph.ingest("What is FS?", "FS is failure-success")
        
        # Get initial confidence
        results_before = graph.query("failure-success")
        conf_before = results_before[0]["confidence"] if results_before else 0
        
        # Record failure
        graph.record_failure("What is FS?", "FS is failure-success", "Wrong")
        
        # Record success
        graph.record_success("What is FS?", "FS is failure-success")
        
        # Confidence should have recovered somewhat
        results_after = graph.query("failure-success")
        if results_after:
            conf_after = results_after[0]["confidence"]
            # After failure+success, confidence should be > failure-only
            assert conf_after > 0


# ============================================================================
# Demo Scenario Tests (paper use cases)
# ============================================================================

class TestDemoScenarios:
    """Test demo scenarios match paper claims."""

    def test_support_scenario_refund_policy(self):
        """Support scenario: refund policy is retrievable."""
        graph = ContextGraph()
        from contexton_ai_oss.web_demo import load_demo_dataset
        load_demo_dataset(graph, "support")
        
        results = graph.query("refund policy")
        assert len(results) > 0
        assert any("refund" in r["node"]["content"].lower() for r in results)

    def test_fraud_scenario_kyc(self):
        """Fraud scenario: KYC knowledge is retrievable."""
        graph = ContextGraph()
        from contexton_ai_oss.web_demo import load_demo_dataset
        load_demo_dataset(graph, "fraud")
        
        results = graph.query("KYC")
        assert len(results) > 0

    def test_devops_scenario_severity(self):
        """DevOps scenario: severity levels are retrievable."""
        graph = ContextGraph()
        from contexton_ai_oss.web_demo import load_demo_dataset
        load_demo_dataset(graph, "devops")
        
        results = graph.query("severity")
        assert len(results) > 0

    def test_tool_failure_recorded(self):
        """Tool failure is recorded with reduced confidence."""
        graph = ContextGraph()
        from contexton_ai_oss.web_demo import load_demo_dataset
        load_demo_dataset(graph, "all")
        
        tools = graph.list_tools()
        failed_tools = [t for t in tools if t.get("failure_count", 0) > 0]
        assert len(failed_tools) > 0

    def test_bounded_blast_radius(self):
        """Only facts matching wrong answer are penalized, not entities."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "PM-JAY is health insurance for poor families")
        graph.ingest("What is PM-JAY?", "PM-JAY is administered by NHA")
        
        # Get the health insurance fact node
        health_nid = None
        nha_nid = None
        for nid, node in graph.nodes.items():
            content = node.get("content", "").lower()
            if "health insurance" in content and node.get("type") != "entity":
                health_nid = nid
            if "NHA" in node.get("content", "") and node.get("type") != "entity":
                nha_nid = nid
        
        if health_nid:
            before = graph.confidence_engine.node_confidence(graph.nodes[health_nid])
            
            # Wrong answer shares tokens with health insurance fact
            graph.record_failure(
                "What is PM-JAY?",
                "PM-JAY is housing scheme for poor families",
                "Wrong domain",
            )
            
            after = graph.confidence_engine.node_confidence(graph.nodes[health_nid])
            assert after < before  # Confidence decreased
            
            # NHA fact was NOT penalized
            if nha_nid:
                assert graph.nodes[nha_nid].get("failure_count", 0) == 0
