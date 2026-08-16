#!/usr/bin/env node
/**
 * Automated browser tests for the ContextON_Graph web demo.
 *
 * Drives a real headless Chrome via the Chrome DevTools Protocol using
 * only Node's built-in `fetch` and `WebSocket` - zero npm dependencies.
 * It starts its own isolated web server and Chrome instance, so it never
 * touches the demo running on :8080.
 *
 * Usage:
 *   node tests/web_demo_test.mjs
 *
 * Env overrides:
 *   CHROME_PATH  - path to the Chrome executable (auto-detected otherwise)
 *   WEB_PORT     - port for the test web server (default 8090)
 */

import { spawn, execSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const WEB_PORT = process.env.WEB_PORT || 8090;
const BASE = `http://127.0.0.1:${WEB_PORT}`;

let passed = 0;
let failed = 0;
const failures = [];

function ok(cond, label) {
  if (cond) { passed++; console.log(`  ✅ ${label}`); }
  else { failed++; failures.push(label); console.log(`  ❌ ${label}`); }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, label, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try { if (await fn()) return true; } catch {}
    await sleep(150);
  }
  return false;
}

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  const candidates = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ];
  for (const c of candidates) if (existsSync(c)) return c;
  return "chrome";
}

function killTree(proc) {
  if (!proc || proc.exitCode !== null) return;
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /PID ${proc.pid} /T /F`, { stdio: "ignore" });
    } else {
      proc.kill("SIGKILL");
    }
  } catch {}
}

/* ---------------- tiny CDP client ---------------- */
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); }
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error("ws connect failed")); });
    const c = new CDP(ws);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.id && c.pending.has(msg.id)) {
        const { resolve, reject } = c.pending.get(msg.id);
        c.pending.delete(msg.id);
        msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
      }
    };
    return c;
  }
  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async eval(expression) {
    const r = await this.send("Runtime.evaluate", {
      expression, returnByValue: true, awaitPromise: true,
    });
    if (r.exceptionDetails) {
      throw new Error("page JS error: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    }
    return r.result?.value;
  }
  close() { try { this.ws.close(); } catch {} }
}

/* ---------------- main ---------------- */
const serverDataDir = mkdtempSync(path.join(os.tmpdir(), "cg-web-test-"));
const chromeProfile = mkdtempSync(path.join(os.tmpdir(), "cg-chrome-test-"));
let serverProc = null;
let chromeProc = null;

function startWebServer() {
  serverProc = spawn("python", ["-m", "contexton_graph.cli", "web", "--port", String(WEB_PORT), "--data-dir", serverDataDir], {
    cwd: ROOT, stdio: "ignore", env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  serverProc.on("exit", () => { serverProc = null; });
}

async function waitForServer() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`${BASE}/api/stats`); if (r.ok) return true; } catch {}
    await sleep(300);
  }
  return false;
}

async function startChrome() {
  chromeProc = spawn(findChrome(), [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--user-data-dir=${chromeProfile}`,
    "--remote-debugging-port=0",
    BASE,
  ], { stdio: "ignore" });
  // Chrome writes its debugging port to DevToolsActivePort in the profile dir
  const portFile = path.join(chromeProfile, "DevToolsActivePort");
  for (let i = 0; i < 80; i++) {
    if (existsSync(portFile)) {
      try {
        const [port] = readFileSync(portFile, "utf-8").trim().split("\n");
        const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
        const page = targets.find((t) => t.type === "page" && t.url.startsWith(BASE));
        if (page) return { port, wsUrl: page.webSocketDebuggerUrl };
      } catch {}
    }
    await sleep(250);
  }
  throw new Error("Chrome did not start (DevToolsActivePort not found)");
}

/* ---------------- page helpers (run inside the browser) ---------------- */
const JS = {
  clickButton: (text) => `
    (() => {
      const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes(${JSON.stringify(text)}));
      if (!b) return false; b.click(); return true;
    })()`,
  setValue: (id, v) => `document.getElementById(${JSON.stringify(id)}).value = ${JSON.stringify(v)}`,
  statsNodes: `parseInt((document.querySelectorAll('#stats .stat b')[0]||{}).textContent) || 0`,
  queryResults: `
    (() => [...document.querySelectorAll('#qresults .result')].map(r => {
      const badge = (r.querySelector('.badge')||{}).textContent || '';
      const b = (r.querySelector('b')||{}).textContent || '';
      const conf = parseFloat(b) || 0;
      return { badge, conf, text: r.textContent.slice(0, 60) };
    }))()`,
  hasText: (id, text) => `document.getElementById(${JSON.stringify(id)}).textContent.includes(${JSON.stringify(text)})`,
};

