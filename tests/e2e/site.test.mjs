// Teste în browser (Chromium real + serverul PHP real) pentru site-ul pregătit în build/site.
// Rulare: python3 scripts/stories.py stage && node --test tests/e2e/*.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = 8790 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const index = JSON.parse(readFileSync(join(ROOT, "build/site/stories/index.json"), "utf-8"));
const STORY = index.stories[0];
const STORY_URL = `${BASE}/poveste.html?id=${STORY.id}`;
const SHEETS = STORY.pages + 2; // copertă + pagini + final
// o poveste nouă primește vocea abia la publicare; testul vocii folosește una care o are deja
const VOICED = index.stories.find((s) => existsSync(join(ROOT, "build/site/stories", s.id, "audio/manifest.json")));

let server, browser, site;

before(async () => {
  site = mkdtempSync(join(tmpdir(), "iamlio-"));
  cpSync(join(ROOT, "build/site"), site, { recursive: true });
  rmSync(join(site, "api/data/citiri.json"), { force: true });
  server = spawn("php", ["-S", `127.0.0.1:${PORT}`, "-t", site], { stdio: "ignore" });
  for (let i = 0; i < 50; i++) {
    try { if ((await fetch(`${BASE}/stories/index.json`)).ok) break; } catch { /* încă pornește */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await chromium.launch();
});

after(async () => {
  await browser?.close();
  server?.kill();
  rmSync(site, { recursive: true, force: true });
});

async function page(options = {}) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, ...options });
  const p = await context.newPage();
  p.errors = [];
  p.on("pageerror", (e) => p.errors.push(e.message));
  return p;
}

const current = (p) => p.evaluate(() => document.querySelector(".sheet.is-current")?.getAttribute("aria-label"));
const settle = (p, label) => p.waitForFunction((l) => document.querySelector(".sheet.is-current")?.getAttribute("aria-label") === l, label);

test("biblioteca afișează poveștile cu titlu și contor", async () => {
  const p = await page();
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal(await p.textContent(".story-card h3"), STORY.title);
  assert.match(await p.textContent(".story-reads"), /primul|Citită/);
  assert.deepEqual(p.errors, []);
});

test("navigare: butoane, tastatură, atingere, swipe, final și reluare", async () => {
  const p = await page();
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  assert.equal(await p.textContent("#story-title"), STORY.title);
  assert.equal(await current(p), "Copertă");

  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  await p.click("#prev-btn");
  await settle(p, "Copertă");
  await p.keyboard.press("ArrowRight");
  await settle(p, "Pagina 1");

  const box = await p.locator("#book").boundingBox();
  const y = box.y + box.height / 2;
  await p.mouse.click(box.x + box.width * 0.8, y); // atingere în dreapta
  await settle(p, "Pagina 2");

  await p.mouse.move(box.x + box.width * 0.85, y); // swipe spre stânga
  await p.mouse.down();
  await p.mouse.move(box.x + box.width * 0.2, y, { steps: 10 });
  await p.mouse.up();
  await settle(p, "Pagina 3");

  // derulare verticală (ex. a textului) care se întoarce în același loc: NU întoarce pagina
  await p.mouse.move(box.x + box.width * 0.7, y);
  await p.mouse.down();
  await p.mouse.move(box.x + box.width * 0.7, y - 120, { steps: 6 });
  await p.mouse.move(box.x + box.width * 0.7, y, { steps: 6 });
  await p.mouse.up();
  await p.waitForTimeout(400);
  assert.equal(await current(p), "Pagina 3");

  for (let i = 3; i < SHEETS - 1; i++) {
    await p.click("#next-btn");
    await settle(p, i + 1 === SHEETS - 1 ? "Sfârșit" : `Pagina ${i + 1}`);
  }
  assert.ok(await p.isDisabled("#next-btn"));
  await p.click("text=Citește din nou");
  await settle(p, "Copertă");
  assert.deepEqual(p.errors, []);
});

