"""Synchronize the installed tool snapshot from the repository's authoritative tools tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

FAMILIES = ('browser-inspection', 'inspection-experiments', 'inspection-transport',
            'camera-capture-experiment', 'desk-inbox-experiment', 'workbench-notes', 'physical-workcell')
SUFFIXES = {'.py', '.mjs', '.json', '.xml', '.html', '.swift', '.txt', '.md'}
EXCLUDED = {'output', 'results', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.git'}


def inventory(project: Path) -> dict[str, bytes]:
    result = {}
    for family in FAMILIES:
        candidates = []
        for directory, dirs, names in os.walk(project / 'tools' / family, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith('.'))
            candidates.extend(Path(directory) / name for name in sorted(names))
        for path in candidates:
            relative = path.relative_to(project / 'tools')
            if any(part in EXCLUDED or part.startswith('.') for part in relative.parts):
                continue
            if path.name.startswith('test_') or '.test.' in path.name or path.suffix not in SUFFIXES:
                continue
            if path.is_symlink():
                raise ValueError(f'Tool sources must not be symlinks: {relative}')
            if path.is_file():
                if path.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError(f'Oversized tool source: {relative}')
                result[relative.as_posix()] = path.read_bytes()
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in result.items()}
    result['MANIFEST.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    return result


def synchronize(project: Path, *, check: bool = False) -> int:
    target = project / 'jevdual/python/jevdual/_tool_resources'
    files = inventory(project)
    actual = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if check:
        if actual != files:
            raise ValueError('Installed tool snapshot differs from tools/: run scripts/sync_tool_resources.py')
        return len(files)
    target.mkdir(parents=True, exist_ok=True)
    for name in actual.keys() - files.keys():
        (target / name).unlink()
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = synchronize(Path(__file__).resolve().parents[2], check=args.check)
    print(json.dumps({'files': count, 'checked': args.check}))


if __name__ == '__main__':
    main()
