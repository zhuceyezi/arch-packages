#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time


def recipe_hash(name):
    digest = hashlib.sha256()
    for path in sorted(Path('packages', name).rglob('*')):
        if path.is_file():
            digest.update(str(path).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', default='previous/manifest.json')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--candidate-package')
    parser.add_argument('--candidate-commit')
    args = parser.parse_args()
    previous_path = Path(args.previous)
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    selected = []
    for name, source in json.loads(Path('packages.json').read_text()).items():
        if args.candidate_package and name != args.candidate_package:
            continue
        remote = f'https://github.com/{source["repository"]}.git'
        if args.candidate_package:
            commit = args.candidate_commit or ''
        elif 'commit' in source:
            commit = source['commit']
        else:
            ref = f'refs/heads/{source["branch"]}'
            line = subprocess.check_output(['git', 'ls-remote', '--exit-code', remote, ref], text=True)
            commit = line.split()[0]
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise RuntimeError(f'{name}: invalid source commit')
        entry = dict(source, name=name, commit=commit, recipe=recipe_hash(name))
        old = previous.get(name, {})
        changed = any(old.get(key) != entry[key] for key in ('commit', 'recipe'))
        expired = time.time() - old.get('built_at', 0) >= 7 * 24 * 60 * 60
        if args.candidate_package or args.force or changed or expired:
            selected.append(entry)
    if args.candidate_package and not selected:
        raise RuntimeError('plan: unknown candidate package')
    Path('plan.json').write_text(json.dumps(selected, indent=2) + '\n')
    result = {'include': selected}
    print(json.dumps(result))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('matrix=' + json.dumps(result, separators=(',', ':')) + '\n')
            output.write('changed=' + str(bool(selected)).lower() + '\n')
            output.write('publish=' + str(not bool(args.candidate_package)).lower() + '\n')


if __name__ == '__main__':
    main()
