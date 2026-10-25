# Iamlio — Lio îți citește o poveste

Site cu povești ilustrate pentru copii de 3–7 ani, în limba română. Paginile se întorc cu degetul
(swipe) ca într-o carte, iar Lio, puiul de leu, citește povestea cu voce.

## Cum adaugi o poveste

Spune-i AI-ului conectat la acest repository (ChatGPT, Claude etc.):

> Fă o poveste despre un arici care învață să împartă.

AI-ul trebuie să respecte [`REGULI_POVESTI.md`](REGULI_POVESTI.md) (fișierul [`AGENTS.md`](AGENTS.md)
îl trimite automat acolo). El scrie textul, generează imaginile și le salvează în
`public/stories/<id>/`. După push, GitHub Actions face restul:

1. verifică povestea după reguli;
2. generează vocea în română cu `edge-tts` (gratuit; voce caldă `ro-RO-AlinaNeural` sau `ro-RO-EmilNeural`);
3. actualizează biblioteca;
4. urcă site-ul pe host prin **FTPS**.

Dacă fișierele audio lipsesc, site-ul citește textul cu vocea română a browserului.

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
python3 -m http.server -d public 8000
```

Deschide http://localhost:8000.
