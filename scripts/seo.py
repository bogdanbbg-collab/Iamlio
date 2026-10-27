"""Tot ce ajută site-ul să fie găsit în Google și citit corect de asistenții AI (ChatGPT, Gemini, Claude…).

Se generează la `stories.py stage`, din poveștile publicate:
- p/<id>.html — pagina statică a fiecărei povești (fără JavaScript): titlu, rezumat, ce învață copilul, textul
  întreg, date structurate (schema.org) și imaginea pentru distribuire (Open Graph). E pagina pe care o indexează
  motoarele de căutare; butonul „Citește cu Lio” deschide cititorul cu voce.
- sitemap.xml — toate paginile, cu data ultimei modificări și coperta fiecărei povești (pentru Google Imagini);
- robots.txt — ce se poate indexa și unde e sitemap-ul;
- llms.txt și llms-full.txt — rezumatul site-ului și textul poveștilor pentru asistenții AI (https://llmstxt.org);
- în index.html: lista tuturor poveștilor ca legături simple (vizibilă și fără JavaScript), datele structurate ale
  site-ului și, dacă sunt setate, codurile de verificare Google Search Console / Bing Webmaster Tools.
"""

import hashlib
import json
import os
import subprocess
from html import escape
from pathlib import Path

import canon

SITE_NAME = "Iamlio"
TAGLINE = "Lio îți citește o poveste"
DESCRIPTION = ("Povești ilustrate pentru copii, în limba română, citite cu voce de Lio, puiul de leu: "
               "cu imaginație, umor, ceva de învățat și un final liniștitor. Gratuit, fără reclame și fără cont.")
CONTACT = "contact@iamlio.ro"


def base_url():
    return (os.environ.get("SITE_URL") or "https://iamlio.ro").rstrip("/")


def story_url(base, sid):
    return f"{base}/p/{sid}.html"


def plain_image(rel):
    """Calea imaginii fără ?v=… (pentru adrese absolute în sitemap și în datele structurate)."""
    return rel.split("?")[0]


def category_labels(ids):
    return [canon.CATEGORIES[c][0] for c in ids or [] if c in canon.CATEGORIES]


def last_changed(sid, fallback):
    """Data ultimei modificări a poveștii (din istoricul git), altfel data publicării."""
    return file_changed(f"public/stories/{sid}", fallback)


def file_changed(rel, fallback=None):
    """Data ultimei modificări a unui fișier sau folder din repository (din istoricul git)."""
    try:
        day = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                             capture_output=True, text=True, timeout=20, cwd=Path(__file__).resolve().parent.parent)
        if day.returncode == 0 and len(day.stdout.strip()) == 10:
            return day.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return fallback


def write_all(site, entries, stories):
    """entries: intrările din stories/index.json (cu minutes, published, cover); stories: story.json publicate."""
    site = Path(site)
    base = base_url()
    by_id = {s["id"]: s for s in stories}
    entries = [e for e in entries if e["id"] in by_id]
    for entry in entries:
        entry["lastmod"] = last_changed(entry["id"], entry.get("published") or entry.get("created"))
    write_thumbnails(site, entries)
    write_story_pages(site, entries, by_id, base)
    write_sitemap(site, entries, by_id, base)
    write_robots(site, base)
    write_llms(site, entries, by_id, base)
    update_home(site, entries, base)


# ---------- coperți mici pentru bibliotecă ----------

THUMB_SIZE = (768, 512)  # destul pentru un card pe telefon cu ecran dens; coperta mare rămâne pentru ecranele late
COVER_SIZES = "(max-width: 640px) calc(100vw - 32px), 380px"


