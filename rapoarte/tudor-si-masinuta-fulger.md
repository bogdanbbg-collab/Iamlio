# Tudor și mașinuța Fulger

**Stare: ❌ NEPUBLICATĂ** · verificată la 2026-10-31 05:00 UTC

Poveste: `public/stories/tudor-si-masinuta-fulger/story.json`

## De corectat (de aceea nu este publicată)

- pagina 9: imaginea images/pagina-09.png nu există
- pagina 10: imaginea images/pagina-10.png nu există
- pagina 11: imaginea images/pagina-11.png nu există
- pagina 12: imaginea images/pagina-12.png nu există

## Note de la publicare

- pagina 9: limita de imagini sau de cost (pe publicare sau pe lună) a fost atinsă; restul se generează la o publicare următoare sau luna viitoare (vezi rapoarte/buget-imagini.md)
- pe site rămâne versiunea publicată anterior (commit 83903e2) până când corectezi problemele de mai sus

## Reparat automat

Aceste lucruri au fost corectate automat în `story.json` (preia versiunea din repository înainte de a modifica din nou povestea):

- coperta: imaginea a fost generată automat (@cf/black-forest-labs/flux-2-klein-4b)
- pagina 1: imaginea a fost generată automat (@cf/black-forest-labs/flux-2-klein-4b)
- pagina 2: imaginea a fost generată automat (@cf/black-forest-labs/flux-1-schnell)
- pagina 4: imaginea a fost generată automat (@cf/black-forest-labs/flux-1-schnell)
- pagina 5: imaginea a fost generată automat (@cf/black-forest-labs/flux-2-klein-4b)
- pagina 7: imaginea a fost generată automat (@cf/black-forest-labs/flux-1-schnell)
- pagina 8: imaginea a fost generată automat (@cf/black-forest-labs/flux-1-schnell)

## Avertismente (merită verificate, dar nu blochează publicarea)

- personaje/ana.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/bulina.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/fulger.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/lio.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)
- personaje/tudor.png: fișier necunoscut, nu se publică (într-o poveste intră doar story.json, images/ și audio/)

## Ce faci mai departe

1. Corectează în `story.json` (și în `images/`) fiecare punct de la „De corectat”, respectând `REGULI_POVESTI.md`.
2. Rulează `python3 scripts/stories.py validate` dacă poți; trebuie să afișeze `[OK]`.
3. Fă commit pe `master`. După câteva minute, citește din nou acest raport.
4. Repetă până când starea este „PUBLICATĂ”.
