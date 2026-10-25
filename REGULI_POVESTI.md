# Regulile poveștilor Iamlio

Acest fișier conține **regulile obligatorii** pentru orice poveste adăugată pe site-ul **Iamlio** („I Am Lio”).
Se aplică **oricărui AI** (ChatGPT, Claude, Gemini, Copilot etc.) și oricărui om. Nu contează cu ce unealtă
se scrie povestea: rezultatul trebuie să treacă prin aceste reguli și prin verificarea automată
`python3 scripts/stories.py validate`.

Când primești o cerere de tipul „fă o poveste despre …”, **nu scrie direct povestea**: urmează
[fluxul de lucru](#9-fluxul-de-lucru-obligatoriu) de la capătul fișierului, pas cu pas.
Dacă cererea încalcă o regulă (de ex. e prea înfricoșătoare), **adapteaz-o** ca să respecte regulile și
spune pe scurt ce ai schimbat.

---

## 1. Publicul și limba

- **Vârsta:** copii de **3–7 ani**. Câmpul `age` este `"3-5"`, `"5-7"` sau `"3-7"`.
  Poveștile lungi (peste 6 minute) sunt de obicei pentru `"5-7"`.
- **Limba:** română corectă, naturală, **cu diacritice** (ă, â, î, ș, ț). Folosește „ș” și „ț” cu virgulă,
  nu cu sedilă (ş, ţ).
- Dialogul se scrie cu linie de dialog: `— Bună, a spus Lio.` Ghilimele românești: „așa”.
- Textul e făcut **pentru a fi citit cu voce tare**: propoziții scurte (ideal sub 15 cuvinte), ritm plăcut,
  cuvinte simple. Un cuvânt nou sau mai greu se explică imediat, în poveste („un telescop — un ochean mare
  prin care vezi stelele de aproape”).
- Numerele se scriu în litere („trei iepurași”). Fără abrevieri, fără emoji în text.

## 2. Lungimea: între 2 și 10 minute

Durata se calculează automat din text: **≈ 130 de cuvinte pe minut + ~2,5 secunde pentru fiecare
întoarcere de pagină**. Verificarea respinge orice poveste sub 2 sau peste 10 minute.

| Tip | Durată | Pagini | Cuvinte în total |
| --- | --- | --- | --- |
| Scurtă (de seară, pentru cei mici) | 2–4 min | 6–10 | ~220–480 |
| Medie | 4–7 min | 10–16 | ~480–850 |
| Lungă (pentru 5–7 ani) | 7–10 min | 16–24 | ~850–1200 |

- **6–24 de pagini**, **20–70 de cuvinte pe pagină** (coperta și pagina de final se adaugă automat).
- Dacă cel care cere nu spune lungimea, alege o poveste **medie (4–6 minute)**.
- Fiecare pagină = **un singur moment** al poveștii, care se poate desena într-o singură imagine.

## 3. Ce face o poveste Iamlio bună

Fiecare poveste trebuie să le aibă pe **toate** cele patru:

1. **Imaginație.** Ceva neobișnuit și minunat: animale care vorbesc, un loc magic, un obiect fermecat,
   o călătorie pe nori, o picătură de ploaie curajoasă. Evită poveștile „banale” fără nicio surpriză.
2. **Ceva folositor de învățat** (câmpul `learning`, 1–3 lucruri, obligatoriu). Învățătura e **împletită în
   acțiune**, nu ținută ca o lecție. Exemple:
   - cunoștințe: numere și numărat, culori, forme, litere, contrarii (mare/mic), anotimpuri, vremea,
     animale și unde trăiesc, plante, corpul omenesc, planete și stele, meserii;
   - deprinderi: spălatul pe dinți și pe mâini, mâncarea sănătoasă, ordinea, somnul, siguranța
     (strada, focul, străinii — explicate liniștit, fără frică);
   - emoții și relații: prietenie, împărțit, rândul la joacă, curaj, răbdare, a cere iertare,
     a recunoaște și a numi emoțiile (tristețe, furie, teamă, bucurie), empatie, incluziune;
   - natură și lume: grija pentru animale și pentru planetă, tradiții românești, prietenie cu cei diferiți.
3. **Umor.** Cel puțin **două momente amuzante**: o situație caraghioasă, un personaj neîndemânatic dar
   simpatic, sunete haioase („bâz-bâz”, „pleosc!”), o repetiție care la final are o întorsătură, un joc de
   cuvinte simplu. Umorul nu râde niciodată de cineva și nu umilește.
4. **Emoție și final fericit.** Fir clar: **început → o problemă pe înțelesul copiilor → încercări (de obicei
   trei) → rezolvare prin curaj, prietenie sau ingeniozitate → final cald și liniștitor**. Morala (`moral`)
   e o singură propoziție pozitivă.

**Personaje:** maximum 4–5 personaje importante, nume ușor de pronunțat, fiecare cu o trăsătură clară
(curios, fricos dar bun, poznaș…). Eroul rezolvă problema **el însuși**, cu ajutor, nu doar e salvat.

**Interzis:** violență, moarte, sânge, răniri descrise, monștri cu adevărat înfricoșători, pericole reale
prezentate ca joacă (foc, prize, apă adâncă, medicamente), abandon, pedepse dure, rușinare, limbaj urât,
stereotipuri (de gen, etnie, aspect), reclame și mărci comerciale, teme politice sau religioase,
frici rămase nerezolvate la final. Un „personaj negativ” poate exista doar dacă e mai degrabă comic
și se îndreaptă la final.

## 4. Lio — personajul site-ului

Lio este mascota site-ului: **„Lio îți citește o poveste”**. Poate fi eroul poveștii, poate apărea ca prieten
sau ghid, sau poate lipsi (atunci povestea e doar „citită” de Lio). Dacă apare, arată **mereu la fel**:

> **Lio:** un pui de leu mic, rotunjor și prietenos, cu proporții de bebeluș (capul cât jumătate din corp);
> blană galben-aurie; coamă scurtă, pufoasă, portocaliu-caramel, cu o șuviță ondulată în creștet; ochi mari,
> rotunzi, căprui-închis, cu sclipiri; obraji rozalii; nas mic maro în formă de inimioară; urechi rotunde cu
> interior roz; poartă mereu o **eșarfă turcoaz cu steluțe galbene**; coada are un smoc caramel la vârf.
> Merge pe două lăbuțe, cu înălțimea și energia unui copil de 4 ani. Este curios, blând, puțin stângaci și curajos.

Descriere în engleză (de copiat cuvânt cu cuvânt în prompturile de imagine):

> *Lio: a small, chubby, adorable lion cub with baby proportions (big round head about half of his height),
> soft golden-yellow fur, a short fluffy caramel-orange mane with one curly tuft on top, big round dark-brown
> sparkling eyes, rosy cheeks, a small brown heart-shaped nose, round ears with pink inside, always wearing a
> turquoise scarf with little yellow stars, a caramel tuft at the tip of the tail, walks upright like a
> 4-year-old child, friendly and curious expression.*

## 5. Personaje cunoscute (cerute explicit)

Uneori se cer povești cu personaje care există deja (din basme, cărți, desene animate).

- **Personaje din basme și povești clasice** (Scufița Roșie, Capra cu trei iezi, Albă-ca-Zăpada,
  Hansel și Gretel, Pinocchio, Făt-Frumos, Harap-Alb, Ursul păcălit de vulpe, Degețica etc.):
  sunt permise oricând. Le desenezi după **înfățișarea clasică, cunoscută** a personajului.
- **Personaje din filme, seriale sau cărți moderne** (de exemplu din desenele animate actuale):
  le folosești **doar dacă utilizatorul le cere explicit pe nume**. Atunci:
  - personajul trebuie să fie **fidel** cu felul în care e cunoscut: aceleași culori, haine, frizură,
    accesorii, proporții, personalitate și fel de a vorbi;
  - scrie în `characters` o **descriere vizuală foarte detaliată** (în engleză), ca imaginile să semene cu
    originalul chiar dacă generatorul nu recunoaște numele; unele generatoare refuză numele protejate,
    caz în care folosești doar descrierea, fără nume;
  - marchează personajul cu `"knownCharacter": true` și `"source"` (de unde e, ex. `"basm popular"` sau
    numele filmului/serialului);
  - povestea rămâne una **nouă, originală**: nu copia scene sau replici din film/carte.
- Toate celelalte reguli (vârstă, ton, interdicții) se aplică și personajelor cunoscute.

## 6. Ilustrațiile

Imaginile sunt la fel de importante ca textul. Trebuie să fie **foarte frumoase, făcute pentru copii, și
să arate exact ce se întâmplă pe pagina respectivă.**

### Stilul Iamlio (obligatoriu)

Aspect de **film de animație 3D modern pentru copii** (în genul filmelor de animație de la marile studiouri):
personaje rotunjoare și expresive, ochi mari și vii, texturi moi (blană, pânză, frunze), lumină caldă și
cinematografică, culori bogate dar blânde, fundaluri detaliate și magice, adâncime de câmp ușoară,
compoziție de cadru de film. Nimic înfricoșător, nimic întunecat sau agresiv; chiar și scenele de noapte
sunt luminoase și calde.

### Imaginea trebuie să reflecte pagina

Pentru fiecare pagină, `imagePrompt` descrie **concret** ce se vede:

- **cine** apare (toți cei care sunt în acel moment al poveștii, cu descrierea lor completă);
- **unde** (locul, momentul zilei, vremea, anotimpul);
- **ce fac** (acțiunea exactă de pe pagină) și **ce simt** (expresii: surprins, vesel, îngrijorat…);
- **obiectele importante** pomenite în text (dacă textul spune „o umbrelă roșie cu buline”, ea apare);
- **încadrarea** (plan general, plan apropiat, de sus…), variată de la o pagină la alta.

O imagine **nu** contrazice textul (dacă e noapte în text, e noapte și în imagine; dacă sunt trei iepurași,
se văd trei).

### Personaje identice în toată povestea

- Descrie fiecare personaj o singură dată în `characters` (în engleză) și **copiază descrierea întreagă** în
  fiecare `imagePrompt` în care apare. Același păr, aceleași haine, aceleași culori, aceleași proporții.
- Dacă generatorul permite imagini de referință: generează mai întâi coperta (sau o „fișă de personaj”) și
  folosește-o ca referință pentru toate paginile.

### Reguli tehnice

- O imagine pentru **fiecare pagină** + **o copertă** (coperta prezintă eroii și lumea poveștii, fără titlu scris).
- **Fără niciun text, litere sau cifre în imagine.** Fără logo-uri și mărci.
- Format **orizontal 3:2**, ideal **1536×1024 px**. Subiectul principal în **centrul** imaginii
  (pe telefon marginile pot fi tăiate).
- Format **.png, .jpg sau .webp**. Imaginile se optimizează **automat** (devin .webp, sub ~400 KB) la publicare.

### Șablon de prompt pentru imagine (în engleză)

```
High-quality 3D animated feature film still for young children, modern family animation movie style,
adorable expressive characters with big eyes and soft rounded shapes, detailed soft textures,
warm cinematic lighting, rich gentle colors, magical and cozy atmosphere, shallow depth of field,
nothing scary, no text, no letters, no numbers, no logos.
Landscape 3:2 composition, main subject centered.
Characters in this scene: <descrierea completă a fiecărui personaj prezent, din characters>.
Setting: <locul, momentul zilei, vremea>.
Action: <ce se întâmplă exact pe această pagină>.
Emotions: <expresiile personajelor>.
Important details: <obiectele pomenite în text>.
Camera: <wide shot / medium shot / close-up / low angle ...>.
```

Câmpul `illustrationStyle` din `story.json` conține primele 4 rânduri (stilul), identice pentru toate paginile.

## 7. Vocea (text-to-speech)

- **Nu o genera tu.** Vocea se generează **automat** de GitHub Actions (cu `edge-tts`, gratuit), după push.
- Fiecare poveste primește **ambele voci**: **feminină** (`ro-RO-AlinaNeural`) și **masculină**
  (`ro-RO-EmilNeural`). Cel care citește alege vocea din site.
- Ca să sune bine: propoziții scurte, punctuație corectă (virgula = mică pauză), numere în litere,
  onomatopee scrise cum se pronunță („Bâz-bâz!”).
- Nu crea fișiere audio și nu adăuga câmpuri `audio` — se generează în folderul `audio/`.

## 8. Fișierele

Fiecare poveste stă în propriul folder: `public/stories/<id>/`

```
public/stories/<id>/
├── story.json          ← textul și datele poveștii (obligatoriu)
├── images/
│   ├── coperta.png
│   ├── pagina-01.png
│   ├── pagina-02.png
│   └── …
└── audio/              ← generat AUTOMAT (feminin/ și masculin/)
```

- **Titlul (`title`) e obligatoriu:** scurt (2–7 cuvinte), cald, ușor de spus, de preferat cu numele eroului
  („Lio și steluța căzătoare”). Apare în bibliotecă, pe copertă și în cititor.
- `<id>` = titlul fără diacritice, cu litere mici și cratime: `lio-si-steluta-cazatoare`.
- Imaginile: `images/coperta.*`, `images/pagina-01.*`, `images/pagina-02.*` … (două cifre).
- **Nu edita** `public/stories/index.json` și `audio/` — sunt generate automat.

### Formatul `story.json`

```json
{
  "id": "aricelul-care-numara-stelele",
  "title": "Aricelul care număra stelele",
  "summary": "Una-două propoziții care îi fac pe copii curioși, pentru biblioteca site-ului.",
  "age": "3-7",
  "moral": "Când nu renunți, chiar și lucrurile grele devin posibile.",
  "learning": ["numără până la zece", "stelele se văd doar noaptea", "răbdarea"],
  "created": "2026-10-25",
  "tags": ["numere", "noapte", "răbdare"],
  "illustrationStyle": "High-quality 3D animated feature film still for young children, ...",
  "characters": [
    {
      "name": "Țepișor",
      "description": "a tiny round baby hedgehog with soft light-brown spikes, a cream belly, big shiny black eyes, a tiny red knitted hat ..."
    },
    {
      "name": "Lio",
      "description": "a small, chubby, adorable lion cub with baby proportions ..."
    }
  ],
  "cover": {
    "image": "images/coperta.png",
    "imagePrompt": "Promptul complet folosit pentru copertă"
  },
  "pages": [
    {
      "text": "Textul paginii 1.",
      "image": "images/pagina-01.png",
      "imagePrompt": "Promptul complet folosit pentru imaginea paginii 1"
    }
  ]
}
```

Pentru un personaj cunoscut se adaugă în `characters`: `"knownCharacter": true, "source": "…"`.

## 9. Fluxul de lucru (obligatoriu)

Când primești „fă o poveste despre X”:

1. **Înțelege cererea.** Subiect, personaje cerute, lungime (implicit 4–6 minute), vârstă (implicit 3–7).
   Dacă cererea are ceva nepotrivit pentru copii, adapteaz-o (secțiunea 3) și spune ce ai schimbat.
2. **Planifică.** Alege: elementul de imaginație, cele 1–3 lucruri de învățat, cele cel puțin două momente
   amuzante, problema și rezolvarea, morala. Alege numărul de pagini după tabelul din secțiunea 2.
3. **Scrie povestea** pagină cu pagină (20–70 de cuvinte pe pagină, un moment pe pagină).
4. **Recitește ca un părinte** și verifică lista de mai jos; corectează până trece totul.
5. **Descrie personajele** în `characters` (în engleză, foarte vizual; Lio exact ca în secțiunea 4).
6. **Scrie prompturile** de imagine cu șablonul din secțiunea 6: coperta + câte unul pentru fiecare pagină.
7. **Generează imaginile** (coperta prima, apoi paginile, păstrând personajele identice) și verifică fiecare
   imagine: se potrivește cu textul? personajele arată la fel? nu are text? Refă-le pe cele care nu se potrivesc.
8. **Salvează** `story.json` și imaginile în `public/stories/<id>/`.
9. **Verifică:** `python3 scripts/stories.py validate` (dacă poți rula comenzi) — trebuie să apară `[OK]`.
10. **Commit și push** pe branch-ul principal. GitHub Actions face restul: optimizează imaginile → verifică
    povestea → generează vocea feminină și masculină → actualizează biblioteca → urcă site-ul prin FTPS.

O poveste care nu trece verificarea automată **nu** este publicată.

### Lista de verificare (înainte de commit)

- [ ] Titlu scurt și frumos; `summary` care stârnește curiozitatea.
- [ ] Durată între 2 și 10 minute (6–24 pagini, 20–70 de cuvinte pe pagină).
- [ ] Are imaginație, ceva de învățat (`learning`), cel puțin două momente amuzante și final fericit.
- [ ] Nimic din lista „Interzis”; nimic care ar speria un copil de 3 ani înainte de culcare.
- [ ] Română corectă, cu diacritice (ș, ț cu virgulă), numere în litere, dialog cu linie de dialog.
- [ ] Fiecare personaj descris o dată în `characters` și copiat întocmai în prompturile în care apare.
- [ ] Fiecare imagine arată exact momentul paginii ei, în stilul Iamlio, fără text în imagine.
- [ ] Personajele cunoscute (dacă au fost cerute) sunt fidele originalului și marcate cu `knownCharacter`.
