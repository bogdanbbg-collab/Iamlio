#!/usr/bin/env bash
# Instalează ffmpeg (și ffprobe) în GitHub Actions, rapid și fără să depindă de o singură oglindă Ubuntu:
# - pachetele .deb se păstrează între rulări în ~/.cache/apt-ffmpeg (salvat de actions/cache);
# - descărcarea folosește oglinda principală Ubuntu, nu oglinda Azure a mașinilor GitHub, care a fost uneori
#   foarte lentă (sub 60 KB/s), iar instalarea nu se mai termina.
set -euo pipefail

if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  exit 0
fi

CACHE="$HOME/.cache/apt-ffmpeg"
mkdir -p "$CACHE/partial"
sudo sed -i 's#mirror+file:/etc/apt/apt-mirrors.txt#http://archive.ubuntu.com/ubuntu/#g' \
  /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true
sudo apt-get update -q -o Acquire::Retries=3
sudo apt-get install -y -q --no-install-recommends -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
  -o Dir::Cache::archives="$CACHE" ffmpeg
sudo rm -rf "$CACHE/partial" "$CACHE/lock"
sudo chown -R "$(id -u):$(id -g)" "$CACHE"
ffmpeg -version | head -1
