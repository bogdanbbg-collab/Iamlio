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
const STORY = index.stories[0];
const STORY_URL = `${BASE}/poveste.html?id=${STORY.id}`;
const SHEETS = STORY.pages + 2; // copertă + pagini + final
// o poveste nouă primește vocea abia la publicare; testul vocii folosește una care o are deja
const VOICED = index.stories.find((s) => existsSync(join(ROOT, "build/site/stories", s.id, "audio/manifest.json")));

let server, browser, site;

// Povești de probă (copii ale primei povești) cu categorii, vârste și durate diferite, pentru filtre și recomandări.
const EXTRA = [
  { id: "test-ursul", title: "Ursulețul somnoros", categories: ["de-culcare", "animale"], age: "3-5", minutes: 3 },
  { id: "test-comoara", title: "Comoara din pădure", categories: ["aventuri", "amuzante"], age: "5-7", minutes: 6 },
  { id: "test-planete", title: "Lio printre planete", categories: ["invatam", "aventuri"], age: "5-7", minutes: 9 },
];

function addExtraStories(root) {
  const library = JSON.parse(readFileSync(join(root, "stories/index.json"), "utf-8"));
  for (const extra of EXTRA) {
    cpSync(join(root, "stories", STORY.id), join(root, "stories", extra.id), { recursive: true });
    const file = join(root, "stories", extra.id, "story.json");
    const story = JSON.parse(readFileSync(file, "utf-8"));
    Object.assign(story, { id: extra.id, title: extra.title, categories: extra.categories, age: extra.age });
    writeFileSync(file, JSON.stringify(story));
    library.stories.push({ ...STORY, ...extra, cover: STORY.cover.replace(STORY.id, extra.id), tags: [] });
  }
  writeFileSync(join(root, "stories/index.json"), JSON.stringify(library));
  // povești personalizate: au doar link secret, nu intră în bibliotecă; cea neaprobată stă în zona protejată,
  // exact cum o pune `stories.py stage` când există PREVIEW_PASSWORD
  for (const [id, approved] of [["test-ana-k7p2qx", false], ["test-ana-aprobata-q9w3zz", true]]) {
    const folder = approved ? join(root, "stories", id) : join(root, "api/data/previzualizare", id);
    cpSync(join(root, "stories", STORY.id), folder, { recursive: true });
    const file = join(folder, "story.json");
    const story = JSON.parse(readFileSync(file, "utf-8"));
    Object.assign(story, { id, title: "Ana și steluța", personalized: { for: "Ana" }, approved });
    writeFileSync(file, JSON.stringify(story));
  }
  const salt = "sare-de-test";
  writeFileSync(join(root, "api/data/previzualizare.json"),
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
  server = spawn("php", ["-S", `127.0.0.1:${PORT}`, "-t", site], { stdio: "ignore" });
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
  return p;
}

const current = (p) => p.evaluate(() => document.querySelector(".sheet.is-current")?.getAttribute("aria-label"));
const settle = (p, label) => p.waitForFunction((l) => document.querySelector(".sheet.is-current")?.getAttribute("aria-label") === l, label);

test("biblioteca afișează poveștile cu titlu și contor", async () => {
  const p = await page();
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal(await p.textContent(".story-card h3"), STORY.title);
  assert.equal(await p.textContent(".story-card .story-minutes"), `~${STORY.minutes} min`);
  assert.match(await p.textContent(".story-reads"), /primul|Citită/);
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
  test(`ecran ${name}: fără derulare laterală, textul încape pe fiecare pagină a fiecărei povești`, async () => {
    // mișcare redusă doar ca testul să fie rapid; așezarea paginii e aceeași
    const p = await page({ viewport: { width: viewport[0], height: viewport[1] }, reducedMotion: "reduce" });
    for (const url of [`${BASE}/`, STORY_URL, `${BASE}/confidentialitate.html`]) {
      await p.goto(url);
      await p.waitForTimeout(300);
      assert.equal(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, url);
    }
    for (const story of index.stories) {
      await p.goto(`${BASE}/poveste.html?id=${story.id}`);
      await p.waitForSelector(".sheet.is-current");
      for (let i = 1; i < story.pages + 2; i++) {
        await p.keyboard.press("ArrowRight");
        await p.waitForFunction(() => !document.querySelector(".sheet.is-turning"));
        const overflow = await p.evaluate(() => {
          const text = document.querySelector(".sheet.is-current .sheet-text");
          return text ? text.scrollHeight > text.clientHeight + 2 : false;
        });
        assert.equal(overflow, false, `${story.id}, pagina ${i}`);
      }
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
  // animația normală durează 1300 ms; sub 1000 ms (cu tot cu clicul, pe un server încărcat) înseamnă fără animație
  assert.ok(Date.now() - start < 1000, `a durat ${Date.now() - start} ms`);
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

test("filtre: categorie, vârstă, durată, păstrate în adresă, cu mesaj când nu se potrivește nimic", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  assert.equal((await cardTitles(p)).length, 1 + EXTRA.length);
  await p.click('#category-chips [data-value="animale"]');
  assert.deepEqual(await cardTitles(p), ["Ursulețul somnoros"]);
  assert.match(p.url(), /categorie=animale/);
  await p.click('#category-chips [data-value=""]');
  await p.click('[data-filter="varsta"] [data-value="3-5"]');
  assert.ok(!(await cardTitles(p)).includes("Comoara din pădure"), "poveștile de 5–7 ani dispar la 3–5 ani");
  await p.click('[data-filter="durata"] [data-value="lungi"]');
  assert.equal(await p.locator(".empty-state").count(), 1);
  await p.click('[data-filter="varsta"] [data-value=""]');
  assert.deepEqual(await cardTitles(p), ["Lio printre planete"]);
  await p.reload();
  await p.waitForSelector(".story-card");
  assert.deepEqual(await cardTitles(p), ["Lio printre planete"], "filtrul rămâne după reîncărcare");
  assert.equal(await p.getAttribute('[data-filter="durata"] [data-value="lungi"]', "aria-pressed"), "true");
  assert.match(await p.textContent("#results-count"), /1 din 4/);
  assert.deepEqual(p.errors, []);
});

test("favorite: inimioara de pe card și din poveste, filtrul „Favorite”", async () => {
  const p = await page({ viewport: { width: 1280, height: 900 } });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
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

test("recomandări: la final, două povești asemănătoare, fără cea curentă", async () => {
  const p = await page({ reducedMotion: "reduce" });
  await p.goto(`${BASE}/poveste.html?id=test-comoara`);
  await p.waitForSelector(".sheet.is-current");
  for (let i = 1; i < SHEETS; i++) {
    await p.click("#next-btn");
    await settle(p, i === SHEETS - 1 ? "Sfârșit" : `Pagina ${i}`);
  }
  await p.waitForSelector(".end-recs:not([hidden]) .rec-card");
  const links = await p.$$eval(".is-current .rec-card", (cards) => cards.map((c) => c.getAttribute("href")));
  assert.equal(links.length, 2);
  assert.ok(!links.some((href) => href.includes("test-comoara")), "nu se recomandă povestea curentă");
  assert.ok(links[0].includes("test-planete"), "prima recomandare are categorii comune (aventuri)");
  await p.click(".is-current .rec-card >> nth=0");
  await p.waitForURL(/test-planete/);
  await p.waitForSelector(".sheet.is-current");
  assert.equal(await p.textContent("#story-title"), "Lio printre planete");
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
