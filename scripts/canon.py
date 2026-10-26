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
