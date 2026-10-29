# Iamlio — Lio îți citește o poveste

Site cu povești ilustrate pentru copii de 3–7 ani, în limba română. Paginile se întorc cu degetul
(swipe) ca într-o carte, iar Lio, puiul de leu, citește povestea cu voce.

## Ce poate face cititorul

- pagini care se întorc ca într-o carte (swipe, atingere, săgeți, tastatură);
- Lio citește cu voce feminină sau masculină, iar **replica citită se evidențiază sincron** cu vocea;
- **Setări de citire** (butonul din dreapta sus): vocea, **viteza** (0,8×–1,1×), Lio dă singur paginile,
  **mod de culcare** (culori calme, imagini mai puțin luminoase, voce mai încetă) și **ecran complet**
  (pe iPhone/iPad: Partajează → „Adaugă pe ecranul principal”, iar site-ul se deschide ca o aplicație);
- **reluarea poveștii**: coperta propune „Continuă” de la pagina la care a rămas copilul;
- **Lio salută** la început și **își ia rămas-bun** la final (altfel la poveștile de culcare decât la aventuri);
  în modul de culcare, la final apare un Lio somnoros;
- **Întrebările lui Lio** după poveste: 1–3 întrebări cu variante ilustrate, citite cu voce, fără punctaj.

## Povești personalizate (cu prenumele copilului)

Cere-i AI-ului, de exemplu: „Fă o poveste personalizată pentru Ana, 4 ani, despre dinozauri” (textul complet e în
`PROMPT_POVESTE.md`). Povestea primește un **link secret** și nu apare în bibliotecă și nici în Google.
**Până o aprobi, nu e publică deloc:** stă pe server într-o zonă protejată și se deschide doar cu parola de
administrator (secretul `ADMIN_PASSWORD`, vezi mai jos), la adresa `poveste.html?previzualizare=<id>` din
`rapoarte/<poveste>.md`. Citește povestea și, dacă e în regulă, spune-i AI-ului „aprobă povestea <id>”. După
publicare, raportul arată link-ul pentru părinți (`poveste.html?id=<id>`). Fără secretul `ADMIN_PASSWORD`,
poveștile neaprobate nu se urcă deloc pe host.
Se folosește doar prenumele copilului. Ca să ștergi o poveste personalizată, șterge-i folderul din
`public/stories/` (sau cere-i AI-ului) — dispare de pe site la următoarea publicare.

Biblioteca are **categorii** (de culcare, aventuri, animale, prietenie și emoții, învățăm, amuzante), **filtre**
după durată (scurte / medii / lungi), **favorite** (♡ pe fiecare poveste) și eticheta „Continuă · pagina N” pentru
poveștile începute. Vârsta nu apare nicăieri pe site (site-ul se prezintă simplu, „povești pentru copii”); regulile
de scriere a poveștilor rămân gândite pentru copiii mici. Filtrele stau în adresa paginii, deci o listă filtrată
(de ex. `/?categorie=de-culcare`) poate fi trimisă cuiva. Filtrele stau strânse sub butonul „Filtre”.

De la trei povești apare butonul **„Lio, alege tu!”** (o poveste la întâmplare, alta decât data trecută). Poveștile
apărute pe site în ultimele 14 zile au eticheta **„Nou”**, iar **„Povestea săptămânii”** (prima în listă) este cea
publicată în ultimele 7 zile sau, dacă nu e niciuna, câte o poveste din bibliotecă pe rând. Data publicării o notează
robotul în `rapoarte/publicari.json` când povestea apare prima oară pe site.

Preferințele rămân doar în browserul de pe dispozitiv (fără conturi).

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
4. generează vocea în română: întâi **Google Chirp 3 HD**, apoi, treptat, **Gemini TTS „povestitorul”** (cu emoție;
   secretul `GEMINI_API_KEY`, cota gratuită de ~10 cereri pe zi, variabila `GEMINI_TTS_DAILY`; workflow-ul zilnic
   reia după reînnoirea cotei, întâi poveștile noi și vocea feminină). Chirp 3 HD (secretul `GOOGLE_TTS_API_KEY`; 1.000.000 de caractere
   gratuite pe lună, limită proprie de 800.000 în variabila `MAX_TTS_CHARS_MONTH`, consumul în
   `rapoarte/buget-voce.md`), **în două variante**: naratoare Sulafat și narator Algieba; Lio și fiecare personaj
   au voce proprie. Fără cheie, peste limită sau dacă Google nu răspunde, se folosește `edge-tts` (gratuit),
   iar la publicarea următoare se încearcă din nou Chirp. Cu **regie de voce** (ton pe fiecare replică, pauze);
   reîncearcă automat la erori de rețea și verifică apoi că există toate fișierele (`scripts/test_voce.py` și
   workflow-ul „Test voce” fac mostre pentru alegerea vocilor);
