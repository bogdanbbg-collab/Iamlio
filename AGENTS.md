# Iamlio — instrucțiuni pentru agenți AI

Iamlio („I Am Lio”) este un site static cu povești ilustrate pentru copii de 3–7 ani, în limba română.
Lio, un pui de leu, „citește” poveștile cu voce, iar paginile se întorc ca într-o carte.

## Regula principală

**Înainte să creezi sau să modifici o poveste, citește `REGULI_POVESTI.md` și respectă-l întocmai.**
Regulile se aplică oricărui AI (ChatGPT, Claude, Gemini etc.). Când utilizatorul spune
„fă o poveste despre …”, urmează secțiunea „Fluxul de lucru” din acel fișier.

## Structura proiectului

- `public/` — tot ce se urcă pe host (site-ul propriu-zis)
  - `index.html` + `assets/js/library.js` — biblioteca de povești
  - `poveste.html` + `assets/js/reader.js` — cititorul cu întoarcere de pagină și voce
  - `assets/js/iamlio.js` — funcții comune (vocea aleasă, contorul de citiri, Lio animat)
  - `assets/css/style.css` — stilurile (responsive: telefon, tabletă, calculator)
  - `assets/img/lio*.svg`, `favicon.svg` — Lio, generat din `scripts/lio_svg.py` (nu edita SVG-urile de mână)
  - `assets/lio-replici.json` — ce spune Lio când e atins pe pagina principală
  - `api/citiri.php` — contorul „citită de X ori” (PHP; datele stau în `api/data/citiri.json`, care nu se urcă din repo)
  - `stories/<id>/story.json` + `images/` — poveștile
  - `stories/<id>/audio/{feminin,masculin}/`, `assets/audio/` și `stories/index.json` — **generate automat, nu le edita**
- `scripts/stories.py` — `validate` | `audio` (ambele voci) | `index` | `all`
- `.github/workflows/publica-site.yml` — la fiecare push pe branch-ul principal: validează,
  generează vocea, actualizează biblioteca și urcă `public/` pe host prin FTPS.

## Verificare

```bash
python3 scripts/stories.py validate   # trebuie să afișeze [OK] pentru fiecare poveste
php -S localhost:8000 -t public       # previzualizare locală (cu contor) la http://localhost:8000
```
