"""
MCP server for ContextOn.AI OSS.

Exposes the knowledge graph as Model Context Protocol tools so that
Claude, Cursor, Codex, and other MCP-compatible assistants can query
and update it.

Requires the optional 'mcp' dependency:

    pip install contexton-ai-oss[mcp]

Start it with the CLI:

    contexton-ai-oss serve                 # stdio (for Claude/Cursor MCP config)
    contexton-ai-oss serve --port 8080     # streamable HTTP
"""

from typing import Any, Dict, List, Optional


def create_server(data_dir: Optional[str] = None):
    """
    Create an MCP server backed by a ContextGraph instance.

    Args:
        data_dir: Directory used to persist the graph. If None, the
            graph lives in memory only.

    Returns:
        An mcp.server.mcpserver.server.MCPServer instance.
    """
    # Lazy import so the core package never requires the mcp SDK
    from mcp.server.mcpserver.server import MCPServer

    from .graph import ContextGraph

    graph = ContextGraph(data_dir=data_dir)

    server = MCPServer(
        name="contexton-ai-oss",
        version="0.1.0",
        title="ContextOn.AI OSS",
        description=(
            "Confidence-aware knowledge graph with failure learning. "
            "Agents can store conversation knowledge, query it, learn from "
            "wrong answers, and resolve entity aliases."
        ),
    )

    @server.tool(
        title="Ingest conversation",
        description="Store a conversation turn (question + answer) into the knowledge graph.",
    )
    def ingest(query: str, answer: str, agent_id: str = "") -> Dict[str, Any]:
        """Store a conversation turn into the graph."""
        return graph.ingest(query=query, answer=answer, agent_id=agent_id)

    @server.tool(
        title="Query the graph",
        description=(
            "Retrieve knowledge nodes relevant to a question, ranked by "
            "relevance and confidence, with quality badges."
        ),
    )
    def query(
        query: str,
        min_confidence: float = 0.0,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query the graph with confidence-ranked retrieval."""
        return [
            {
                "content": r["node"].get("content"),
                "node_type": r["node"].get("type"),
                "confidence": round(r["confidence"], 3),
                "badge": r["badge"],
                "score": round(r["score"], 3),
            }
            for r in graph.query(query, min_confidence=min_confidence, max_results=max_results)
        ]

    @server.tool(
        title="Record a failure",
        description=(
            "Tell the graph that an agent gave a WRONG answer. The graph "
            "marks the related knowledge as less reliable so future queries "
            "avoid it. This is ContextOn.AI OSS's key differentiator."
        ),
    )
    def record_failure(query: str, answer: str, reason: str = "") -> Dict[str, Any]:
        """Record that an agent gave a wrong answer."""
        return graph.record_failure(query=query, answer=answer, reason=reason)

    @server.tool(
        title="Record a success",
        description=(
            "Tell the graph that an agent gave a CORRECT answer. Related "
            "knowledge is verified and confidence is restored."
        ),
    )
    def record_success(query: str, answer: str) -> Dict[str, Any]:
        """Record that an agent gave a correct answer."""
        return graph.record_success(query=query, answer=answer)

    @server.tool(
        title="Suggest questions",
        description="Ask the graph what it can answer - returns suggested questions with reasons.",
    )
    def suggest_questions(top_n: int = 5) -> List[Dict[str, Any]]:
        """Suggest questions the graph can answer."""
        return graph.suggest_questions(top_n=top_n)

    @server.tool(
        title="Graph statistics",
        description="Get node/edge counts and confidence distribution of the graph.",
    )
    def get_stats() -> Dict[str, Any]:
        """Get graph statistics."""
        return graph.get_stats()

    @server.tool(
        title="Get entity aliases",
        description="List known entity aliases (e.g. PM-JAY -> Pradhan Mantri Jan Arogya Yojana).",
    )
    def get_aliases(entity: str = "") -> Dict[str, List[str]]:
        """Get entity alias mappings."""
        return graph.get_aliases(entity)

    @server.tool(
        title="Resolve entity aliases",
        description="Merge duplicate entity nodes into canonical nodes and report what was merged.",
    )
    def resolve_aliases() -> Dict[str, Any]:
        """Merge duplicate entity nodes."""
        return graph.resolve_aliases()

    @server.tool(
        title="Confidence breakdown",
        description="Explain how a node's confidence score was calculated.",
    )
    def get_confidence_breakdown(node_id: str) -> Dict[str, Any]:
        """Get the confidence breakdown for a node."""
        node = graph.get_node(node_id)
        if node is None:
            return {"error": f"no node with id {node_id}"}
        return graph.confidence_engine.get_confidence_breakdown(node)

    # --- Agent capabilities: skills, tools, context, hygiene, scoping ---

    @server.tool(
        title="Ingest a skill/procedure",
        description="Store a reusable 'how to' procedure with ordered steps.",
    )
    def ingest_procedure(name: str, steps: List[str], agent_id: str = "") -> Dict[str, Any]:
        """Store a reusable skill/procedure."""
        return graph.ingest_procedure(name=name, steps=steps, agent_id=agent_id)

    @server.tool(
        title="Get a procedure",
        description="Retrieve a stored procedure by name, with its ordered steps.",
    )
    def get_procedure(name: str) -> Dict[str, Any]:
        """Retrieve a procedure by name."""
        proc = graph.get_procedure(name)
        if proc is None:
            return {"error": f"no procedure named {name}"}
        return proc

    @server.tool(
        title="Register a tool",
        description="Register a tool in the graph's tool registry memory.",
    )
    def register_tool(name: str, description: str = "", agent_id: str = "") -> str:
        """Register a tool."""
        return graph.register_tool(name=name, description=description, agent_id=agent_id)

    @server.tool(
        title="List tools",
        description="List registered tools with confidence, badge, and failure counts.",
    )
    def list_tools() -> List[Dict[str, Any]]:
        """List registered tools."""
        return graph.list_tools()

    @server.tool(
        title="Record a tool outcome",
        description="Record whether a tool call succeeded or failed (failures lower the tool's confidence).",
    )
    def record_tool_outcome(name: str, success: bool, error: str = "") -> Dict[str, Any]:
        """Record a tool call outcome."""
        return graph.record_tool_outcome(name=name, success=success, error=error)

    @server.tool(
        title="Get auto-context",
        description=(
            "Assemble confident, badge-annotated context for an agent's current "
            "question - the auto-context injection layer."
        ),
    )
    def get_context(
        query: str,
        session_id: str = "",
        max_tokens: int = 2000,
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """Assemble context for an agent."""
        return graph.get_context(
            query=query,
            session_id=session_id,
            max_tokens=max_tokens,
            min_confidence=min_confidence,
        )

    @server.tool(
        title="Agent memory",
        description="List all knowledge owned by a specific agent (transparency scoping).",
    )
    def get_agent_memory(agent_id: str) -> Dict[str, Any]:
        """Return an agent's owned knowledge."""
        return graph.get_agent_memory(agent_id)

    @server.tool(
        title="Memory hygiene sweep",
        description="Report stale and low-confidence knowledge that needs re-verification.",
    )
    def hygiene_sweep(max_age_days: int = 30, min_confidence: float = 0.5) -> Dict[str, Any]:
        """Run the memory hygiene sweep."""
        return graph.hygiene_sweep(max_age_days=max_age_days, min_confidence=min_confidence)

    @server.tool(
        title="Prune old knowledge",
        description="Report (or, with dry_run=False, delete) old low-confidence facts and observations.",
    )
    def prune(max_age_days: int = 90, min_confidence: float = 0.2, dry_run: bool = True) -> Dict[str, Any]:
        """Prune old, low-confidence knowledge."""
        return graph.prune(max_age_days=max_age_days, min_confidence=min_confidence, dry_run=dry_run)

    @server.tool(
        title="Visualize graph",
        description="Generate an interactive HTML visualization of the graph.",
    )
    def visualize(output_path: str = "graph.html") -> str:
        """Generate an interactive HTML visualization."""
        return graph.visualize(output_path)

    return server


def run_stdio(data_dir: Optional[str] = None) -> None:
    """Run the MCP server over stdio (for Claude/Cursor MCP configs)."""
    import asyncio

    server = create_server(data_dir=data_dir)
    asyncio.run(server.run_stdio_async())


def run_http(data_dir: Optional[str] = None, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the MCP server over streamable HTTP."""
    import asyncio

    server = create_server(data_dir=data_dir)
    asyncio.run(server.run_streamable_http_async(host=host, port=port))
