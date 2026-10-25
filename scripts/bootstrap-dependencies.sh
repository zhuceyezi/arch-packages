#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
cp "$root/packages/python-pulsectl/"* "$build/"
chown -R builder:builder "$build"
commit=$(python -c 'import json; print(json.load(open("packages.json"))["python-pulsectl"]["commit"])')
runuser -u builder -- env SOURCE_COMMIT="$commit" bash -c 'cd "$1"; makepkg --noconfirm --force' bash "$build"
pacman -U --noconfirm "$build/"*.pkg.tar.zst
