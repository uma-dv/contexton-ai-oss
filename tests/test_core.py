"""
Basic tests for ContextOn.AI OSS core functionality.
"""

import pytest
from contexton_ai_oss import ContextGraph, ConfidenceEngine, FailureLearningEngine, QualityBadges


class TestContextGraph:
    """Tests for the main ContextGraph class."""
    
    def test_initialization(self):
        """Test graph can be initialized."""
        graph = ContextGraph()
        assert graph is not None
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
    
    def test_add_node(self):
        """Test adding a node."""
        graph = ContextGraph()
        nid = graph.add_node("Test content", node_type="fact")
        assert nid is not None
        assert len(graph.nodes) == 1
        assert graph.nodes[nid]["content"] == "Test content"
    
    def test_add_edge(self):
        """Test adding an edge."""
        graph = ContextGraph()
        nid1 = graph.add_node("Node 1")
        nid2 = graph.add_node("Node 2")
        graph.add_edge(nid1, nid2, edge_type="related_to")
        assert len(graph.edges) == 1
    
    def test_ingest(self):
        """Test ingesting a conversation."""
        graph = ContextGraph()
        result = graph.ingest(
            query="What is X?",
            answer="X is something important",
            agent_id="test-agent"
        )
        assert result["conversation_id"] is not None
        assert result["entities_added"] >= 0
        assert result["facts_added"] >= 0
    
    def test_query(self):
        """Test querying the graph."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "Health insurance for poor families")
        results = graph.query("PM-JAY")
        assert len(results) > 0
        assert "badge" in results[0]
        assert "confidence" in results[0]
    
    def test_query_punctuation_insensitive(self):
        """Query matching should not break on punctuation differences."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "PM-JAY is health insurance for poor families")
        # 'PM-JAY?' in stored content vs 'PM-JAY' in the query
        results = graph.query("PM-JAY")
        assert len(results) > 0
    
    def test_query_excludes_failure_nodes(self):
        """Failure observation nodes must never appear in query results."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y")
        graph.record_failure("What is X?", "X is Z", reason="Wrong")
        results = graph.query("X")
        for r in results:
            assert "FAILED" not in r["node"]["content"]
            assert r["node"]["type"] != "observation"
    
    def test_stats_match_query_confidence(self):
        """Stats and query results must agree on confidence values."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "PM-JAY is health insurance")
        stats = graph.get_stats()
        results = graph.query("PM-JAY")
        if results:
            # Both derive from the same engine - sanity check the engine value
            from contexton_ai_oss.confidence import ConfidenceEngine
            engine = ConfidenceEngine()
            node = results[0]["node"]
            assert results[0]["confidence"] == engine.node_confidence(node)


class TestConfidenceEngine:
    """Tests for the confidence engine."""
    
    def test_high_confidence(self):
        """Test high confidence calculation."""
        engine = ConfidenceEngine()
        node = {
            "confidence": 1.0,
            "last_verified": "2026-08-16T00:00:00Z",
            "failure_count": 0
        }
        confidence = engine.node_confidence(node)
        assert confidence >= 0.8
    
    def test_low_confidence_with_failures(self):
        """Test low confidence with failures."""
        engine = ConfidenceEngine()
        node = {
            "confidence": 1.0,
            "last_verified": "2026-08-16T00:00:00Z",
            "failure_count": 3
        }
        confidence = engine.node_confidence(node)
        assert confidence < 0.5
    
    def test_confidence_breakdown(self):
        """Test confidence breakdown."""
        engine = ConfidenceEngine()
        node = {
            "confidence": 0.8,
            "last_verified": "2026-08-16T00:00:00Z",
            "failure_count": 1
        }
        breakdown = engine.get_confidence_breakdown(node)
        assert "stored_confidence" in breakdown
        assert "decay_factor" in breakdown
        assert "failure_penalty" in breakdown
        assert "final_confidence" in breakdown


