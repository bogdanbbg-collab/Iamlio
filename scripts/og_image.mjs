// Imaginea care apare când cineva trimite un link spre iamlio.ro (Open Graph, 1200×630):
// public/assets/img/og-image.png. Rulare: node scripts/og_image.mjs
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(ROOT, "package.json"));
const { chromium } = require("playwright");

const lio = readFileSync(join(ROOT, "public/assets/img/lio-static.svg"), "utf-8");
const font = (name) => `data:font/woff2;base64,${readFileSync(join(ROOT, "public/assets/fonts", name)).toString("base64")}`;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: "Baloo 2"; src: url(${font("baloo2-latin.woff2")}) format("woff2"); font-weight: 400 800; }
@font-face { font-family: "Baloo 2"; src: url(${font("baloo2-latin-ext.woff2")}) format("woff2"); font-weight: 400 800;
  unicode-range: U+0100-024F, U+0259, U+1E00-1EFF, U+2020, U+20A0-20AB, U+20AD-20CF, U+2113, U+2C60-2C7F, U+A720-A7FF; }
html, body { margin: 0; width: 1200px; height: 630px; overflow: hidden; }
body { display: flex; align-items: center; gap: 56px; padding: 0 80px 0 120px; box-sizing: border-box; font-family: "Baloo 2", sans-serif;
  background: radial-gradient(circle at 12% 10%, #FFE9C7 0, transparent 45%), radial-gradient(circle at 92% 75%, #DDF3EE 0, transparent 45%), #FFF8EC; }
.lio { width: 380px; flex: 0 0 auto; } .lio svg { width: 100%; height: auto; display: block; }
h1 { margin: 0; font-size: 104px; line-height: 1; color: #2B2D42; font-weight: 800; } h1 span { color: #E88A3C; }
h2 { margin: 18px 0 0; font-size: 46px; line-height: 1.1; color: #2B2D42; font-weight: 700; }
p { margin: 18px 0 0; font-size: 31px; line-height: 1.4; color: #5C5F7A; font-weight: 600; }
</style></head><body><div class="lio">${lio}</div><div>
<h1>I am <span>Lio</span></h1><h2>Lio îți citește o poveste</h2><p>Povești ilustrate și citite cu voce,<br>pentru copii</p>
</div></body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(html);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: join(ROOT, "public/assets/img/og-image.png") });
await browser.close();
console.log("public/assets/img/og-image.png");
