"""
Command-line interface for ContextOn.AI OSS.

Usage:
    contexton-ai-oss serve [--port 8080] [--data-dir DIR]   # MCP server
    contexton-ai-oss query "question" [--data-dir DIR]
    contexton-ai-oss ingest "question" "answer" [--agent agent]
    contexton-ai-oss record-failure "question" "answer" [--reason r]
    contexton-ai-oss record-success "question" "answer"
    contexton-ai-oss stats [--data-dir DIR]
    contexton-ai-oss visualize [OUTPUT] [--data-dir DIR]
    contexton-ai-oss aliases [--data-dir DIR]
"""

import argparse
import sys

from .graph import ContextGraph

VERSION = "0.1.0"


def _print_utf8(obj) -> None:
    """Print a Python object as readable text, emoji-safe on Windows."""
    import io

    if isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if isinstance(obj, str):
        print(obj)
    elif isinstance(obj, list):
        for item in obj:
            print(item)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            print(f"{key}: {value}")
    else:
        print(obj)


def _load_graph(data_dir):
    return ContextGraph(data_dir=data_dir)


def cmd_serve(args) -> None:
    from .mcp_server import run_http, run_stdio

    if args.port:
        print(f"Starting ContextOn.AI OSS MCP server on http://{args.host}:{args.port}/mcp", file=sys.stderr)
        run_http(data_dir=args.data_dir, host=args.host, port=args.port)
    else:
        print("Starting ContextOn.AI OSS MCP server (stdio)...", file=sys.stderr)
        run_stdio(data_dir=args.data_dir)


def cmd_query(args) -> None:
    graph = _load_graph(args.data_dir)
    results = graph.query(args.query, min_confidence=args.min_confidence, max_results=args.max_results)
    if not results:
        print("No results found.")
        return
    for r in results:
        print(f"{r['badge']} {r['confidence']:.0%} | {r['node']['content'][:120]}")


def cmd_ingest(args) -> None:
    graph = _load_graph(args.data_dir)
    result = graph.ingest(query=args.query, answer=args.answer, agent_id=args.agent)
    _print_utf8(result)


def cmd_record_failure(args) -> None:
    graph = _load_graph(args.data_dir)
    result = graph.record_failure(query=args.query, answer=args.answer, reason=args.reason)
    _print_utf8(result)


def cmd_record_success(args) -> None:
    graph = _load_graph(args.data_dir)
    result = graph.record_success(query=args.query, answer=args.answer)
    _print_utf8(result)


def cmd_stats(args) -> None:
    graph = _load_graph(args.data_dir)
    _print_utf8(graph.get_stats())


def cmd_visualize(args) -> None:
    graph = _load_graph(args.data_dir)
    path = graph.visualize(args.output)
    print(f"Visualization written to {path}")


def cmd_aliases(args) -> None:
    graph = _load_graph(args.data_dir)
    aliases = graph.get_aliases()
    if not aliases:
        print("No entity aliases recorded.")
        return
    for canonical, alias_list in aliases.items():
        print(f"{canonical} -> {', '.join(alias_list)}")


def cmd_procedure(args) -> None:
    graph = _load_graph(args.data_dir)
    if args.action == "ingest":
        steps = [s.strip() for s in args.steps.split(";") if s.strip()]
        result = graph.ingest_procedure(name=args.name, steps=steps, agent_id=args.agent)
        _print_utf8(result)
    else:  # get
        proc = graph.get_procedure(args.name)
        if proc is None:
            print(f"No procedure named '{args.name}'")
            return
        print(f"{proc['badge']} {proc['name']} (confidence {proc['confidence']:.0%})")
        for i, step in enumerate(proc["steps"], 1):
            print(f"  {i}. {step}")


def cmd_tools(args) -> None:
    graph = _load_graph(args.data_dir)
    if args.action == "register":
        graph.register_tool(name=args.name, description=args.description, agent_id=args.agent)
        print(f"Registered tool: {args.name}")
    elif args.action == "list":
        tools = graph.list_tools()
        if not tools:
            print("No tools registered.")
            return
        for t in tools:
            print(f"{t['badge']} {t['name']} (confidence {t['confidence']:.0%}, failures {t['failure_count']})")
    elif args.action == "outcome":
        result = graph.record_tool_outcome(name=args.name, success=args.success, error=args.error)
        _print_utf8(result)


