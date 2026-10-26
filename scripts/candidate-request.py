#!/usr/bin/env python3
"""Translate a connector-created validation branch into non-publishing inputs."""
import json
import os
from pathlib import Path
import re


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate candidate request key')
        result[key] = value
    return result


def resolve(event, ref, package, commit, request_path):
    if ref != 'refs/heads/main' and not ref.startswith('refs/heads/candidate-validation/'):
        raise ValueError('unauthorized workflow ref')
    validation = ref.startswith('refs/heads/candidate-validation/')
    if validation:
        if event != 'push':
            raise ValueError('candidate branches only accept push events')
        request = json.loads(Path(request_path).read_text(), object_pairs_hook=unique_object)
        if not isinstance(request, dict) or set(request) != {'package', 'commit'}:
            raise ValueError('candidate request must contain only package and commit')
        package, commit = request['package'], request['commit']
    if package and package != 'none':
        if package not in {'linux-arctis-manager', 'elyterminal'}:
            raise ValueError('unauthorized candidate package')
        if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('candidate commit must be a full lowercase SHA')
        return package, commit
    if validation or commit:
        raise ValueError('invalid empty candidate request')
    return '', ''


if __name__ == '__main__':
    if os.environ.get('GITHUB_REPOSITORY') != 'zhuceyezi/arch-packages':
        raise ValueError('unauthorized workflow repository')
    package, commit = resolve(os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'],
                             os.getenv('INPUT_PACKAGE', ''), os.getenv('INPUT_COMMIT', ''),
                             '.github/candidate.json')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'package={package}\ncommit={commit}\n')
