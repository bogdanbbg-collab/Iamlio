"""Valorile „oficiale” Iamlio, folosite de verificare, de șablon și de comanda `new`.

Dacă schimbi stilul sau aspectul lui Lio, schimbă-le AICI și în REGULI_POVESTI.md (secțiunile 4 și 6),
apoi rulează `python3 scripts/stories.py template` ca să actualizezi sablon/story.json.
"""

# Stilul ilustrațiilor: fiecare imagePrompt îl conține cuvânt cu cuvânt (prin illustrationStyle).
STYLE = (
    "High-quality 3D animated feature film still for young children, modern family animation movie style, "
    "adorable expressive characters with big eyes and soft rounded shapes, detailed soft textures, "
    "warm cinematic lighting, rich gentle colors, magical and cozy atmosphere, shallow depth of field, "
    "nothing scary, no text, no letters, no numbers, no logos. Landscape 3:2 composition, main subject centered."
)
STYLE_MARKERS = ("3d animated", "for young children", "no text", "nothing scary", "landscape 3:2")

# Lio arată mereu la fel.
LIO_DESCRIPTION = (
    "a small, chubby, adorable lion cub with baby proportions (big round head about half of his height), "
    "soft golden-yellow fur, a short fluffy caramel-orange mane with one curly tuft on top, big round dark-brown "
    "sparkling eyes, rosy cheeks, a small brown heart-shaped nose, round ears with pink inside, always wearing a "
    "turquoise scarf with little yellow stars, a caramel tuft at the tip of the tail, walks upright like a "
    "4-year-old child, friendly and curious expression"
)
LIO_MARKERS = ("lion cub", "golden-yellow fur", "caramel-orange mane", "turquoise scarf", "yellow stars")
LIO_VOICE = {"pitch": 12, "rate": 3}

# Categoriile bibliotecii: fiecare poveste are 1–3 (câmpul "categories"). Ordinea de aici e ordinea de pe site.
CATEGORIES = {
    "de-culcare": ("De culcare", "🌙"),
    "aventuri": ("Aventuri", "🧭"),
    "animale": ("Animale", "🐾"),
    "prietenie": ("Prietenie și emoții", "💛"),
    "invatam": ("Învățăm", "📚"),
    "amuzante": ("Amuzante", "😄"),
}
MAX_CATEGORIES = 3

# Ce spune Lio la începutul și la sfârșitul fiecărei povești, după prima ei categorie.
# Se alege mereu aceeași variantă pentru aceeași poveste (după id), ca vocea generată să rămână stabilă.
LIO_INTROS = {
    "de-culcare": ["Bună seara! E vremea de poveste. Pune-te comod sub pătură și ascultă.",
                   "Bună seara, prietene! Stingem lumina mare și pornim într-o poveste liniștită."],
    "aventuri": ["Ești gata de aventură? Ține-te bine, pornim!",
                 "Bună! Azi mergem într-o călătorie. Ia-mă de lăbuță și hai!"],
    "animale": ["Bună! Azi cunoaștem niște animale tare simpatice.",
                "Ssst… auzi? Ne așteaptă prietenii din pădure!"],
    "prietenie": ["Bună! Am pentru tine o poveste despre prieteni.",
                  "Bună! Hai să vedem ce înseamnă să ai un prieten adevărat."],
    "invatam": ["Bună! Azi descoperim ceva nou. Ești curios?",
                "Bună, micuțule explorator! Hai să aflăm ceva interesant."],
    "amuzante": ["Bună! Pregătește-te să râzi, povestea asta e tare haioasă!",
                 "Hi-hi! Am o poveste caraghioasă pentru tine!"],
}
LIO_OUTROS = {
    "de-culcare": ["Noapte bună, somn ușor! Te aștept mâine seară cu o nouă poveste.",
                   "Gata, e timpul de somn. Vise frumoase! Noapte bună!"],
    "default": ["Ți-a plăcut? Te aștept cu drag la o nouă poveste!",
                "Ce poveste frumoasă! Mai citim una data viitoare. Pa-pa!"],
}
LIO_PERSONAL_INTRO = "Bună, {name}! Lio are o poveste specială, doar pentru tine."
LIO_PERSONAL_OUTRO = "Te-ai descurcat minunat, {name}! Te îmbrățișez și te aștept la o nouă poveste."

