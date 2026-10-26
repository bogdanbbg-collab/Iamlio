// Teste în browser (Chromium, Firefox sau WebKit/Safari + serverul PHP real) pentru site-ul din build/site.
// Rulare: python3 scripts/stories.py stage && BROWSER=webkit node --test tests/e2e/*.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";

const require = createRequire(import.meta.url);
const ENGINE = process.env.BROWSER || "chromium";
const engine = require("playwright")[ENGINE];

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = 8790 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const index = JSON.parse(readFileSync(join(ROOT, "build/site/stories/index.json"), "utf-8"));
// povestea de referință a testelor e mereu aceeași (prima publicată), oricâte povești noi apar
const STORY = index.stories.find((s) => s.id === "lio-si-steluta-cazatoare") || index.stories[0];
const STORY_URL = `${BASE}/poveste.html?id=${STORY.id}`;
const SHEETS = STORY.pages + 2; // copertă + pagini + final
// o poveste nouă primește vocea abia la publicare; testul vocii folosește una care o are deja
const VOICED = index.stories.find((s) => existsSync(join(ROOT, "build/site/stories", s.id, "audio/manifest.json")));

// mai multe procese PHP: o descărcare audio lungă (WebKit) nu mai ține pe loc celelalte cereri
const PHP_OPTIONS = { stdio: "ignore", env: { ...process.env, PHP_CLI_SERVER_WORKERS: "4" } };

let server, browser, site;

// Povești de probă (copii ale primei povești) cu categorii, vârste și durate diferite, pentru filtre.
const EXTRA = [
  { id: "test-ursul", title: "Ursulețul somnoros", categories: ["de-culcare", "animale"], age: "3-5", minutes: 3 },
  { id: "test-comoara", title: "Comoara din pădure", categories: ["aventuri", "amuzante"], age: "5-7", minutes: 6 },
  { id: "test-planete", title: "Lio printre planete", categories: ["invatam", "aventuri"], age: "5-7", minutes: 9 },
];

