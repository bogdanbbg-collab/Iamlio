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
- are **imagini în stil de film de animație 3D pentru copii**, câte una pe pagină, care arată **exact** ce
  se întâmplă pe pagină, cu personaje identice de la o pagină la alta și fără text în imagine;
- poate folosi **personaje cunoscute** doar dacă utilizatorul le cere, desenate fidel (secțiunea 5);
- are o **autoevaluare cinstită** (`review`): imaginație, învățătură, cel puțin două momente amuzante cu pagina lor,
  emoție, siguranță, imagini, voce;
- are **regie de voce** scrisă de tine (`narration` pe fiecare pagină, `voice` pentru personaje — secțiunea 7);
  fișierele audio (feminin și masculin) **nu** le generezi tu, se generează automat.

## Ce produci

Pornești **întotdeauna** de la șablon: `python3 scripts/stories.py new "Titlul poveștii"` (sau copiezi
`sablon/story.json`). Stilul imaginilor și Lio sunt deja completate corect; completezi tot ce e `DE COMPLETAT`.
Model complet: `public/stories/lio-si-steluta-cazatoare/story.json`.

- `public/stories/<id>/story.json` — după formatul din `REGULI_POVESTI.md`, secțiunea 8;
- `public/stories/<id>/images/coperta.*` și `pagina-NN.*` — imaginile generate (png/jpg/webp).

Apoi rulezi `python3 scripts/stories.py validate` (trebuie să afișeze `[OK]`), faci commit și push pe `master`.
GitHub Actions optimizează imaginile, verifică povestea, generează vocile, actualizează biblioteca
și urcă site-ul pe host prin FTPS.

## Ce NU modifici

`public/stories/index.json`, folderele `audio/`, `public/assets/audio/` (generate automat) și
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
  - `stories/<id>/` — poveștile
- `scripts/stories.py` — `optimize` | `validate` | `audio` (ambele voci) | `verify-audio` | `index` | `all`
- `scripts/canon.py` — valorile oficiale: stilul imaginilor, descrierea și vocea lui Lio, câmpurile `review`
- `sablon/story.json` — șablonul de poveste (generat din `canon.py` cu `python3 scripts/stories.py template`)
- `scripts/voce.py` — regia de voce (tonuri, profiluri de personaj, pauze, lipirea cu ffmpeg)
- `tests/` — teste automate (`python3 -m unittest discover -s tests`), rulate la fiecare publicare
- `.github/workflows/publica-site.yml` — publicarea automată

## Verificare și previzualizare

```bash
python3 scripts/stories.py validate   # trebuie să afișeze [OK] pentru fiecare poveste
python3 -m unittest discover -s tests # testele automate
php -S localhost:8000 -t public       # previzualizare locală (cu contor) la http://localhost:8000
```
