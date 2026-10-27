// Teste pentru panoul de administrare (admin.html + api/admin.php, api/vizita.php, api/erori.php, api/citiri.php),
// pe o copie a build/site cu serverul PHP real.
// Rulare: python3 scripts/stories.py stage && BROWSER=webkit node --test tests/e2e/admin.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ENGINE = process.env.BROWSER || "chromium";
const engine = require("playwright")[ENGINE];
const AXE = require.resolve("axe-core/axe.min.js");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = 9090 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const PASSWORD = "parola-admin-de-test";
const STORY = JSON.parse(readFileSync(join(ROOT, "build/site/stories/index.json"), "utf-8")).stories[0];

// mai multe procese PHP: o descărcare audio lungă (WebKit) nu mai ține pe loc celelalte cereri
const PHP_OPTIONS = { stdio: "ignore", env: { ...process.env, PHP_CLI_SERVER_WORKERS: "4" } };

let server, browser, site;

before(async () => {
  site = mkdtempSync(join(tmpdir(), "iamlio-admin-"));
  cpSync(join(ROOT, "build/site"), site, { recursive: true });
  for (const name of ["citiri.json", "vizite.json", "erori.json", "pareri.json"]) rmSync(join(site, "api/data", name), { force: true });
  const salt = "sare";
  writeFileSync(join(site, "api/data/parola.json"),
    JSON.stringify({ salt, hash: createHash("sha256").update(salt + PASSWORD).digest("hex") }));
  server = spawn("php", ["-S", `127.0.0.1:${PORT}`, "-t", site], PHP_OPTIONS);
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch(`${BASE}/`); await r.arrayBuffer(); if (r.ok) break; } catch { /* încă pornește */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await engine.launch();
});

after(async () => {
  await browser?.close();
  server?.kill();
  rmSync(site, { recursive: true, force: true });
});

async function page(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce", ...options });
  const p = await context.newPage();
  p.errors = [];
  p.on("pageerror", (e) => p.errors.push(e.message));
  // o încălcare a politicii de securitate (CSP) e tot o eroare: ceva din pagină ar fi fost blocat
  p.on("console", (m) => { if (/Content[ -]Security[ -]Policy/i.test(m.text())) p.errors.push(m.text()); });
  return p;
}

async function loggedIn() {
  const p = await page();
  await p.goto(`${BASE}/admin.html`);
  await p.fill("#password", PASSWORD);
  await p.click("#login button");
  await p.waitForSelector("#panel:not([hidden])");
  return p;
}

const adminData = async (p) => (await p.context().request.get(`${BASE}/api/admin.php`)).json();
const today = (data) => data.azi;

test("admin: fără parolă nu se vede nimic; parola greșită e refuzată; sesiunea e un cookie HttpOnly strict", async () => {
  const response = await fetch(`${BASE}/api/admin.php`);
  await response.arrayBuffer();
  assert.equal(response.status, 401);
  const p = await page();
  await p.goto(`${BASE}/admin.html`);
  await p.waitForSelector("#login:not([hidden])");
  assert.ok(await p.isHidden("#panel"));
  await p.fill("#password", "gresit");
  await p.click("#login button");
  await p.waitForFunction(() => document.getElementById("login-message").textContent.includes("nu este corectă"));
  await p.fill("#password", PASSWORD);
  await p.click("#login button");
  await p.waitForSelector("#panel:not([hidden])");
  const cookie = (await p.context().cookies()).find((c) => c.name === "iamlio_admin");
  assert.ok(cookie && cookie.httpOnly && cookie.sameSite === "Strict");
  assert.equal(await p.getAttribute('meta[name="robots"]', "content"), "noindex, nofollow");
  await p.click("#logout");
  await p.waitForSelector("#login:not([hidden])");
  assert.equal((await p.context().request.get(`${BASE}/api/admin.php`)).status(), 401);
  assert.deepEqual(p.errors, []);
});

test("admin: vizitele și poveștile deschise apar pe zile; vizitele administratorului nu se numără", async () => {
  const admin = await loggedIn();
  const before = await adminData(admin);
  const day = today(before);
  const visitorsBefore = before.vizite[day]?.vizitatori || 0;

  const visitor = await page();
  await visitor.goto(`${BASE}/`);
  await visitor.waitForSelector(".story-card");
  await visitor.goto(`${BASE}/poveste.html?id=${STORY.id}`);
  await visitor.waitForSelector(".sheet.is-current");
  await visitor.waitForTimeout(500);
  await visitor.context().close();

  await admin.goto(`${BASE}/`);
  await admin.goto(`${BASE}/poveste.html?id=${STORY.id}`);
  await admin.waitForSelector(".sheet.is-current");
  await admin.waitForTimeout(500);

  const after = await adminData(admin);
  assert.equal(after.vizite[day].vizitatori, visitorsBefore + 1, "un vizitator, numărat o dată pe zi");
  assert.equal(after.vizite[day].afisari.acasa, (before.vizite[day]?.afisari?.acasa || 0) + 1);
  assert.equal(after.vizite[day].afisari.poveste, (before.vizite[day]?.afisari?.poveste || 0) + 1);
  assert.equal(after.citiri.zile[day][STORY.id], (before.citiri.zile[day]?.[STORY.id] || 0) + 1,
    "povestea deschisă de administrator nu se numără");

  await admin.goto(`${BASE}/admin.html`);
  await admin.waitForSelector("#panel:not([hidden])");
  assert.match(await admin.textContent("#top"), new RegExp(STORY.title));
  assert.match(await admin.textContent("#tiles"), /Vizitatori azi/);
  assert.equal(await admin.locator("#chart-visits .admin-bar").count(), 30);
});