// data publicării: „Ursulețul somnoros” e nou (publicat azi), celelalte sunt vechi
const day = (offset) => { const d = new Date(Date.now() - offset * 86400000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const PUBLISHED = { "test-ursul": day(0) };

const LONG_TEXT = ("Într-o dimineață cu miros de trifoi, Aricel privea păsărelele care dansau printre norii pufoși. " +
  "— Uitați-vă la mine! a strigat el, întinzând lăbuțele ca două aripi. — Astăzi învăț să zbor! Piu, pasărea " +
  "albastră, a făcut un cerc deasupra lui. Cipi, cea galbenă, a ciripit curioasă, iar Riri, cu pieptul roșcat, " +
  "a coborât aproape de pământ. Aricel a simțit un gâdilat de aventură până în vârful țepilor lui mici strălucitori.");

function addExtraStories(root) {
  const library = JSON.parse(readFileSync(join(root, "stories/index.json"), "utf-8"));
  // biblioteca de test e mereu aceeași (prima poveste + cele de test), oricâte povești reale are site-ul
  library.stories = library.stories.filter((s) => s.id === STORY.id);
  library.stories.forEach((s) => { s.published = day(60); });
  for (const extra of EXTRA) {
    cpSync(join(root, "stories", STORY.id), join(root, "stories", extra.id), { recursive: true });
    const file = join(root, "stories", extra.id, "story.json");
    const story = JSON.parse(readFileSync(file, "utf-8"));
    Object.assign(story, { id: extra.id, title: extra.title, categories: extra.categories, age: extra.age });
    writeFileSync(file, JSON.stringify(story));
    library.stories.push({ ...STORY, ...extra, cover: STORY.cover.replace(STORY.id, extra.id), tags: [],
      published: PUBLISHED[extra.id] || day(60) });
  }
  writeFileSync(join(root, "stories/index.json"), JSON.stringify(library));
  // o poveste cu pagini de 70 de cuvinte lungi (maximul permis de reguli), pentru încăperea textului
  cpSync(join(root, "stories", STORY.id), join(root, "stories", "test-lunga"), { recursive: true });
  const longFile = join(root, "stories", "test-lunga", "story.json");
  const longStory = JSON.parse(readFileSync(longFile, "utf-8"));
  longStory.id = "test-lunga";
  longStory.pages.forEach((page) => { page.text = LONG_TEXT; page.narration = [{ text: LONG_TEXT }]; });
  writeFileSync(longFile, JSON.stringify(longStory));
  // povești personalizate: au doar link secret, nu intră în bibliotecă; cea neaprobată stă în zona protejată,
  // exact cum o pune `stories.py stage` când există ADMIN_PASSWORD
  for (const [id, approved] of [["test-ana-k7p2qx", false], ["test-ana-aprobata-q9w3zz", true]]) {
    const folder = approved ? join(root, "stories", id) : join(root, "api/data/previzualizare", id);
    cpSync(join(root, "stories", STORY.id), folder, { recursive: true });
    const file = join(folder, "story.json");
    const story = JSON.parse(readFileSync(file, "utf-8"));
    Object.assign(story, { id, title: "Ana și steluța", personalized: { for: "Ana" }, approved });
    writeFileSync(file, JSON.stringify(story));
  }
  const salt = "sare-de-test";
  writeFileSync(join(root, "api/data/parola.json"),
    JSON.stringify({ salt, hash: createHash("sha256").update(salt + PREVIEW_PASSWORD).digest("hex") }));
}

const PREVIEW_PASSWORD = "parola-de-test";

// corpul răspunsului se citește complet (altfel fetch din Node poate crăpa)
async function drain(response) { await response.arrayBuffer(); return response; }

before(async () => {
  site = mkdtempSync(join(tmpdir(), "iamlio-"));
  cpSync(join(ROOT, "build/site"), site, { recursive: true });
  rmSync(join(site, "api/data/citiri.json"), { force: true });
  addExtraStories(site);
  server = spawn("php", ["-S", `127.0.0.1:${PORT}`, "-t", site], PHP_OPTIONS);
  for (let i = 0; i < 50; i++) {
    try { if ((await fetch(`${BASE}/stories/index.json`)).ok) break; } catch { /* încă pornește */ }
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
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, ...options });
  const p = await context.newPage();
  p.errors = [];
  p.on("pageerror", (e) => p.errors.push(e.message));
  // o încălcare a politicii de securitate (CSP) e tot o eroare: ceva din pagină ar fi fost blocat
  p.on("console", (m) => { if (/Content[ -]Security[ -]Policy/i.test(m.text())) p.errors.push(m.text()); });
  return p;
}

const current = (p) => p.evaluate(() => document.querySelector(".sheet.is-current")?.getAttribute("aria-label"));
const settle = (p, label) => p.waitForFunction((l) => document.querySelector(".sheet.is-current")?.getAttribute("aria-label") === l, label);

test("biblioteca afișează poveștile cu titlu și contor", async () => {
  const p = await page();
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  const card = p.locator(".story-card", { has: p.locator("h3", { hasText: STORY.title }) });
  assert.equal(await card.count(), 1);
  assert.equal(await card.locator(".story-minutes").textContent(), `~${STORY.minutes} min`);
  assert.match(await card.locator(".story-reads").textContent(), /primul|Citită/);
  // vocea se alege din setările cititorului, nu de pe pagina principală
  assert.equal(await p.locator(".voice-switch").count(), 0);
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
  await p.click("#settings-btn");
  await p.click('#settings .voice-switch [data-voice="masculin"]');
  await p.click("#settings-close");
  await p.reload();
  await p.waitForSelector(".sheet.is-current");
  assert.equal(await p.getAttribute('#settings .voice-switch [data-voice="masculin"]', "aria-pressed"), "true");
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
  const status = async (url, method) => { const r = await fetch(url, { method }); await r.text(); return r.status; };
  assert.equal(await status(`${BASE}/api/citiri.php?id=nu-exista`, "POST"), 404);
  assert.equal(await status(`${BASE}/api/citiri.php?id=../etc`, "POST"), 404);
  assert.equal(await status(`${BASE}/api/citiri.php`, "DELETE"), 405);
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-reads");
  const card = p.locator(".story-card", { has: p.locator("h3", { hasText: STORY.title }) });
  assert.equal(await card.locator(".story-reads").textContent(), "Citită o dată");
});

test("biblioteca apare chiar dacă contorul de citiri nu răspunde, iar contorul vine după", async () => {
  const p = await page();
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  await p.route("**/api/citiri.php*", async (route) => { await held; await route.continue(); });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card", { timeout: 4000 });
  assert.equal(await p.locator(".story-reads").count(), 0, "fără contor cât timp nu a răspuns");
  release();
  await p.waitForSelector(".story-reads");
  assert.deepEqual(p.errors, []);
});

test("biblioteca: dacă lista poveștilor nu vine, o cere din nou o dată", async () => {
  const p = await page();
  let attempts = 0;
  await p.route("**/stories/index.json", (route) => {
    attempts += 1;
    return attempts === 1 ? route.abort() : route.continue();
  });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal(attempts, 2);
});

test("fără zoom la dublă atingere (mărirea cu două degete rămâne)", async () => {
  const p = await page();
  for (const url of [`${BASE}/`, STORY_URL]) {
    await p.goto(url);
    const values = await p.evaluate(() => [document.documentElement, document.body, document.querySelector("button")]
      .map((node) => getComputedStyle(node).touchAction));
    assert.deepEqual(values, ["manipulation", "manipulation", "manipulation"], url);
    const viewport = await p.getAttribute('meta[name="viewport"]', "content");
    assert.ok(!/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\D|$)/.test(viewport), "mărirea nu e interzisă");
  }
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
  test(`ecran ${name}: fără derulare laterală, textul încape pe fiecare pagină a fiecărei povești`, async () => {
    // mișcare redusă doar ca testul să fie rapid; așezarea paginii e aceeași
    const p = await page({ viewport: { width: viewport[0], height: viewport[1] }, reducedMotion: "reduce" });
    for (const url of [`${BASE}/`, STORY_URL, `${BASE}/confidentialitate.html`]) {
      await p.goto(url);
      await p.waitForTimeout(300);
      assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, url);
    }
    // toate poveștile reale, plus una cu pagini de 70 de cuvinte (maximul din reguli)
    for (const story of [...index.stories, { id: "test-lunga", pages: STORY.pages }]) {
      await p.goto(`${BASE}/poveste.html?id=${story.id}`);
      await p.waitForSelector(".sheet.is-current");
      for (let i = 1; i < story.pages + 2; i++) {
        await p.keyboard.press("ArrowRight");
        await p.waitForFunction(() => !document.querySelector(".sheet.is-turning"));
        await p.waitForFunction(() => [...document.querySelectorAll(".sheet.is-current img")].every((img) => img.complete));
        await p.evaluate(() => document.fonts.ready);
        await p.waitForTimeout(150); // potrivirea textului se reface la 100 ms după o schimbare
        const fit = await p.evaluate(() => {
          const text = document.querySelector(".sheet.is-current .sheet-text");
          return text ? { overflow: text.scrollHeight > text.clientHeight + 2, size: parseFloat(getComputedStyle(text).fontSize),
            scroll: text.scrollHeight, client: text.clientHeight, fonts: document.fonts.status } : { overflow: false, size: 99 };
        });
        assert.equal(fit.overflow, false, `${story.id}, pagina ${i}: ${JSON.stringify(fit)}`);
        assert.ok(fit.size >= 13, `${story.id}, pagina ${i}: litera de ${fit.size}px e prea mică`);
      }
    }
    for (const control of ["#play-btn", "#next-btn", "#prev-btn"]) {
      assert.ok(await p.isVisible(control), control);
    }
    assert.deepEqual(p.errors, []);
  });
}

for (const [name, viewport] of [["telefon", [390, 844]], ["telefon mic", [360, 640]], ["telefon culcat", [844, 390]], ["tabletă", [1024, 768]]]) {
  test(`butoane pentru degete mici, ${name}: săgețile și Lio mari, restul de cel puțin 44 px`, async () => {
    const p = await page({ viewport: { width: viewport[0], height: viewport[1] } });
    await p.goto(STORY_URL);
    await p.waitForSelector(".sheet.is-current");
    const size = (selector) => p.$eval(selector, (e) => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); });
    for (const nav of ["#prev-btn", "#next-btn"]) assert.ok(await size(nav) >= 56, `${nav}: ${await size(nav)} px`);
    assert.ok(await size("#play-btn") >= 60, `#play-btn: ${await size("#play-btn")} px`);
    const small = await p.$$eval(".reader-bar a, .reader-bar button", (nodes) => nodes
      .map((e) => { const r = e.getBoundingClientRect(); return [e.className, Math.round(Math.min(r.width, r.height))]; })
      .filter(([, s]) => s && s < 44));
    assert.deepEqual(small, []);
  });
}