test("vocea aleasă se păstrează, iar Lio citește cu fișierele vocii alese", { skip: !VOICED && "nicio poveste nu are încă voce" }, async () => {
  const p = await page();
  await p.goto(`${BASE}/poveste.html?id=${VOICED.id}`);
  await p.waitForSelector(".sheet.is-current");
  await p.click('.voice-switch [data-voice="masculin"]');
  await p.reload();
  await p.waitForSelector(".sheet.is-current");
  assert.equal(await p.getAttribute('.voice-switch [data-voice="masculin"]', "aria-pressed"), "true");
  const request = p.waitForRequest((r) => r.url().includes(`/stories/${VOICED.id}/audio/masculin/coperta.mp3`));
  await p.click("#play-btn");
  await request;
  assert.match(await p.getAttribute("#play-btn", "class"), /is-playing/);
  await p.click("#play-btn");
  assert.doesNotMatch(await p.getAttribute("#play-btn", "class"), /is-playing/);
  assert.deepEqual(p.errors, []);
});

test("contorul: o citire pe vizitator, apoi afișat în bibliotecă și în poveste", async () => {
  const p = await page();
  await p.goto(STORY_URL);
  await p.waitForFunction(() => !document.getElementById("story-reads").hidden);
  assert.equal(await p.textContent("#story-reads"), "Citită o dată");
  const again = await (await fetch(`${BASE}/api/citiri.php?id=${STORY.id}`, { method: "POST" })).json();
  assert.equal(again.numarat, false);
  assert.equal(again.citiri[STORY.id], 1);
  assert.equal((await fetch(`${BASE}/api/citiri.php?id=nu-exista`, { method: "POST" })).status, 404);
  assert.equal((await fetch(`${BASE}/api/citiri.php?id=../etc`, { method: "POST" })).status, 404);
  assert.equal((await fetch(`${BASE}/api/citiri.php`, { method: "DELETE" })).status, 405);
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-reads");
  assert.equal(await p.textContent(".story-reads"), "Citită o dată");
});

test("poveste inexistentă: mesaj clar, fără erori", async () => {
  const p = await page();
  await p.goto(`${BASE}/poveste.html?id=nu-exista`);
  await p.waitForSelector(".reader-error");
  assert.match(await p.textContent(".reader-error"), /Nu am găsit/);
  assert.deepEqual(p.errors, []);
});

for (const [name, viewport] of [["telefon", [375, 667]], ["telefon culcat", [844, 390]],
  ["tabletă", [820, 1180]], ["tabletă culcată", [1180, 820]], ["calculator", [1440, 900]]]) {
  test(`ecran ${name}: fără derulare laterală, textul încape pe fiecare pagină`, async () => {
    const p = await page({ viewport: { width: viewport[0], height: viewport[1] } });
    for (const url of [`${BASE}/`, STORY_URL]) {
      await p.goto(url);
      await p.waitForTimeout(300);
      assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, url);
    }
    await p.waitForSelector(".sheet.is-current");
    for (let i = 1; i < SHEETS; i++) {
      await p.keyboard.press("ArrowRight");
      await p.waitForFunction(() => !document.querySelector(".sheet.is-turning"));
      const overflow = await p.evaluate(() => {
        const text = document.querySelector(".sheet.is-current .sheet-text");
        return text ? text.scrollHeight > text.clientHeight + 2 : false;
      });
      assert.equal(overflow, false, `pagina ${i}`);
    }
    for (const control of ["#play-btn", "#next-btn", "#prev-btn"]) {
      assert.ok(await p.isVisible(control), control);
    }
    assert.deepEqual(p.errors, []);
  });
}

test("mișcare redusă: pagina se schimbă imediat", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  const start = Date.now();
  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  assert.ok(Date.now() - start < 500, `a durat ${Date.now() - start} ms`);
});
