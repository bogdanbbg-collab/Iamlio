# Iamlio — Lio îți citește o poveste

Site cu povești ilustrate pentru copii de 3–7 ani, în limba română. Paginile se întorc cu degetul
(swipe) ca într-o carte, iar Lio, puiul de leu, citește povestea cu voce.

## Cum adaugi o poveste

Spune-i AI-ului conectat la acest repository (ChatGPT, Claude, Gemini etc.), de exemplu:

> Fă o poveste de 5 minute despre un arici care învață să numere stelele.
>
> Fă o poveste cu Scufița Roșie în care Lio o ajută să găsească drumul.

Orice AI trebuie să urmeze [`REGULI_POVESTI.md`](REGULI_POVESTI.md) (fișierul [`AGENTS.md`](AGENTS.md) îl
trimite automat acolo). Regulile cer: 2–10 minute, imaginație, ceva de învățat, umor, final fericit și imagini
în stil de film de animație 3D pentru copii, fidele textului și personajelor. AI-ul scrie textul, generează
imaginile și le salvează în `public/stories/<id>/`. După push, GitHub Actions face restul:

1. rulează testele automate: Python, PHP și **teste în browser** (Chromium real: navigare, swipe, voce,
   contor, telefon/tabletă/calculator, mișcare redusă); publicarea pornește doar de pe `master` și doar dacă
   testele trec;
2. **repară automat** ce e mecanic (diacritice, stil, personaje în prompturi, Lio, regie și voci de personaje,
   nume de fișiere și foldere) și **generează imaginile lipsă** dacă e activat generatorul (vezi mai jos);
3. optimizează imaginile (WebP, 1536×1024) și verifică povestea după reguli; scrie raportul
   `rapoarte/<poveste>.md` (**PUBLICATĂ** / **NEPUBLICATĂ** și ce e de corectat) — o poveste care nu trece
   **nu ajunge pe site**, dar nu le oprește pe celelalte;
4. generează vocea în română cu `edge-tts` (gratuit), **în două variante**: feminină (`ro-RO-AlinaNeural`)
   și masculină (`ro-RO-EmilNeural`), cu **regie de voce** (ton pe fiecare replică, voci de personaje, pauze);
   reîncearcă automat la erori de rețea și verifică apoi că există toate fișierele;
5. actualizează biblioteca;
6. urcă site-ul pe host prin **FTPS** (eșuează clar dacă lipsesc datele de conectare);
7. verifică site-ul live (pagina, biblioteca, vocea, contorul, protecția datelor).

Regulile sunt legate de proiect pentru orice AI: `AGENTS.md` (ChatGPT Codex și alții), `CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`, `.cursor/rules/`. Toate trimit la aceleași reguli și la șablonul
`sablon/story.json`. Pentru un chat obișnuit care nu citește singur proiectul, copiază textul din
[`PROMPT_POVESTE.md`](PROMPT_POVESTE.md).

Dacă un fișier audio lipsește totuși pe server, site-ul citește textul cu vocea română a browserului.

## Generarea automată a imaginilor (opțională)

Dacă AI-ul folosit nu poate genera imagini, proiectul le poate genera singur cu OpenAI:
**Settings → Secrets and variables → Actions → New repository secret** → `OPENAI_API_KEY` (o cheie de la
platform.openai.com; se plătește separat de abonamentul ChatGPT). Opțional, la **Variables**: `IMAGE_MODEL`
(implicit `gpt-image-2`), `IMAGE_QUALITY` (`low` / `medium` / `high`, implicit `medium`), `MAX_IMAGES`
(maximum de imagini pe publicare, implicit 40), `MAX_IMAGES_MONTH` (maximum pe lună calendaristică, implicit 200;
contorul lunar stă în `rapoarte/buget-imagini.json`). Fără cheie, imaginile lipsă apar în raport ca „de corectat”.

## Dacă ceva nu merge după o publicare (revenire)

- **O poveste deja publicată nu dispare** dacă o modificare nouă a ei e greșită: pe site rămâne ultima ei
  versiune bună (din istoricul git), iar raportul ei spune ce e de corectat.
- **Revenire la tot site-ul:** fiecare publicare reușită primește un tag `publicat-AAAALLZZ-OOMMSS`
  (lista: tab-ul **Code → Tags**). În **Actions → Publică site-ul → Run workflow**, scrie tag-ul la „versiune”
  și pornește: se republică exact acea versiune, fără să se modifice nimic în repository. Pentru a anula definitiv
  o modificare: **Revert** pe commit-ul cu problema (sau `git revert <commit>` și push).

## Monitorizare

Workflow-ul **Monitorizare site** verifică site-ul live la fiecare 6 ore (pagina, biblioteca, o poveste, vocea,
contorul și protecția datelor). Dacă ceva nu merge, deschide un issue în GitHub (primești email); când site-ul
își revine, issue-ul se închide singur.

## Protecția branch-ului `master`

Recomandat: **Settings → Rules → Rulesets → New branch ruleset**, țintă `master`, cu **Restrict deletions** și
**Block force pushes** activate. Nu activa „Require a pull request”: ar bloca robotul care salvează vocile și
AI-urile care publică direct. Calitatea e păzită de verificările obligatorii: publicarea pornește doar de pe
`master` și doar dacă testele trec, iar poveștile greșite nu ajung pe site.

## Contorul „citită de X ori”

`public/api/citiri.php` numără de câte ori a fost deschisă fiecare poveste: o dată pe sesiune de browser
și, pe server, cel mult o dată la 30 de minute pe adresă și poveste (maximum 30 pe oră de la aceeași adresă).
Adresa IP nu se salvează: se păstrează cel mult o oră doar amprente HMAC cu o cheie secretă generată pe server
(`api/data/cheie.txt`) și schimbată zilnic. Detalii pentru părinți: `public/confidentialitate.html`.
Site-ul nu încarcă nimic de la alte companii (nici fonturi), fără cookie-uri, reclame sau programe de analiză.
Are nevoie de **PHP pe host** (orice hosting obișnuit cu cPanel are). Numerele se salvează în
`public/api/data/citiri.json` pe server; fișierul nu e în repository și nu e suprascris la publicare.
Dacă hostul nu are PHP, site-ul funcționează normal, doar fără contor.

## Conectarea la host (FTPS)

În GitHub: **Settings → Secrets and variables → Actions → New repository secret** și adaugă:

| Secret | Exemplu | Obligatoriu |
| --- | --- | --- |
| `FTP_SERVER` | `ftp.domeniul-tau.ro` | da |
| `FTP_USERNAME` | `user@domeniul-tau.ro` | da |
| `FTP_PASSWORD` | parola contului FTP | da |
| `FTP_SERVER_DIR` | `public_html/` (cu `/` la final) | nu (implicit `./`) |
| `FTP_PORT` | `21` | nu |

Apoi rulează din nou workflow-ul **Publică site-ul** din tab-ul **Actions** (sau fă orice push).

## Previzualizare locală

```bash
python3 scripts/stories.py validate
python3 scripts/stories.py index
php -S localhost:8000 -t public      # sau: python3 -m http.server -d public 8000 (fără contor)
```

Deschide http://localhost:8000.