def cmd_context(args) -> None:
    graph = _load_graph(args.data_dir)
    ctx = graph.get_context(
        query=args.query,
        session_id=args.session,
        max_tokens=args.max_tokens,
        min_confidence=args.min_confidence,
    )
    print(ctx["context_text"] or "No context found.")
    print(f"\n({ctx['item_count']} items)")


def cmd_hygiene(args) -> None:
    graph = _load_graph(args.data_dir)
    report = graph.hygiene_sweep(max_age_days=args.max_age, min_confidence=args.min_confidence)
    _print_utf8(report)


def cmd_agent_memory(args) -> None:
    graph = _load_graph(args.data_dir)
    memory = graph.get_agent_memory(args.agent)
    print(f"Agent '{args.agent}': {memory['node_count']} nodes")
    for ntype, nodes in memory["by_type"].items():
        print(f"  [{ntype}]")
        for n in nodes[:10]:
            print(f"    {n['badge']} {n['content'][:80]}")


def cmd_web(args) -> None:
    from .web_demo import run_web

    run_web(host=args.host, port=args.port, data_dir=args.data_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contexton-ai-oss",
        description="Confidence-aware knowledge graph with failure learning for AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"contexton-ai-oss {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    # serve
    p = sub.add_parser("serve", help="Run the MCP server (stdio by default, --port for HTTP)")
    p.add_argument("--port", type=int, default=None, help="Serve over HTTP on this port (default: stdio)")
    p.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind (HTTP mode only)")
    p.add_argument("--data-dir", type=str, default=None, help="Directory to persist the graph")
    p.set_defaults(func=cmd_serve)

    # query
    p = sub.add_parser("query", help="Query the knowledge graph")
    p.add_argument("query", type=str)
    p.add_argument("--min-confidence", type=float, default=0.0)
    p.add_argument("--max-results", type=int, default=5)
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_query)

    # ingest
    p = sub.add_parser("ingest", help="Ingest a conversation turn")
    p.add_argument("query", type=str)
    p.add_argument("answer", type=str)
    p.add_argument("--agent", type=str, default="")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_ingest)

    # record-failure
    p = sub.add_parser("record-failure", help="Record that an agent gave a wrong answer")
    p.add_argument("query", type=str)
    p.add_argument("answer", type=str)
    p.add_argument("--reason", type=str, default="")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_record_failure)

    # record-success
    p = sub.add_parser("record-success", help="Record that an agent gave a correct answer")
    p.add_argument("query", type=str)
    p.add_argument("answer", type=str)
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_record_success)

    # stats
    p = sub.add_parser("stats", help="Show graph statistics")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_stats)

    # visualize
    p = sub.add_parser("visualize", help="Generate an interactive HTML visualization")
    p.add_argument("output", type=str, nargs="?", default="graph.html")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_visualize)

    # aliases
    p = sub.add_parser("aliases", help="Show entity alias mappings")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_aliases)

    # procedure
    p = sub.add_parser("procedure", help="Ingest or retrieve a skill/procedure")
    p.add_argument("action", type=str, choices=["ingest", "get"], help="ingest a new procedure or get an existing one")
    p.add_argument("name", type=str)
    p.add_argument("--steps", type=str, default="", help="Semicolon-separated steps (for ingest)")
    p.add_argument("--agent", type=str, default="")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_procedure)

    # tools
    p = sub.add_parser("tools", help="Manage the tool registry")
    p.add_argument("action", type=str, choices=["register", "list", "outcome"], help="register a tool, list tools, or record an outcome")
    p.add_argument("name", type=str, nargs="?", default="")
    p.add_argument("--description", type=str, default="")
    p.add_argument("--success", action="store_true", help="Tool call succeeded (for outcome)")
    p.add_argument("--error", type=str, default="")
    p.add_argument("--agent", type=str, default="")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_tools)

    # context
    p = sub.add_parser("context", help="Assemble auto-context for an agent")
    p.add_argument("query", type=str)
    p.add_argument("--session", type=str, default="")
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--min-confidence", type=float, default=0.5)
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_context)

    # hygiene
    p = sub.add_parser("hygiene", help="Memory hygiene sweep (stale / low-confidence knowledge)")
    p.add_argument("--max-age", type=int, default=30)
    p.add_argument("--min-confidence", type=float, default=0.5)
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_hygiene)

    # agent-memory
    p = sub.add_parser("agent-memory", help="Show knowledge owned by an agent")
    p.add_argument("agent", type=str)
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_agent_memory)

    # web demo
    p = sub.add_parser("web", help="Run the browser web demo")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--data-dir", type=str, default=None)
    p.set_defaults(func=cmd_web)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