test("securitate: fiecare pagină are politica de conținut (doar fișiere proprii, fără scripturi din pagină)", async () => {
  for (const url of ["", "poveste.html", "confidentialitate.html", "admin.html", `p/${STORY.id}.html`]) {
    const html = await (await fetch(`${BASE}/${url}`)).text();
    const csp = html.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/);
    assert.ok(csp, `${url || "/"}: lipsește politica`);
    assert.ok(!csp[1].includes("unsafe-eval") && !/script-src[^;]*unsafe-inline/.test(csp[1]), csp[1]);
    assert.ok(!/<script>/.test(html), `${url || "/"}: script direct în pagină`);
  }
  const api = await fetch(`${BASE}/api/citiri.php`);
  await api.arrayBuffer();
  assert.equal(api.headers.get("x-frame-options"), "DENY");
});

test("textul lung încape și când fontul, contorul și imaginile vin târziu (conexiune lentă)", async () => {
  const p = await page({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  // „Citită de X ori” apare târziu în bara de sus, care crește și micșorează cartea
  for (const pattern of ["**/api/citiri.php*", "**/stories/test-lunga/images/**", "**/assets/fonts/*.woff2"]) {
    await p.route(pattern, async (route) => {
      await new Promise((r) => setTimeout(r, 1500));
      await route.continue();
    });
  }
  await p.goto(`${BASE}/poveste.html?id=test-lunga`);
  await p.waitForSelector(".sheet.is-current");
  // pagina 1 se deschide înainte ca bara de sus să crească; apoi apare contorul, fără să mai dăm pagina
  await p.keyboard.press("ArrowRight");
  await p.waitForFunction(() => document.getElementById("story-reads").hidden === false, null, { timeout: 10000 });
  await p.waitForFunction(() => [...document.querySelectorAll(".sheet.is-current img")].every((img) => img.complete && img.naturalWidth));
  await p.waitForFunction(() => document.fonts.status === "loaded" && [...document.fonts].some((f) => f.status === "loaded"));
  await p.waitForTimeout(400);
  const overflow = await p.evaluate(() => {
    const text = document.querySelector(".sheet.is-current .sheet-text");
    return text.scrollHeight > text.clientHeight + 2;
  });
  assert.equal(overflow, false);
});

test("mișcare redusă: pagina se schimbă imediat", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  const start = Date.now();
  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  // animația normală durează 1300 ms; sub 1000 ms (cu tot cu clicul, pe un server încărcat) înseamnă fără animație
  assert.ok(Date.now() - start < 1000, `a durat ${Date.now() - start} ms`);
});

test("animația paginii: camera se mișcă pe pagina curentă, cu efectul ales în poveste", async () => {
  const story = JSON.parse(readFileSync(join(ROOT, "build/site/stories", STORY.id, "story.json"), "utf-8"));
  const first = story.pages[0].animation;
  const p = await page();
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  const state = await p.evaluate(() => {
    const art = document.querySelector(".sheet.is-current .sheet-art");
    const next = document.querySelector(".sheet.is-next .sheet-art img");
    return {
      classes: art.className,
      animation: getComputedStyle(art.querySelector("img")).animationName,
      nextAnimation: next ? getComputedStyle(next).animationName : "none",
      bits: art.querySelectorAll(".fx span").length,
      fxHidden: art.querySelector(".fx")?.getAttribute("aria-hidden"),
    };
  });
  assert.match(state.classes, new RegExp(`cam-${first.camera}`));
  assert.equal(state.animation, first.camera === "still" ? "none" : `cam-${first.camera}`);
  assert.equal(state.nextAnimation, "none", "doar pagina curentă se mișcă");
  if (first.effect !== "none") {
    assert.ok(state.bits > 0, "efectul paginii apare");
    assert.equal(state.fxHidden, "true", "efectul e doar decor pentru cititoarele de ecran");
  }
  assert.deepEqual(p.errors, []);
});

test("animația paginii: cu „Reducere mișcare” imaginea stă pe loc și nu apar efecte", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  const state = await p.evaluate(() => ({
    animations: [...document.querySelectorAll(".sheet-art img")].map((img) => getComputedStyle(img).animationName),
    bits: document.querySelectorAll(".fx span").length,
  }));
  assert.ok(state.animations.every((name) => name === "none"), state.animations.join(","));
  assert.equal(state.bits, 0);
});

