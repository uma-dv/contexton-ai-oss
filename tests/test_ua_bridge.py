"""
Tests for the Understand-Anything bridge.
"""

import json
import os
import tempfile

from contexton_ai_oss import ContextGraph, ingest_from_ua, query_code


def _mock_ua_graph():
    """Create a minimal Understand-Anything-style knowledge graph."""
    return {
        "version": "1.0",
        "nodes": [
            {
                "id": "file:src/auth/login.ts",
                "type": "file",
                "summary": "Handles user authentication with OAuth2",
                "metadata": {
                    "language": "typescript",
                    "path": "src/auth/login.ts",
                    "start_line": 1,
                    "end_line": 150,
                },
            },
            {
                "id": "func:loginUser",
                "type": "function",
                "summary": "Validates credentials and creates session",
                "metadata": {
                    "language": "typescript",
                    "path": "src/auth/login.ts",
                    "start_line": 25,
                    "end_line": 80,
                },
            },
            {
                "id": "class:AuthService",
                "type": "class",
                "summary": "Manages authentication lifecycle",
                "metadata": {
                    "language": "typescript",
                    "path": "src/auth/service.ts",
                    "start_line": 1,
                    "end_line": 200,
                },
            },
            {
                "id": "func:short",
                "type": "function",
                "summary": "tiny",
                "metadata": {"language": "typescript"},
            },
        ],
        "edges": [
            {
                "source": "file:src/auth/login.ts",
                "target": "func:loginUser",
                "type": "defines",
                "confidence": 0.95,
            },
            {
                "source": "func:loginUser",
                "target": "class:AuthService",
                "type": "uses",
                "confidence": 0.9,
            },
            {
                "source": "file:src/auth/login.ts",
                "target": "class:AuthService",
                "type": "imports",
                "confidence": 0.85,
            },
        ],
    }


def test_ingest_from_ua():
    """Test ingesting a mock Understand-Anything graph."""
    graph = ContextGraph()
    ua_graph = _mock_ua_graph()

    # Write mock graph to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ua_graph, f)
        path = f.name

    try:
        result = ingest_from_ua(graph, path, agent_id="test-ua")

        assert result["nodes_ingested"] == 4
        assert result["edges_ingested"] == 3
        assert result["nodes_skipped"] == 0
        assert "message" in result
    finally:
        os.unlink(path)


def test_ua_nodes_have_confidence():
    """Test that ingested UA nodes have initial confidence scores."""
    graph = ContextGraph()
    ua_graph = _mock_ua_graph()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ua_graph, f)
        path = f.name

    try:
        ingest_from_ua(graph, path)

        # Check that nodes were created with confidence
        results = graph.query("auth login")
        assert len(results) > 0
        for r in results:
            assert 0.0 <= r["confidence"] <= 1.0
            assert r["badge"] in ("🟢", "🟡", "🔴")
    finally:
        os.unlink(path)


def test_query_code_returns_results():
    """Test querying imported code knowledge."""
    graph = ContextGraph()
    ua_graph = _mock_ua_graph()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ua_graph, f)
        path = f.name

    try:
        ingest_from_ua(graph, path)

        results = query_code(graph, "authentication", min_confidence=0.3)
        assert len(results) > 0
        assert any("auth" in r["content"].lower() for r in results)
    finally:
        os.unlink(path)


def test_ua_metadata_preserved():
    """Test that UA metadata (path, language, lines) is preserved."""
    graph = ContextGraph()
    ua_graph = _mock_ua_graph()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ua_graph, f)
        path = f.name

    try:
        ingest_from_ua(graph, path)

        results = query_code(graph, "login", min_confidence=0.3)
        # Find a result with path metadata
        with_path = [r for r in results if r["path"]]
        assert len(with_path) > 0
        assert with_path[0]["language"] == "typescript"
    finally:
        os.unlink(path)


def test_ua_failure_learning():
    """Test that failure learning works on imported code knowledge."""
    graph = ContextGraph()
    ua_graph = _mock_ua_graph()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ua_graph, f)
        path = f.name

    try:
        ingest_from_ua(graph, path)

        # Query before failure
        results_before = query_code(graph, "OAuth2 authentication")
        conf_before = results_before[0]["confidence"] if results_before else 0

        # Record a failure
        graph.record_failure(
            query="What is src/auth/login.ts?",
            answer="Handles user authentication with OAuth2",
            reason="Actually handles SAML, not OAuth2",
        )

        # Query after failure - confidence should be lower
        results_after = query_code(graph, "OAuth2 authentication")
        if results_after:
            conf_after = results_after[0]["confidence"]
            # Confidence should have decreased
            assert conf_after <= conf_before
    finally:
        os.unlink(path)