5. actualizează biblioteca;
6. **testează încă o dată site-ul final** (exact ce se urcă, cu vocile și imaginile noi) în browser; dacă pică,
   nu se publică nimic;
7. urcă site-ul pe host prin **FTPS** (eșuează clar dacă lipsesc datele de conectare);
8. verifică site-ul live (pagina, biblioteca, vocea, contorul, panoul de administrare, protecția datelor).

Fiecare pagină are o politică de securitate a conținutului (CSP): încarcă doar fișiere de pe iamlio.ro, fără
scripturi străine sau scrise direct în pagină. `public/.htaccess` (pentru Apache, ca pe cPanel) adaugă antetele de
securitate, trimite `http://` pe `https://`, blochează fișierele ascunse, comprimă textul și setează cache-ul
(CSS/JS cu amprentă: un an; imaginile și vocile: 30 de zile; paginile și datele: verificate la fiecare vizită).
E testat pe un server Apache real (`tests/e2e/apache.test.mjs`). Dacă schimbi versiunea de PHP din cPanel
(MultiPHP Manager), cPanel scrie câteva rânduri în `.htaccess`: copiază-le și în `public/.htaccess`, altfel
următoarea publicare le șterge.

Regulile sunt legate de proiect pentru orice AI: `AGENTS.md` (ChatGPT Codex și alții), `CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md`, `.cursor/rules/`. Toate trimit la aceleași reguli și la șablonul
`sablon/story.json`. Pentru un chat obișnuit care nu citește singur proiectul, copiază textul din
[`PROMPT_POVESTE.md`](PROMPT_POVESTE.md).

Dacă un fișier audio lipsește totuși pe server, site-ul citește textul cu vocea română a browserului.

## Generarea automată a imaginilor (opțională)

Dacă AI-ul folosit nu poate genera imagini, proiectul le generează singur la publicare, după descrierile din poveste.

Se încearcă, în ordine, variantele configurate; dacă una refuză (cota gratuită e 0 sau s-a terminat), imaginea se
face cu următoarea. Ca să afli ce merge: **Actions → Test generare imagini → Run workflow** generează câte o imagine
de probă cu fiecare variantă și arată rezultatul în rezumat (imaginile apar la Artifacts).

**Gratuit (dacă Google oferă imagini pe nivelul gratuit) — Gemini „Nano Banana”:** cheie din aistudio.google.com
(API Keys → Create API key), pusă în GitHub ca secretul `GEMINI_API_KEY`. Nu lega un cont de plată în Google
AI Studio: cât timp proiectul e pe „Free tier”, nu se plătește nimic. Pornește de la imaginea copertei, deci
personajele rămân identice.

**Gratuit, rezervă — Cloudflare Workers AI:** cont gratuit pe cloudflare.com (fără card). Din panoul Cloudflare
copiezi **Account ID** și creezi un **API token** cu permisiunea „Workers AI” (Read și Edit), apoi le pui în GitHub
ca secretele `CLOUDFLARE_ACCOUNT_ID` și `CLOUDFLARE_API_TOKEN`. Cota gratuită zilnică ajunge pentru câteva povești
pe zi; pe planul gratuit nu se plătește nimic, iar dacă cota se termină, restul imaginilor se fac a doua zi.
Modelul implicit e FLUX.2 klein 4B (se poate schimba cu variabila `CLOUDFLARE_IMAGE_MODEL`): fiecare pagină primește
coperta ca imagine de referință, iar scenele cu Lio și `scripts/referinte/lio.png`, ca personajele să arate la fel;
dacă modelul refuză o cerere, imaginea se face cu FLUX.1 schnell, fără referințe. Merită privită povestea după
publicare. Cota zilei (cam 50 de imagini) se reînnoiește la
00:00 UTC; în fiecare noapte, workflow-ul „Imagini rămase (zilnic)” pornește singur publicarea dacă lipsesc imagini.

**Gratuit, prima variantă — Pollinations:** imaginile ies cele mai frumoase; când nu merge, se folosește Cloudflare. Cont gratuit
pe enter.pollinations.ai (te conectezi cu GitHub), creezi o cheie **secretă** („sk_…”) și o pui în GitHub ca
secretul `POLLINATIONS_API_KEY`. Modelul implicit e Z-Image Turbo (variabila `POLLINATIONS_IMAGE_MODEL`).

