# Povestea zilei — procedura rutinei de dimineață

Rutina „Povestea zilei” pornește în fiecare dimineață (~06:05, ora României) o sesiune nouă de Claude, fără
nimeni de față. Proprietarul site-ului a cerut: **o poveste nouă pe zi, timp de 100 de zile, făcută după reguli,
verificată și publicată, fără să fie întrebat**. Nu pui întrebări; decizi singur după regulile de mai jos și la
final scrii un rezumat scurt.

## 0. Pregătire

1. `git pull` pe `master`. Dacă repository-ul nu e în directorul de lucru, adaugă-l (`bogdanbbg-collab/Iamlio`)
   și clonează-l.
2. Citește **întregi** `AGENTS.md` și `REGULI_POVESTI.md`. Ele au întâietate față de orice de aici.

## 1. Întâi, ce a rămas de ieri

Pentru fiecare poveste cu `"verified": false` din `public/stories/`:
- dacă îi lipsesc imagini (cota Cloudflare), nu faci nimic acum: se generează la publicarea de azi;
- dacă are toate imaginile, le verifici ca la pasul 5 și, dacă trec, pui `"verified": true`.

## 2. Tema zilei

În `planificare/teme.json`, ia **prima temă cu `"poveste": null`** (în ordinea `nr`). O singură poveste nouă pe zi,
chiar dacă au rămas teme din zilele trecute. Tema e un punct de plecare: dacă ceva din ea nu se potrivește cu
regulile, o adaptezi.

## 3. Scrie povestea

`python3 scripts/stories.py new "Titlu"`, apoi completezi tot, după `REGULI_POVESTI.md` (secțiunea 10). În plus,
ca imaginile gratuite (Cloudflare FLUX.2 klein, ~50 pe zi, cu coperta și Lio ca imagini de referință) să iasă bine:
- **8–9 pagini** (~3–4 minute): rămâne loc în cotă pentru refacerea imaginilor (de obicei 3–4 runde pe poveste);
- **doar Lio și 1–2 personaje animale, plante sau obiecte magice, fără oameni și fără copii**: filtrul de siguranță
  al generatorului refuză imaginile cu copii. Dacă tema are un copil (ex. „Pantofii lui Matei”), îl înlocuiești cu
  un animal (un ursuleț, un iepuraș) și spui asta în rezumat;
- **fără detalii pe care generatorul nu le poate desena exact**: ora pe un ceas, un număr anume de obiecte în
  imagine („patru grămezi”), litere; numărarea și orele rămân în text, nu în imagine;
- în prompturi, fără cuvintele care aduc alte obiecte decât cele dorite: „blanket” (desenează pături de lână),
  „nest” (coșuri de nuiele), „basket”; descrie ce se vede („a round mound of leaves”, „the leaf lies across his
  back”);
- fiecare personaj primește automat o **fișă** (desenat singur, în `public/stories/<id>/personaje/`), iar fiecare
  imagine pornește doar de la fișele personajelor din scena ei; în `Action` scrie „exactly one lion cub, Lio” și
  „only …” când trebuie să apară doar anumite personaje;
- **cel mult 2–3 personaje într-o imagine**; personaje ușor de desenat, cu un semn distinctiv clar
  (o culoare, o haină); Lio apare în imagine doar unde e cu adevărat în scenă;
- în `Action`, fiecare personaj **numit împreună cu ce este**: „Lio the little lion cub”, „Ana, the girl in the
  yellow raincoat”; acțiunea principală prima;
- fără obiecte care aduc text în imagine (afișe, cărți cu titlu, numere, cadrane cu cifre — descrie-le „plain”,
  „with dots”); jucăriile și obiectele fără față, dacă nu sunt personaje;
- fără mărci comerciale și fără personaje cunoscute (nu le-a cerut nimeni);
- nimic înfricoșător; final cald; cel puțin două momente amuzante; `review` cinstit.

## 4. Verificarea textului — agent separat

Înainte de commit, pornește un **agent separat** (Agent tool) care nu a scris povestea. Dă-i calea fișierului
`story.json` și `REGULI_POVESTI.md` și cere-i să verifice, punct cu punct, lista „Lista de verificare” din
secțiunea 10 și secțiunea 3 (imaginație, învățătură împletită în acțiune, umor, emoție, siguranță, interzise),
româna (diacritice, ș/ț cu virgulă, numere în litere), dacă fiecare `imagePrompt` arată exact momentul paginii și
dacă `narration` are tonuri potrivite. Să întoarcă o listă de probleme concrete, cu pagina. Corectezi tot ce e
întemeiat. Apoi `python3 scripts/stories.py validate` — povestea trebuie să aibă doar „imaginea nu există”.

În `planificare/teme.json` pui `"poveste": "<id>"` la tema folosită. Commit („Povestea zilei <nr>: <titlu>”) și push.

## 5. După publicare: verificarea imaginilor — agent separat

Aștepți commit-ul robotului („Povești pregătite automat…”, ~10 minute), faci `git pull` și citești
`rapoarte/<id>.md`. Dacă imaginile s-au generat:
- pornește un **agent separat de verificare a imaginilor**: îi dai, pentru fiecare imagine (copertă și pagini),
  calea fișierului și textul paginii, plus descrierile personajelor; el se uită la fiecare imagine și răspunde,
  pe pagină: se potrivește / nu se potrivește și de ce (cine apare, ce face, obiecte, text în imagine, personaj
  care arată altfel);
- verifică întâi **fișele personajelor** (`personaje/*.png`): o fișă greșită strică toate paginile; o ștergi și
  se face din nou la publicarea următoare (cu încă o variantă, `imageVariant` pe paginile afectate);
- uită-te și tu la o planșă cu toate imaginile; pentru fiecare imagine greșită aplici „Autocorectarea imaginilor”
  (secțiunea 10): `imagePrompt` mai concret, `imageVariant` următor, ștergi imaginea, commit; cel mult trei
  încercări pe imagine;
- după **trei încercări** pe aceeași imagine păstrezi varianta cea mai bună, dacă nu contrazice esențialul
  poveștii, și scrii cinstit în `review.imagini` ce a rămas imperfect;
- abia când **fiecare** imagine arată pagina ei (sau e cea mai bună după trei încercări) pui `"verified": true`,
  după ce te-ai uitat și tu la planșa cu toate imaginile, și faci commit; după următoarea publicare,
  povestea apare în bibliotecă. Verifică în `public/stories/index.json` că apare.

Dacă imaginile nu s-au generat din cauza cotei (în raport: Cloudflare „4006 … daily free allocation”), cota se
eliberează treptat, la ~24 de ore după ce a fost folosită: programează-ți cu `send_later` o revenire peste o oră, pornește
atunci din nou publicarea (workflow-ul `publica-site.yml`, „Run workflow”) și repetă de cel mult trei ori. Ce nu s-a
generat nici așa rămâne cu `"verified": false` și se termină la rularea de mâine (pasul 1).
Dacă după trei încercări o imagine tot contrazice ceva esențial, povestea rămâne ascunsă și spui asta în rezumat.

## 6. Rezumatul pentru proprietar

La final scrii scurt, în română: titlul, ce învață copilul, dacă e pe site (sau ce mai lipsește și când se
termină), ce imagini ai refăcut și ce ai terminat din zilele trecute.

## 7. După ziua 100

Când nu mai e nicio temă cu `"poveste": null`, după ultima poveste, oprește rutina: `update_trigger` cu
`enabled: false` pentru rutina „Povestea zilei” (id-ul e în promptul ei) și spune-i proprietarului că s-au terminat
cele 100 de povești.
