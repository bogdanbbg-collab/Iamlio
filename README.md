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

1. rulează testele automate (Python, JavaScript, PHP);
2. optimizează imaginile (WebP, 1536×1024);
3. verifică povestea după reguli (durată, structură, câmpuri, prompturi de imagine, regie de voce, diacritice) —
   **orice eroare oprește publicarea**;
4. generează vocea în română cu `edge-tts` (gratuit), **în două variante**: feminină (`ro-RO-AlinaNeural`)
   și masculină (`ro-RO-EmilNeural`), cu **regie de voce** (ton pe fiecare replică, voci de personaje, pauze);
   reîncearcă automat la erori de rețea și verifică apoi că există toate fișierele;
5. actualizează biblioteca;
6. urcă site-ul pe host prin **FTPS** (eșuează clar dacă lipsesc datele de conectare);
7. verifică site-ul live (pagina, biblioteca, vocea, contorul, protecția datelor).

Dacă AI-ul nu citește singur fișierele din repository, începe cererea cu:
„Citește întâi REGULI_POVESTI.md din repository-ul Iamlio și respectă-l întocmai.”

Dacă un fișier audio lipsește totuși pe server, site-ul citește textul cu vocea română a browserului.

## Dacă ceva nu merge după o publicare (revenire)

Fiecare publicare corespunde unui commit. Ca să revii la versiunea anterioară: în GitHub, deschide commit-ul
cu problema → **Revert** (sau `git revert <commit>` și push). Workflow-ul publică automat versiunea corectă.

## Contorul „citită de X ori”

`public/api/citiri.php` numără de câte ori a fost deschisă fiecare poveste: o dată pe sesiune de browser
și, pe server, cel mult o dată la 30 de minute pentru același vizitator (fără să păstreze adresa IP).
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
