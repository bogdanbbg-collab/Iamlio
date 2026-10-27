"""Anunță Bing (și celelalte motoare IndexNow: Yandex, Seznam, Naver) despre paginile noi sau schimbate.

Bing alimentează și căutarea din ChatGPT și Copilot, așa că o poveste nouă apare acolo în ore, nu în săptămâni.
Rulează după publicare: `python3 scripts/indexnow.py build/site`. Trimite paginile din sitemap.xml modificate în
ultimele zile (plus pagina principală). Cheia e publică prin definiție (fișierul <cheie>.txt de pe site).
O eroare aici nu oprește publicarea.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ENDPOINT = "https://api.indexnow.org/indexnow"
RECENT_DAYS = 2


def key_of(site):
    for file in sorted(Path(site).glob("*.txt")):
        if re.fullmatch(r"[0-9a-f]{32}", file.stem) and file.read_text(encoding="utf-8").strip() == file.stem:
            return file.stem
    return ""


def recent_urls(site, today=None):
    today = today or date.today()
    xml = (Path(site) / "sitemap.xml").read_text(encoding="utf-8")
    urls = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        mod = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", block)
        if loc and mod and date.fromisoformat(mod.group(1)) >= today - timedelta(days=RECENT_DAYS):
            urls.append(loc.group(1))
    return urls


def main(argv):
    site = argv[1] if len(argv) > 1 else "build/site"
    base = (os.environ.get("SITE_URL") or "https://iamlio.ro").rstrip("/")
    key = key_of(site)
    urls = recent_urls(site)
    if not key or not urls:
        print("IndexNow: nimic de anunțat" if key else "IndexNow: lipsește fișierul cu cheia")
        return 0
    body = {"host": base.split("://", 1)[1], "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls}
    request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"IndexNow: {len(urls)} pagini anunțate (HTTP {response.status})")
    except Exception as exc:  # serviciul extern nu trebuie să oprească publicarea
        print(f"::warning::IndexNow nu a răspuns: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