test("nicio pagină nu încarcă nimic de la alte site-uri (fonturi, reclame, urmărire)", async () => {
  const p = await page();
  const external = [];
  p.on("request", (r) => { if (!r.url().startsWith(BASE) && !r.url().startsWith("data:")) external.push(r.url()); });
  for (const url of [`${BASE}/`, STORY_URL, `${BASE}/confidentialitate.html`]) {
    await p.goto(url);
    await p.waitForLoadState("networkidle");
  }
  assert.deepEqual(external, []);
});

const audioState = (p) => p.evaluate(() => {
  const a = document.querySelector("audio");
  return { rate: a.playbackRate, volume: a.volume, src: a.src };
});

test("distribuire: fiecare poveste are pagina ei cu titlu și copertă (Open Graph), care duce la cititor", async () => {
  const html = await (await fetch(`${BASE}/p/${STORY.id}.html`)).text();
  assert.ok(html.includes(`<meta property="og:title" content="${STORY.title}">`));
  const image = html.match(/property="og:image" content="https:\/\/[^/]+\/(p\/[^"?]+\.jpg)\?v=/);
  assert.ok(image, "og:image cu coperta poveștii");
  const response = await fetch(`${BASE}/${image[1]}`);
  assert.equal(response.headers.get("content-type"), "image/jpeg");
  assert.ok((await response.arrayBuffer()).byteLength > 10000);
  const p = await page();
  await p.goto(`${BASE}/p/${STORY.id}.html`);
  await p.waitForURL(/poveste\.html\?id=/);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#settings-btn");
  assert.ok(await p.isVisible("#share-btn"));
});

test("dialogul de setări păstrează focusul cu Tab și Shift+Tab", async () => {
  const p = await page();
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#settings-btn");
  const inside = () => p.evaluate(() => document.getElementById("settings").contains(document.activeElement));
  for (let i = 0; i < 25; i++) {
    await p.keyboard.press("Tab");
    assert.ok(await inside(), `după ${i + 1} × Tab focusul a ieșit din dialog`);
  }
  for (let i = 0; i < 25; i++) {
    await p.keyboard.press("Shift+Tab");
    assert.ok(await inside(), `după ${i + 1} × Shift+Tab focusul a ieșit din dialog`);
  }
  await p.keyboard.press("Escape");
  assert.equal(await p.evaluate(() => document.activeElement.id), "settings-btn");
});

