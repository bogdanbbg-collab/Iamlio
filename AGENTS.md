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
  - `assets/css/style.css` — stilurile
  - `stories/<id>/story.json` + `images/` — poveștile
  - `stories/<id>/audio/` și `stories/index.json` — **generate automat, nu le edita**
- `scripts/stories.py` — `validate` | `audio` | `index` | `all`
- `.github/workflows/publica-site.yml` — la fiecare push pe branch-ul principal: validează,
  generează vocea, actualizează biblioteca și urcă `public/` pe host prin FTPS.

## Verificare

```bash
python3 scripts/stories.py validate   # trebuie să afișeze [OK] pentru fiecare poveste
python3 -m http.server -d public 8000 # previzualizare locală la http://localhost:8000
```
