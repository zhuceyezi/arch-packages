#!/usr/bin/env bash
set -euo pipefail
if ! gh api "repos/$GITHUB_REPOSITORY/releases" --jq 'any(.[]; .tag_name == "repo")' | grep -qx true; then
    gh release create repo --repo "$GITHUB_REPOSITORY" --title 'Aleafy Arch repository' --notes 'Signed Arch packages; pacman uses the atomic GitHub Pages deployment.'
fi
gh release upload repo --repo "$GITHUB_REPOSITORY" --clobber site/x86_64/* site/aleafy.asc
