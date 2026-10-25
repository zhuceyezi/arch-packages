#!/usr/bin/env python3
import html
import json
import os
from pathlib import Path
import shutil
import subprocess


def info(package):
    data = subprocess.check_output(['bsdtar', '-xOf', str(package), '.PKGINFO'], text=True)
    fields = dict(line.split(' = ', 1) for line in data.splitlines() if ' = ' in line)
    return fields['pkgname'], fields['pkgver']


root = Path('site/x86_64')
old_path = Path('previous/manifest.json')
manifest = json.loads(old_path.read_text()) if old_path.exists() else {}
incoming = {}
for path in sorted(Path('dist').glob('*/build.json')):
    entry = json.loads(path.read_text())
    package, = path.parent.glob('*.pkg.tar.zst')
    name, version = info(package)
    if name != entry['name']:
        raise RuntimeError('repository: package name differs from build metadata')
    old = manifest.get(name, {})
    if old.get('version') and int(subprocess.check_output(['vercmp', version, old['version']])) <= 0:
        raise RuntimeError(f'repository: {name} {version} does not upgrade {old["version"]}')
    entry.update(version=version, filename=package.name)
    versions = [package.name, *old.get('archives', [old['filename']] if old else [])]
    entry['archives'] = list(dict.fromkeys(versions))[:3]
    manifest[name] = entry
    incoming[name] = entry
if not incoming:
    raise RuntimeError('repository: no packages were built')
for name, entry in manifest.items():
    if not (root / entry['filename']).is_file():
        raise RuntimeError(f'repository: missing current package for {name}')
keep = {filename for entry in manifest.values()
        for filename in entry.get('archives', [entry['filename']])}
for path in root.glob('*.pkg.tar.zst'):
    if path.name not in keep:
        path.unlink()
        path.with_name(path.name + '.sig').unlink()
packages = [str(root / entry['filename']) for entry in manifest.values()]
subprocess.run(['repo-add', '--sign', '--key', os.environ['REPO_SIGNING_FINGERPRINT'],
                str(root / 'aleafy.db.tar.gz'), *packages], check=True)
for alias in ['aleafy.db', 'aleafy.files', 'aleafy.db.sig', 'aleafy.files.sig']:
    path = root / alias
    target = path.resolve()
    if path.is_symlink():
        path.unlink()
        shutil.copyfile(target, path)
Path('site/manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
links = '\n'.join(f'<li><a href="x86_64/{html.escape(p.name)}">{html.escape(p.name)}</a></li>'
                  for p in sorted(root.iterdir()) if p.is_file())
Path('site/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
    '<title>Aleafy Arch 软件仓库</title><h1>Aleafy Arch 软件仓库</h1>'
    '<p>从个人 fork 构建的签名 Arch 软件包。</p><ul>' + links + '</ul></html>')