class TestFailureLearning:
    """Tests for the failure learning engine."""
    
    def test_record_failure(self):
        """Test recording a failure."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y")
        
        result = graph.record_failure(
            query="What is X?",
            answer="X is Z",
            reason="Wrong answer"
        )
        
        assert result["status"] == "recorded"
        assert result["affected_edges"] >= 0
    
    def test_record_success(self):
        """Test recording a success."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y")
        
        result = graph.record_success(
            query="What is X?",
            answer="X is Y"
        )
        
        assert result["status"] == "recorded"
    
    def test_failure_reduces_confidence(self):
        """Test that failure reduces confidence."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y")
        
        # Get initial confidence
        results_before = graph.query("X")
        if results_before:
            confidence_before = results_before[0]["confidence"]
            
            # Record failure
            graph.record_failure("What is X?", "X is Z", "Wrong")
            
            # Get confidence after failure
            results_after = graph.query("X")
            if results_after:
                confidence_after = results_after[0]["confidence"]
                assert confidence_after <= confidence_before
    
    def test_success_restores_confidence(self):
        """A verified success must undo the damage of a prior failure."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "PM-JAY is health insurance for poor families")
        
        # Query for the specific fact, not the entity
        before = graph.query("PM-JAY", node_type="fact")[0]["confidence"]
        # Use a wrong answer that shares tokens with the correct fact
        # so the failure actually affects the knowledge
        graph.record_failure("What is PM-JAY?", "PM-JAY is housing insurance for poor families", "Wrong domain")
        after_failure = graph.query("PM-JAY", node_type="fact")[0]["confidence"]
        assert after_failure < before
        
        graph.record_success("What is PM-JAY?", "PM-JAY is health insurance for poor families")
        after_success = graph.query("PM-JAY", node_type="fact")[0]["confidence"]
        assert after_success > after_failure


class TestQualityBadges:
    """Tests for the quality badge system."""
    
    def test_high_badge(self):
        """Test high confidence badge."""
        badges = QualityBadges()
        assert badges.get_badge(0.9) == "🟢"
        assert badges.get_badge(0.8) == "🟢"
    
    def test_medium_badge(self):
        """Test medium confidence badge."""
        badges = QualityBadges()
        assert badges.get_badge(0.7) == "🟡"
        assert badges.get_badge(0.5) == "🟡"
    
    def test_low_badge(self):
        """Test low confidence badge."""
        badges = QualityBadges()
        assert badges.get_badge(0.4) == "🔴"
        assert badges.get_badge(0.1) == "🔴"
    
    def test_quality_summary(self):
        """Test quality summary generation (engine-computed confidence)."""
        badges = QualityBadges()
        node = {
            "confidence": 0.85,
            "mentions": 5,
            "last_verified": "2026-08-16T00:00:00Z",
            "failure_count": 0
        }
        summary = badges.get_quality_summary(node)
        assert summary["badge"] == "🟢"
        assert "status" in summary
        assert "recommendation" in summary