test("admin: erorile din browser apar grupate, fără date personale, și se pot șterge", async () => {
  const visitor = await page();
  await visitor.goto(`${BASE}/`);
  await visitor.waitForSelector(".story-card");
  await visitor.evaluate(() => { setTimeout(() => { throw new Error("eroare de test"); }, 0); });
  await visitor.evaluate(() => { setTimeout(() => { throw new Error("eroare de test"); }, 0); });
  await visitor.waitForTimeout(800);

  const admin = await loggedIn();
  const data = await adminData(admin);
  const group = data.erori.find((g) => g.mesaj.includes("eroare de test"));
  assert.ok(group, JSON.stringify(data.erori));
  assert.equal(group.tip, "js");
  assert.equal(group.numar, 1, "aceeași eroare se trimite o singură dată pe pagină");
  assert.match(Object.keys(group.browsere)[0], /·/);
  assert.ok(!JSON.stringify(group).includes("127.0.0.1"), "fără adresa IP");

  await admin.reload();
  await admin.waitForSelector("#panel:not([hidden])");
  assert.match(await admin.textContent("#errors"), /eroare de test/);
  admin.once("dialog", (dialog) => dialog.accept());
  await admin.click("#clear-errors");
  await admin.waitForFunction(() => document.getElementById("errors").textContent.includes("Nicio eroare"));
});

test("admin: „Ți-a plăcut povestea?” se numără o dată pe zi și apare în panou", async () => {
  const vote = async (nota) => {
    const r = await fetch(`${BASE}/api/parere.php?id=${STORY.id}&nota=${nota}`, { method: "POST" });
    return { status: r.status, body: await r.json() };
  };
  const first = await vote(3);
  assert.equal(first.status, 200);
  assert.equal(first.body.numarat, true);
  assert.equal((await vote(1)).body.numarat, false, "același vizitator, aceeași zi: nu se mai numără");
  const bad = await fetch(`${BASE}/api/parere.php?id=${STORY.id}&nota=7`, { method: "POST" });
  await bad.arrayBuffer();
  assert.equal(bad.status, 400);
  const unknown = await fetch(`${BASE}/api/parere.php?id=nu-exista&nota=3`, { method: "POST" });
  await unknown.arrayBuffer();
  assert.equal(unknown.status, 404);
  const get = await fetch(`${BASE}/api/parere.php`);
  await get.arrayBuffer();
  assert.equal(get.status, 405, "totalurile nu sunt publice");

  const admin = await loggedIn();
  const data = await adminData(admin);
  assert.equal(data.pareri[STORY.id]["3"], 1);
  await admin.reload();
  await admin.waitForSelector("#panel:not([hidden])");
  assert.match(await admin.textContent("#likes"), new RegExp(STORY.title));
});

test("admin: rapoartele de erori invalide sau prea multe sunt refuzate", async () => {
  const bad = await fetch(`${BASE}/api/erori.php`, { method: "POST", body: "nu e json" });
  await bad.arrayBuffer();
  assert.equal(bad.status, 400);
  const get = await fetch(`${BASE}/api/erori.php`);
  await get.arrayBuffer();
  assert.equal(get.status, 405);
  let last = 0;
  for (let i = 0; i < 32; i++) {
    const r = await fetch(`${BASE}/api/erori.php`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tip: "js", mesaj: `raport ${i}`, sursa: "x.js", linie: i }) });
    await r.arrayBuffer();
    last = r.status;
  }
  assert.equal(last, 429, "cel mult 30 de rapoarte pe zi de la același vizitator");
});

test("admin: previzualizarea poveștilor personalizate se deschide cu aceeași parolă", async () => {
  const admin = await loggedIn();
  const state = await (await admin.context().request.get(`${BASE}/api/previzualizare.php?stare=1`)).json();
  assert.equal(state.autentificat, true);
});

test("admin: accesibilitate (WCAG AA) pe ecranul de intrare și pe panou", async () => {
  const p = await page({ bypassCSP: true }); // altfel politica paginii ar bloca scriptul axe al testului
  await p.goto(`${BASE}/admin.html`);
  await p.waitForSelector("#login:not([hidden])");
  for (const step of ["intrare", "panou"]) {
    if (step === "panou") {
      await p.fill("#password", PASSWORD);
      await p.click("#login button");
      await p.waitForSelector("#panel:not([hidden])");
    }
    await p.addScriptTag({ path: AXE });
    const result = await p.evaluate(() => window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } }));
    assert.deepEqual(result.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).slice(0, 3).join(", ")}`), [], step);
  }
});

test("admin: pe telefon panoul nu are derulare laterală", async () => {
  const p = await page({ viewport: { width: 390, height: 844 } });
  await p.goto(`${BASE}/admin.html`);
  await p.fill("#password", PASSWORD);
  await p.click("#login button");
  await p.waitForSelector("#panel:not([hidden])");
  assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
});
