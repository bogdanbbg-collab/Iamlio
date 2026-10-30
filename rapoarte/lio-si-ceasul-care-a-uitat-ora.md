# Lio și ceasul care a uitat ora

**Stare: ❌ NEPUBLICATĂ** · verificată la 2026-10-30 06:40 UTC

Poveste: `public/stories/lio-si-ceasul-care-a-uitat-ora/story.json`

## De corectat (de aceea nu este publicată)

- pagina 1: imaginea images/pagina-01.png nu există
- pagina 3: imaginea images/pagina-03.png nu există
- pagina 4: imaginea images/pagina-04.png nu există
- pagina 6: imaginea images/pagina-06.png nu există

## Note de la publicare

- pagina 1: limita de imagini sau de cost (pe publicare sau pe lună) a fost atinsă; restul se generează la o publicare următoare sau luna viitoare (vezi rapoarte/buget-imagini.md)
- pe site rămâne versiunea publicată anterior (commit 2e2f303) până când corectezi problemele de mai sus

## Avertismente (merită verificate, dar nu blochează publicarea)

- personaje/bunicul-ceas.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/cucu.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/lio.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)

## Ce faci mai departe

1. Corectează în `story.json` (și în `images/`) fiecare punct de la „De corectat”, respectând `REGULI_POVESTI.md`.
2. Rulează `python3 scripts/stories.py validate` dacă poți; trebuie să afișeze `[OK]`.
3. Fă commit pe `master`. După câteva minute, citește din nou acest raport.
4. Repetă până când starea este „PUBLICATĂ”.