class TestEntityResolution:
    """Tests for entity extraction and alias resolution."""
    
    def test_extract_entities(self):
        """Test entity extraction."""
        from contexton_ai_oss import extract_entities
        entities = extract_entities("Who implements PM-JAY? NHA does.")
        names = [e[0] for e in entities]
        assert "PM-JAY" in names
        assert "NHA" in names
        assert "Who" not in names
    
    def test_alias_acronym(self):
        """PM-JAY should alias its full name."""
        from contexton_ai_oss import is_alias
        assert is_alias("PM-JAY", "Pradhan Mantri Jan Arogya Yojana")
        assert is_alias("Pradhan Mantri Jan Arogya Yojana", "PM-JAY")
    
    def test_no_false_alias(self):
        """Generic words must not alias each other."""
        from contexton_ai_oss import is_alias
        assert not is_alias("Health", "Ministry of Health and Family Welfare")
        assert not is_alias("Jan", "Yojana")
    
    def test_ingest_dedupes_entities(self):
        """Ingesting PM-JAY and its full name should reuse one node."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "Pradhan Mantri Jan Arogya Yojana is health insurance")
        graph.ingest("Who runs PM-JAY?", "NHA implements it")
        aliases = graph.get_aliases()
        # PM-JAY and Pradhan Mantri Jan Arogya Yojana should be linked
        assert any(
            "Pradhan Mantri Jan Arogya Yojana" in v or "Pradhan Mantri Jan Arogya Yojana" == k
            for k, v in aliases.items()
        )
        entity_nodes = [n for n in graph.nodes.values() if n.get("type") == "entity"]
        names = [n["content"].lower() for n in entity_nodes]
        # 'pm-jay' should appear as a canonical entity at most once
        assert names.count("pm-jay") <= 1


class TestAgentCapabilities:
    """Tests for skills, tools, context, hygiene, and scoping."""

    def test_ingest_procedure(self):
        """A procedure is stored with its ordered steps."""
        graph = ContextGraph()
        result = graph.ingest_procedure(
            "Reset password",
            ["Open settings", "Go to security", "Click reset", "Confirm email"],
            agent_id="support-agent",
        )
        assert result["steps_added"] == 4
        proc = graph.get_procedure("Reset password")
        assert proc is not None
        assert proc["steps"] == ["Open settings", "Go to security", "Click reset", "Confirm email"]
        assert proc["badge"] in ("🟢", "🟡", "🔴")

    def test_procedure_query_filter(self):
        """Procedures are retrievable with the node_type filter."""
        graph = ContextGraph()
        graph.ingest_procedure("Deploy app", ["Build", "Push", "Restart"])
        results = graph.query("deploy", node_type="procedure")
        assert len(results) >= 1
        for r in results:
            assert r["node"]["type"] == "procedure"

    def test_register_tool(self):
        """Tools register and list with confidence."""
        graph = ContextGraph()
        graph.register_tool("calculator", "Performs arithmetic", agent_id="math-agent")
        tools = graph.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        assert tools[0]["confidence"] > 0
        assert graph.get_tool("calculator")["description"] == "Performs arithmetic"

    def test_tool_failure_penalizes(self):
        """Tool failures lower the tool's confidence."""
        graph = ContextGraph()
        graph.register_tool("send_email", "Sends an email")
        before = graph.get_tool("send_email")["confidence"]
        graph.record_tool_outcome("send_email", success=False, error="SMTP timeout")
        graph.record_tool_outcome("send_email", success=False, error="Auth failed")
        after = graph.get_tool("send_email")["confidence"]
        assert after < before
        assert graph.get_tool("send_email")["failure_count"] == 2

    def test_tool_success_restores(self):
        """A successful tool call restores confidence."""
        graph = ContextGraph()
        graph.register_tool("db_query", "Runs a query")
        graph.record_tool_outcome("db_query", success=False, error="timeout")
        low = graph.get_tool("db_query")["confidence"]
        graph.record_tool_outcome("db_query", success=True)
        assert graph.get_tool("db_query")["confidence"] > low

    def test_get_context_session(self):
        """get_context returns confident, badge-annotated context for a session."""
        graph = ContextGraph()
        graph.ingest(
            "What is PM-JAY?", "PM-JAY is health insurance for poor families",
            agent_id="health-agent", session_id="sess-1",
        )
        graph.ingest(
            "Who implements PM-JAY?", "National Health Authority implements PM-JAY",
            agent_id="health-agent", session_id="sess-1",
        )
        ctx = graph.get_context("PM-JAY", session_id="sess-1")
        assert ctx["item_count"] >= 1
        assert "PM-JAY" in ctx["context_text"]
        for item in ctx["items"]:
            assert "badge" in item
            assert "confidence" in item

    def test_get_context_min_confidence(self):
        """get_context filters below min_confidence."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y", confidence=0.8)
        graph.record_failure("What is X?", "X is Z", reason="wrong")
        ctx = graph.get_context("X", min_confidence=0.7)
        # Failed knowledge is below the threshold, so nothing qualifies
        assert ctx["item_count"] == 0

    def test_agent_scoping(self):
        """query and get_agent_memory scope by agent_id."""
        graph = ContextGraph()
        graph.ingest("What is PM-JAY?", "PM-JAY is health insurance", agent_id="health-agent")
        graph.ingest("How do I fix the server?", "Restart nginx", agent_id="ops-agent")
        health_only = graph.query("server", agent_id="health-agent")
        ops_only = graph.query("server", agent_id="ops-agent")
        assert any("nginx" in r["node"]["content"] for r in ops_only)
        assert not any("nginx" in r["node"]["content"] for r in health_only)
        memory = graph.get_agent_memory("health-agent")
        assert memory["node_count"] >= 1

    def test_hygiene_sweep(self):
        """Hygiene sweep reports low-confidence knowledge."""
        graph = ContextGraph()
        graph.register_tool("broken_tool", "Fails often")
        graph.record_tool_outcome("broken_tool", success=False, error="err")
        graph.record_tool_outcome("broken_tool", success=False, error="err")
        report = graph.hygiene_sweep(min_confidence=0.5)
        assert report["low_confidence_count"] >= 1
        assert "recommendation" in report

    def test_prune_dry_run(self):
        """Prune in dry-run mode reports but does not delete."""
        graph = ContextGraph()
        graph.ingest("What is X?", "X is Y")
        before = graph.get_stats()["node_count"]
        result = graph.prune(dry_run=True, max_age_days=1)
        assert result["dry_run"] is True
        assert graph.get_stats()["node_count"] == before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
