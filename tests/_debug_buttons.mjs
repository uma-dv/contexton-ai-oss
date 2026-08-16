import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const WEB_PORT = 8092;
const BASE = `http://127.0.0.1:${WEB_PORT}`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const dataDir = mkdtempSync(path.join(os.tmpdir(), "cg-dbg-"));
const profile = mkdtempSync(path.join(os.tmpdir(), "cg-chrome-dbg-"));

const server = spawn("python", ["-m", "contexton_graph.cli", "web", "--port", String(WEB_PORT), "--data-dir", dataDir], { cwd: ROOT, stdio: "ignore", env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
for (let i = 0; i < 60; i++) { try { if ((await fetch(`${BASE}/api/stats`)).ok) break; } catch {} await sleep(300); }

const chromePath = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const chrome = spawn(chromePath, ["--headless=new", "--disable-gpu", "--no-first-run", `--user-data-dir=${profile}`, "--remote-debugging-port=0", BASE], { stdio: "ignore" });
let wsUrl = null;
for (let i = 0; i < 80; i++) {
  const pf = path.join(profile, "DevToolsActivePort");
  if (existsSync(pf)) {
    try {
      const [port] = readFileSync(pf, "utf-8").trim().split("\n");
      const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = targets.find((t) => t.type === "page" && t.url.startsWith(BASE));
      if (page) { wsUrl = page.webSocketDebuggerUrl; break; }
    } catch {}
  }
  await sleep(250);
}
console.log("ws:", wsUrl);

const ws = new WebSocket(wsUrl);
await new Promise((res) => (ws.onopen = res));
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(m.error) : p.resolve(m.result); } };
const send = (method, params = {}) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.value;
await send("Runtime.enable");

console.log("button count:", await ev(`document.querySelectorAll('button').length`));
console.log("all button texts:", JSON.stringify(await ev(`[...document.querySelectorAll('button')].map(b => b.textContent)`), null, 0));
console.log("find 'Load demo':", await ev(`(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes('Load demo')); return b ? 'FOUND' : 'NOT FOUND'; })()`));
console.log("find 'Reset':", await ev(`(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes('Reset')); return b ? 'FOUND' : 'NOT FOUND'; })()`));
console.log("find 'Hygiene sweep':", await ev(`(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes('Hygiene sweep')); return b ? 'FOUND' : 'NOT FOUND'; })()`));
console.log("find 'Query graph':", await ev(`(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().includes('Query graph')); return b ? 'FOUND' : 'NOT FOUND'; })()`));
console.log("loadDemo defined?", await ev(`typeof loadDemo`));
console.log("reset defined?", await ev(`typeof reset`));
console.log("hygiene defined?", await ev(`typeof hygiene`));
console.log("body snippet:", await ev(`document.body.innerHTML.slice(0, 300)`));

ws.close();
try { chrome.kill(); } catch {}
try { server.kill(); } catch {}
try { rmSync(dataDir, { recursive: true, force: true }); } catch {}
try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(0);
