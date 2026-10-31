"""Consumul resurselor folosite de Iamlio, pentru panoul de administrare (secțiunea „Consum și cote”).

Se calculează la fiecare publicare (din stories.py stage) și ajunge în api/data/admin-info.json, câmpul "consum".
Fiecare resursă: nume, cât s-a folosit, limita (sau None, dacă nu are), unitatea, când se resetează și o notă.
Ce nu se poate afla (o cheie lipsă, un serviciu care nu răspunde) se sare, fără să oprească publicarea.
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import voce

CLOUDFLARE_IMAGES_DAY = 50  # estimat: 10.000 de „neuroni” gratuiți pe zi ajung pentru ~50 de imagini FLUX.2 klein 1536×1024
POLLINATIONS_IMAGE_COST = 0.004  # pollen pe imagine (din mesajul de eroare al Pollinations)
ACTIONS_MINUTES_MONTH = 2000  # GitHub Free, repository privat
TIMEOUT = 15


def _number(name, default):
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        return float(default)


def _month_end(now):
    first = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first.replace(hour=0, minute=0, second=0, microsecond=0)


def _day_end(now):
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _read(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _get(url, headers):
    request = urllib.request.Request(url, headers={"User-Agent": "iamlio-publicare", **headers})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def resource(rid, name, used, limit, unit, reset=None, note="", estimated=False):
    return {"id": rid, "nume": name, "folosit": used, "limita": limit, "unitate": unit,
            "resetare": reset.isoformat(timespec="seconds") if reset else None, "nota": note, "estimat": estimated}


def voice(reports, now):
    month = now.strftime("%Y-%m")
    used = int(_read(Path(reports) / "buget-voce.json").get(month, 0))
    limit = int(_number("MAX_TTS_CHARS_MONTH", voce.DEFAULT_CHIRP_MONTH_CHARS))
    note = ("Google Chirp 3 HD: 1.000.000 de caractere gratuite pe lună; la limita de aici vocile trec pe "
            "edge-tts (gratuit) până luna viitoare.")
    if not os.environ.get("GOOGLE_TTS_API_KEY"):
        note = "Cheia GOOGLE_TTS_API_KEY nu e configurată: vocile se fac cu edge-tts. " + note
    return resource("voce", "Voci (Google Chirp 3 HD)", used, limit, "caractere", _month_end(now), note)


def gemini_voice(reports, stories_dir, now):
    """Povestitorul Gemini: cererile de azi din cota gratuită și câte fișiere audio au deja vocea lui."""
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    used = int(_read(Path(reports) / "buget-gemini-voce.json").get(voce.gemini_day(now), 0))
    limit = int(_number("GEMINI_TTS_DAILY", voce.DEFAULT_GEMINI_DAILY))
    done = total = 0
    for manifest_file in Path(stories_dir).glob("*/audio/manifest.json"):
        manifest = _read(manifest_file)
        motor = manifest.get("motor") if isinstance(manifest.get("motor"), dict) else {}
        for key in voce.VOICES:
            files = manifest.get(key) if isinstance(manifest.get(key), dict) else {}
            engines = motor.get(key) if isinstance(motor.get(key), dict) else {}
            total += len(files)
            done += sum(1 for name in files if engines.get(name) == "gemini")
    reset = (now - timedelta(hours=8)).replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return resource("gemini-voce", "Voci Gemini, povestitorul (azi)", used, limit, "cereri", reset,
                    f"{done} din {total} fișiere audio au deja vocea Gemini (cu emoție); celelalte au vocea Chirp și "
                    f"se refac câte {limit} pe zi, întâi poveștile noi și vocea feminină.")


def images(reports, now):
    month = now.strftime("%Y-%m")
    budget = _read(Path(reports) / "buget-imagini.json").get(month) or {}
    if not isinstance(budget, dict):
        budget = {"imagini": budget}
    today = (budget.get("zile") or {}).get(now.date().isoformat()) or {}
    by_provider = budget.get("furnizori") or {}
    found = []
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
        found.append(resource("cloudflare", "Imagini Cloudflare (azi)", int(today.get("cloudflare", 0)),
                              int(_number("CLOUDFLARE_IMAGES_DAY", CLOUDFLARE_IMAGES_DAY)), "imagini", _day_end(now),
                              f"Cotă gratuită pe zi, eliberată treptat, la ~24 de ore după folosire. Luna aceasta: {by_provider.get('cloudflare', 0)} imagini.",
                              estimated=True))
    if os.environ.get("POLLINATIONS_API_KEY"):
        found.append(pollinations(int(by_provider.get("pollinations", 0))))
    if os.environ.get("GEMINI_API_KEY"):
        found.append(resource("gemini", "Imagini Gemini (luna aceasta)", int(by_provider.get("gemini", 0)), None,
                              "imagini", _month_end(now), "Cheia nu are cotă gratuită pentru imagini; se încearcă primul, "
                              "apoi se trece la următorul."))
    if os.environ.get("OPENAI_API_KEY"):
        found.append(resource("openai", "Imagini OpenAI (cost luna aceasta)", round(float(budget.get("lei", 0)), 2),
                              _number("MAX_LEI_MONTH", 100), "lei", _month_end(now),
                              f"Cu plată. {by_provider.get('openai', 0)} imagini luna aceasta."))
    free = sum(int(by_provider.get(name, 0)) for name in ("cloudflare", "pollinations"))
    total = int(budget.get("imagini", 0))
    found.append(resource("imagini", "Imagini cu plată (luna aceasta)", total - free,
                          int(_number("MAX_IMAGES_MONTH", 200)), "imagini", _month_end(now),
                          f"Limita proprie pe lună (variabila MAX_IMAGES_MONTH). În total, {total} imagini luna aceasta, "
                          f"dintre care {free} gratuite (nu intră în limită)."))
    return found


def pollinations(month_images):
    """Soldul de pollen al contului Pollinations (dacă serviciul îl spune)."""
    key = os.environ["POLLINATIONS_API_KEY"]
    note = f"Luna aceasta: {month_images} imagini. O imagine costă ~{POLLINATIONS_IMAGE_COST} pollen."
    try:
        data = _get("https://gen.pollinations.ai/account/balance", {"Authorization": f"Bearer {key}"})
        balance = float(data.get("balance", data.get("pollen")))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return resource("pollinations", "Pollinations (sold)", None, None, "pollen",
                        note=f"Soldul nu a putut fi citit ({str(exc)[:120]}). {note}")
    left = int(balance / POLLINATIONS_IMAGE_COST)
    return resource("pollinations", "Pollinations (sold)", round(balance, 4), None, "pollen",
                    note=f"Ajunge pentru ~{left} imagini. {note}")


def actions_minutes(now):
    """Minutele GitHub Actions din luna aceasta (aproximativ: rotunjite în sus pe fiecare job, ca la facturare)."""
    token, repo = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    api = f"https://api.github.com/repos/{repo}"
    try:
        if not _get(api, headers).get("private", True):
            return resource("actions", "GitHub Actions (minute)", None, None, "minute",
                            note="Repository public: minutele sunt gratuite și nelimitate.")
        start = now.replace(day=1).date().isoformat()
        minutes, page = 0, 1
        while page <= 20:
            runs = _get(f"{api}/actions/runs?created=>={start}&per_page=100&page={page}", headers).get("workflow_runs") or []
            for run in runs:
                minutes += _run_minutes(api, run, headers)
            if len(runs) < 100:
                break
            page += 1
    except (OSError, ValueError) as exc:
        return resource("actions", "GitHub Actions (minute)", None, None, "minute",
                        note=f"Nu s-a putut citi ({str(exc)[:120]}).")
    return resource("actions", "GitHub Actions (minute, luna aceasta)", minutes,
                    int(_number("ACTIONS_MINUTES_MONTH", ACTIONS_MINUTES_MONTH)), "minute", _month_end(now),
                    "Aproximativ (fiecare job rotunjit în sus la minut). Limita: variabila ACTIONS_MINUTES_MONTH "
                    "(2.000 pentru GitHub Free, 3.000 pentru Pro).", estimated=True)


def _duration(start, end):
    if not start or not end:
        return 0
    a = datetime.fromisoformat(start.replace("Z", "+00:00"))
    b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return max(0, -(-int((b - a).total_seconds()) // 60))


def _run_minutes(api, run, headers):
    # publicarea are mai multe joburi în paralel: pentru ea se citesc joburile; celelalte au câte unul
    if "publica-site" not in (run.get("path") or ""):
        return _duration(run.get("run_started_at"), run.get("updated_at"))
    jobs = _get(f"{api}/actions/runs/{run['id']}/jobs?per_page=50", headers).get("jobs") or []
    return sum(_duration(j.get("started_at"), j.get("completed_at")) for j in jobs)


def hosting(site):
    size = sum(f.stat().st_size for f in Path(site).rglob("*") if f.is_file())
    quota = _number("HOSTING_QUOTA_MB", 0)
    return resource("hosting", "Spațiu pe host (site-ul publicat)", round(size / 1_048_576, 1), quota or None, "MB",
                    note="Doar fișierele site-ului (fără datele contorului)." + (
                        "" if quota else " Pune spațiul total al găzduirii în variabila HOSTING_QUOTA_MB ca să vezi și bara."))


def collect(reports, site, now=None, stories_dir=None):
    now = now or datetime.now(timezone.utc)
    found = [voice(reports, now)]
    storyteller = gemini_voice(reports, stories_dir or Path(site) / "stories", now)
    if storyteller:
        found.append(storyteller)
    found += images(reports, now)
    minutes = actions_minutes(now)
    if minutes:
        found.append(minutes)
    found.append(hosting(site))
    return {"actualizat": now.isoformat(timespec="seconds"), "resurse": found}
