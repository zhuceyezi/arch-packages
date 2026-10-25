#!/usr/bin/env bash
set -euo pipefail
destination=${1:-previous}
mkdir -p "$destination"
if gh api "repos/$GITHUB_REPOSITORY/releases" --jq 'any(.[]; .tag_name == "repo" and any(.assets[]; .name == "manifest.json"))' | grep -qx true; then
    gh release download repo --repo "$GITHUB_REPOSITORY" --dir "$destination" --clobber --pattern manifest.json
    if [[ ${2:-} != manifest-only ]]; then
        python - "$destination/manifest.json" <<'PY' > "$destination/downloads.txt"
import json
import sys
for entry in json.load(open(sys.argv[1])).values():
    for name in entry.get('archives', [entry['filename']]):
        print(name)
        print(name + '.sig')
PY
        while IFS= read -r asset; do
            gh release download repo --repo "$GITHUB_REPOSITORY" --dir "$destination" --clobber --pattern "$asset"
        done < "$destination/downloads.txt"
    fi
fi
