# Iamlio — instrucțiuni pentru agenți AI

Iamlio („I Am Lio”) este un site static cu povești ilustrate pentru copii de 3–7 ani, în limba română.
Lio, un pui de leu, „citește” poveștile cu voce (feminină sau masculină), iar paginile se întorc ca într-o carte.

## Regula principală

**Orice poveste — indiferent de AI-ul care o creează — trebuie să respecte `REGULI_POVESTI.md`.**
Citește fișierul **întreg** înainte de a scrie ceva și urmează pas cu pas „Fluxul de lucru (obligatoriu)”
de la secțiunea 10. Secțiunea 9 spune exact ce respinge verificarea automată. Dacă cererea utilizatorului nu respectă regulile, adapteaz-o la reguli și spune ce ai schimbat.

Pe scurt, o poveste Iamlio:
- durează **2–10 minute** (6–24 de pagini, 20–70 de cuvinte pe pagină);
- are **imaginație**, **ceva folositor de învățat** (`learning`), **umor** și un **final fericit**;
- are **1–3 categorii** (`categories`: de-culcare, aventuri, animale, prietenie, invatam, amuzante);
- are, ideal, **1–2 întrebări ale lui Lio** după poveste (`questions`, cu variante ilustrate — secțiunea 8);
- dacă e **personalizată** (cu prenumele unui copil): `stories.py new "Titlu" --pentru Prenume`, **doar prenumele**,
  `"approved": false` — o aprobă doar proprietarul site-ului (secțiunea 8, „Povești personalizate”);
- are **imagini în stil de film de animație 3D pentru copii**, câte una pe pagină, care arată **exact** ce
  se întâmplă pe pagină, cu personaje identice de la o pagină la alta și fără text în imagine;
- poate folosi **personaje cunoscute** doar dacă utilizatorul le cere, desenate fidel (secțiunea 5);
- are o **autoevaluare cinstită** (`review`): imaginație, învățătură, cel puțin două momente amuzante cu pagina lor,
  emoție, siguranță, imagini, voce;
- are **animație pe fiecare pagină** (`animation`: mișcarea camerei și un efect potrivit cu scena — secțiunea 6);
- are **regie de voce** scrisă de tine (`narration` pe fiecare pagină, `voice` pentru personaje — secțiunea 7);
  fișierele audio (feminin și masculin) **nu** le generezi tu, se generează automat.

## Ce produci

Pornești **întotdeauna** de la șablon: `python3 scripts/stories.py new "Titlul poveștii"` (sau copiezi
`sablon/story.json`). Stilul imaginilor și Lio sunt deja completate corect; completezi tot ce e `DE COMPLETAT`.
Model complet: `public/stories/lio-si-steluta-cazatoare/story.json`.

- `public/stories/<id>/story.json` — după formatul din `REGULI_POVESTI.md`, secțiunea 8;
- `public/stories/<id>/images/coperta.*` și `pagina-NN.*` — imaginile generate (png/jpg/webp).

Apoi rulezi `python3 scripts/stories.py prepare` sau `validate` (trebuie să afișeze `[OK]`), faci commit și push
pe `master`. GitHub Actions repară automat ce e mecanic, generează imaginile lipsă (dacă e activat), optimizează,
verifică, generează vocile, actualizează biblioteca și urcă site-ul pe host prin FTPS.

**Treaba ta nu s-a terminat la commit.** După 3–5 minute, preia ultima versiune din repository și citește
`rapoarte/<id>.md`. Dacă scrie **NEPUBLICATĂ**, corectează tot ce e la „De corectat” și fă din nou commit —
repetă până când raportul spune **PUBLICATĂ**. Dacă nu poți aștepta, spune-i utilizatorului să-ți ceară
„verifică raportul poveștii” peste câteva minute.

**Apoi te uiți la fiecare imagine și te autocorectezi singur** (`REGULI_POVESTI.md`, secțiunea 10, „Autocorectarea
imaginilor”): o imagine care contrazice textul se reface, nu povestea. Rescrii `imagePrompt` concret (ce se vede,
nu „fără X”), pui `"imageVariant": 1, 2, 3…`, ștergi imaginea și faci commit; cel mult trei încercări pe imagine.
Nu ceri voie pentru asta; la final spui ce ai refăcut.

**Id-ul unei povești e permanent.** După ce o poveste a fost publicată, nu redenumi folderul ei (adresa
`poveste.html?id=…` ar înceta să funcționeze); poți schimba titlul din `story.json`, dar nu și id-ul.

## Ce NU modifici