test("setări: viteza vocii și modul de culcare se aplică și se păstrează", { skip: !VOICED && "nicio poveste nu are încă voce" }, async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(`${BASE}/poveste.html?id=${VOICED.id}`);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#settings-btn");
  assert.ok(await p.isVisible("#settings .settings-panel"));
  await p.click('[data-speed="0.8"]');
  await p.click("#bedtime");
  await p.keyboard.press("Escape");
  assert.ok(await p.isHidden("#settings"));
  assert.match(await p.getAttribute("body", "class"), /bedtime/);
  await p.click("#play-btn");
  await p.waitForFunction(() => document.querySelector("audio").src.includes(".mp3"));
  const state = await audioState(p);
  assert.equal(state.rate, 0.8);
  assert.equal(state.volume, 0.7);
  await p.click("#play-btn");
  await p.reload();
  await p.waitForSelector(".sheet.is-current");
  assert.match(await p.getAttribute("body", "class"), /bedtime/);
  assert.equal(await p.getAttribute('[data-speed="0.8"]', "aria-pressed"), "true");
  assert.deepEqual(p.errors, []);
});

test("reluare: povestea continuă de la pagina la care a rămas copilul", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(STORY_URL);
  await p.waitForSelector(".sheet.is-current");
  assert.ok(await p.isHidden(".resume"));
  for (let i = 1; i <= 3; i++) {
    await p.click("#next-btn");
    await settle(p, `Pagina ${i}`);
  }
  await p.reload();
  await p.waitForSelector(".resume:not([hidden])");
  assert.match(await p.textContent(".resume-text"), /pagina 3/);
  await p.click(".resume-continue");
  await settle(p, "Pagina 3");
  for (let i = 4; i < SHEETS; i++) {
    await p.click("#next-btn"); // un clic în timpul întoarcerii e ignorat (corect), deci așteptăm fiecare pagină
    await settle(p, i === SHEETS - 1 ? "Sfârșit" : `Pagina ${i}`);
  }
  await p.reload();
  await p.waitForSelector(".sheet.is-current");
  assert.ok(await p.isHidden(".resume"), "după ce povestea a fost terminată, nu mai propune reluarea");
});

test("evidențiere: replica citită se colorează sincron cu vocea", { skip: !VOICED && "nicio poveste nu are încă voce" }, async () => {
  const p = await page({ reducedMotion: "reduce" });
  // momente cunoscute pentru pagina 1, ca testul să nu depindă de durata reală a vocii
  await p.route("**/audio/manifest.json*", async (route) => {
    const manifest = await (await route.fetch()).json();
    manifest.timing = { feminin: { "pagina-01.mp3": [[0, 0.4], [0.5, 30]] }, masculin: { "pagina-01.mp3": [[0, 0.4], [0.5, 30]] } };
    await route.fulfill({ json: manifest });
  });
  await p.goto(`${BASE}/poveste.html?id=${VOICED.id}`);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  const spans = await p.locator(".sheet.is-current .seg").count();
  assert.ok(spans >= 2, "textul paginii are replicile marcate");
  await p.click("#play-btn");
  await p.waitForFunction(() => document.querySelector("audio").readyState >= 1);
  await p.evaluate(() => { document.querySelector("audio").currentTime = 1; });
  await p.waitForFunction(() => document.querySelectorAll(".sheet.is-current .seg")[1].classList.contains("is-spoken"));
  assert.equal(await p.locator(".sheet.is-current .seg.is-spoken").count(), 1);
  await p.click("#play-btn");
  await p.waitForTimeout(500); // browserul mai trimite o actualizare de timp după pauză
  assert.equal(await p.locator(".seg.is-spoken").count(), 0);
});

test("aplicație: manifest și pictograme pentru „Adaugă pe ecranul principal”", async () => {
  const manifest = await (await fetch(`${BASE}/manifest.webmanifest`)).json();
  assert.equal(manifest.short_name, "Iamlio");
  for (const icon of manifest.icons) {
    const response = await fetch(`${BASE}/${icon.src}`);
    const body = await response.arrayBuffer(); // corpul se citește complet (altfel fetch din Node poate crăpa)
    assert.equal(response.status, 200, icon.src);
    assert.ok(body.byteLength > 1000, icon.src);
  }
  const p = await page();
  await p.goto(STORY_URL);
  await p.click("#settings-btn");
  const offered = await p.isVisible("#fullscreen-btn") || await p.isVisible("#fullscreen-hint");
  assert.ok(offered, "ecranul complet e oferit (buton sau explicație pentru iPhone)");
});

const cardTitles = (p) => p.$$eval(".story-card h3", (nodes) => nodes.map((n) => n.textContent));

for (const [name, viewport] of [["telefon", [390, 844]], ["telefon mic", [360, 640]], ["tabletă", [1024, 768]]]) {
  test(`pagina principală, ${name}: prima copertă se vede întreagă fără derulare`, async () => {
    const p = await page({ viewport: { width: viewport[0], height: viewport[1] } });
    await p.goto(`${BASE}/`);
    await p.waitForSelector(".story-card");
    const cover = await p.evaluate(() => document.querySelector(".story-cover").getBoundingClientRect().toJSON());
    assert.ok(cover.top >= 0 && cover.bottom <= viewport[1], `coperta e între ${cover.top} și ${cover.bottom} px`);
  });
}