def write_thumbnails(site, entries):
    """Coperta fiecărei povești în mărime de card (de câteva ori mai mică), trecută și în stories/index.json."""
    from PIL import Image, ImageOps

    index_file = site / "stories" / "index.json"
    library = json.loads(index_file.read_text(encoding="utf-8"))
    small = {}
    for entry in entries:
        sid = entry["id"]
        source = site / plain_image(entry["cover"])
        # aceeași variantă mică pe care o folosește și cititorul (stories.py, version_story_assets)
        target = source.with_name(f"{source.stem}-mic.webp")
        try:
            if not target.is_file():
                with Image.open(source) as image:
                    ImageOps.fit(image.convert("RGB"), THUMB_SIZE, Image.LANCZOS).save(target, "WEBP", quality=78, method=6)
        except OSError:
            continue  # fără copertă mică, biblioteca folosește coperta mare
        version = hashlib.sha1(target.read_bytes()).hexdigest()[:10]
        small[sid] = f"stories/{sid}/{target.relative_to(site / 'stories' / sid).as_posix()}?v={version}"
        entry["coverSmall"] = small[sid]
    for story in library.get("stories") or []:
        if story.get("id") in small:
            story["coverSmall"] = small[story["id"]]
    index_file.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------- paginile statice ale poveștilor ----------

def write_story_pages(site, entries, by_id, base):
    from PIL import Image, ImageOps

    folder = site / "p"
    folder.mkdir(exist_ok=True)
    css = site / "assets" / "css" / "pagina.css"
    css_version = hashlib.sha1(css.read_bytes()).hexdigest()[:10] if css.exists() else "1"
    for entry in entries:
        story = by_id[entry["id"]]
        sid = story["id"]
        cover_rel = story["cover"]["image"]
        cover = site / "stories" / sid / plain_image(cover_rel)
        with Image.open(cover) as image:
            card = ImageOps.fit(image.convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.4))
            card.save(folder / f"{sid}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        card_version = hashlib.sha1((folder / f"{sid}.jpg").read_bytes()).hexdigest()[:10]
        others = [e for e in entries if e["id"] != sid]
        (folder / f"{sid}.html").write_text(
            story_page(story, entry, others, base, css_version, card_version), encoding="utf-8")


def story_page(story, entry, others, base, css_version, card_version):
    sid = story["id"]
    url = story_url(base, sid)
    title, summary = escape(story["title"]), escape(story.get("summary") or "")
    reader = f"../poveste.html?id={sid}"
    minutes = entry.get("minutes") or 5
    labels = category_labels(story.get("categories"))
    learning = [x for x in story.get("learning") or [] if isinstance(x, str)]
    cover_rel = story["cover"]["image"]
    data = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": story["title"],
        "headline": story["title"],
        "description": story.get("summary") or "",
        "url": url,
        "image": f"{base}/stories/{sid}/{plain_image(cover_rel)}",
        "inLanguage": "ro",
        "genre": "Poveste pentru copii",
        "isAccessibleForFree": True,
        "timeRequired": f"PT{minutes}M",
        "keywords": ", ".join([*labels, *[t for t in story.get("tags") or [] if isinstance(t, str)]]),
        "teaches": learning,
        "datePublished": entry.get("published") or story.get("created"),
        "dateModified": entry.get("lastmod"),
        "author": {"@type": "Organization", "name": SITE_NAME, "url": f"{base}/"},
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": f"{base}/",
                      "logo": {"@type": "ImageObject", "url": f"{base}/assets/img/icon-512.png"}},
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": f"{base}/"},
    }
    if story.get("moral"):
        data["abstract"] = story["moral"]
    # „</” nu are voie să apară în <script>: o poveste nu poate închide blocul de date
    json_ld = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    pages = "\n".join(f"      <p>{escape(p.get('text') or '')}</p>" for p in story.get("pages") or [])
    learn = "".join(f"<li>{escape(x)}</li>" for x in learning)
    facts = " · ".join([f"~{minutes} minute", *labels])
    more = "\n".join(f'      <li><a href="{escape(e["id"])}.html">{escape(e["title"])}</a></li>' for e in others)
    moral = f'\n      <p class="moral">{escape(story["moral"])}</p>' if story.get("moral") else ""
    return f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{title} — poveste pentru copii citită de Lio | {SITE_NAME}</title>
