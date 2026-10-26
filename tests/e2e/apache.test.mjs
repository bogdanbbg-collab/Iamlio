// public/.htaccess pe un server Apache real (cu PHP), ca pe hosting: antete de securitate, cache, compresie,
// fișiere ascunse și date private blocate, redirecționare spre HTTPS, iar site-ul și PHP-ul funcționează.
// Se sare peste test dacă pe calculator nu e instalat Apache (pe mașinile GitHub este).
// Rulare: python3 scripts/stories.py stage && node --test tests/e2e/apache.test.mjs
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { execFileSync, spawn } from "node:child_process";
import { chmodSync, cpSync, existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import http from "node:http";

const require = createRequire(import.meta.url);
const ENGINE = process.env.BROWSER || "chromium";
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const APACHE = ["/usr/sbin/apache2", "/usr/sbin/httpd"].find((p) => existsSync(p));
const MODULES = ["/usr/lib/apache2/modules", "/usr/lib64/httpd/modules"].find((p) => existsSync(p));
const PHP = MODULES && readdirSync(MODULES).find((f) => /^libphp.*\.so$/.test(f));
const SKIP = !APACHE || !MODULES ? "Apache nu e instalat" : false;
const PORT = 9190 + Math.floor(Math.random() * 100);
const BASE = `http://127.0.0.1:${PORT}`;
const STORY = JSON.parse(readFileSync(join(ROOT, "build/site/stories/index.json"), "utf-8")).stories[0];

let dir, site, server, browser;

before(async () => {
  if (SKIP) return;
  dir = mkdtempSync(join(tmpdir(), "iamlio-apache-"));
  site = join(dir, "site");
  cpSync(join(ROOT, "build/site"), site, { recursive: true });
  writeFileSync(join(site, ".ftp-deploy-sync-state.json"), "{}");
  writeFileSync(join(site, "api/data/citiri.json"), '{"citiri":{}}');
  const root = process.getuid && process.getuid() === 0;
  if (root) execFileSync("chmod", ["-R", "a+rwX", dir]); // Apache nu rulează ca root: utilizatorul lui trebuie să poată citi și scrie
  const modules = ["mpm_prefork", "authz_core", "mime", "dir", "rewrite", "headers", "filter", "deflate", "env", "setenvif"];
  const config = [
    `ServerRoot "${dir}"`, `Listen 127.0.0.1:${PORT}`, `ServerName 127.0.0.1`, `PidFile "${dir}/apache.pid"`,
    `ErrorLog "${dir}/error.log"`, "LogLevel warn",
    ...modules.map((m) => `LoadModule ${m}_module "${MODULES}/mod_${m}.so"`),
    ...(PHP ? [`LoadModule php_module "${MODULES}/${PHP}"`, "AddHandler application/x-httpd-php .php"] : []),
    ...(root ? ["User www-data", "Group www-data"] : []),
    `DocumentRoot "${site}"`, "DirectoryIndex index.html index.php", "TypesConfig /etc/mime.types",
    `<Directory "${site}">`, "  AllowOverride All", "  Require all granted", "</Directory>",
  ].join("\n");
  writeFileSync(join(dir, "apache.conf"), config);
  if (root) chmodSync(join(dir, "apache.conf"), 0o644);
  server = spawn(APACHE, ["-f", join(dir, "apache.conf"), "-DFOREGROUND"], { stdio: "ignore", detached: true });
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch(`${BASE}/`); await r.arrayBuffer(); if (r.ok) break; } catch { /* încă pornește */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  browser = await require("playwright")[ENGINE].launch();
});

after(async () => {
  await browser?.close();
  if (server) try { process.kill(-server.pid, "SIGKILL"); } catch { /* deja oprit */ } // Apache cu tot cu procesele lui
  if (dir) rmSync(dir, { recursive: true, force: true });
});

// cu node:http, nu cu fetch: fetch nu lasă schimbarea antetului Host
function getWithHost(path, headers) {
  return new Promise((resolve, reject) => {
    http.get({ host: "127.0.0.1", port: PORT, path: `/${path}`, headers }, (res) => {
      res.resume();
      res.on("end", () => resolve({ status: res.statusCode, headers: res.headers }));
    }).on("error", reject);
  });
}

async function get(path, headers = {}) {
  const response = await fetch(`${BASE}/${path}`, { headers, redirect: "manual" });
  const body = await response.text();
  return { status: response.status, headers: response.headers, body };
}

test("Apache: antete de securitate și cache pe pagini și fișiere", { skip: SKIP }, async () => {
  const home = await get("");
  assert.equal(home.status, 200, readFileSync(join(dir, "error.log"), "utf-8"));
  assert.equal(home.headers.get("x-content-type-options"), "nosniff");
  assert.equal(home.headers.get("x-frame-options"), "DENY");
  assert.match(home.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  assert.match(home.headers.get("referrer-policy"), /strict-origin/);
  assert.equal(home.headers.get("cache-control"), "no-cache");
  const css = await get("assets/css/style.css", { "Accept-Encoding": "gzip" });
  assert.match(css.headers.get("cache-control"), /immutable/);
  assert.equal(css.headers.get("content-encoding"), "gzip");
  assert.equal((await get("stories/index.json")).headers.get("cache-control"), "no-cache");
  assert.equal((await get("manifest.webmanifest")).headers.get("content-type"), "application/manifest+json");
});

test("Apache: fișierele ascunse și datele private nu se servesc", { skip: SKIP }, async () => {
  for (const path of [".htaccess", ".ftp-deploy-sync-state.json", "api/data/citiri.json", "api/data/.htaccess"]) {
    assert.equal((await get(path)).status, 403, path);
  }
});

test("Apache: vizitele pe http:// sunt trimise pe https://", { skip: SKIP }, async () => {
  const response = await getWithHost("poveste.html?id=x", { Host: "iamlio.ro" });
  assert.equal(response.status, 301);
  assert.equal(response.headers.location, "https://iamlio.ro/poveste.html?id=x");
  assert.equal((await getWithHost("", { Host: "iamlio.ro", "X-Forwarded-Proto": "https" })).status, 200,
    "în spatele unui proxy HTTPS nu redirecționează la nesfârșit");
});

test("Apache: PHP funcționează (contor, panou fără parolă refuzat)", { skip: SKIP || (!PHP && "PHP pentru Apache nu e instalat") }, async () => {
  const reads = await get("api/citiri.php");
  assert.equal(reads.status, 200, reads.body);
  assert.ok(JSON.parse(reads.body).citiri);
  assert.equal((await get("api/admin.php")).status, 401);
});

test("Apache: biblioteca și o poveste se deschid în browser fără erori și fără încălcări ale politicii", { skip: SKIP }, async () => {
  const p = await (await browser.newContext()).newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  p.on("console", (m) => { if (/Content[ -]Security[ -]Policy/i.test(m.text())) errors.push(m.text()); });
  await p.goto(`${BASE}/`);
  await p.waitForSelector(".story-card");
  await p.goto(`${BASE}/poveste.html?id=${STORY.id}`);
  await p.waitForSelector(".sheet.is-current img");
  assert.ok(await p.$eval(".sheet.is-current img", (img) => img.complete && img.naturalWidth > 0));
  assert.deepEqual(errors, []);
});