test("„Lio, alege tu!”: deschide altă poveste decât data trecută, gata de citit", async () => {
  const p = await page();
  let previous = "";
  for (let i = 0; i < 6; i++) {
    await p.goto(`${BASE}/`);
    await p.waitForSelector("#lio-picks:not([hidden])");
    await p.click("#lio-picks");
    await p.waitForURL(/poveste\.html\?id=/);
    await p.waitForSelector(".sheet.is-current");
    const id = new URL(p.url()).searchParams.get("id");
    assert.ok(id && id !== previous, `a ales ${id} după ${previous}`);
    assert.ok(!p.url().includes("citeste=1"), "la reîncărcare nu mai pornește singură");
    previous = id;
  }
  // vocea a pornit singură sau, dacă browserul a cerut o atingere, Lio așteaptă (nu rămâne „blocat” pornit fără sunet)
  await p.waitForTimeout(500);
  const state = await p.evaluate(() => ({
    playing: document.getElementById("play-btn").classList.contains("is-playing"),
    paused: document.querySelector("audio").paused,
  }));
  assert.ok(state.playing ? !state.paused : true, JSON.stringify(state));
  assert.deepEqual(p.errors, []);
});

test("„Lio, alege tu!”: dacă browserul blochează sunetul, Lio așteaptă o atingere, fără vocea browserului", { skip: !VOICED && "nicio poveste nu are încă voce" }, async () => {
  const p = await page();
  await p.addInitScript(() => {
    window.__spoken = 0;
    HTMLMediaElement.prototype.play = function () { return Promise.reject(new DOMException("blocat", "NotAllowedError")); };
    if (window.speechSynthesis) speechSynthesis.speak = () => { window.__spoken++; };
  });
  await p.goto(`${BASE}/poveste.html?id=${VOICED.id}&citeste=1`);
  await p.waitForSelector(".sheet.is-current");
  await p.waitForTimeout(500);
  assert.equal(await p.evaluate(() => document.getElementById("play-btn").classList.contains("is-playing")), false);
  assert.equal(await p.evaluate(() => window.__spoken), 0);
  assert.equal(await p.getAttribute(".sheet.is-current", "aria-label"), "Copertă");
  // un semn static arată unde să apeși; dispare la apăsare
  assert.ok(await p.isVisible(".tap-hint"));
  assert.match(await p.getAttribute("#play-btn", "class"), /needs-tap/);
  await p.click("#play-btn");
  assert.ok(await p.isHidden(".tap-hint"));
});

test("„Nou” și „Povestea săptămânii”: după data publicării, povestea săptămânii prima", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal((await cardTitles(p))[0], "Ursulețul somnoros", "povestea publicată săptămâna aceasta e prima");
  const first = p.locator(".story-card").first();
  assert.equal(await first.locator(".story-featured").count(), 1);
  assert.equal(await first.locator(".story-new").count(), 1);
  assert.equal(await p.locator(".story-new").count(), 1, "doar povestea publicată recent e „Nou”");
  assert.equal(await p.locator(".story-featured").count(), 1);
});

test("„Povestea săptămânii” fără povești noi: una din bibliotecă, aceeași toată săptămâna; sub trei povești nu apare", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  let keep = 4;
  await p.route("**/stories/index.json*", async (route) => {
    const body = await (await route.fetch()).json();
    body.stories = body.stories.slice(0, keep).map((s) => ({ ...s, published: "2020-01-01" }));
    await route.fulfill({ json: body });
  });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal(await p.locator(".story-new").count(), 0);
  assert.equal(await p.locator(".story-featured").count(), 1);
  const featured = await p.locator(".story-card").first().locator("h3").textContent();
  await p.reload();
  await p.waitForSelector(".story-card");
  assert.equal(await p.locator(".story-card").first().locator("h3").textContent(), featured);
  keep = 2;
  await p.reload();
  await p.waitForSelector(".story-card");
  assert.equal(await p.locator(".story-featured").count(), 0);
});

test("„Lio, alege tu!” apare doar de la trei povești", async () => {
  const p = await page();
  await p.route("**/stories/index.json*", async (route) => {
    const body = await (await route.fetch()).json();
    body.stories = body.stories.slice(0, 2);
    await route.fulfill({ json: body });
  });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.ok(await p.isHidden("#lio-picks"));
});

test("cu o singură poveste nu apare butonul „Filtre”", async () => {
  const p = await page();
  await p.route("**/stories/index.json*", async (route) => {
    const body = await (await route.fetch()).json();
    body.stories = body.stories.slice(0, 1);
    await route.fulfill({ json: body });
  });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.ok(await p.isHidden("#filters-toggle"));
  assert.ok(await p.isHidden("#filters"));
});

