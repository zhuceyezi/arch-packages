#!/usr/bin/env bash
set -euo pipefail
name=${1:?package name required}
commit=${2:?source commit required}
[[ $name =~ ^[a-z0-9-]+$ && $commit =~ ^[0-9a-f]{40}$ ]]
root=$(cd "$(dirname "$0")/.." && pwd)
build=${ARCH_BUILD_ROOT:-"$root/work/build"}/$name
mkdir -p "$build" "$root/dist/$name"
cp "$root/packages/$name/"* "$build/"
cd "$build"
export SOURCE_COMMIT=$commit
export PKGREL_OVERRIDE=${GITHUB_RUN_NUMBER:-1}
export PACKAGER='Aleafy <32574743+zhuceyezi@users.noreply.github.com>'
makepkg --noconfirm --cleanbuild --force
mapfile -t packages < <(makepkg --packagelist)
for package in "${packages[@]}"; do
    [[ -f $package ]]
    cp "$package" "$root/dist/$name/"
done
python - "$name" "$commit" "$root" <<'PY'
import json
from pathlib import Path
import sys
import time

name, commit, root = sys.argv[1:]
root = Path(root)
plan = json.loads((root / 'plan.json').read_text())
entry = next(item for item in plan if item['name'] == name and item['commit'] == commit)
entry['built_at'] = int(time.time())
(root / 'dist' / name / 'build.json').write_text(json.dumps(entry, indent=2) + '\n')
PY