async function main() {
  console.log("🌐 Starting test web server...");
  startWebServer();
  if (!(await waitForServer())) throw new Error("web server did not start");
  console.log(`   server up at ${BASE}`);

  console.log("🟠 Starting headless Chrome...");
  const { wsUrl } = await startChrome();
  console.log("   chrome connected");

  const cdp = await CDP.connect(wsUrl);
  await cdp.send("Runtime.enable");

  console.log("\n📋 Running tests\n");

  // --- 0. Page fully loaded (buttons parsed, stats rendered by JS) ---
  ok(await waitFor(async () => {
    const ready = await cdp.eval(`document.readyState === 'complete'`);
    const stats = await cdp.eval(`document.querySelectorAll('#stats .stat').length`);
    return ready && stats > 0;
  }, "page ready"), "page finished loading and JS rendered");

  // --- 1. Page loads ---
  ok(await cdp.eval(`document.title.includes('ContextON_Graph')`), "page title loads");

  // --- 2. Load demo ---
  ok(await cdp.eval(JS.clickButton("Load demo")), "Load demo button exists");
  ok(await waitFor(async () => (await cdp.eval(JS.statsNodes)) >= 30, "demo loads nodes"),
     "Load demo populates the graph (>=30 nodes)");
  ok(await waitFor(async () => cdp.eval(JS.hasText("aliases", "Know Your Customer")), "aliases render"),
     "entity aliases rendered (KYC ↔ Know Your Customer)");
  ok(await waitFor(async () => cdp.eval(JS.hasText("tools", "risk_scorer")), "tools render"),
     "tool registry rendered (risk_scorer)");
  ok(await waitFor(async () => cdp.eval(JS.hasText("procedures", "Verify suspicious transaction")), "procedures render"),
     "skills rendered (Verify suspicious transaction)");

  // --- 4. Query ---
  await cdp.eval(JS.setValue("qq", "fraud alert"));
  ok(await cdp.eval(JS.clickButton("Query graph")), "Query graph button exists");
  ok(await waitFor(async () => {
    const r = await cdp.eval(JS.queryResults);
    return r.length > 0 && r.some(x => x.text.includes("fraud"));
  }, "query returns results"), "query returns fraud-alert results");
  const before = (await cdp.eval(JS.queryResults))[0];
  ok(before && before.badge === "🟢", `fresh knowledge is 🟢 (conf ${before ? before.conf : "?"})`);

  // --- 5. Auto-context ---
  ok(await cdp.eval(JS.clickButton("Get context")), "Get context button exists");
  ok(await waitFor(async () => cdp.eval(JS.hasText("qresults", "Context pack")), "context pack renders"),
     "auto-context injection renders a context pack");

  // --- 6. Failure learning ---
  await cdp.eval(JS.setValue("fq", "What triggers a fraud alert?"));
  await cdp.eval(JS.setValue("fa", "Fraud alerts trigger only for missing card payments"));
  ok(await cdp.eval(JS.clickButton("Record failure")), "Record failure button exists");
  ok(await waitFor(async () => cdp.eval(JS.hasText("flearn", "Recorded failure")), "failure recorded"),
     "failure recorded");

  // query again - confidence must drop
  await cdp.eval(JS.clickButton("Query graph"));
  ok(await waitFor(async () => {
    const r = await cdp.eval(JS.queryResults);
    return r.length > 0 && r[0].badge === "🔴";
  }, "confidence drops after failure"), "query after failure shows 🔴 lower confidence");

  // --- 7. Success restores ---
  await cdp.eval(JS.setValue("fa", "Unusual transactions above the daily limit or from unrecognized devices trigger a fraud alert"));
  ok(await cdp.eval(JS.clickButton("Record success")), "Record success button exists");
  ok(await waitFor(async () => cdp.eval(JS.hasText("flearn", "confidence increased")), "success recorded"),
     "success recorded");
  await cdp.eval(JS.clickButton("Query graph"));
  ok(await waitFor(async () => {
    const r = await cdp.eval(JS.queryResults);
    return r.length > 0 && r[0].badge === "🟢";
  }, "confidence restored"), "query after success shows 🟢 restored confidence");

  // --- 8. Skills ---
  await cdp.eval(JS.setValue("pn", "Test skill"));
  await cdp.eval(JS.setValue("ps", "Step one; Step two; Step three"));
  ok(await cdp.eval(JS.clickButton("Add skill →")), "Add skill button exists");
  ok(await waitFor(async () => cdp.eval(JS.hasText("procedures", "Test skill")), "skill added"),
     "new skill appears in the skills panel");

  // --- 9. Tools ---
  await cdp.eval(JS.setValue("tn", "test_tool"));
  await cdp.eval(JS.setValue("td", "A test tool"));
  ok(await cdp.eval(JS.clickButton("Register")), "Register tool button exists");
  ok(await waitFor(async () => cdp.eval(JS.hasText("tools", "test_tool")), "tool registered"),
     "new tool appears in the tool registry");

  // --- 10. Hygiene ---
  ok(await cdp.eval(JS.clickButton("Hygiene sweep")), "Hygiene sweep button exists");
  ok(await waitFor(async () => cdp.eval(`document.getElementById('hygiene').querySelector('.result') !== null`), "hygiene runs"),
     "hygiene sweep renders a recommendation");

  // --- 11. Market modal ---
  ok(await cdp.eval(JS.clickButton("Market vs us")), "Market vs us button exists");
  ok(await waitFor(async () => cdp.eval(`document.getElementById('market').style.display === 'flex'`), "market opens"),
     "market comparison modal opens");
  ok(await cdp.eval(`document.getElementById('market').textContent.includes('Graphiti')`), "market table has competitors");
  await cdp.eval(`closeMarket()`);
  ok(await cdp.eval(`document.getElementById('market').style.display === 'none'`), "market modal closes");

  // --- 12. How-it-works flowchart modal ---
  ok(await cdp.eval(JS.clickButton("How it works")), "How it works button exists");
  ok(await waitFor(async () => cdp.eval(`document.getElementById('flowchart').style.display === 'flex'`), "flowchart opens"),
     "How-it-works flowchart modal opens");
  ok(await cdp.eval(`document.getElementById('flowchart').textContent.includes('confidence engine')`), "flowchart shows engine title");
  ok(await cdp.eval(`document.getElementById('flowchart').querySelectorAll('.fstage').length >= 8`), "flowchart has all stages");
  ok(await cdp.eval(`document.getElementById('flowchart').textContent.includes('failure learning')`), "flowchart explains failure loop");
  await cdp.eval(`closeFlow()`);
  ok(await cdp.eval(`document.getElementById('flowchart').style.display === 'none'`), "flowchart modal closes");

  // --- 13. Guided tour ---
  ok(await cdp.eval(JS.clickButton("▶ Guided tour")), "Guided tour button exists");
  ok(await waitFor(async () => cdp.eval(`document.getElementById('tourbox').style.display === 'block'`), "tour opens"),
     "guided tour opens");
  const step1 = await cdp.eval(`document.getElementById('tourstep').textContent`);
  ok(step1.includes("Step 1"), `tour starts at step 1 (got: ${step1})`);
  await cdp.eval(`document.getElementById('tourbtn').click()`);
  ok(await waitFor(async () => {
    const s = await cdp.eval(`document.getElementById('tourstep').textContent`);
    return s.includes("Step 2");
  }, "tour advances"), "tour advances to step 2");
  // Let the tour finish cleanly
  await cdp.eval(`skipTour()`);
  ok(await cdp.eval(`document.getElementById('tourbox').style.display === 'none'`), "tour can be skipped/closed");

  // --- 14. How-it-works calculator ---
  ok(await waitFor(async () => cdp.eval(JS.hasText("cw-result", "Final confidence")), "calculator initializes"),
     "confidence calculator initializes");
  // Drag failures to 2 -> must drop the badge to 🔴
  await cdp.eval(`document.getElementById('cw-failures').value = 2; updateCalc();`);
  ok(await waitFor(async () => {
    const t = await cdp.eval(`document.getElementById('cw-result').textContent`);
    return t.includes("🔴") || t.includes("0.1");
  }, "calculator reacts"), "calculator reacts to failure count slider");

  // --- 15. Reset clears loaded data (graph had >=30 nodes) ---
  ok(await cdp.eval(JS.clickButton("Reset")), "reset button exists");
  ok(await waitFor(async () => (await cdp.eval(JS.statsNodes)) === 0, "reset empties loaded graph"),
     "reset clears loaded data back to 0 nodes");

  cdp.close();
  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
  console.log(`Result: ${passed} passed, ${failed} failed`);
  if (failures.length) {
    console.log("Failures:");
    failures.forEach((f) => console.log("  - " + f));
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error("Fatal:", err.message || err);
  process.exitCode = 1;
}).finally(() => {
  killTree(chromeProc);
  killTree(serverProc);
  try { rmSync(serverDataDir, { recursive: true, force: true }); } catch {}
  try { rmSync(chromeProfile, { recursive: true, force: true }); } catch {}
});