# Întrebările lui Lio după poveste (câmpul opțional "questions"): fără punctaj, doar pentru joacă.
MAX_QUESTIONS = 3
OPTIONS_PER_QUESTION = (2, 3)
MAX_QUESTION_WORDS = 20

# Poveștile personalizate (câmpul "personalized"): nu apar în bibliotecă, au link secret și așteaptă aprobarea.
PERSONAL_SUFFIX_LENGTH = 6  # id-ul se termină cu un cod aleator, ca link-ul să nu poată fi ghicit

# Autoevaluarea pe care o scrie AI-ul în story.json (câmpul "review").
REVIEW_FIELDS = {
    "imaginatie": "ce element magic sau neobișnuit are povestea",
    "invatare": "cum sunt împletite în acțiune lucrurile din learning (cu paginile)",
    "umor": "lista momentelor amuzante, fiecare cu pagina: [\"pagina 2: …\", \"pagina 5: …\"]",
    "emotie": "problema, cele trei încercări, cum se rezolvă și de ce finalul e liniștitor",
    "siguranta": "de ce nimic din poveste nu sperie sau nu e nepotrivit pentru 3–7 ani",
    "imagini": "cum ai verificat că fiecare imagine arată pagina ei și că personajele sunt identice",
    "voce": "cum ai ales tonurile, pauzele și vocile personajelor",
}
MIN_REVIEW_CHARS = 20
MIN_HUMOR_MOMENTS = 2
MIN_DISTINCT_MOODS = 3
MIN_KNOWN_CHARACTER_DESCRIPTION = 120
PLACEHOLDER = "DE COMPLETAT"

# Animația paginii în cititor (câmpul "animation" pe copertă și pe fiecare pagină): camera se mișcă încet peste
# imagine și, dacă se potrivește cu scena, apare un efect ușor. Le desenează browserul: fără fișiere în plus,
# iar pe telefoanele cu „Reducere mișcare” animația se oprește.
CAMERAS = {
    "zoom-in": "camera se apropie încet (momente importante, emoții, surprize)",
    "zoom-out": "camera se depărtează încet (locuri largi, începuturi, finaluri)",
    "pan-left": "camera alunecă spre stânga",
    "pan-right": "camera alunecă spre dreapta",
    "pan-up": "camera urcă (cer, zbor, copaci înalți)",
    "pan-down": "camera coboară (ceva care cade, privit de sus)",
    "still": "imaginea stă pe loc",
}
EFFECTS = {
    "none": "fără efect",
    "sparkles": "sclipiri aurii (magie, ceva fermecat)",
    "stars": "stele care licăresc (noapte, cer)",
    "leaves": "frunze care cad (toamnă, vânt, pădure)",
    "snow": "fulgi de zăpadă",
    "drops": "picături (ploaie, stropi, apă)",
    "bubbles": "bule care urcă (apă, săpun, ceva care fierbe sau gâlgâie)",
    "glow": "lumină caldă care pâlpâie (lumânare, felinar, foc de tabără, ceva luminos)",
    "fireflies": "licurici (seară de vară, poiană)",
    "hearts": "inimioare care urcă (dragoste, îmbrățișare, mulțumire)",
}
# Când lipsește animația: camerele alternează, iar efectul se ghicește din scenă (cuvinte căutate în acțiunea din
# imagePrompt și în textul paginii, fără diacritice; prima potrivire câștigă).
CAMERA_CYCLE = ("zoom-in", "pan-right", "zoom-out", "pan-left")
EFFECT_HINTS = (
    ("snow", ("snow", "zapad", "fulg")),
    ("glow", ("candle", "lantern", "campfire", "lumanar", "felinar")),
    ("stars", ("starry", "night sky", "stars", "stele", "noaptea")),
    ("fireflies", ("firefl", "licurici")),
    ("leaves", ("autumn leaves", "falling leaves", "frunze")),
    ("drops", ("rain", "raindrop", "splash", "ploaie", "stropi")),
    ("bubbles", ("bubble", "bule")),
    ("hearts", ("hug", "imbratis")),
    ("sparkles", ("sparkl", "magic wand", "fermecat", "magic")),
)
