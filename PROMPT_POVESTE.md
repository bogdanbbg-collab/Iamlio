# Cum ceri o poveste nouă (text de copiat)

Unele AI-uri (Codex, Claude Code, Gemini CLI, Copilot, Cursor) citesc singure regulile din proiect.
Pentru un chat obișnuit (ChatGPT, Gemini, Claude pe web sau pe telefon) conectat la repository,
**copiază textul de mai jos** și înlocuiește doar ultima linie.

---

```
Lucrezi în repository-ul GitHub bogdanbbg-collab/Iamlio (branch master), site-ul de povești pentru copii Iamlio.

Înainte de orice, citește ÎNTREG fișierele AGENTS.md și REGULI_POVESTI.md și respectă-le întocmai,
mai ales „Fluxul de lucru (obligatoriu)” și secțiunea „Ce verifică automat proiectul”.
Pornește de la sablon/story.json și uită-te la exemplul public/stories/lio-si-steluta-cazatoare/story.json.

Pe scurt, povestea trebuie:
- să fie pentru copii de 3–7 ani, în română corectă cu diacritice, cu imaginație, ceva util de învățat,
  cel puțin două momente amuzante și final fericit, liniștitor;
- să dureze cât cer mai jos (implicit 4–6 minute; oricum între 2 și 10 minute);
- să aibă câte o imagine pe pagină plus copertă, în stilul Iamlio (film de animație 3D pentru copii),
  care arată exact ce se întâmplă pe pagină, cu personaje identice pe toate paginile și fără text în imagine;
- să aibă regie de voce (narration) pe fiecare pagină și profil de voce pentru personajele care vorbesc;
- să aibă autoevaluarea (review) completată cinstit.

Generează textul și imaginile, salvează-le în public/stories/<id>/ (story.json + images/), verifică lista
din REGULI_POVESTI.md, apoi fă commit pe master. Nu genera fișiere audio și nu modifica index.json.
După 3–5 minute citește rapoarte/<id>.md: dacă scrie NEPUBLICATĂ, corectează tot ce e la „De corectat”
și fă din nou commit, până când scrie PUBLICATĂ.
La final spune-mi titlul, durata estimată și ce ai adaptat din cererea mea (dacă ai adaptat ceva).

Povestea: <AICI scrii ce vrei, de ex.: „o poveste de 5 minute despre un arici care învață să numere stelele”>
```

---

După commit, proiectul repară automat ce poate, generează vocea și publică. Starea fiecărei povești e în
`rapoarte/<id>.md`. Dacă AI-ul s-a oprit înainte să fie publicată, scrie-i doar:
„Citește rapoarte/<id>.md și corectează până când povestea e publicată.”