test("filtre: categorie, durată, favorite, păstrate în adresă, cu mesaj când nu se potrivește nimic", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal((await cardTitles(p)).length, 1 + EXTRA.length);
  assert.ok(await p.isHidden("#filters"), "filtrele stau strânse sub butonul „Filtre”");
  // vârsta nu se afișează nicăieri pe site: nici filtru, nici pe carduri
  assert.equal(await p.locator('[data-filter="varsta"]').count(), 0);
  assert.ok(!/\d[–-]\d ani/.test(await p.textContent("body")), "fără „3–7 ani” pe pagină");
  await p.click("#filters-toggle");
  assert.equal(await p.getAttribute("#filters-toggle", "aria-expanded"), "true");
  await p.click('#category-chips [data-value="animale"]');
  assert.deepEqual(await cardTitles(p), ["Ursulețul somnoros"]);
  assert.match(p.url(), /categorie=animale/);
  await p.click('#category-chips [data-value=""]');
  await p.click('[data-filter="durata"] [data-value="lungi"]');
  assert.deepEqual(await cardTitles(p), ["Lio printre planete"]);
  await p.click('#category-chips [data-value="amuzante"]');
  assert.equal(await p.locator(".empty-state").count(), 1);
  await p.click('#category-chips [data-value=""]');
  assert.deepEqual(await cardTitles(p), ["Lio printre planete"]);
  await p.reload();
  await p.waitForSelector(".story-card");
  assert.deepEqual(await cardTitles(p), ["Lio printre planete"], "filtrul rămâne după reîncărcare");
  assert.ok(await p.isVisible("#filters"), "cu filtre alese în adresă, panoul e deschis");
  assert.equal(await p.textContent("#filters-badge"), "1");
  assert.equal(await p.getAttribute('[data-filter="durata"] [data-value="lungi"]', "aria-pressed"), "true");
  assert.match(await p.textContent("#results-count"), /1 din 4/);
  assert.deepEqual(p.errors, []);
});

test("favorite: inimioara de pe card și din poveste, filtrul „Favorite”", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  await p.click("#filters-toggle");
  await p.click("#favorites-filter");
  assert.match(await p.textContent(".empty-state"), /Încă nu ai povești favorite/);
  await p.click("#favorites-filter");
  const card = p.locator(".story-card", { hasText: "Comoara din pădure" });
  await card.locator(".fav-btn").click();
  assert.equal(await card.locator(".fav-btn").getAttribute("aria-pressed"), "true");
  await p.click("#favorites-filter");
  assert.deepEqual(await cardTitles(p), ["Comoara din pădure"]);
  await p.goto(`${BASE}/poveste.html?id=test-comoara`);
  await p.waitForSelector(".reader-bar .fav-btn");
  assert.equal(await p.getAttribute(".reader-bar .fav-btn", "aria-pressed"), "true");
  await p.click(".reader-bar .fav-btn");
  await p.goto(`${BASE}/?favorite=1`);
  await p.waitForSelector(".empty-state");
  assert.deepEqual(p.errors, []);
});

test("final: fără listă de recomandări, iar „Alte povești” duce în bibliotecă", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(`${BASE}/poveste.html?id=test-comoara`);
  await p.waitForSelector(".sheet.is-current");
  for (let i = 1; i < SHEETS; i++) {
    await p.click("#next-btn");
    await settle(p, i === SHEETS - 1 ? "Sfârșit" : `Pagina ${i}`);
  }
  await p.waitForTimeout(500);
  assert.equal(await p.locator(".is-current a[href*='poveste.html']").count(), 0, "nicio legătură spre alte povești");
  await p.click(".is-current .pill-alt");
  await p.waitForSelector(".story-card");
  assert.equal(new URL(p.url()).pathname, "/");
  assert.deepEqual(p.errors, []);
});