<meta name="description" content="{summary}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:locale" content="ro_RO">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{base}/p/{sid}.jpg?v={card_version}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Coperta poveștii „{title}”">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/css/pagina.css?v={css_version}">
<script type="application/ld+json">{json_ld}</script>
</head>
<body>
  <header class="top">
    <a class="brand" href="../"><img src="../favicon.svg" alt="" width="40" height="40"><span>I am <strong>Lio</strong></span></a>
  </header>
  <main>
    <article>
      <img class="cover" src="../stories/{sid}/{escape(cover_rel)}" alt="Coperta poveștii „{title}”" width="1536" height="1024">
      <h1>{title}</h1>
      <p class="lead">{summary}</p>
      <p class="facts">{escape(facts)}</p>
      <p><a class="read" href="{reader}">▶ Citește cu Lio</a></p>
      <section>
        <h2>Ce învață copilul</h2>
        <ul>{learn}</ul>
      </section>
      <section class="text">
        <h2>Povestea</h2>
{pages}{moral}
      </section>
      <p><a class="read" href="{reader}">▶ Ascult-o citită de Lio, cu imagini</a></p>
    </article>
    <nav class="more" aria-label="Alte povești">
      <h2>Alte povești</h2>
      <ul>
{more}
      </ul>
      <p><a href="../">Toate poveștile</a></p>
    </nav>
  </main>
  <footer>{SITE_NAME} · povești pentru copii · <a href="../despre.html">Despre</a> · <a href="../confidentialitate.html">Confidențialitate</a> · <a href="mailto:{CONTACT}">{CONTACT}</a></footer>