`public/stories/index.json`, folderele `audio/`, `public/assets/audio/`, `rapoarte/` (generate automat) și
codul site-ului (`public/*.html`, `public/assets/`, `scripts/`, `.github/`) — decât dacă ți se cere explicit.

## Structura proiectului

- `public/` — tot ce se urcă pe host (site-ul propriu-zis)
  - `index.html` + `assets/js/library.js` — biblioteca de povești
  - `poveste.html` + `assets/js/reader.js` — cititorul cu întoarcere de pagină și voce
  - `assets/js/iamlio.js` — funcții comune (vocea aleasă, contorul de citiri, Lio animat)
  - `assets/css/style.css` — stilurile (responsive: telefon, tabletă, calculator)
  - `assets/img/lio*.svg`, `favicon.svg` — Lio, generat din `scripts/lio_svg.py` (nu edita SVG-urile de mână)
  - `assets/lio-replici.json` — ce spune Lio când e atins pe pagina principală
  - `api/citiri.php` — contorul „citită de X ori” (PHP; datele stau în `api/data/citiri.json` pe server)
  - `admin.html` + `assets/js/admin.js` + `api/admin.php` — panoul de administrare (vizite, citiri, erori, consum și cote; parola
    `ADMIN_PASSWORD`); `api/vizita.php` și `api/erori.php` primesc vizitele și erorile (doar totaluri, fără date personale)
  - `api/previzualizare.php` — previzualizarea poveștilor personalizate neaprobate, cu aceeași parolă (`comun.php`: funcții comune)
  - `.htaccess` — setările serverului Apache: securitate, HTTPS, cache, compresie (testat în `tests/e2e/apache.test.mjs`)
  - `p/<id>.html` (generat la publicare) — pagina statică a fiecărei povești (pentru Google, AI și distribuire): titlu,
    rezumat, ce învață copilul, textul complet, date structurate și copertă (Open Graph); stil în `assets/css/pagina.css`
  - `sitemap.xml`, `robots.txt`, `llms.txt`, `llms-full.txt` (generate la publicare de `scripts/seo.py`)
  - `stories/<id>/` — poveștile
- `scripts/stories.py` — `optimize` | `validate` | `audio` (ambele voci) | `verify-audio` | `index` | `all`
- `scripts/seo.py` — tot ce ajută la găsirea în Google și în asistenții AI (paginile statice, sitemap, llms.txt,
  datele structurate; codurile de verificare din variabilele `GOOGLE_SITE_VERIFICATION` și `BING_SITE_VERIFICATION`)
- `scripts/canon.py` — valorile oficiale: stilul imaginilor, descrierea și vocea lui Lio, câmpurile `review`
- `sablon/story.json` — șablonul de poveste (generat din `canon.py` cu `python3 scripts/stories.py template`)
- `scripts/pregatire.py` — repararea automată a poveștilor (`stories.py prepare`)
- `scripts/imagini.py` — generarea automată a imaginilor lipsă, în ordine: Gemini (`GEMINI_API_KEY`), Pollinations
  (`POLLINATIONS_API_KEY`), Cloudflare Workers AI (`CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`), OpenAI cu plată
  (`OPENAI_API_KEY`);
  `python3 scripts/imagini.py test` (sau workflow-ul „Test generare imagini”) arată care merge
- `rapoarte/` — raportul fiecărei povești după publicare (PUBLICATĂ / NEPUBLICATĂ și ce e de corectat)
- `scripts/consum.py` — consumul serviciilor (voci, imagini, GitHub Actions, spațiu) pentru panoul de administrare
- `scripts/voce.py` — regia de voce (Google Chirp 3 HD, rezervă edge-tts; tonuri, profiluri de personaj, pauze, lipirea cu ffmpeg)
- `tests/` — teste automate (`python3 -m unittest discover -s tests`) și teste în browser
  (`python3 scripts/stories.py stage && node --test tests/e2e/*.test.mjs`, inclusiv accesibilitatea cu axe-core),
  rulate la fiecare publicare
- `.github/workflows/publica-site.yml` — publicarea automată (și revenirea la o versiune anterioară)
- `.github/workflows/monitorizare.yml` — verificarea site-ului live în fiecare oră
- `public/confidentialitate.html` — informarea pentru părinți despre date
- `requirements.lock`, `package-lock.json` — versiunile exacte ale tuturor dependențelor (`.github/dependabot.yml`
  propune lunar actualizări, ca pull request-uri verificate de teste)

## Verificare și previzualizare

```bash
python3 scripts/stories.py validate   # trebuie să afișeze [OK] pentru fiecare poveste
python3 -m unittest discover -s tests # testele automate
php -S localhost:8000 -t public       # previzualizare locală (cu contor) la http://localhost:8000
```
