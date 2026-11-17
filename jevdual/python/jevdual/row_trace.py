"""Private, bounded observation diagnostics. Never an input or qualification source."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

MAX_BYTES = 4 * 1024 * 1024


class _SnapshotUnproven(ValueError):
    pass


def get(value, key):
    return value.get(key) if isinstance(value, dict) else getattr(value, key, None)


def configuration(pid: int, window_id: int):
    name = os.environ.get('FOOTWORK_ROW_TRACE_CONFIG')
    if not name:
        return None
    path = Path(name)
    if not path.is_absolute() or path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError('invalid row trace configuration file')
    data = json.loads(path.read_text())
    if set(data) != {'pid', 'window_id', 'url', 'output'}:
        raise ValueError('invalid row trace configuration fields')
    if type(data['pid']) is not int or type(data['window_id']) is not int or (data['pid'], data['window_id']) != (pid, window_id):
        raise ValueError('row trace target mismatch')
    raw_url = data['url']
    if not isinstance(raw_url, str) or len(raw_url) > 2048 or not raw_url.isascii() or any(ord(c) <= 32 or ord(c) == 127 or c in '\\?#' for c in raw_url):
        raise ValueError('invalid row trace URL')
    url = urlsplit(raw_url)
    if (not raw_url.startswith('http://') or url.scheme != 'http'
            or not re.fullmatch(r'127\.0\.0\.1(?::[0-9]+)?', url.netloc)
            or url.port == 0 or url.username or url.password or url.fragment or url.query):
        raise ValueError('row trace requires an exact numeric-loopback page')
    output = Path(data['output'])
    if not output.is_absolute() or output.exists() or output.is_symlink() or output.parent.resolve() != output.parent:
        raise ValueError('row trace requires a new regular private artifact')
    return output, data['url']


def retain(path, request, snapshot, candidates):
    # O_EXCL/O_NOFOLLOW ensures missing evidence cannot be masked by an old file.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        result = {'version': 1, 'request': request, 'snapshot_id': get(snapshot, 'snapshot_id'),
                  'input_performed': False, 'truncated': False, 'status': 'missing_sdk_trace'}
        raw = get(snapshot, 'row_trace_json')
        if isinstance(raw, str) and len(raw.encode()) > MAX_BYTES:
            result.update(status='sdk_trace_oversize', truncated=True)
        elif raw is not None:
            try:
                sdk = json.loads(raw)
                if (type(sdk) is not dict or type(sdk.get('version')) is not int or sdk.get('version') != 1
                        or any(type(request.get(key)) is not int for key in ('pid', 'window_id'))
                        or type(sdk.get('pid')) is not int or type(sdk.get('window_id')) is not int
                        or sdk.get('pid') != request.get('pid') or sdk.get('window_id') != request.get('window_id')
                        or sdk.get('scope_url') != request.get('row_trace_url')):
                    raise ValueError('trace binding mismatch')
                if any(type(get(snapshot, key)) is not int or get(snapshot, key) != request.get(key)
                       for key in ('pid', 'window_id')):
                    raise ValueError('trace envelope identity mismatch')
                snapshot_id, trace_id = get(snapshot, 'snapshot_id'), sdk.get('snapshot_id')
                if not isinstance(snapshot_id, str) or not snapshot_id or not isinstance(trace_id, str) or not trace_id:
                    result.update(status='snapshot_unproven', sdk=None, truncated=sdk.get('truncated') is True,
                                  unbound_summary={k: sdk[k] for k in ('status', 'error', 'node', 'role', 'budget', 'references', 'comparisons', 'reads') if k in sdk})
                    raise _SnapshotUnproven('missing snapshot binding')
                if snapshot_id != trace_id:
                    raise ValueError('trace snapshot mismatch')
                result.update(status='retained', sdk=sdk, truncated=sdk.get('truncated') is True)
                # Unscoped content is never retained, even if a faulty producer emits it.
                if sdk.get('scope_matched') is not True:
                    result['sdk'] = {k: sdk[k] for k in ('version', 'pid', 'window_id', 'status', 'scope_url', 'scope_matched', 'truncated',
                                                       'error', 'node', 'role', 'budget', 'references', 'comparisons', 'reads', 'request') if k in sdk}
                    result['status'] = 'scope_unproven'
                else:
                    result['typed_elements'] = [
                        {'index': get(e, 'element_index'), 'token_present': bool(get(e, 'element_token')),
                         'expected_row': _proof(get(e, 'expected_row'))}
                        for e in (get(snapshot, 'elements') or [])[:2048]
                    ]
                    result['candidates'] = [
                        {'id': get(c, 'id'), 'native_row_control': get(c, 'native_row_control')}
                        for c in candidates[:1000]
                    ]
                    if len(get(snapshot, 'elements') or []) > 2048 or len(candidates) > 1000:
                        result['truncated'] = True
            except _SnapshotUnproven:
                pass
            except (TypeError, ValueError, AttributeError):
                result.update(status='invalid_sdk_trace', sdk=None)
        encoded = json.dumps(result, ensure_ascii=True)
        if len(encoded.encode()) > MAX_BYTES:
            encoded = json.dumps({'version': 1, 'request': request, 'snapshot_id': get(snapshot, 'snapshot_id'),
                                  'status': 'retention_oversize', 'truncated': True, 'input_performed': False})
        stream.write(encoded + '\n')


def _proof(value):
    if value is None:
        return None
    from jevdual.native_row import FIELDS
    return {k: get(value, k) for k in FIELDS}
