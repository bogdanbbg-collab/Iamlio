// Verificarea automată a accesibilității (axe-core, regulile WCAG 2.1 A și AA) pe paginile principale.
// Rulare: python3 scripts/stories.py stage && node --test tests/e2e/accesibilitate.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ENGINE = process.env.BROWSER || "chromium";
const engine = require("playwright")[ENGINE];
const AXE = require.resolve("axe-core/axe.min.js");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SITE = join(ROOT, "build/site");
const PORT = 8890 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const STORY = JSON.parse(readFileSync(join(SITE, "stories/index.json"), "utf-8")).stories[0];

let server, browser;

before(async () => {
  server = spawn("php", ["-S", `127.0.0.1:${PORT}`, "-t", SITE], { stdio: "ignore" });
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch(`${BASE}/`); await r.arrayBuffer(); if (r.ok) break; } catch { /* încă pornește */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await engine.launch();
});

after(async () => {
  await browser?.close();
  server?.kill();
});

// Problemele „serioase” și „critice” opresc publicarea; celelalte se afișează în jurnal.
async function audit(p, label) {
  await p.addScriptTag({ path: AXE });
  const result = await p.evaluate(() => window.axe.run(document, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
  }));
  const describe = (v) => `${v.id} (${v.impact}): ${v.help} — ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(", ")}`;
  for (const v of result.violations.filter((v) => !["serious", "critical"].includes(v.impact))) {
    console.log(`[${label}] de îmbunătățit: ${describe(v)}`);
  }
  const blocking = result.violations.filter((v) => ["serious", "critical"].includes(v.impact));
  assert.deepEqual(blocking.map(describe), [], `${label}: probleme de accesibilitate`);
}

async function page(options = {}) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce", ...options });
  return context.newPage();
}

test("accesibilitate: biblioteca", async () => {
  const p = await page();
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  await audit(p, "biblioteca");
});

test("accesibilitate: cititorul, cu setările deschise", { skip: !STORY && "nicio poveste" }, async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/poveste.html?id=${STORY.id}`);
  await p.waitForSelector(".sheet.is-current");
  await audit(p, "cititorul");
  await p.click("#settings-btn");
  await audit(p, "setările");
});

test("accesibilitate: pagina de confidențialitate", async () => {
  const p = await page();
  await p.goto(`${BASE}/confidentialitate.html`);
  await audit(p, "confidențialitate");
});
