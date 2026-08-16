# Upgrading to Enterprise

ContextOn.AI OSS is the open-source version. The enterprise
platform is designed to teach the concept of
confidence-aware, failure-learning knowledge graphs.

## What ContextOn.AI OSS Gives You (Open Source)

| Capability | What It Does |
|------------|--------------|
| Graph building | Stores conversations as entities, facts, and relationships |
| Confidence scoring | Every node/edge has a trust score (0–1) |
| Failure learning | Wrong answers lower confidence; successes restore it |
| Quality badges | 🟢🟡🔴 visual trust indicators |
| Entity resolution | Links aliases like "PM-JAY" ↔ "Pradhan Mantri Jan Arogya Yojana" |
| Suggested questions | Tells you what the graph can answer |
| Visualization | Interactive graph.html |
| MCP server | Works with Claude, Cursor, Codex |

## What It Does NOT Do

The open-source version deliberately does **not** include enterprise
capabilities. There is no multi-tenant isolation, no quality
auditing, no drift detection, no compliance reporting, and no enterprise
connectors.

## Why You Would Upgrade

You will hit these limits as you move from a demo to a team deployment:

1. **Isolation** — everyone can see everything. Teams need scope-bound
   access so each group only sees what it's entitled to.
2. **Quality auditing** — confidence scores are heuristics. Enterprises
   need audited, 5-dimension quality scoring for compliance.
3. **Drift detection** — as knowledge changes, stale or corrupted context
   needs to be detected and flagged automatically.
4. **Compliance reporting** — who accessed what, when, and why — with
   audit trails.
5. **Enterprise connectors** — SAP, ServiceNow, Salesforce integrations.

## The Upgrade Path

> You've seen how confidence scoring and failure learning work. Now
> imagine every answer audited for 5 quality dimensions, with full
> isolation and compliance reporting. That's the enterprise platform.

Visit the GitHub repository for the enterprise platform.