test("biblioteca arată „Continuă · pagina N” pentru povestea începută", async () => {
  const p = await page({ reducedMotion: "reduce", viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/poveste.html?id=test-ursul`);
  await p.waitForSelector(".sheet.is-current");
  await p.click("#next-btn");
  await settle(p, "Pagina 1");
  await p.click("#next-btn");
  await settle(p, "Pagina 2");
  await p.goto(`${BASE}/`);
  const card = p.locator(".story-card", { hasText: "Ursulețul somnoros" });
  await card.locator(".story-resume").waitFor();
  assert.equal(await card.locator(".story-resume").textContent(), "Continuă · pagina 2");
});

async function goToEnd(p, id) {
  await p.goto(`${BASE}/poveste.html?id=${id}`);
  await p.waitForSelector(".sheet.is-current");
  for (let i = 1; i < SHEETS; i++) {
    await p.click("#next-btn");
    await settle(p, i === SHEETS - 1 ? "Sfârșit" : `Pagina ${i}`);
  }
}

test("Lio salută pe copertă și își ia rămas-bun la final", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(STORY_URL);
  await p.waitForSelector(".lio-bubble");
  assert.ok((await p.textContent(".lio-bubble")).length > 10);
  await goToEnd(p, STORY.id);
  assert.ok((await p.textContent(".is-current .end-outro")).length > 10);
});

test("întrebările lui Lio: greșit → mai încearcă, corect → bravo, apoi următoarea și „Gata!”", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await goToEnd(p, STORY.id);
  const story = JSON.parse(readFileSync(join(site, "stories", STORY.id, "story.json"), "utf-8"));
  if (!story.questions?.length) return; // povestea nu are întrebări
  await p.click(".is-current .pill-quiz");
  await p.waitForSelector(".quiz:not([hidden]) .quiz-option");
  for (let n = 0; n < story.questions.length; n++) {
    const question = story.questions[n];
    assert.equal(await p.textContent(".quiz-question"), question.text);
    assert.match(await p.textContent(".quiz-progress"), new RegExp(`${n + 1} din ${story.questions.length}`));
    const wrong = question.answer === 0 ? 1 : 0;
    await p.click(`.quiz-option >> nth=${wrong}`);
    assert.match(await p.getAttribute(`.quiz-option >> nth=${wrong}`, "class"), /is-wrong/);
    assert.ok(await p.isHidden(".quiz-actions .pill:not(.pill-alt)"), "nu trece mai departe la un răspuns greșit");
    await p.click(`.quiz-option >> nth=${question.answer}`);
    assert.match(await p.getAttribute(`.quiz-option >> nth=${question.answer}`, "class"), /is-right/);
    assert.match(await p.getAttribute(".quiz-lio", "src"), /lio-bravo/);
    await p.click(".quiz-actions .pill:not(.pill-alt)");
  }
  assert.ok(await p.isHidden(".quiz"), "„Gata!” închide întrebările");
  assert.deepEqual(p.errors, []);
});

test("mod de culcare: la final, Lio e somnoros", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.addInitScript(() => localStorage.setItem("iamlio-culcare", "1"));
  await goToEnd(p, STORY.id);
  assert.match(await p.getAttribute(".is-current .end-lio", "src"), /lio-somnoros/);
});

test("povești personalizate: link secret, în afara bibliotecii, previzualizare până la aprobare", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.ok(!(await cardTitles(p)).includes("Ana și steluța"), "nu apare în bibliotecă");
  // neaprobată: nu există în partea publică, iar serverul nu dă fișierele fără parolă
  assert.equal((await fetch(`${BASE}/stories/test-ana-k7p2qx/story.json`).then(drain)).status, 404);
  assert.equal((await fetch(`${BASE}/api/previzualizare.php?id=test-ana-k7p2qx&f=story.json`).then(drain)).status, 401);
  assert.equal((await fetch(`${BASE}/api/previzualizare.php?id=test-ana-k7p2qx&f=../../citiri.php`).then(drain)).status, 401);
  await p.goto(`${BASE}/poveste.html?id=test-ana-k7p2qx`);
  await p.waitForSelector(".reader-error");
  await p.goto(`${BASE}/poveste.html?previzualizare=test-ana-k7p2qx`);
  await p.waitForSelector(".preview-login input[type=password]");
  assert.ok(!(await p.textContent("body")).includes("Ana și steluța"), "fără parolă nu se vede nimic din poveste");
  await p.fill(".preview-login input", "gresit");
  await p.click(".preview-login button");
  await p.waitForSelector("text=Parola nu este corectă");
  await p.fill(".preview-login input", PREVIEW_PASSWORD);
  await p.click(".preview-login button");
  await p.waitForSelector(".preview-banner");
  assert.match(await p.textContent(".preview-banner"), /Ana/);
  assert.equal(await p.getAttribute('meta[name="robots"]', "content"), "noindex, nofollow");
  await p.waitForSelector(".sheet.is-current img");
  const cover = await p.getAttribute(".sheet.is-current img", "src");
  assert.match(cover, /^api\/previzualizare\.php\?id=test-ana-k7p2qx&f=images\//);
  assert.ok(await p.$eval(".sheet.is-current img", (img) => img.complete && img.naturalWidth > 0), "imaginea vine prin server");
  // după autentificare, căile în afara poveștii tot nu se pot citi
  const cookies = (await p.context().cookies()).map((c) => `${c.name}=${c.value}`).join("; ");
  const outside = await fetch(`${BASE}/api/previzualizare.php?id=test-ana-k7p2qx&f=../../cheie.txt`, { headers: { cookie: cookies } }).then(drain);
  assert.equal(outside.status, 404);
  await p.goto(`${BASE}/poveste.html?id=test-ana-aprobata-q9w3zz`);
  await p.waitForSelector(".sheet.is-current");
  assert.equal(await p.locator(".preview-banner").count(), 0, "după aprobare nu mai e previzualizare");
  assert.equal(await p.getAttribute('meta[name="robots"]', "content"), "noindex, nofollow");
});
