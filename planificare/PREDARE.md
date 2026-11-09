# Predare: cum continui povestea zilei (pentru orice asistent AI)

Acest document e pentru un asistent AI (ChatGPT, Gemini, Claude sau altul) care preia proiectul **Iamlio**:
site-ul **iamlio.ro**, cu povești ilustrate pentru copii de 3–7 ani, în limba română, din repository-ul GitHub
**bogdanbbg-collab/Iamlio**. Urmează pașii **în ordine**. Proprietarul site-ului nu vrea să fie întrebat la fiecare
pas: decizi singur după regulile de mai jos și îi scrii doar rezumatul.

Regulile de bază sunt în `AGENTS.md`, `REGULI_POVESTI.md` și `planificare/RUTINA.md`. Citește-le **întregi** înainte
de orice; au întâietate față de acest document. Aici e doar ordinea pașilor și ce ai de programat.

---

## Etapa 1 — o singură dată, la preluare

1. **Verifică ce poți face.** Ai nevoie de toate patru:
   - acces de scriere la repository: poți face commit și push pe `master`, sau măcar poți deschide pull request-uri;
   - poți rula comenzi în repository (`python3`, `git`);
   - poți **deschide și privi imagini** (fișierele `.webp` și `.png` din `public/stories/<id>/`);
   - poți rula singur o sarcină zilnică, programată.

   Dacă îți lipsește ceva, **te oprești** și îi spui proprietarului exact ce lipsește. Nu publici o poveste ale
   cărei imagini nu le-ai văzut.

2. **Verifică să nu lucreze alt asistent în paralel.** Rulează
   `git log --since="2 days ago" --format="%ad %s" --date=short | grep "Povestea zilei"`. Dacă vezi povești noi din
   ultimele două zile, scrise de altcineva, îi spui proprietarului că mai rulează o rutină. Doi asistenți care scriu
   povești în paralel se încurcă la teme și la commit-uri. Alt asistent se oprește doar când îi spune proprietarul.

3. **Pregătește mediul:** `pip install -r requirements.lock` (pentru `stories.py`). Apoi rulează
   `python3 scripts/stories.py status` și `python3 scripts/stories.py validate`, ca să vezi starea poveștilor.

4. **Programează rutina zilnică**, dacă unealta ta poate: în fiecare zi la **06:05, ora României**, cu instrucțiunea:
   > Fă rutina zilnică din `planificare/PREDARE.md`, etapa 2, în repository-ul bogdanbbg-collab/Iamlio.

   Dacă unealta ta nu poate programa, îi spui proprietarului. El îți va scrie în fiecare dimineață:
   „fă rutina zilnică din PREDARE.md”.

5. Fă **o dată etapa 2 acum**, ca să verifici că totul merge. Apoi îi scrii proprietarului ce ai programat și la ce oră.

---

## Etapa 2 — rutina zilnică

Urmezi `planificare/RUTINA.md` pas cu pas. Pe scurt:

1. **Preia ultima versiune:** `git pull` pe `master`. Recitește `AGENTS.md`, `REGULI_POVESTI.md` și
   `planificare/RUTINA.md`; s-ar putea să se fi schimbat.

2. **Termină ce a rămas din zilele trecute.** Pentru fiecare poveste cu `"verified": false` care **nu** are
   `"imaginiInPauza": true`, verifici imaginile ca la pasul 8 și o termini.

3. **Alege tema.** Iei prima temă cu `"poveste": null` din `planificare/teme.json`. O singură poveste nouă pe zi.

4. **Adaptează tema** la regulile pentru imaginile gratuite din `RUTINA.md`, secțiunea 3:
   - 8–9 pagini;
   - doar Lio și 1–2 personaje animale, plante sau obiecte magice; fără oameni și fără copii (copilul din temă devine
     un animal);
   - în imagini, fără ore pe ceas, fără numere exacte de obiecte, fără oglinzi și fără guri de aproape;
   - obiectele cu față se descriu ca obiecte obișnuite.

