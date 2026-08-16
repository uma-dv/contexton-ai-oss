"""
Web demo for ContextOn.AI OSS - a dependency-free single-page app.

Shows every capability of the open-source tool in a browser:
memory (ingest/query), skills (procedures), tools, auto-context,
failure learning, entity aliases, hygiene, live graph visualization,
plus a guided walkthrough and a market comparison panel.

Start it with:

    contexton-ai-oss web --port 8080 --data-dir ./data

Then open http://127.0.0.1:8080
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .graph import ContextGraph


SCENARIOS = {
    "support": {"label": "Customer support", "agent": "support-agent"},
    "fraud": {"label": "Banking & fraud alerts", "agent": "fraud-agent"},
    "devops": {"label": "IT/DevOps incidents", "agent": "ops-agent"},
}


def _load_support_scenario(graph: ContextGraph) -> None:
    """Customer support use case."""
    graph.ingest(
        "What is the refund policy?",
        "Full refunds within 30 days of purchase for unused plans",
        agent_id="support-agent", session_id="s1",
    )
    graph.ingest(
        "How long does shipping take?",
        "Standard shipping takes 3 to 5 business days, express shipping takes 1 to 2 days",
        agent_id="support-agent", session_id="s1",
    )
    graph.ingest(
        "How do I track my order?",
        "Go to the order page, enter your order ID, and see the live tracking status",
        agent_id="support-agent", session_id="s1",
    )
    graph.ingest_procedure(
        "Process order refund",
        [
            "Verify the order ID in the order system",
            "Check the 30-day refund policy",
            "Approve the refund in the billing system",
            "Notify the customer by email",
        ],
        agent_id="support-agent",
    )
    graph.ingest_procedure(
        "Handle return request",
        ["Check the return window", "Verify item condition", "Generate return label", "Confirm pickup"],
        agent_id="support-agent",
    )

def _load_fraud_scenario(graph: ContextGraph) -> None:
    """Banking & fraud alerts use case."""
    graph.ingest(
        "What triggers a fraud alert?",
        "Unusual transactions above the daily limit or from unrecognized devices trigger a fraud alert",
        agent_id="fraud-agent", session_id="f1",
    )
    graph.ingest(
        "What is the daily transaction limit?",
        "The default daily transaction limit is 50,000 per account",
        agent_id="fraud-agent", session_id="f1",
    )
    graph.ingest(
        "What is KYC?",
        "Know Your Customer (KYC) verification confirms customer identity before account opening",
        agent_id="fraud-agent", session_id="f1",
    )
    graph.ingest(
        "What does AML compliance require?",
        "Anti-Money Laundering (AML) compliance requires reporting suspicious transactions above the threshold",
        agent_id="fraud-agent", session_id="f2",
    )
    graph.ingest_procedure(
        "Verify suspicious transaction",
        [
            "Freeze the transaction",
            "Check the customer profile against KYC records",
            "Review the AML risk score",
            "Escalate to the fraud team if the score is high",
        ],
        agent_id="fraud-agent",
    )
    graph.ingest_procedure(
        "Escalate fraud case",
        ["Create a case in the risk system", "Attach transaction evidence", "Assign to senior analyst", "Notify compliance"],
        agent_id="fraud-agent",
    )

def _load_devops_scenario(graph: ContextGraph) -> None:
    """IT/DevOps incident operations use case."""
    graph.ingest(
        "What are the incident severity levels?",
        "P1 incidents are critical outages, P2 are major, P3 are minor, and P4 are cosmetic",
        agent_id="ops-agent", session_id="o1",
    )
    graph.ingest(
        "Who is on call for P1 incidents?",
        "The Site Reliability Engineering (SRE) team is on call 24/7 for P1 incidents",
        agent_id="ops-agent", session_id="o1",
    )
    graph.ingest(
        "What is the incident response SLA?",
        "Acknowledge P1 incidents within 5 minutes and restore service within 1 hour",
        agent_id="ops-agent", session_id="o1",
    )
    graph.ingest_procedure(
        "Resolve critical incident",
        [
            "Acknowledge the alert in the monitoring dashboard",
            "Identify the affected service",
            "Roll back the latest deployment if needed",
            "Post an update in the incident channel",
            "Schedule the post-incident review",
        ],
        agent_id="ops-agent",
    )
    graph.ingest_procedure(
        "Run post-incident review",
        ["Collect the timeline of events", "Identify the root cause", "List action items", "Track action items to completion"],
        agent_id="ops-agent",
    )


def _load_tools(graph: ContextGraph, scenario: str) -> None:
    """Register the tools for the requested scenario, with a recorded
    failure on one of them so tool memory is visible."""
    if scenario in ("all", "support"):
        graph.register_tool("order_lookup", "Looks up customer orders", agent_id="support-agent")
        graph.register_tool("shipping_tracker", "Tracks shipments in real time", agent_id="support-agent")
    if scenario in ("all", "fraud"):
        graph.register_tool("transaction_checker", "Checks transaction details and history", agent_id="fraud-agent")
        graph.register_tool("risk_scorer", "Scores transaction risk for fraud detection", agent_id="fraud-agent")
        graph.record_tool_outcome("risk_scorer", success=False, error="Risk model timeout after 30s")
    if scenario in ("all", "devops"):
        graph.register_tool("pagerduty_api", "Triggers and acknowledges incident pages", agent_id="ops-agent")
        graph.register_tool("monitoring_dashboard", "Shows live service health metrics", agent_id="ops-agent")
        graph.record_tool_outcome("monitoring_dashboard", success=False, error="Metrics endpoint unreachable")


def load_demo_dataset(graph: ContextGraph, scenario: str = "all") -> Dict[str, Any]:
    """Load a demo scenario (or all of them) into the graph.

    Args:
        graph: The graph to populate
        scenario: "all", "support", "fraud", or "devops"
    """
    if scenario in ("all", "support"):
        _load_support_scenario(graph)
    if scenario in ("all", "fraud"):
        _load_fraud_scenario(graph)
    if scenario in ("all", "devops"):
        _load_devops_scenario(graph)
    _load_tools(graph, scenario)

    labels = [v["label"] for k, v in SCENARIOS.items() if scenario in ("all", k)]
    return {
        "status": "loaded",
        "scenario": scenario,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "agents": sorted({n.get("agent_id") for n in graph.nodes.values() if n.get("agent_id")}),
        "message": f"Demo loaded: {', '.join(labels)}.",
    }


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ContextOn.AI OSS - Web Demo</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js" defer></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
<style>
  :root { --bg:#0f1420; --panel:#171e2e; --panel2:#1d2740; --text:#e6ecf5;
          --muted:#8fa3c0; --accent:#4f8cff; --green:#22c55e; --yellow:#eab308; --red:#ef4444;
          --highlight:#ffd166; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--text); }
  header { padding:12px 22px; background:var(--panel); border-bottom:1px solid #24304a;
           display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
  header h1 { font-size:17px; margin:0; } header .sub { color:var(--muted); font-size:12px; }
  header .actions { margin-left:auto; display:flex; gap:8px; }
  .wrap { display:flex; gap:16px; padding:16px 22px; flex-wrap:wrap; }
  .col { flex:1 1 420px; min-width:360px; display:flex; flex-direction:column; gap:14px; }
  .card { background:var(--panel); border:1px solid #24304a; border-radius:10px; padding:14px; transition:box-shadow .2s; }
  .card h2 { margin:0 0 10px; font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
  .card.hl { outline:2px solid var(--highlight); outline-offset:2px; box-shadow:0 0 18px rgba(255,209,102,.25); }
  label { display:block; font-size:12px; color:var(--muted); margin:8px 0 3px; }
  input, textarea, select { width:100%; background:var(--panel2); color:var(--text);
    border:1px solid #2c3a5c; border-radius:6px; padding:8px 10px; font-size:13px; }
  textarea { min-height:60px; resize:vertical; }
  button { background:var(--accent); color:#fff; border:0; border-radius:6px; padding:8px 14px;
    font-size:13px; cursor:pointer; margin-top:8px; }
  button.sec { background:#2c3a5c; } button.danger { background:#7f1d1d; } button.gold { background:#b45309; }
  button:hover { filter:brightness(1.15); }
  .row { display:flex; gap:8px; } .row > * { flex:1; }
  .result { background:var(--panel2); border-radius:6px; padding:8px 10px; margin-top:6px;
    font-size:13px; border-left:3px solid var(--muted); }
  .result .meta { color:var(--muted); font-size:11px; }
  pre.out { background:#0b1018; padding:10px; border-radius:6px; font-size:12px; overflow:auto;
    max-height:260px; white-space:pre-wrap; }
  .badge { font-size:14px; }
  #graph { height:340px; border:1px solid #24304a; border-radius:8px; background:#0b1018; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .stat { background:var(--panel2); border-radius:6px; padding:8px; text-align:center; }
  .stat b { display:block; font-size:20px; } .stat span { font-size:11px; color:var(--muted); }
  .tag { display:inline-block; background:#24304a; border-radius:4px; padding:1px 7px; font-size:11px; margin-right:4px; }
  /* Walkthrough overlay */
  #tourbox { position:fixed; top:16px; left:50%; transform:translateX(-50%); width:min(640px,92vw);
    background:var(--panel); border:1px solid var(--highlight); border-radius:12px; padding:16px 18px;
    box-shadow:0 10px 40px rgba(0,0,0,.5); z-index:50; display:none; }
  #tourbox .stepno { color:var(--highlight); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
  #tourbox h3 { margin:4px 0 6px; font-size:15px; }
  #tourbox p { margin:0 0 10px; font-size:13px; color:#c6d4ea; line-height:1.45; }
  #tourbox .tbtns { display:flex; gap:8px; justify-content:flex-end; }
  #tourbox button { margin-top:0; }
  .dim { position:fixed; inset:0; background:rgba(6,9,16,.55); z-index:40; display:none; }
  /* Market comparison modal */
  #market { position:fixed; inset:0; background:rgba(6,9,16,.7); z-index:60; display:none;
    align-items:center; justify-content:center; padding:20px; }
  #market .box { background:var(--panel); border:1px solid #2c3a5c; border-radius:12px;
    max-width:900px; width:100%; max-height:86vh; overflow:auto; padding:20px; }
  #market table { width:100%; border-collapse:collapse; font-size:12px; margin-top:10px; }
  #market th, #market td { border:1px solid #24304a; padding:6px 8px; text-align:left; }
  #market th { background:var(--panel2); color:var(--muted); }
  #market td.us { background:rgba(79,140,255,.12); }
  #market .close { float:right; }
  .note { font-size:12px; color:var(--muted); margin-top:6px; }
  .ok { color:var(--green); } .no { color:var(--red); }
  /* Animated how-it-works flowchart */
  #flowchart { position:fixed; inset:0; background:rgba(6,9,16,.72); z-index:70; display:none;
    align-items:center; justify-content:center; padding:20px; }
  #flowchart .box { background:var(--panel); border:1px solid #2c3a5c; border-radius:12px;
    max-width:980px; width:100%; max-height:90vh; overflow:auto; padding:20px; }
  .flow { display:flex; align-items:stretch; flex-wrap:wrap; margin:18px 0 8px; }
  .fstage { flex:1 1 118px; min-width:108px; background:var(--panel2); border:1px solid #2c3a5c;
    border-radius:8px; padding:10px 8px; text-align:center; font-size:12px; opacity:.45;
    animation: stagePulse 14s infinite; }
  .fstage .ico { font-size:20px; display:block; margin-bottom:4px; }
  .fstage b { display:block; font-size:12px; margin-bottom:2px; }
  .fstage span { color:var(--muted); font-size:10.5px; line-height:1.3; display:block; }
  .fconn { flex:0 0 30px; display:flex; align-items:center; justify-content:center;
    color:var(--accent); font-size:13px; animation: connMove .8s infinite; }
  @keyframes stagePulse { 0%,6% { opacity:.45; box-shadow:none; }
    10%,30% { opacity:1; box-shadow:0 0 14px rgba(79,140,255,.55); }
    34%,100% { opacity:.45; box-shadow:none; } }
  @keyframes connMove { 0% { transform:translateX(-2px); opacity:.35; }
    100% { transform:translateX(2px); opacity:1; } }
  .floop .fl { display:block; animation: flShow 14s infinite; font-size:10.5px; margin-top:2px; }
  .floop .fs { display:block; animation: fsShow 14s infinite; font-size:10.5px; margin-top:2px; }
  @keyframes flShow { 0%,42% { opacity:0; } 46%,60% { opacity:1; color:var(--red); }
    64%,100% { opacity:0; } }
  @keyframes fsShow { 0%,64% { opacity:0; } 68%,82% { opacity:1; color:var(--green); }
    86%,100% { opacity:0; } }
  .flegend { margin-top:12px; font-size:12px; color:var(--muted); }
</style>
</head>
<body>
<div class="dim" id="dim"></div>
<div id="tourbox">
  <div class="stepno" id="tourstep">Step 1 / 13</div>
  <h3 id="tourtitle">Welcome</h3>
  <p id="tourtext"></p>
  <div class="tbtns">
    <button class="sec" onclick="skipTour()">Skip</button>
    <button id="tourbtn" onclick="tourNext()">Next →</button>
  </div>
</div>
<div id="market">
  <div class="box">
    <button class="sec close" onclick="closeMarket()">Close ✕</button>
    <h2>ContextOn.AI OSS vs the market</h2>
    <p class="note">What exists today vs what this open-source tool brings. Novel features are marked <b style="color:var(--accent)">ContextOn.AI OSS</b>.</p>
    <table>
      <tr><th>Capability</th><th>Graphify</th><th>Graphiti (Zep)</th><th>Mem0</th><th>MS GraphRAG</th><th class="us">ContextOn.AI OSS</th></tr>
      <tr><td>Primary use</td><td>Code graphs</td><td>Temporal agent memory</td><td>Vector memory</td><td>Graph RAG</td><td class="us">Agent context graphs</td></tr>
      <tr><td>Confidence scoring</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓ 0–1 per node/edge</td></tr>
      <tr><td>Failure learning</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓ record_failure/success</td></tr>
      <tr><td>Quality badges 🟢🟡🔴</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓</td></tr>
      <tr><td>Entity alias resolution</td><td class="no">⚠</td><td class="no">⚠</td><td class="no">✕</td><td class="no">⚠</td><td class="us ok">✓ KYC ↔ Know Your Customer</td></tr>
      <tr><td>Skills / procedures</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓ reusable "how to" steps</td></tr>
      <tr><td>Tool registry memory</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓ tools with failure tracking</td></tr>
      <tr><td>Auto-context injection</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">⚠</td><td class="us ok">✓ get_context()</td></tr>
      <tr><td>Memory hygiene</td><td class="no">✕</td><td class="no">⚠</td><td class="no">✕</td><td class="no">✕</td><td class="us ok">✓ decay sweeps</td></tr>
      <tr><td>Deterministic retrieval</td><td class="no">⚠ hybrid</td><td class="no">⚠ hybrid</td><td class="no">✕ embeddings</td><td class="no">⚠ hybrid</td><td class="us ok">✓ no embeddings needed</td></tr>
      <tr><td>Isolation / quality auditing / compliance</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="no">✕</td><td class="us">✕ (enterprise tier)</td></tr>
      <tr><td>MCP server</td><td class="no">⚠</td><td class="no">⚠</td><td class="no">⚠</td><td class="no">⚠</td><td class="us ok">✓ built-in</td></tr>
      <tr><td>Core dependencies</td><td>many</td><td>many</td><td>many</td><td>heavy</td><td class="us ok">0</td></tr>
    </table>
    <p class="note"><b>What this brings that no other open-source tool has:</b> confidence scoring + failure learning + quality badges combined, with deterministic (embedding-free) retrieval, skills, tool memory, auto-context, and memory hygiene — all behind a built-in MCP server and this web demo. Enterprise isolation, quality auditing, drift detection, and compliance live in the enterprise tier.</p>
  </div>
</div>
<div id="flowchart">
  <div class="box">
    <button class="sec close" onclick="closeFlow()">Close ✕</button>
    <h2>How it works — the confidence engine</h2>
    <p class="note">Every piece of knowledge carries a <b>confidence score 0–1</b> with a quality badge, computed by a simple explainable formula. The animation below shows the full lifecycle: knowledge enters → gets scored → the agent uses it → failures and successes feed back into the score.</p>
    <div class="flow">
      <div class="fstage"><span class="ico">📥</span><b>Ingest</b><span>question + answer stored as nodes and edges</span></div>
      <div class="fconn">→</div>
      <div class="fstage"><span class="ico">🧮</span><b>Score</b><span>base × decay × failure_penalty = confidence 0–1</span></div>
      <div class="fconn">→</div>
      <div class="fstage"><span class="ico">🔎</span><b>Retrieve</b><span>deterministic keyword match, no embeddings</span></div>
      <div class="fconn">→</div>
      <div class="fstage"><span class="ico">🤖</span><b>Agent answers</b><span>knowledge injected with 🟢🟡🔴 badge</span></div>
      <div class="fconn">→</div>
      <div class="fstage"><span class="ico">✅</span><b>Verify</b><span>was the answer right or wrong?</span></div>
    </div>
    <div class="flow floop">
      <div class="fstage"><span class="ico">❌</span><b>Failure</b><span>wrong answer → failure_count +1 → confidence halves → 🔴, agent avoids it next time</span>
        <span class="fl">failure learning — unique to ContextOn.AI OSS</span></div>
      <div class="fconn">↩</div>
      <div class="fstage"><span class="ico">✅</span><b>Success</b><span>right answer → failure undone → mentions +1 → confidence restored → 🟢</span>
        <span class="fs">the feedback loop no other tool has</span></div>
      <div class="fconn">↩</div>
      <div class="fstage"><span class="ico">🔄</span><b>Loop</b><span>back to Retrieve — the graph keeps learning</span></div>
    </div>
    <div class="flegend"><b>Formula:</b> confidence = base × decay × failure_penalty · base = max(stored, mentions/5) capped at 1.0 · decay = 0.95^days_since_verified · failure = 0.5^failure_count · badges: 🟢 ≥ 0.8 · 🟡 0.5–0.8 · 🔴 &lt; 0.5</div>
    <p class="note">Try the live calculator above — move the sliders and watch the score react to age and failures in real time.</p>
  </div>
</div>

<header>
  <h1>🧠 ContextOn.AI OSS</h1>
  <span class="sub">Open-source agent memory · confidence · failure learning · skills · tools</span>
  <div class="actions">
    <button class="gold" onclick="startTour()">▶ Guided tour</button>
    <button class="sec" onclick="openMarket()">Market vs us</button>
    <button class="sec" onclick="openFlow()">How it works</button>
    <select id="scenario" title="Choose a demo use case" style="width:auto;margin-top:8px">
      <option value="all">All use cases</option>
      <option value="support">Customer support</option>
      <option value="fraud">Banking &amp; fraud alerts</option>
      <option value="devops">IT/DevOps incidents</option>
    </select>
    <button onclick="loadDemo()">Load demo</button>
    <button class="danger" onclick="reset()">Reset</button>
  </div>
</header>

<div class="wrap">
  <div class="col">
    <div class="card" id="c-how">
      <h2>How it works</h2>
      <p class="note">Every piece of knowledge carries a <b>confidence score 0–1</b> with a quality badge. The score comes from a simple, explainable formula:</p>
      <pre class="out" style="max-height:none">confidence = base × decay × failure_penalty

base    = max(stored, mentions / 5)   capped at 1.0
decay   = 0.95 ^ days_since_verified
failure = 0.5 ^ failure_count

badges: 🟢 ≥ 0.8 · 🟡 0.5–0.8 · 🔴 &lt; 0.5</pre>
      <p class="note"><b>Try it live</b> — move the sliders, the engine computes the real score:</p>
      <label>Stored confidence (trust at ingest)</label>
      <input type="range" id="cw-stored" min="0" max="100" value="80" oninput="updateCalc()"> <span id="cv-stored">0.8</span>
      <label>Mentions (times verified)</label>
      <input type="range" id="cw-mentions" min="1" max="10" value="1" oninput="updateCalc()"> <span id="cv-mentions">1</span>
      <label>Days since last verified (decay)</label>
      <input type="range" id="cw-days" min="0" max="90" value="0" oninput="updateCalc()"> <span id="cv-days">0</span>
      <label>Failure count (penalty)</label>
      <input type="range" id="cw-failures" min="0" max="5" value="0" oninput="updateCalc()"> <span id="cv-failures">0</span>
      <div id="cw-result" style="margin-top:10px"><div class="result">…</div></div>
      <p class="note"><b>Failure learning loop:</b> agent gives a wrong answer → failure_count +1 and confidence halves → 🔴. Agent gives the correct answer → failure undone, confidence restored → 🟢. That feedback loop is what no other tool has.</p>
    </div>

    <div class="card" id="c-ingest">
      <h2>Ingest knowledge</h2>
      <label>Question</label><input id="inq" placeholder="What triggers a fraud alert?">
      <label>Answer</label><textarea id="ina" placeholder="Unusual transactions above the daily limit trigger a fraud alert..."></textarea>
      <div class="row">
        <div><label>Agent</label><input id="inagent" placeholder="fraud-agent"></div>
        <div><label>Session</label><input id="insession" placeholder="sess-1 (optional)"></div>
      </div>
      <button onclick="api('ingest',{query:V('inq'),answer:V('ina'),agent_id:V('inagent'),session_id:V('insession')})">Ingest →</button>
    </div>

    <div class="card" id="c-proc">
      <h2>Skills (procedures)</h2>
      <label>Procedure name</label><input id="pn" placeholder="Reset password">
      <label>Steps (separate with ;)</label><textarea id="ps" placeholder="Open settings; Go to security; Click reset; Confirm email"></textarea>
      <button onclick="api('procedure',{name:V('pn'),steps:V('ps').split(';').map(s=>s.trim()).filter(Boolean),agent_id:V('inagent')})">Add skill →</button>
      <div id="procedures"></div>
    </div>

    <div class="card" id="c-tools">
      <h2>Tools</h2>
      <div class="row">
        <div><label>Tool name</label><input id="tn" placeholder="send_email"></div>
        <div><label>Description</label><input id="td" placeholder="Sends an email"></div>
      </div>
      <div class="row">
        <button onclick="api('tools/register',{name:V('tn'),description:V('td')})">Register</button>
        <button class="sec" onclick="loadTools()">Refresh</button>
      </div>
      <div id="tools"></div>
    </div>
  </div>

  <div class="col">
    <div class="card" id="c-query">
      <h2>Query &amp; auto-context</h2>
      <label>Question</label><input id="qq" placeholder="fraud alert">
      <div class="row">
        <button onclick="runQuery()">Query graph</button>
        <button class="sec" onclick="runContext()">Get context (injection)</button>
      </div>
      <div id="qresults"></div>
    </div>

    <div class="card" id="c-flearn">
      <h2>Failure learning <span class="tag">key feature</span></h2>
      <label>Agent gave a WRONG answer</label>
      <div class="row">
        <input id="fq" placeholder="Question">
        <input id="fa" placeholder="Wrong answer">
      </div>
      <div class="row">
        <button onclick="recordFailure()">Record failure</button>
        <button class="sec" onclick="recordSuccess()">Record success</button>
      </div>
      <div id="flearn"></div>
      <p class="note">Record a failure → confidence drops to 🔴. Record the correct answer → it recovers to 🟢. No other tool learns from mistakes.</p>
    </div>

    <div class="card" id="c-graph">
      <h2>Graph</h2>
      <div id="graph"></div>
      <button class="sec" onclick="loadGraph()">Refresh graph</button>
    </div>
  </div>

  <div class="col">
    <div class="card" id="c-stats">
      <h2>Stats &amp; health</h2>
      <div class="grid2" id="stats"></div>
      <div class="row">
        <button class="sec" onclick="loadStats()">Refresh stats</button>
        <button class="sec" onclick="hygiene()">Hygiene sweep</button>
      </div>
      <div id="hygiene"></div>
    </div>
    <div class="card" id="c-aliases">
      <h2>Entity aliases</h2>
      <div id="aliases"></div>
    </div>
    <div class="card" id="c-out">
      <h2>Live output</h2>
      <pre class="out" id="out">Ready. Click "Load demo" or "Guided tour" to get started.</pre>
    </div>
  </div>
</div>

<script>
function V(id){return document.getElementById(id).value;}
function setV(id,v){document.getElementById(id).value=v;}
function log(t){document.getElementById('out').textContent = typeof t==='string'?t:JSON.stringify(t,null,2);}
function badge(b){return '<span class="badge">'+b+'</span>';}
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}

async function api(path, body){
  const r = await fetch('/api/'+path, {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body||{})});
  const data = await r.json();
  log(data);
  refreshAll();
  return data;
}
function refreshAll(){ loadStats(); loadGraph(); loadAliases(); loadTools(); loadProcedures(); }

async function runQuery(){
  const data = await api('query',{query:V('qq'),agent_id:V('inagent')});
  const el = document.getElementById('qresults');
  if(!data.results || !data.results.length){ el.innerHTML='<div class="result">No results.</div>'; return; }
  el.innerHTML = data.results.map(r=>
    '<div class="result">'+badge(r.badge)+' <b>'+r.confidence+'</b> · <span class="tag">'+r.node_type+'</span>'+
    '<div>'+esc(r.content)+'</div></div>').join('');
}
async function runContext(){
  const data = await api('context',{query:V('qq'),session_id:V('insession')});
  document.getElementById('qresults').innerHTML =
    '<div class="result"><b>Context pack ('+data.item_count+' items)</b><pre class="out">'+esc(data.context_text||'None')+'</pre></div>';
}
async function recordFailure(){
  const data = await api('failure',{query:V('fq'),answer:V('fa'),reason:'incorrect'});
  document.getElementById('flearn').innerHTML =
    '<div class="result">'+badge('🔴')+' '+esc(data.message)+'<div class="meta">affected edges: '+data.affected_edges+' · nodes: '+data.affected_nodes+'</div></div>';
  return data;
}
async function recordSuccess(){
  const data = await api('success',{query:V('fq'),answer:V('fa')});
  document.getElementById('flearn').innerHTML =
    '<div class="result">'+badge('🟢')+' '+esc(data.message)+'</div>';
  return data;
}
async function loadStats(){
  const r = await fetch('/api/stats'); const s = await r.json();
  document.getElementById('stats').innerHTML =
    stat(s.node_count,'Nodes')+stat(s.edge_count,'Edges')+stat(Math.round(s.avg_confidence*100)+'%','Avg confidence')+
    stat(s.communities,'Communities');
}
function stat(v,l){return '<div class="stat"><b>'+v+'</b><span>'+l+'</span></div>';}

let network=null;
async function loadGraph(){
  const container = document.getElementById('graph');
  // vis.js loads async (deferred) - retry until it is available so the
  // rest of the page never blocks on the CDN
  if(typeof vis === 'undefined'){
    container.innerHTML='<div style="padding:20px;color:#8fa3c0">Loading graph library…</div>';
    setTimeout(loadGraph, 1000);
    return;
  }
  const r = await fetch('/api/graph'); const g = await r.json();
  if(!g.nodes.length){ container.innerHTML='<div style="padding:20px;color:#8fa3c0">Empty graph - ingest something.</div>'; return; }
  const nodes = new vis.DataSet(g.nodes.map(n=>({id:n.id,label:n.label,color:{background:n.color,border:n.color},title:n.content})));
  const edges = new vis.DataSet(g.edges.map(e=>({from:e.source,to:e.target,arrows:'to'})));
  if(network){ network.setData({nodes,edges}); }
  else { network = new vis.Network(container,{nodes,edges},{physics:{enabled:true},nodes:{shape:'dot',size:18,font:{size:11,color:'#e6ecf5'}}}); }
}
async function loadAliases(){
  const r = await fetch('/api/aliases'); const a = await r.json();
  const el = document.getElementById('aliases');
  const list = a.aliases||{};
  if(!Object.keys(list).length){ el.innerHTML='<div class="result">No aliases yet.</div>'; return; }
  el.innerHTML = Object.entries(list).map(([k,v])=>
    '<div class="result">'+badge('🔗')+' <b>'+esc(k)+'</b> = '+v.map(esc).join(', ')+'</div>').join('');
}
async function loadTools(){
  const r = await fetch('/api/tools'); const t = await r.json();
  document.getElementById('tools').innerHTML = (t.tools||[]).map(x=>
    '<div class="result">'+badge(x.badge)+' <b>'+esc(x.name)+'</b> · '+x.confidence+' · <span class="meta">failures '+x.failure_count+'</span></div>').join('')||'<div class="result">None.</div>';
}
async function loadProcedures(){
  const r = await fetch('/api/procedures'); const p = await r.json();
  document.getElementById('procedures').innerHTML = (p.procedures||[]).map(x=>
    '<div class="result">'+badge(x.badge)+' <b>'+esc(x.name)+'</b> · <span class="meta">'+x.steps.length+' steps</span></div>').join('')||'<div class="result">None.</div>';
}
async function hygiene(){
  const r = await fetch('/api/hygiene'); const h = await r.json();
  document.getElementById('hygiene').innerHTML =
    '<div class="result">'+badge('🧹')+' '+esc(h.recommendation)+'<div class="meta">stale: '+h.stale_count+' · low-confidence: '+h.low_confidence_count+'</div></div>';
  return h;
}

const SCENARIO_FILLS = {
  all:    { inq:'What triggers a fraud alert?', ina:'Unusual transactions above the daily limit or from unrecognized devices trigger a fraud alert', inagent:'fraud-agent', insession:'f1', qq:'fraud alert', pn:'Verify suspicious transaction', ps:'Freeze the transaction; Check the customer profile against KYC records; Review the AML risk score; Escalate to the fraud team if the score is high', tn:'risk_scorer', td:'Scores transaction risk for fraud detection' },
  fraud:  { inq:'What triggers a fraud alert?', ina:'Unusual transactions above the daily limit or from unrecognized devices trigger a fraud alert', inagent:'fraud-agent', insession:'f1', qq:'fraud alert', pn:'Verify suspicious transaction', ps:'Freeze the transaction; Check the customer profile against KYC records; Review the AML risk score; Escalate to the fraud team if the score is high', tn:'risk_scorer', td:'Scores transaction risk for fraud detection' },
  support:{ inq:'What is the refund policy?', ina:'Full refunds within 30 days of purchase for unused plans', inagent:'support-agent', insession:'s1', qq:'refund policy', pn:'Process order refund', ps:'Verify the order ID; Check the 30-day refund policy; Approve in billing; Notify the customer', tn:'order_lookup', td:'Looks up customer orders' },
  devops: { inq:'What are the incident severity levels?', ina:'P1 incidents are critical outages, P2 are major, P3 are minor, and P4 are cosmetic', inagent:'ops-agent', insession:'o1', qq:'incident severity', pn:'Resolve critical incident', ps:'Acknowledge the alert; Identify the affected service; Roll back the latest deployment; Post an update; Schedule the review', tn:'monitoring_dashboard', td:'Shows live service health metrics' },
};

async function loadDemo(){
  const scenario = document.getElementById('scenario').value;
  const data = await api('demo', {scenario});
  // Fill the forms so users see exactly what was loaded and can tweak it
  const f = SCENARIO_FILLS[scenario] || SCENARIO_FILLS.all;
  setV('inq', f.inq); setV('ina', f.ina); setV('inagent', f.inagent); setV('insession', f.insession);
  setV('qq', f.qq); setV('pn', f.pn); setV('ps', f.ps); setV('tn', f.tn); setV('td', f.td);
  log(data);
  return data;
}
function reset(){
  fetch('/api/reset',{method:'POST'}).then(()=>{ log('Graph reset.'); refreshAll(); });
}

/* ---------------- Guided walkthrough ---------------- */
const TOUR = [
  {card:'c-ingest', title:'Welcome 👋', text:'This is ContextOn.AI OSS: a knowledge graph for AI agents that scores confidence, learns from failures, stores skills and tools, and injects context. Click Next to take the 60-second tour — every step runs for real on live data.'},
  {card:'c-ingest', title:'1. Load the demo dataset', text:'We will load a realistic multi-agent dataset across three use cases: customer support (refunds, shipping), banking & fraud alerts (KYC, AML, transaction checks), and IT/DevOps incident ops (SRE, P1 incidents). Click "Load demo".', run:()=>loadDemo()},
  {card:'c-stats', title:'2. Stats & health', text:'The graph now has nodes (facts, entities, conversations, procedures, tools) and edges. The stats panel shows counts, average confidence, and communities. Watch the average confidence move as we go.'},
  {card:'c-query', title:'3. Query with confidence', text:'Ask the graph "fraud alert". Results are ranked by relevance AND confidence, with 🟢🟡🔴 badges. Notice "KYC" and "Know Your Customer" are one entity — aliases were resolved automatically.', run:()=>runQuery()},
  {card:'c-query', title:'4. Auto-context injection', text:'Now click "Get context". This is the context layer agents consume: a confident, badge-annotated pack for the current session, packed to a token budget. No embeddings needed — fully deterministic.', run:()=>runContext()},
  {card:'c-flearn', title:'5. Failure learning (the key feature)', text:'This is what no other tool does. Pretend the agent gave a WRONG answer about fraud alerts. Record it. Then query again — confidence drops to 🔴 and the graph remembers not to trust that path.', run:()=>{setV('fq','What triggers a fraud alert?');setV('fa','Fraud alerts trigger only for missing card payments');return recordFailure();}},
  {card:'c-query', title:'6. See the damage', text:'Run the query again — the same knowledge now returns 🔴 with much lower confidence. The graph learned from the failure.', run:()=>runQuery()},
  {card:'c-flearn', title:'7. Record the correct answer', text:'Now the agent gives the RIGHT answer. Record it as a success — this verifies the knowledge and restores confidence.', run:()=>{setV('fa','Unusual transactions above the daily limit or from unrecognized devices trigger a fraud alert');return recordSuccess();}},
  {card:'c-query', title:'8. Confidence restored', text:'Query once more: 🟢 high confidence again. Failures are remembered, successes restore trust. That feedback loop is the core differentiator.', run:()=>runQuery()},
  {card:'c-proc', title:'9. Skills (procedures)', text:'Agents stored "how to" skills across domains — refund processing, fraud verification, and incident runbooks — each with ordered steps and a confidence badge. Agents retrieve skills like any knowledge.', run:()=>loadProcedures()},
  {card:'c-tools', title:'10. Tool registry memory', text:'Tools are registered with descriptions. Note risk_scorer and monitoring_dashboard have failures recorded — their confidence is lower. The graph tracks which tools work and which ones fail.', run:()=>loadTools()},
  {card:'c-aliases', title:'11. Entity aliases', text:'"KYC" and "Know Your Customer", "AML" and "Anti-Money Laundering", "SRE" and "Site Reliability Engineering" each resolved to one canonical entity. Cleaner graphs, better retrieval.'},
  {card:'c-stats', title:'12. Memory hygiene', text:'Run the hygiene sweep — it flags stale or low-confidence knowledge that needs re-verification. Run it nightly to keep the graph trustworthy.', run:()=>hygiene()},
  {card:'c-graph', title:'13. Live graph', text:'The graph view colors nodes by confidence: 🟢 high, 🟡 medium, 🔴 low. You just watched some of these flip from 🟢 → 🔴 → 🟢 during the failure demo.', run:()=>loadGraph()},
  {card:'c-out', title:'Done 🎉', text:'That is the whole open-source tool. Now open "Market vs us" to see how it differs from Graphify, Graphiti, Mem0, and GraphRAG — and what the enterprise tier adds (isolation, quality auditing, drift detection, compliance).', run:()=>openMarket()},
];

let tourIdx = 0;
let tourActive = false;
function startTour(){
  tourIdx = 0; tourActive = true;
  document.getElementById('dim').style.display='block';
  document.getElementById('tourbox').style.display='block';
  showTourStep();
}
function showTourStep(){
  const s = TOUR[tourIdx];
  document.getElementById('tourstep').textContent = 'Step '+(tourIdx+1)+' / '+TOUR.length;
  document.getElementById('tourtitle').textContent = s.title;
  document.getElementById('tourtext').textContent = s.text;
  document.getElementById('tourbtn').textContent = (tourIdx===TOUR.length-1) ? 'Finish' : 'Next →';
  // highlight the target card
  document.querySelectorAll('.card.hl').forEach(c=>c.classList.remove('hl'));
  if(s.card && document.getElementById(s.card)) document.getElementById(s.card).classList.add('hl');
  // auto-run the step action (fills fields + executes)
  if(s.run){ try{ s.run(); }catch(e){} }
}
function tourNext(){
  tourIdx++;
  if(tourIdx >= TOUR.length){ skipTour(); return; }
  showTourStep();
}
function skipTour(){
  tourActive=false;
  document.getElementById('dim').style.display='none';
  document.getElementById('tourbox').style.display='none';
  document.querySelectorAll('.card.hl').forEach(c=>c.classList.remove('hl'));
}
function openMarket(){ document.getElementById('market').style.display='flex'; }
function closeMarket(){ document.getElementById('market').style.display='none'; }
function openFlow(){ document.getElementById('flowchart').style.display='flex'; }
function closeFlow(){ document.getElementById('flowchart').style.display='none'; }

/* How-it-works confidence calculator (server-backed, debounced) */
let calcTimer=null;
async function updateCalc(){
  const stored=+V('cw-stored')/100, mentions=+V('cw-mentions'), days=+V('cw-days'), failures=+V('cw-failures');
  setV('cv-stored',stored.toFixed(1)); setV('cv-mentions',mentions); setV('cv-days',days); setV('cv-failures',failures);
  clearTimeout(calcTimer);
  calcTimer=setTimeout(async()=>{
    const r=await fetch('/api/breakdown',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({stored,mentions,days,failures})});
    const b=await r.json();
    document.getElementById('cw-result').innerHTML =
      '<div class="result">'+badge(b.badge)+' Final confidence: <b>'+b.final_confidence+'</b>'+
      '<div class="meta">base '+b.base_score+' × decay '+b.decay_factor+' × failure penalty '+b.failure_penalty+
      '  (mentions '+b.mentions+', '+b.days_since_verified+'d old, '+b.failure_count+' failures)</div></div>';
  },120);
}

refreshAll(); updateCalc();
</script>
</body>
</html>
"""


