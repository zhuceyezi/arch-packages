#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
fingerprint=${REPO_SIGNING_FINGERPRINT:?signing fingerprint required}
[[ $fingerprint =~ ^[0-9A-F]{40}$ ]]
export GNUPGHOME
GNUPGHOME=$(mktemp -d)
chmod 700 "$GNUPGHOME"
trap 'gpgconf --kill all; rm -rf "$GNUPGHOME"' EXIT
printf '%s' "${REPO_SIGNING_KEY:?signing key required}" | gpg --batch --import
unset REPO_SIGNING_KEY
gpg --batch --import keyring/aleafy.asc
if ! gpg --batch --list-secret-keys --with-colons "$fingerprint" | grep -q '^sec:'; then
    echo 'publish: signing key does not match pinned fingerprint' >&2
    exit 1
fi
mkdir -p site/x86_64
for file in previous/*.pkg.tar.zst previous/*.pkg.tar.zst.sig; do
    [[ ! -e $file ]] || cp "$file" site/x86_64/
done
for package in site/x86_64/*.pkg.tar.zst; do
    [[ ! -e $package ]] || gpg --batch --verify "$package.sig" "$package"
done
for package in dist/*/*.pkg.tar.zst; do
    [[ -e $package ]]
    gpg --batch --yes --local-user "$fingerprint" --detach-sign "$package"
    cp "$package" "$package.sig" site/x86_64/
done
python scripts/repository.py
cp keyring/aleafy.asc site/aleafy.asc
cp site/manifest.json site/x86_64/manifest.json
touch site/.nojekyll
if ! gh api "repos/$GITHUB_REPOSITORY/releases" --jq 'any(.[]; .tag_name == "repo")' | grep -qx true; then
    gh release create repo --repo "$GITHUB_REPOSITORY" --title 'Aleafy Arch repository' --notes 'Signed Arch packages; pacman uses the atomic GitHub Pages deployment.'
fi
gh release upload repo --repo "$GITHUB_REPOSITORY" --clobber site/x86_64/* site/aleafy.asc
