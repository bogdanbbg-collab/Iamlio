#!/usr/bin/env bash
# Instalează în GitHub Actions un browser Playwright (chromium | firefox | webkit) cu dependențele lui, rapid:
# - pachetele de sistem (.deb) se păstrează între rulări în ~/.cache/apt-browser (salvat de actions/cache),
#   iar browserul în ~/.cache/ms-playwright;
# - descărcarea folosește oglinda principală Ubuntu, nu oglinda Azure a mașinilor GitHub, care a fost uneori
#   atât de lentă încât instalarea nu se mai termina (vezi și instaleaza_ffmpeg.sh).
set -euo pipefail

browser="${1:?browserul: chromium, firefox sau webkit}"
CACHE="$HOME/.cache/apt-browser"
mkdir -p "$CACHE/partial"
sudo sed -i 's#mirror+file:/etc/apt/apt-mirrors.txt#http://archive.ubuntu.com/ubuntu/#g' \
  /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true
printf 'Dir::Cache::archives "%s";\nAcquire::Retries "3";\nAcquire::http::Timeout "30";\n' "$CACHE" \
  | sudo tee /etc/apt/apt.conf.d/99-iamlio >/dev/null
npx playwright install-deps "$browser"
sudo rm -rf "$CACHE/partial" "$CACHE/lock"
sudo chown -R "$(id -u):$(id -g)" "$CACHE"
npx playwright install "$browser"
