#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
POLICY = json.loads((ROOT / 'upstream.json').read_text())


def git(path, *args, check=True):
    return subprocess.run(['git', '-C', str(path), *args], check=check,
                          capture_output=True, text=True)


def releases(repository):
    # Public release metadata only; never load local gh/keychain credentials.
    rows = []
    page = 1
    while True:
        request = urllib.request.Request(
            f'https://api.github.com/repos/{repository}/releases?per_page=100&page={page}',
            headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'arch-upstream-check'})
        with urllib.request.urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise RuntimeError('unexpected release API response')
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        page += 1


def version(tag):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', tag)
    return tuple(map(int, match.groups())) if match else None


def guard(name, path, ref):
    policy = POLICY[name]
    failures = []
    if git(path, 'merge-base', '--is-ancestor', policy['custom_baseline'], ref,
           check=False).returncode:
        failures.append('自定义功能基线不在候选版本历史中')
    for feature in policy['features']:
        for filename, anchors in feature['files'].items():
            result = git(path, 'show', f'{ref}:{filename}', check=False)
            if result.returncode or any(anchor not in result.stdout for anchor in anchors):
                failures.append(feature['name'] + ': ' + filename)
    return failures


def check_one(name, workspace_root=None):
    policy = POLICY[name]
    path = workspace_root / name if workspace_root else Path(policy['path'])
    if workspace_root and not path.exists():
        workspace_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--branch', policy['branch'],
                        f'https://github.com/{policy["fork"]}.git', str(path)], check=True)
    remote = git(path, 'remote', 'get-url', 'origin').stdout.strip()
    if remote != f'https://github.com/{policy["fork"]}.git':
        raise RuntimeError(name + ': origin does not match the authorized fork')
    git(path, 'fetch', '--no-tags', 'origin',
        f'refs/heads/{policy["branch"]}:refs/remotes/origin/{policy["branch"]}')
    ref = 'origin/' + policy['branch']
    head = git(path, 'rev-parse', ref).stdout.strip()
    failures = guard(name, path, ref)
    if failures:
        return {'name': name, 'status': 'blocked', 'reason': 'customization',
                'details': failures, 'fork_commit': head}
    rows = []
    for attempt in range(3):
        try:
            rows = releases(policy['upstream'])
            break
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(2)
    stable = [row for row in rows if not row.get('draft') and not row.get('prerelease')
              and version(row.get('tag_name', ''))]
    if not stable:
        raise RuntimeError(name + ': no published stable release found')
    latest = max(stable, key=lambda row: version(row['tag_name']))
    tag = latest['tag_name']
    if version(tag) < version(policy['baseline_version']):
        raise RuntimeError(name + ': upstream release feed predates the configured baseline')
    target = f'refs/upstream-sync/{name}/{tag}'
    git(path, 'fetch', '--no-tags', f'https://github.com/{policy["upstream"]}.git',
        f'refs/tags/{tag}:{target}')
    commit = git(path, 'rev-parse', target + '^{commit}').stdout.strip()
    included = git(path, 'merge-base', '--is-ancestor', commit, head, check=False).returncode == 0
    return {'name': name, 'status': 'current' if included else 'update_available',
            'tag': tag, 'upstream_commit': commit, 'fork_commit': head,
            'release_url': latest['html_url'], 'branch': policy['branch'],
            'local_changes_preserved': bool(git(path, 'status', '--porcelain').stdout)}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('check')
    check.add_argument('package', choices=[*POLICY, 'all'], default='all', nargs='?')
    check.add_argument('--workspace-root', type=Path,
                       help='Cloud checkout root; clone missing public forks without credentials')
    gate = commands.add_parser('guard')
    gate.add_argument('package', choices=POLICY)
    gate.add_argument('path', type=Path)
    gate.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    if args.command == 'guard':
        failures = guard(args.package, args.path, args.ref)
        print(json.dumps({'package': args.package, 'passed': not failures,
                          'failures': failures}, ensure_ascii=False, indent=2))
        return bool(failures)
    results = []
    for name in POLICY if args.package == 'all' else [args.package]:
        try:
            results.append(check_one(name, args.workspace_root))
        except Exception as error:
            results.append({'name': name, 'status': 'error', 'detail': str(error)})
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return any(row['status'] in {'error', 'blocked'} for row in results)


if __name__ == '__main__':
    sys.exit(main())