**Cu plată — OpenAI:** se folosește doar dacă variantele gratuite nu sunt configurate sau dau eroare.
Dacă AI-ul folosit nu poate genera imagini, proiectul le poate genera singur cu OpenAI:
**Settings → Secrets and variables → Actions → New repository secret** → `OPENAI_API_KEY` (o cheie de la
platform.openai.com; se plătește separat de abonamentul ChatGPT). Opțional, la **Variables**: `IMAGE_MODEL`
(implicit `gpt-image-2`), `IMAGE_QUALITY` (`low` / `medium` / `high`, implicit `medium`), `MAX_IMAGES`
(maximum de imagini pe publicare, implicit 40), `MAX_IMAGES_MONTH` (maximum pe lună calendaristică, implicit 200)
și `MAX_LEI_MONTH` (cât se poate cheltui pe lună, în lei, implicit 100). Costul fiecărei imagini se calculează din
tokenii raportați de OpenAI și prețurile din `scripts/imagini.py` (modificabile cu variabilele `IMAGE_PRICE_TEXT_IN`,
`IMAGE_PRICE_IMAGE_IN`, `IMAGE_PRICE_OUT` — dolari pe 1 milion de tokeni — și `USD_LEI`; verifică-le pe pagina de
prețuri OpenAI). Totalul lunar e în `rapoarte/buget-imagini.md`; suma exactă facturată se vede în contul OpenAI.
Fără cheie, imaginile lipsă apar în raport ca „de corectat”.

## Dacă ceva nu merge după o publicare (revenire)

- **O poveste deja publicată nu dispare** dacă o modificare nouă a ei e greșită: pe site rămâne ultima ei
  versiune bună (din istoricul git), iar raportul ei spune ce e de corectat.
- **Revenire la tot site-ul:** fiecare publicare reușită primește un tag `publicat-AAAALLZZ-OOMMSS`
  (lista: tab-ul **Code → Tags**). În **Actions → Publică site-ul → Run workflow**, scrie tag-ul la „versiune”
  și pornește: se republică exact acea versiune, fără să se modifice nimic în repository. Pentru a anula definitiv
  o modificare: **Revert** pe commit-ul cu problema (sau `git revert <commit>` și push).

## Panoul de administrare

`https://iamlio.ro/admin.html`, cu parola din secretul `ADMIN_PASSWORD` (aceeași deschide și previzualizarea
poveștilor personalizate). Arată: vizitatorii și paginile afișate pe zi, poveștile deschise pe zi și clasamentul
lor, biblioteca pe categorii, ce e de rezolvat (povești nepublicate, personalizate care așteaptă aprobarea),
erorile din browserele vizitatorilor și de pe server (ultimele 14 zile) și versiunea publicată.
Statisticile sunt doar totaluri pe zi, fără cookie-uri pentru vizitatori și fără adrese IP; vizitele tale, cât
ești autentificat, nu se numără. Sesiunea durează 12 ore; după 10 parole greșite într-o oră, încercările se blochează.

## Monitorizare

Workflow-ul **Monitorizare site** verifică site-ul live în fiecare oră (pagina, biblioteca, o poveste, ambele
voci, contorul, previzualizarea protejată și protecția datelor; fiecare adresă cu codul HTTP, tipul și conținutul ei). Dacă ceva nu merge, deschide un issue în GitHub (primești email); când site-ul
își revine, issue-ul se închide singur.

## Protecția branch-ului `master`

Recomandat: **Settings → Rules → Rulesets → New branch ruleset**, țintă `master`, cu **Restrict deletions** și
**Block force pushes** activate. Nu activa „Require a pull request”: ar bloca robotul care salvează vocile și
AI-urile care publică direct. Calitatea e păzită de verificările obligatorii: publicarea pornește doar de pe
`master` și doar dacă testele trec, iar poveștile greșite nu ajung pe site.

## Contorul „citită de X ori”

`public/api/citiri.php` numără de câte ori a fost deschisă fiecare poveste: o dată pe sesiune de browser
și, pe server, cel mult o dată la 30 de minute pe adresă și poveste (maximum 120 pe oră de la aceeași adresă,
ca o grădiniță sau o familie cu aceeași rețea să nu fie limitată). Scrierea e atomică, iar în
`api/data/copii/` se păstrează o copie zilnică a numerelor (ultimele 14 zile).
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
| `ADMIN_PASSWORD` | o parolă lungă, doar a ta | pentru panoul de administrare și previzualizarea poveștilor personalizate |

Apoi rulează din nou workflow-ul **Publică site-ul** din tab-ul **Actions** (sau fă orice push).

## Previzualizare locală

```bash
python3 scripts/stories.py validate
python3 scripts/stories.py index
php -S localhost:8000 -t public      # sau: python3 -m http.server -d public 8000 (fără contor)
```

Deschide http://localhost:8000.
