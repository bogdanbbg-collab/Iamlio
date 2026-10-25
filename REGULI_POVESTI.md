# Regulile poveștilor Iamlio

Acest fișier conține **regulile obligatorii** pentru orice poveste adăugată pe site-ul **Iamlio** („I Am Lio”).
Orice AI (ChatGPT, Claude, Gemini etc.) sau om care adaugă o poveste trebuie să le respecte întocmai.
Când primești cererea „fă o poveste despre …”, urmează pașii din secțiunea [Fluxul de lucru](#7-fluxul-de-lucru).

---

## 1. Publicul și limba

- **Vârsta:** copii de **3–7 ani** (maximum 7 ani).
- **Limba:** română corectă, **cu diacritice** (ă, â, î, ș, ț). Folosește „ș” și „ț” cu virgulă, nu cu sedilă (ş, ţ).
- Dialogul se scrie cu linie de dialog: `— Bună, a spus Lio.`
- Ghilimele românești: „așa”.

## 2. Conținutul poveștii

- **8–12 pagini** de poveste (fără copertă și pagina de final, care se fac automat).
- **20–60 de cuvinte pe pagină.** Propoziții scurte (ideal sub 15 cuvinte), cuvinte simple.
- Un singur fir narativ, clar: **început → o problemă mică → încercare/ajutor → rezolvare → final fericit**.
- **Final fericit și liniștitor**, potrivit și pentru seara, înainte de culcare.
- O **morală** simplă, pozitivă, într-o singură propoziție (ex.: „Când ajuți un prieten, drumurile grele devin ușoare.”).
- Maximum **3–4 personaje** cu nume ușor de pronunțat.
- Sunt binevenite: repetiții jucăușe, onomatopee („pof!”, „fâș-fâș”), numărat, culori, emoții numite pe nume.

**Interzis:** violență, moarte, sânge, monștri înfricoșători, pericole reale prezentate ca amuzante,
abandon, pedepse dure, limbaj urât, stereotipuri, mărci comerciale, personaje protejate de drepturi de autor
(Disney, Pixar, Peppa etc.), reclame, teme religioase sau politice, frici nerezolvate la final.

## 3. Lio — personajul site-ului

Lio este mascota site-ului: **„Lio îți citește o poveste”**. Lio poate fi eroul poveștii sau poate apărea
ca prieten/ghid. Dacă apare, trebuie desenat **mereu la fel**:

> **Lio:** un pui de leu mic, rotunjor și prietenos; blană galben-aurie; coamă scurtă, pufoasă,
> portocaliu-caramel; ochi mari, rotunzi, căprui-închis cu sclipiri albe; obraji rozalii; nas mic maro în
> formă de inimioară; urechi rotunde; poartă mereu o **eșarfă turcoaz cu steluțe galbene**; coada are un smoc
> caramel la vârf. Merge pe două lăbuțe, cu înălțimea și energia unui copil de 4 ani. Este curios, blând și curajos.

Descriere în engleză (pentru generatoarele de imagini):

> *Lio: a small, chubby, friendly lion cub with golden-yellow fur, a short fluffy caramel-orange mane, big round
> dark-brown eyes with white sparkles, rosy cheeks, a small brown heart-shaped nose, round ears, always wearing a
> turquoise scarf with little yellow stars, a caramel tuft at the tip of the tail, walks upright like a 4-year-old child.*

## 4. Ilustrațiile

- **O imagine pentru fiecare pagină** + **o imagine de copertă**.
- **Același stil în toată povestea** și aceleași personaje (aceleași culori, haine, proporții).
  Scrie descrierea fiecărui personaj o singură dată în `characters` și repet-o în fiecare `imagePrompt`.
- **Stil Iamlio:** ilustrație de carte pentru copii, acuarelă digitală moale, contururi blânde, culori calde
  pastel, lumină caldă, forme rotunde, atmosferă prietenoasă.
- **Fără niciun text, litere sau cifre în imagine.**
- Format **orizontal 3:2** (ideal **1536×1024 px**). Coperta poate fi tot 3:2.
- Fișiere **.webp** (preferat), .jpg sau .png; ideal **sub 400 KB** fiecare.
- Elementul important al scenei în centrul imaginii (marginile pot fi tăiate pe ecrane mici).

**Șablon de prompt pentru imagine** (în engleză, completat pentru fiecare pagină):

```
Children's picture book illustration, soft digital watercolor, gentle outlines, warm pastel colors,
warm soft lighting, rounded friendly shapes, cozy and safe atmosphere, no text, no letters, no numbers.
Landscape 3:2 composition, main subject centered.
Characters: <descrierile personajelor din characters, cuvânt cu cuvânt>.
Scene: <ce se întâmplă pe această pagină>.
```

## 5. Vocea (text-to-speech)

- **Nu trebuie generată de AI-ul care scrie povestea.** Vocea se generează **automat** de GitHub Actions
  (cu `edge-tts`, gratuit) după ce povestea este urcată în repository.
- Vocea implicită: **`ro-RO-AlinaNeural`** (feminină, caldă). Alternativă: **`ro-RO-EmilNeural`** (masculină).
  Se alege prin câmpul `voice` din `story.json`.
- Dacă fișierele audio lipsesc, site-ul citește textul cu vocea română a browserului.
- Pentru o citire bună: scrie numerele în litere („trei iepurași”), evită abrevierile și emoji-urile în text.

## 6. Structura fișierelor

Fiecare poveste stă în propriul folder: `public/stories/<id>/`

```
public/stories/<id>/
├── story.json          ← textul și datele poveștii (obligatoriu)
├── images/
│   ├── coperta.webp
│   ├── pagina-01.webp
│   ├── pagina-02.webp
│   └── …
└── audio/              ← generat AUTOMAT, nu îl crea manual
```

- `<id>` = titlul fără diacritice, cu litere mici și cratime: `lio-si-steluta-cazatoare`.
- Imaginile se numesc `coperta.*` și `pagina-01.*`, `pagina-02.*` … (două cifre).
- **Nu edita** `public/stories/index.json` — este generat automat.

### Formatul `story.json`

```json
{
  "id": "lio-si-steluta-cazatoare",
  "title": "Lio și steluța căzătoare",
  "summary": "O propoziție-două despre poveste, pentru biblioteca site-ului.",
  "age": "3-7",
  "moral": "Când ajuți un prieten, drumurile grele devin ușoare.",
  "voice": "ro-RO-AlinaNeural",
  "created": "2026-10-25",
  "tags": ["prietenie", "curaj", "noapte"],
  "illustrationStyle": "Children's picture book illustration, soft digital watercolor, ...",
  "characters": [
    { "name": "Lio", "description": "a small, chubby, friendly lion cub ..." }
  ],
  "cover": {
    "image": "images/coperta.webp",
    "imagePrompt": "Promptul folosit pentru copertă"
  },
  "pages": [
    {
      "text": "Textul paginii 1.",
      "image": "images/pagina-01.webp",
      "imagePrompt": "Promptul complet folosit pentru imaginea paginii 1"
    }
  ]
}
```

**Nu** crea fișiere audio și nu adăuga câmpuri `audio` — vocea se generează automat în folderul `audio/`.

## 7. Fluxul de lucru

Când primești „fă o poveste despre X”:

1. **Scrie povestea** respectând secțiunile 1–3 (8–12 pagini, 20–60 de cuvinte pe pagină).
2. **Definește personajele** (descrieri vizuale exacte, în engleză) și stilul.
3. **Generează imaginile** (coperta + câte una pe pagină) cu șablonul din secțiunea 4.
4. **Salvează fișierele** în `public/stories/<id>/` exact ca în secțiunea 6.
5. **Verifică** (dacă poți rula comenzi): `python3 scripts/stories.py validate`
6. **Fă commit și push** pe branch-ul principal. GitHub Actions va:
   valida povestea → genera vocea → actualiza biblioteca → urca site-ul pe host prin FTPS.

O poveste care nu trece validarea **nu** este publicată.
