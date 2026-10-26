// Capturi de ecran pentru verificarea vizuală, în fiecare browser (Chromium, Firefox, WebKit).
// Se salvează în build/capturi/<browser>/; în GitHub Actions apar la rularea publicării, ca „capturi-ecran”.
// Rulare: python3 scripts/stories.py stage && BROWSER=webkit node --test tests/e2e/capturi.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ENGINE = process.env.BROWSER || "chromium";
const engine = require("playwright")[ENGINE];

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const BUILT = join(ROOT, "build/site");
let SITE; // o copie: serverul scrie date (contor, vizite) și nu trebuie să ajungă în ce se publică
const OUT = join(ROOT, "build/capturi", ENGINE);
const PORT = 8990 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const STORY = JSON.parse(readFileSync(join(BUILT, "stories/index.json"), "utf-8")).stories[0];

const SCREENS = { telefon: [390, 844], "telefon-mic": [360, 640], "telefon-culcat": [844, 390], tableta: [1024, 768], calculator: [1440, 900] };

let server, browser;

before(async () => {
  mkdirSync(OUT, { recursive: true });
  SITE = mkdtempSync(join(tmpdir(), "iamlio-"));
  cpSync(BUILT, SITE, { recursive: true });
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
  rmSync(SITE, { recursive: true, force: true });
});

async function shot(name, [width, height], url, prepare) {
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: "reduce" });
  const p = await context.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(url);
  await p.waitForLoadState("networkidle");
  if (prepare) await prepare(p);
  await p.waitForTimeout(300);
  await p.screenshot({ path: join(OUT, `${name}.png`) });
  await context.close();
  assert.deepEqual(errors, [], name);
}

test("capturi: pagina principală pe fiecare ecran", async () => {
  for (const [screen, size] of Object.entries(SCREENS)) {
    await shot(`biblioteca-${screen}`, size, `${BASE}/`, (p) => p.waitForSelector(".story-card"));
  }
});

test("capturi: cititorul (copertă, pagină, setări, final)", { skip: !STORY && "nicio poveste" }, async () => {
  const url = `${BASE}/poveste.html?id=${STORY.id}`;
  for (const screen of ["telefon", "telefon-culcat", "tableta"]) {
    const size = SCREENS[screen];
    await shot(`poveste-coperta-${screen}`, size, url, (p) => p.waitForSelector(".sheet.is-current"));
    await shot(`poveste-pagina-${screen}`, size, url, async (p) => {
      await p.waitForSelector(".sheet.is-current");
      await p.click("#next-btn");
    });
  }
  await shot("poveste-setari-telefon", SCREENS.telefon, url, async (p) => {
    await p.waitForSelector(".sheet.is-current");
    await p.click("#settings-btn");
  });
  await shot("poveste-final-tableta", SCREENS.tableta, url, async (p) => {
    await p.waitForSelector(".sheet.is-current");
    for (let i = 0; i < STORY.pages + 1; i++) {
      await p.keyboard.press("ArrowRight");
      await p.waitForFunction(() => !document.querySelector(".sheet.is-turning"));
    }
  });
});