5. **Scrie povestea.** Pornești de la șablon: `python3 scripts/stories.py new "Titlu"`. Completezi tot ce e
   `DE COMPLETAT`: textul, `narration` (regia de voce), `animation`, `characters`, prompturile de imagine în engleză,
   `questions` și un `review` cinstit. Respecți întocmai `REGULI_POVESTI.md`. Model complet:
   `public/stories/lio-si-steluta-cazatoare/story.json`.

6. **Verifică textul separat.** Fă o trecere separată, ca un verificator care **nu** a scris povestea: dacă poți, o
   conversație sau un agent nou. Verifică după „Lista de verificare” din `REGULI_POVESTI.md`, secțiunea 10, plus:
   - siguranța: nimic de imitat periculos, nimic înfricoșător înainte de culcare;
   - sfaturile corecte pentru copii;
   - româna (ș/ț cu virgulă, linia de dialog „—”);
   - prompturile de imagine.

   Corectezi tot ce e întemeiat.

7. **Validează și publică.** `python3 scripts/stories.py validate` trebuie să arate pentru povestea nouă doar
   „imaginea nu există”. Pui `"poveste": "<id>"` la tema folosită în `teme.json`. Faci commit
   („Povestea zilei <nr>: <titlu>”) și push pe `master`.

8. **Verifică imaginile, după publicare.**
   - Aștepți commit-ul robotului „Povești pregătite automat…” (cam 10–15 minute), apoi faci `git pull` și citești
     `rapoarte/<id>.md`.
   - Dacă raportul arată eroarea Cloudflare **4006** (cota zilnică de imagini): peste o oră pornești din nou
     publicarea (workflow-ul `publica-site.yml`, „Run workflow”), de cel mult trei ori. Ce rămâne termini mâine.
   - Te uiți întâi la **fișele personajelor** (`public/stories/<id>/personaje/*.png`), apoi la **fiecare** imagine (copertă și
     pagini), și le compari cu textul paginii: cine apare, ce face, obiectele importante, să nu fie text în imagine,
     să nu fie un personaj dublat sau ceva înfricoșător.
   - O imagine greșită o refaci: scrii un `imagePrompt` mai concret, care descrie ce se vede (nu „fără X”), pui
     `"imageVariant"` următor, ștergi fișierul imaginii, faci commit și push. O fișă de personaj greșită o ștergi și
     corectezi descrierea din `characters`.
   - După **trei încercări** pe aceeași imagine, păstrezi varianta cea mai bună, dacă nu contrazice esențialul
     poveștii. Ce a rămas imperfect scrii cinstit în `review.imagini`. Variantele vechi se găsesc în istoricul git.
   - Pui `"verified": true` doar după ce **ai văzut** toate imaginile. Faci commit și push; după publicare, povestea
     apare în bibliotecă. Verifici asta în `public/stories/index.json` și în raport („PUBLICATĂ”).

9. **Rezumatul pentru proprietar**, scurt, în română: titlul, ce învață copilul, dacă e pe site, ce imagini ai
   refăcut și de ce, ce ai terminat din zilele trecute.

---

## Ce NU faci

- Nu modifici `scripts/`, `.github/`, `public/*.html`, `public/assets/`, `public/stories/index.json`, folderele
  `audio/` și nici `rapoarte/` (sunt generate automat), decât dacă proprietarul cere explicit.
- Nu ceri și nu folosești chei, parole sau token-uri: toate sunt în GitHub Secrets, iar robotul le folosește singur.
- Nu folosești mărci comerciale sau personaje cunoscute (nu le-a cerut nimeni).
- Nu redenumești folderul unei povești publicate: adresa ei s-ar strica.
- Nu pui `"verified": true` fără să fi văzut imaginile și nu pui `"approved": true` la poveștile personalizate:
  pe acelea le aprobă doar proprietarul.
- Nu atingi poveștile cu `"imaginiInPauza": true`: așteaptă un generator de imagini mai bun.

## Când s-au terminat temele

Când nu mai e nicio temă cu `"poveste": null` în `planificare/teme.json`, îți oprești sarcina programată și îi spui
proprietarului că s-au terminat temele.