</body>
</html>
"""


# ---------- sitemap.xml și robots.txt ----------

def write_sitemap(site, entries, by_id, base):
    newest = max((e["lastmod"] for e in entries if e.get("lastmod")), default=None)
    rows = [url_row(f"{base}/", newest), url_row(f"{base}/despre.html", file_changed("public/despre.html")),
            url_row(f"{base}/confidentialitate.html", file_changed("public/confidentialitate.html"))]
    for entry in entries:
        story = by_id[entry["id"]]
        image = (f"{base}/stories/{story['id']}/{plain_image(story['cover']['image'])}", story["title"])
        rows.append(url_row(story_url(base, story["id"]), entry.get("lastmod"), image))
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "".join(rows) + "</urlset>\n", encoding="utf-8")


def url_row(loc, lastmod, image=None):
    row = f"  <url>\n    <loc>{escape(loc)}</loc>\n"
    if lastmod:
        row += f"    <lastmod>{escape(lastmod)}</lastmod>\n"
    if image:
        row += (f"    <image:image><image:loc>{escape(image[0])}</image:loc>"
                f"<image:title>{escape(image[1])}</image:title></image:image>\n")
    return row + "  </url>\n"


def write_robots(site, base):
    (site / "robots.txt").write_text(
        "# Iamlio: tot site-ul poate fi indexat (inclusiv de asistenții AI), în afară de zona de administrare.\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /admin.html\n"
        f"\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")


# ---------- llms.txt pentru asistenții AI ----------

def write_llms(site, entries, by_id, base):
    lines = [f"# {SITE_NAME}", "",
             f"> {SITE_NAME} ({base}) este o bibliotecă gratuită de povești ilustrate pentru copii, în limba română. "
             "Fiecare poveste este citită cu voce (feminină sau masculină, la alegere) de Lio, un pui de leu, iar paginile "
             "se întorc ca într-o carte, cu imagini în stil de film de animație. Poveștile au imaginație, umor, ceva "
             "folositor de învățat și un final liniștitor; la final, Lio pune câteva întrebări. Fără reclame și fără cont.",
             "",
             "Poveștile pot fi filtrate după categorie (de culcare, aventuri, animale, prietenie și emoții, învățăm, "
             "amuzante) și după durată. Fiecare poveste are o pagină cu rezumatul, ce învață copilul și textul complet.",
             "", "## Povești", ""]
    for entry in entries:
        story = by_id[entry["id"]]
        learning = "; ".join(x for x in story.get("learning") or [] if isinstance(x, str))
        details = f"~{entry.get('minutes') or 5} minute"
        if learning:
            details += f"; copilul învață: {learning}"
        lines.append(f"- [{story['title']}]({story_url(base, story['id'])}): {story.get('summary', '')} ({details})")
    lines += ["", "## Despre site", "",
              f"- [Biblioteca de povești]({base}/): toate poveștile, cu filtre după categorie și durată",
              f"- [Despre Iamlio]({base}/despre.html): cum sunt făcute poveștile (reguli de calitate și siguranță)",
              f"- [Confidențialitate]({base}/confidentialitate.html): ce date se folosesc (doar totaluri, fără "
              "reclame, fără urmărire)",
              f"- Contact: {CONTACT}",
              "", "## Optional", "",
              f"- [Textul complet al tuturor poveștilor]({base}/llms-full.txt)", ""]
    (site / "llms.txt").write_text("\n".join(lines), encoding="utf-8")

    full = [f"# {SITE_NAME} — textul complet al poveștilor", "", f"> {DESCRIPTION}", ""]
    for entry in entries:
        story = by_id[entry["id"]]
        full += [f"## {story['title']}", "", f"Adresa: {story_url(base, story['id'])}",
                 f"Durata: ~{entry.get('minutes') or 5} minute",
                 f"Categorii: {', '.join(category_labels(story.get('categories')))}", "",
                 story.get("summary") or "", ""]
        learning = [x for x in story.get("learning") or [] if isinstance(x, str)]
        if learning:
            full += ["Ce învață copilul:", *[f"- {x}" for x in learning], ""]
        full += [p.get("text") or "" for p in story.get("pages") or []]
        if story.get("moral"):
            full += ["", f"Morala: {story['moral']}"]
        full += [""]
    (site / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")


# ---------- pagina principală ----------

NEW_DAYS = 14          # ca în library.js
MIN_FOR_FEATURED = 3
MIN_FOR_PICK = 3


def days_since(day, today):
    from datetime import date

    try:
        return (today - date.fromisoformat(day)).days
    except (TypeError, ValueError):
        return None


def weekly_story(entries, today):
    """Povestea săptămânii, exact ca în library.js (ca pagina să nu se schimbe când pornește JavaScript-ul)."""
    from datetime import date

    if len(entries) < MIN_FOR_FEATURED:
        return ""
    # ca sort-ul stabil din JavaScript: la aceeași zi câștigă cea aflată prima în bibliotecă
    recent = [(d, n, e["id"]) for n, e in enumerate(entries)
              if (d := days_since(e.get("published"), today)) is not None and 0 <= d < 7]
    if recent:
        return min(recent)[2]
    week = (today - date(2024, 1, 1)).days // 7
    ids = sorted(e["id"] for e in entries)
    return ids[week % len(ids)]


def prerender_library(html, entries):
    """Cardurile poveștilor scrise direct în pagină (aceleași ca cele din library.js): se văd imediat, coperta
    principală începe să se descarce odată cu pagina, iar nimic nu mai sare când pornește JavaScript-ul."""
    from datetime import date

    today = date.today()
    featured = weekly_story(entries, today)
    ordered = sorted(entries, key=lambda e: e["id"] != featured)
    cards = []
    for n, entry in enumerate(ordered):
        tags = []
        if entry["id"] == featured:
            tags.append('<span class="story-tag story-featured">⭐ Povestea săptămânii</span>')
        days = days_since(entry.get("published"), today)
        if days is not None and 0 <= days < NEW_DAYS:
            tags.append('<span class="story-tag story-new">Nou</span>')
        first = (entry.get("categories") or [None])[0]
        if first in canon.CATEGORIES and entry["id"] != featured:
            label, emoji = canon.CATEGORIES[first]
            tags.append(f'<span class="story-tag">{emoji} {escape(label)}</span>')
        loading = 'loading="eager" fetchpriority="high"' if n < 2 else 'loading="lazy"'
        srcset = (f' srcset="{escape(entry["coverSmall"])} 768w, {escape(entry["cover"])} 1536w" sizes="{COVER_SIZES}"'
                  if entry.get("coverSmall") else "")
        minutes = entry.get("minutes") or 5
        cards.append(
            f'<article class="story-card" data-id="{escape(entry["id"])}">'
            f'<a class="story-link" href="poveste.html?id={escape(entry["id"])}">'
            f'<div class="story-cover"><img src="{escape(entry["cover"])}"{srcset} alt="" {loading} decoding="async">'
            f'<div class="story-tags">{"".join(tags)}</div><span class="story-play">▶</span></div>'
            f'<div class="story-body"><div class="story-heading"><h3>{escape(entry["title"])}</h3>'
            f'<span class="story-minutes" aria-label="cam {minutes} minute">~{minutes} min</span></div>'
            f'<p class="story-details"></p><p class="story-summary">{escape(entry.get("summary") or "")}</p></div>'
            f'</a></article>')
    if cards:
        html = html.replace('<p class="muted">Se încarcă poveștile…</p>', "\n        ".join(cards), 1)
    # butoanele care depind doar de numărul de povești apar de la început, nu după ce pornește JavaScript-ul
    if len(entries) >= MIN_FOR_PICK:
        html = html.replace('<button id="lio-picks" class="lio-picks" type="button" hidden>',
                            '<button id="lio-picks" class="lio-picks" type="button">', 1)
    if len(entries) > 1:
        html = html.replace('aria-controls="filters" hidden>', 'aria-controls="filters">', 1)
    return html


def update_home(site, entries, base):
    """În index.html: lista poveștilor ca legături simple (pentru cine nu rulează JavaScript, ca roboții AI),
    datele structurate ale site-ului și codurile de verificare pentru Google și Bing (dacă sunt setate)."""
    page = site / "index.html"
    html = page.read_text(encoding="utf-8")
    html = prerender_library(html, entries)
    links = " · ".join(f'<a href="p/{escape(e["id"])}.html">{escape(e["title"])}</a>' for e in entries)
    nav = (f'  <nav class="story-index" aria-label="Toate poveștile">\n    <p><strong>Toate poveștile:</strong> {links}</p>\n'
           f'  </nav>\n\n  <footer class="site-footer">')
    html = html.replace('  <footer class="site-footer">', nav, 1)
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": SITE_NAME, "alternateName": "I am Lio", "url": f"{base}/",
             "inLanguage": "ro", "description": DESCRIPTION},
            {"@type": "Organization", "name": SITE_NAME, "url": f"{base}/", "email": CONTACT,
             "logo": f"{base}/assets/img/icon-512.png"},
            {"@type": "ItemList", "name": "Poveștile lui Lio",
             "itemListElement": [{"@type": "ListItem", "position": n, "url": story_url(base, e["id"]), "name": e["title"]}
                                 for n, e in enumerate(entries, start=1)]},
        ],
    }
    json_ld = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    head = [f'  <script type="application/ld+json">{json_ld}</script>']
    for variable, name in (("GOOGLE_SITE_VERIFICATION", "google-site-verification"), ("BING_SITE_VERIFICATION", "msvalidate.01")):
        code = (os.environ.get(variable) or "").strip()
        if code:
            head.append(f'  <meta name="{name}" content="{escape(code)}">')
    html = html.replace("</head>", "\n".join(head) + "\n</head>", 1)
    page.write_text(html, encoding="utf-8")
