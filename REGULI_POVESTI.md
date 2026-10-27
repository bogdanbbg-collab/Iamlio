# Regulile poveștilor Iamlio

Acest fișier conține **regulile obligatorii** pentru orice poveste adăugată pe site-ul **Iamlio** („I Am Lio”).
Se aplică **oricărui AI** (ChatGPT, Claude, Gemini, Copilot etc.) și oricărui om. Nu contează cu ce unealtă
se scrie povestea: rezultatul trebuie să treacă prin aceste reguli și prin verificarea automată
`python3 scripts/stories.py validate`.

Când primești o cerere de tipul „fă o poveste despre …”, **nu scrie direct povestea**: urmează
[fluxul de lucru](#10-fluxul-de-lucru-obligatoriu) de la capătul fișierului, pas cu pas.
**Pornește întotdeauna de la șablonul [`sablon/story.json`](sablon/story.json)** (stilul imaginilor și Lio
sunt deja completate corect) și citește [secțiunea 9](#9-ce-verifică-automat-proiectul) ca să știi ce
respinge verificarea automată.
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
- Format **.png, .jpg sau .webp** (nu SVG). Imaginile se optimizează **automat** (devin .webp, sub ~450 KB) la publicare.

### Animația paginii: câmpul `animation` (obligatoriu pentru poveștile noi)

În cititor, imaginea paginii curente „prinde viață”: camera se mișcă încet peste ea și, dacă se potrivește cu
scena, apare un efect ușor. Le desenează browserul (fără fișiere și fără timp în plus la publicare); pe telefoanele
cu „Reducere mișcare” animația se oprește singură. Pe copertă și pe **fiecare pagină** scrii:

```json
"animation": { "camera": "zoom-in", "effect": "leaves" }
```

| `camera` | Când o alegi |
| --- | --- |
| `zoom-in` | camera se apropie încet: momente importante, emoții, surprize, un detaliu |
| `zoom-out` | camera se depărtează încet: locuri largi, începutul sau finalul poveștii |
| `pan-left` / `pan-right` | camera alunecă spre stânga / dreapta: drum, mers, privirea spre cineva |
| `pan-up` / `pan-down` | camera urcă (cer, zbor, copaci înalți) / coboară (ceva care cade) |
| `still` | imaginea stă pe loc: momente foarte liniștite |

| `effect` | Când îl alegi |
| --- | --- |
| `none` | fără efect (cele mai multe pagini: efectul e pentru momentele care îl cer) |
| `sparkles` | sclipiri aurii: magie, ceva fermecat care prinde viață |
| `stars` | stele care licăresc: noapte, cer |
| `leaves` | frunze care cad: toamnă, vânt, pădure |
| `snow` | fulgi de zăpadă |
| `drops` | picături: ploaie, stropi, apă |
| `bubbles` | bule care urcă: apă, săpun, ceva care gâlgâie |
| `glow` | lumină caldă care pâlpâie: lumânare, felinar, foc de tabără, ceva care se aprinde |
| `fireflies` | licurici: seară de vară, poiană |
| `hearts` | inimioare care urcă: îmbrățișare, dragoste, mulțumire |

Variază camera de la o pagină la alta și potrivește efectul cu **ce se întâmplă exact pe pagină** (dacă textul
spune că se aprinde lumânarea, `glow`; dacă e noapte cu stele, `stars`). Dacă `animation` lipsește, publicarea o
alege automat și cere în raport să fie verificată.

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

## 7. Vocea și regia de voce

Vocea se generează **automat** de GitHub Actions, după push, în **două variante**: **feminină** (naratoarea
Sulafat) și **masculină** (naratorul Algieba). Cel care citește alege din site.
- Imediat: vocile naturale Google **Chirp 3 HD**, unde Lio și fiecare personaj primesc automat o **voce proprie**;
- apoi, treptat (câteva pagini pe zi, cât permite cota gratuită): **Gemini TTS, „povestitorul”**, care citește
  toată pagina dintr-o dată, cu emoție, râs, suspans și voci pentru personaje. Pentru el contează mult ca
  `description` din `characters` să spună cine e personajul (prima parte, până la virgulă: „a cheerful
  five-year-old boy”), iar textul să aibă punctuație expresivă;
- rezerva, când serviciile Google nu pot: `edge-tts`.
**Nu genera tu fișiere audio** și nu adăuga câmpuri `audio`.

Ca povestea să nu sune robotic, **scrii explicit regia de voce** — cum se citește fiecare bucată.
Fiecare bucată se generează separat, cu intonația ei, apoi bucățile se lipesc cu pauze.

### a) Regia pe pagină: câmpul `narration` (obligatoriu pentru poveștile noi)

Pentru fiecare pagină, `narration` împarte **exact textul paginii** în replici, în ordine. Fiecare replică are:

| Câmp | Ce înseamnă |
| --- | --- |
| `text` | bucata de text, **copiată exact din `text`**, cu aceeași punctuație (verificarea respinge cuvinte diferite; pe site, replica citită se evidențiază sincron cu vocea, deci trebuie să se potrivească exact) |
| `mood` | tonul: `calm`, `vesel`, `entuziasmat`, `mirat`, `trist`, `șoptit`, `misterios`, `somnoros`, `speriat`, `hotărât` |
| `speaker` | (opțional) numele personajului care vorbește, exact ca în `characters`; lipsă = povestitorul |
| `pause` | (opțional) pauza după replică, în secunde (0–3; implicit 0,3, iar după „…” 0,7) |

Cum alegi:
- **narațiunea** e de obicei `calm`; schimbă tonul când se schimbă atmosfera (`misterios` înainte de o
  surpriză, `entuziasmat` la momentul vesel, `somnoros` la final de poveste de seară);
- **fiecare replică de dialog** e o bucată separată, cu `speaker` și tonul emoției personajului;
- **tag-ul de dialog** („a spus el”, „a întrebat Lio”) e o bucată separată, a povestitorului;
- pune **pauze** înaintea momentelor importante (`"pause": 0.6`) și după onomatopee („pleosc!”).

```json
"narration": [
  { "text": "Steluța stătea în iarbă și plângea încet.", "mood": "trist" },
  { "text": "— Nu mai știu drumul spre casă,", "mood": "trist", "speaker": "Steluța" },
  { "text": "a suspinat ea.", "mood": "trist", "pause": 0.6 },
  { "text": "— Nu-ți fie teamă!", "mood": "hotărât", "speaker": "Lio" }
]
```

Dacă `narration` lipsește, vocea se generează simplu: narațiune calmă și dialog mai vioi (acceptat, dar sună mai plat).

### b) Vocile personajelor: câmpul `voice` din `characters`

Fiecare personaj care vorbește poate avea un profil de voce, ca să se deosebească de povestitor:

```json
{ "name": "Steluța", "description": "...", "voice": { "type": "feminin", "pitch": 22, "rate": 2 } }
```

- `type`: `feminin` sau `masculin` — vocea fixă a personajului; lipsă = vocea aleasă de cel care ascultă;
- `pitch`: înălțimea, între −30 și +40 (pozitiv = mai subțire: copii, animale mici; negativ = mai gros: urși, uriași);
  cu Chirp, `pitch` alege tipul vocii: de la +10 în sus o voce tânără și vioaie, de la −8 în jos una gravă, matură;
- `rate`: viteza, între −30 și +30 (negativ = mai rar: bunici, bufnițe înțelepte; pozitiv = mai repede: veverițe);
- `chirp`: (opțional, rar) numele exact al unei voci Chirp 3 HD, dacă vrei una anume (de ex. `"Charon"`); lipsă =
  aleasă automat. Vocile ocupate: Sulafat și Algieba (povestitorul), Leda și Puck (Lio).

Lio are deja profilul lui (`"pitch": 12, "rate": 3`) — folosește-l la fel când Lio vorbește.

### c) Textul în sine

- propoziții scurte și punctuație corectă (virgula = mică pauză, „…” = pauză de suspans);
- numere în litere, fără abrevieri și emoji; onomatopee scrise cum se pronunță („Bâz-bâz!”, „Pleosc!”);
- semnul exclamării și al întrebării schimbă intonația — folosește-le.

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
  **După publicare, id-ul (numele folderului) nu se mai schimbă**, altfel adresa poveștii nu mai funcționează.
- **Pornești de la șablon:** `python3 scripts/stories.py new "Titlul poveștii"` creează folderul și `story.json`
  din [`sablon/story.json`](sablon/story.json); dacă nu poți rula comenzi, copiezi tu șablonul. Completezi tot
  ce e marcat `DE COMPLETAT` (verificarea respinge povestea cât timp mai există acest marcaj).
- Exemplu complet, care trece toate verificările: `public/stories/lio-si-steluta-cazatoare/story.json`.
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
  "categories": ["de-culcare", "animale", "invatam"],
  "created": "2026-10-25",
  "tags": ["numere", "noapte", "răbdare"],
  "illustrationStyle": "High-quality 3D animated feature film still for young children, ...",
  "characters": [
    {
      "name": "Țepișor",
      "description": "a tiny round baby hedgehog with soft light-brown spikes, a cream belly, big shiny black eyes, a tiny red knitted hat ...",
      "voice": { "pitch": 20, "rate": 4 }
    },
    {
      "name": "Lio",
      "description": "a small, chubby, adorable lion cub with baby proportions ...",
      "voice": { "pitch": 12, "rate": 3 }
    }
  ],
  "cover": {
    "image": "images/coperta.png",
    "imagePrompt": "Promptul complet folosit pentru copertă"
  },
  "pages": [
    {
      "text": "Era odată un arici mic. — Câte stele sunt? a întrebat el.",
      "narration": [
        { "text": "Era odată un arici mic.", "mood": "calm" },
        { "text": "— Câte stele sunt?", "mood": "mirat", "speaker": "Țepișor" },
        { "text": "a întrebat el.", "mood": "calm" }
      ],
      "image": "images/pagina-01.png",
      "imagePrompt": "Promptul complet folosit pentru imaginea paginii 1"
    }
  ],
  "review": {
    "imaginatie": "…",
    "invatare": "…",
    "umor": ["pagina 2: …", "pagina 5: …"],
    "emotie": "…",
    "siguranta": "…",
    "imagini": "…",
    "voce": "…"
  }
}
```

Pentru un personaj cunoscut se adaugă în `characters`: `"knownCharacter": true, "source": "…"`.
Salutul și rămas-bunul lui Lio (după categorie sau cu prenumele copilului) se adaugă **automat** — nu le scrie tu.

### Categoriile (`categories`, obligatoriu)

Fiecare poveste are **1–3 categorii**, după care se filtrează biblioteca. Alege-le
dintre (id → ce apare pe site):

| `categories` | Pe site |
| --- | --- |
| `de-culcare` | 🌙 De culcare — liniștite, potrivite pentru seară |
| `aventuri` | 🧭 Aventuri — călătorii, explorări, căutări |
| `animale` | 🐾 Animale — eroii sunt animale sau învață despre ele |
| `prietenie` | 💛 Prietenie și emoții |
| `invatam` | 📚 Învățăm — accent pe ceva concret de învățat (numere, culori, natură…) |
| `amuzante` | 😄 Amuzante — umorul e în prim-plan |

Prima categorie din listă e cea mai importantă: apare ca etichetă pe coperta din bibliotecă.
Dacă lipsesc, proiectul le alege automat după cuvintele din poveste și cere în raport să fie verificate.

### Întrebările lui Lio: câmpul `questions` (recomandat)

După poveste, Lio poate pune **1–3 întrebări** simple. Copilul alege dintre **2–3 variante ilustrate**; nu există
punctaj: la un răspuns greșit Lio spune blând „Mai încearcă!”, la cel corect „Bravo!” și explicația.

- Întrebările verifică dacă povestea a fost înțeleasă sau ce s-a învățat (`learning`), nu detalii mărunte.
- Maximum 20 de cuvinte; un singur răspuns corect, fără ambiguitate.
- Fiecare variantă are `text` și **o imagine** (`image`, din `images/`, de exemplu imaginea unei pagini) **sau un emoji**
  (`emoji`) — copiii mici nu știu încă să citească. Lio citește cu voce întrebarea și variantele.
- `answer` = numărul variantei corecte, **începând de la 0**. `explanation` (opțional) = ce spune Lio după răspunsul corect.

```json
"questions": [
  {
    "text": "Când stau treze bufnițele?",
    "options": [{ "text": "Ziua", "emoji": "☀️" }, { "text": "Noaptea", "emoji": "🌙" }],
    "answer": 1,
    "explanation": "Corect! Bufnițele dorm ziua și stau treze noaptea."
  }
]
```

### Povești personalizate: câmpurile `personalized` și `approved`

Un părinte poate cere o poveste **cu prenumele copilului** („fă o poveste pentru Ana, despre dinozauri”).

- Se creează cu `python3 scripts/stories.py new "Ana și dragonul" --pentru Ana`: id-ul primește un **cod aleator**
  (link secret), iar `story.json` primește `"personalized": {"for": "Ana"}` și `"approved": false`.
- **Doar prenumele** (sau un alint). Niciodată nume de familie, adresă, școală, grădiniță, oraș, fotografii,
  date de sănătate sau alte informații despre copil. Copilul poate fi un personaj al poveștii, alături de Lio;
  în imagini îl desenezi ca un copil de desen animat, **fără să încerci să semene cu un copil real**.
- Prenumele trebuie să apară în poveste; Lio îl salută pe nume la început și la final.
- Povestea **nu apare în bibliotecă** sau în motoarele de căutare; se deschide doar cu link-ul secret.
- Cât timp `"approved": false`, povestea **nu e publică**: la publicare ajunge doar într-o zonă protejată de pe
  server, pe care o poate deschide doar proprietarul site-ului, cu parola de previzualizare
  (`poveste.html?previzualizare=<id>`, link-ul e în `rapoarte/<id>.md`). Proprietarul o citește și, dacă e în
  regulă, spune „aprobă povestea <id>” — atunci (și doar atunci) setezi `"approved": true`.
  Nu seta niciodată singur `approved` pe `true`.
- Toate celelalte reguli (calitate, siguranță, lungime, imagini, voce) se aplică la fel.

### Autoevaluarea: câmpul `review` (obligatoriu)

Înainte de commit, **recitești povestea ca un părinte exigent** și scrii în `review`, concret, cu trimiteri la pagini:

| Câmp | Ce scrii |
| --- | --- |
| `imaginatie` | ce element magic sau neobișnuit are povestea |
| `invatare` | cum sunt împletite în acțiune lucrurile din `learning` (cu paginile) |
| `umor` | lista momentelor amuzante, **cel puțin două**, fiecare de forma `"pagina N: ce se întâmplă"` |
| `emotie` | problema, încercările, cum se rezolvă și de ce finalul e liniștitor |
| `siguranta` | de ce nimic din poveste nu sperie și nu e nepotrivit pentru 3–7 ani |
| `imagini` | cum ai verificat că fiecare imagine arată pagina ei și că personajele sunt identice |
| `voce` | cum ai ales tonurile, pauzele și vocile personajelor |

Dacă nu poți scrie cinstit unul dintre câmpuri (de ex. nu găsești două momente amuzante), **povestea nu e gata**:
îmbunătățește-o, nu completa câmpul de formă.

## 9. Ce repară, generează și verifică automat proiectul

### Ce repară singur proiectul (la fiecare publicare)

Orice AI ar fi scris povestea, înainte de verificare proiectul corectează automat tot ce e mecanic:
ș/ț cu virgulă, „…”, linia de dialog și ghilimelele; `id`, `created`, `age`, `learning` ca listă,
`categories` lipsă (alese după cuvintele din poveste, de verificat), numele
folderului; stilul oficial în `illustrationStyle` și în fiecare `imagePrompt`; descrierea completă a
personajelor din fiecare scenă în prompturi; descrierea și vocea oficială a lui Lio; prompturile de imagine
lipsă (din textul paginii); imaginile numite altfel (`1.png`, `cover.jpg` → `images/pagina-01.png`,
`images/coperta.jpg`); regia de voce lipsă sau greșită (cu detectarea vorbitorului și a tonului din
„a suspinat”, „a strigat”, „a șoptit”, din „!”, „?”, „…”); profilurile de voce pentru personajele care vorbesc;
animația paginii lipsă (camera alternată, efectul ghicit din scenă).

Ce generează singur: **vocea** (feminină și masculină) și, **dacă proprietarul a activat generatorul de imagini**
(secretul `OPENAI_API_KEY`), **imaginile care lipsesc** — coperta întâi, apoi paginile pornind de la copertă,
ca personajele să arate la fel.

Ce **nu** se inventează automat (trebuie scris de AI): textul poveștii, `title`, `summary`, `moral`,
`learning`, `review`, descrierile personajelor noi, imaginile (dacă generatorul nu e activat).
Reparațiile automate sunt o plasă de siguranță: **scrie povestea corect de la început**; regia de voce
scrisă de tine sună mai bine decât cea automată.

### Raportul: `rapoarte/<id>.md`

După fiecare publicare, proiectul scrie pentru fiecare poveste un raport cu starea ei
(**✅ PUBLICATĂ** sau **❌ NEPUBLICATĂ**), ce a reparat automat și **ce mai trebuie corectat**.
O poveste nepublicată **nu apare pe site**, dar nu le oprește pe celelalte.

### Ce verifică automat proiectul

La fiecare publicare, `python3 scripts/stories.py validate` respinge povestea dacă:

- **structura:** lipsesc câmpuri obligatorii (inclusiv `learning`, `categories`, `illustrationStyle`, `review`),
  `categories` nu are 1–3 categorii din lista de mai sus, id-ul nu e
  identic cu folderul, `age` nu e `3-5`/`5-7`/`3-7`, titlul are peste 10 cuvinte, a rămas `DE COMPLETAT`;
- **lungimea:** sub 6 sau peste 24 de pagini, sub 20 sau peste 70 de cuvinte pe pagină, sub 2 sau peste 10 minute;
- **limba:** ș/ț cu sedilă în loc de virgulă;
- **imaginile:** lipsește un fișier, calea nu e `images/nume.png|jpg|webp`, lipsește `imagePrompt` pe copertă
  sau pe o pagină, `illustrationStyle` nu e stilul Iamlio, un `imagePrompt` nu conține `illustrationStyle`
  cuvânt cu cuvânt, un personaj e numit într-un `imagePrompt` fără descrierea lui completă din `characters`;
- **personajele:** descriere vizuală lipsă sau prea scurtă, Lio fără descrierea și vocea oficială, personaj
  cunoscut fără `source` sau fără o descriere foarte detaliată;
- **animația:** `animation.camera` sau `animation.effect` care nu e din listele de la secțiunea 6;
- **vocea:** o pagină fără `narration`, `narration` care nu conține exact cuvintele din `text`, ton necunoscut,
  vorbitor care nu e în `characters`, personaj care vorbește fără profil `voice`, dialog fără `speaker`,
  mai puțin de 3 tonuri diferite în toată povestea;
- **autoevaluarea:** un câmp din `review` lipsă sau scris de formă, mai puțin de două momente amuzante cu pagina lor.

Și avertizează (fără să respingă) pentru: propoziții de peste 25 de cuvinte, cifre în text, cuvinte
nepotrivite pentru copii mici, imagini mari, un personaj din text care lipsește din imaginea paginii.

Ce **nu** poate verifica un program: dacă povestea e cu adevărat frumoasă și amuzantă și dacă imaginile chiar
arată ce scrie. Acestea depind de tine: urmează fluxul de mai jos fără scurtături.

## 10. Fluxul de lucru (obligatoriu)

Când primești „fă o poveste despre X”:

1. **Înțelege cererea.** Subiect, personaje cerute, lungime (implicit 4–6 minute), vârstă (implicit 3–7).
   Dacă cererea are ceva nepotrivit pentru copii, adapteaz-o (secțiunea 3) și spune ce ai schimbat.
2. **Pornește de la șablon** (`python3 scripts/stories.py new "Titlu"` sau o copie a `sablon/story.json`).
3. **Planifică.** Alege: elementul de imaginație, cele 1–3 lucruri de învățat, cele cel puțin două momente
   amuzante, problema și rezolvarea, morala, cele 1–3 categorii. Alege numărul de pagini după tabelul din secțiunea 2.
4. **Scrie povestea** pagină cu pagină (20–70 de cuvinte pe pagină, un moment pe pagină).
   Apoi scrie **regia de voce** (`narration`) pentru fiecare pagină și profilul `voice` al personajelor (secțiunea 7).
5. **Recitește ca un părinte**, corectează și scrie autoevaluarea (`review`); dacă un câmp nu se poate scrie cinstit, îmbunătățește povestea.
6. **Descrie personajele** în `characters` (în engleză, foarte vizual; Lio exact ca în secțiunea 4).
7. **Scrie prompturile** de imagine cu șablonul din secțiunea 6: coperta + câte unul pentru fiecare pagină,
   și animația fiecăreia (`animation`: mișcarea camerei și efectul potrivit cu scena).
8. **Generează imaginile** (coperta prima, apoi paginile, păstrând personajele identice) și verifică fiecare
   imagine: se potrivește cu textul? personajele arată la fel? nu are text? Refă-le pe cele care nu se potrivesc.
9. **Salvează** `story.json` și imaginile în `public/stories/<id>/`.
10. **Verifică:** `python3 scripts/stories.py validate` (dacă poți rula comenzi) — trebuie să apară `[OK]`.
11. **Commit și push** pe branch-ul principal (`master`) sau deschide un pull request. GitHub Actions face restul:
     teste → repară automat → generează imaginile lipsă (dacă e activat) → optimizează imaginile → verifică →
     scrie raportul → generează vocea feminină și masculină → actualizează biblioteca → urcă site-ul prin FTPS →
     verifică site-ul live.
12. **Citește raportul** `rapoarte/<id>.md` după 3–5 minute (preia întâi ultima versiune din repository:
     robotul poate fi reparat automat `story.json` și a mutat imaginile). Dacă scrie **NEPUBLICATĂ**, corectează
     tot ce e la „De corectat”, fă din nou commit și **repetă până când raportul spune PUBLICATĂ**.
13. **Privește fiecare imagine și autocorectează-te, fără să întrebi** (vezi mai jos). Treaba ta se termină abia
     când povestea e PUBLICATĂ și fiecare imagine arată pagina ei.
14. **Bariera.** O poveste nouă are `"verified": false` (din șablon): după generare, raportul spune „ÎN VERIFICARE”,
     povestea se vede doar ca previzualizare (cu parola de administrator, link în raport și în panou), dar **nu apare
     în bibliotecă**. Abia după ce ai privit coperta și fiecare pagină și ai refăcut ce era greșit, pui
     `"verified": true` și faci commit — atunci apare pe site. Nu pui `true` fără să fi văzut imaginile.

O poveste care nu trece verificarea automată **nu** este publicată.

### Autocorectarea imaginilor (obligatorie, pentru fiecare poveste)

Generatorul de imagini greșește uneori: uită un personaj, adaugă unul în plus, desenează un obiect care în
text lipsește (de exemplu nasul pe care tocmai l-a mâncat iepurele) sau nu arată acțiunea paginii. După
publicare, **te uiți la copertă și la fiecare pagină** și le compari cu textul: cine apare, ce face, ce obiecte
sunt (sau lipsesc), momentul zilei, iar personajele arată la fel ca pe celelalte pagini.

Când o imagine contrazice textul, **repari imaginea, nu povestea**:

1. **Nu schimbi textul, morala sau întâmplările** ca să se potrivească cu o imagine greșită. Povestea rămâne cum
   a fost scrisă; imaginea trebuie s-o arate.
2. **Rescrii `imagePrompt` mai concret**, cu ce se vede, nu cu ce lipsește: generatoarele nu înțeleg bine
   „fără X”, „no X”. În loc de „omul de zăpadă fără nas” descrii fața care se vede („o față netedă, doar doi ochi
   și gura”) sau ascunzi lucrul care lipsește prin compoziție (personajul își acoperă fața cu mâinile, e văzut din
   profil, obiectul lipsă apare în altă parte: iepurele ține morcovul în lăbuțe). Pune acțiunea principală prima.
3. **Ceri alt desen** cu `"imageVariant": 1` (apoi 2, 3…) pe acea pagină (sau pe copertă), ștergi fișierul imaginii
   din `images/` și faci commit: la publicare se generează din nou doar imaginea lipsă.
4. Cel mult **trei încercări** pentru aceeași imagine. Apoi păstrezi imaginea care arată cel mai bine momentul
   paginii, cu condiția să nu contrazică ce e esențial în poveste. Ce a rămas imperfect scrii cinstit în `review.imagini`.
5. Detaliile mărunte (o nuanță a hainelor, un fundal puțin altfel) nu se refac; se refac imaginile care schimbă
   ce se întâmplă pe pagină, cine apare sau cum arată personajele.
6. Nu ceri voie pentru aceste corecturi: le faci singur și spui la final ce ai refăcut și de ce.

### Lista de verificare (înainte de commit)

- [ ] Titlu scurt și frumos; `summary` care stârnește curiozitatea.
- [ ] Durată între 2 și 10 minute (6–24 pagini, 20–70 de cuvinte pe pagină).
- [ ] Are imaginație, ceva de învățat (`learning`), cel puțin două momente amuzante și final fericit.
- [ ] Nimic din lista „Interzis”; nimic care ar speria un copil de 3 ani înainte de culcare.
- [ ] Română corectă, cu diacritice (ș, ț cu virgulă), numere în litere, dialog cu linie de dialog.
- [ ] Fiecare pagină are `narration` cu tonuri potrivite; personajele care vorbesc au profil `voice`.
- [ ] Fiecare personaj descris o dată în `characters` și copiat întocmai în prompturile în care apare.
- [ ] Fiecare imagine arată exact momentul paginii ei, în stilul Iamlio, fără text în imagine.
- [ ] Coperta și fiecare pagină au `animation` (camera variată, efectul potrivit cu scena sau `none`).
- [ ] Personajele cunoscute (dacă au fost cerute) sunt fidele originalului și marcate cu `knownCharacter`.
- [ ] `review` completat cinstit, cu pagini concrete; nu a rămas nimic `DE COMPLETAT`.
- [ ] Ideal: 1–2 întrebări (`questions`) cu variante ilustrate și un singur răspuns corect.
- [ ] Poveste personalizată: doar prenumele, id cu cod aleator, `"approved": false` până la aprobarea proprietarului.
- [ ] `python3 scripts/stories.py validate` afișează `[OK]`.
- [ ] După publicare, `rapoarte/<id>.md` spune **PUBLICATĂ**.
- [ ] După publicare, fiecare imagine arată pagina ei (altfel: autocorectarea imaginilor, secțiunea 10).
