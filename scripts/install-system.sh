#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'install-system: run through pkexec' >&2; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
fingerprint=$(cat "$root/keyring/fingerprint")
[[ $fingerprint =~ ^[0-9A-F]{40}$ ]]
key_home=$(mktemp -d)
chmod 700 "$key_home"
trap 'rm -rf "$key_home"' EXIT
actual=$(gpg --homedir "$key_home" --batch --show-keys --with-colons "$root/keyring/aleafy.asc" | awk -F: '$1 == "fpr" {print $10; exit}')
[[ $actual == "$fingerprint" ]] || { echo 'install-system: public key fingerprint differs' >&2; exit 1; }
backup=/var/backups/aleafy-arch/$(date +%Y%m%d-%H%M%S)
mkdir -p "$backup"
cp -a /etc/pacman.conf "$backup/pacman.conf"
if [[ -e /etc/pacman.d/aleafy.conf ]]; then cp -a /etc/pacman.d/aleafy.conf "$backup/aleafy.conf"; fi
install -Dm644 "$root/keyring/aleafy.asc" /etc/pacman.d/keys/aleafy.asc
pacman-key --add /etc/pacman.d/keys/aleafy.asc
pacman-key --lsign-key "$fingerprint"
install -Dm644 "$root/pacman/aleafy.conf" /etc/pacman.d/aleafy.conf
python - <<'PY'
from pathlib import Path
import re

path = Path('/etc/pacman.conf')
text = path.read_text()
include = 'Include = /etc/pacman.d/aleafy.conf'
if include not in text.splitlines():
    match = re.search(r'^\[(?!options\])[^\n]+\]', text, re.MULTILINE)
    if not match:
        raise SystemExit('install-system: cannot find repository section')
    text = text[:match.start()] + include + '\n\n' + text[match.start():]
    path.write_text(text)
PY
pacman-conf --repo aleafy
printf 'System configuration backed up to %s\n' "$backup"
if (( $# )); then
    for package in "$@"; do
        [[ -f $package && -f $package.sig ]]
        pacman-key --verify "$package.sig" "$package"
    done
    pacman -U --needed --noconfirm "$@"
fi