def _fresh_graph(data_dir: Optional[str]) -> ContextGraph:
    """Return a new empty graph, removing any persisted data first."""
    if data_dir:
        try:
            os.remove(os.path.join(data_dir, "graph.json"))
        except OSError:
            pass
    return ContextGraph(data_dir=data_dir)


class WebDemoHandler(BaseHTTPRequestHandler):
    graph: ContextGraph = ContextGraph()
    lock = threading.Lock()

    def log_message(self, fmt, *args):  # quieter logs
        pass

    def _send(self, status: int, body: Any, content_type: str = "application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False, indent=2)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        with self.lock:
            if path == "/":
                self._send(200, INDEX_HTML, "text/html; charset=utf-8")
            elif path == "/api/stats":
                self._send(200, self.graph.get_stats())
            elif path == "/api/aliases":
                self._send(200, {"aliases": self.graph.get_aliases()})
            elif path == "/api/tools":
                self._send(200, {"tools": self.graph.list_tools()})
            elif path == "/api/procedures":
                procs = []
                for nid, node in self.graph.nodes.items():
                    if node.get("type") == "procedure":
                        proc = self.graph.get_procedure(node.get("content", ""))
                        if proc:
                            procs.append(proc)
                self._send(200, {"procedures": procs})
            elif path == "/api/graph":
                nodes, edges = [], []
                for nid, node in self.graph.nodes.items():
                    conf = self.graph.confidence_engine.node_confidence(node)
                    color = "#22c55e" if conf >= 0.8 else ("#eab308" if conf >= 0.5 else "#ef4444")
                    nodes.append({
                        "id": nid,
                        "label": node.get("content", "")[:24],
                        "content": node.get("content", "")[:120],
                        "type": node.get("type"),
                        "color": color,
                    })
                for edge in self.graph.edges:
                    edges.append({"source": edge["source"], "target": edge["target"]})
                self._send(200, {"nodes": nodes, "edges": edges})
            elif path == "/api/hygiene":
                self._send(200, self.graph.hygiene_sweep())
            else:
                self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json()
        with self.lock:
            if path == "/api/ingest":
                self._send(200, self.graph.ingest(
                    query=body.get("query", ""),
                    answer=body.get("answer", ""),
                    agent_id=body.get("agent_id", ""),
                    session_id=body.get("session_id", ""),
                ))
            elif path == "/api/procedure":
                self._send(200, self.graph.ingest_procedure(
                    name=body.get("name", ""),
                    steps=body.get("steps", []),
                    agent_id=body.get("agent_id", ""),
                ))
            elif path == "/api/tools/register":
                self._send(200, {"tool_id": self.graph.register_tool(
                    name=body.get("name", ""),
                    description=body.get("description", ""),
                    agent_id=body.get("agent_id", ""),
                )})
            elif path == "/api/tools/outcome":
                self._send(200, self.graph.record_tool_outcome(
                    name=body.get("name", ""),
                    success=bool(body.get("success")),
                    error=body.get("error", ""),
                ))
            elif path == "/api/query":
                results = self.graph.query(
                    body.get("query", ""),
                    agent_id=body.get("agent_id", ""),
                )
                self._send(200, {"results": [
                    {
                        "content": r["node"].get("content", ""),
                        "node_type": r["node"].get("type"),
                        "confidence": round(r["confidence"], 3),
                        "badge": r["badge"],
                    } for r in results
                ]})
            elif path == "/api/context":
                self._send(200, self.graph.get_context(
                    query=body.get("query", ""),
                    session_id=body.get("session_id", ""),
                ))
            elif path == "/api/failure":
                self._send(200, self.graph.record_failure(
                    query=body.get("query", ""),
                    answer=body.get("answer", ""),
                    reason=body.get("reason", ""),
                ))
            elif path == "/api/success":
                self._send(200, self.graph.record_success(
                    query=body.get("query", ""),
                    answer=body.get("answer", ""),
                ))
            elif path == "/api/demo":
                # Replace any existing data (clear first), so loading a
                # scenario always presents a clean, fresh use case
                scenario = body.get("scenario", "all")
                if scenario not in SCENARIOS and scenario != "all":
                    scenario = "all"
                type(self).graph = _fresh_graph(self.graph.data_dir)
                self._send(200, load_demo_dataset(self.graph, scenario))
            elif path == "/api/breakdown":
                # Authoritative confidence breakdown from the real engine,
                # used by the "How it works" calculator in the UI
                from datetime import datetime, timezone, timedelta

                stored = float(body.get("stored", 0.8))
                mentions = int(body.get("mentions", 1))
                days = int(body.get("days", 0))
                failures = int(body.get("failures", 0))
                fake_node = {
                    "confidence": stored,
                    "mentions": mentions,
                    "last_verified": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
                    "failure_count": failures,
                }
                breakdown = self.graph.confidence_engine.get_confidence_breakdown(fake_node)
                breakdown["final_confidence"] = round(
                    self.graph.confidence_engine.node_confidence(fake_node), 3)
                self._send(200, breakdown)
            elif path == "/api/reset":
                # Clear persisted data and rebuild. Must update the CLASS
                # attribute - each request gets a fresh handler instance.
                type(self).graph = _fresh_graph(self.graph.data_dir)
                self._send(200, {"status": "reset"})
            else:
                self._send(404, {"error": "not found"})


def run_web(host: str = "127.0.0.1", port: int = 8080, data_dir: Optional[str] = None) -> None:
    """Run the web demo server."""
    WebDemoHandler.graph = ContextGraph(data_dir=data_dir)
    server = ThreadingHTTPServer((host, port), WebDemoHandler)
    print(f"ContextOn.AI OSS web demo: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ContextOn.AI OSS web demo")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--data-dir", type=str, default=None)
    args = parser.parse_args()
    run_web(args.host, args.port, args.data_dir)
