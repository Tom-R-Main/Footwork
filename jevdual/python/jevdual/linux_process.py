"""Linux process observations and pinned *individual* signal delivery.

Custody comes from the supervisor, not from possession of a numeric PID. Start
and owner observations are validated across fd acquisition. The pidfd prevents
retargeting after acquisition; it does not prove ancestry or kill a process tree.
No unsupported/denied/exhausted path falls back to numeric signalling.
"""
from __future__ import annotations

import errno
import os
import signal
from pathlib import Path


class ProcessInventory(dict):
    def __init__(self):
        super().__init__()
        self.complete = True
        self.reasons: set[str] = set()
        self.scanned = 0
        self.vanished = 0

    def incomplete(self, reason: str) -> None:
        self.complete = False
        self.reasons.add(reason)


def read_process(pid: int, *, proc: Path = Path('/proc')) -> dict:
    with (proc / str(pid) / 'stat').open('rb') as stream:
        uid = os.fstat(stream.fileno()).st_uid
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('process_stat_oversized')
    fields = raw.decode().rsplit(')', 1)[1].split()
    return {'state': fields[0], 'parent': int(fields[1]), 'group': int(fields[2]),
            'session': int(fields[3]), 'start': fields[19], 'uid': uid}


def process_table(*, limit: int = 16384, proc: Path = Path('/proc')) -> ProcessInventory:
    """Coverage means bounded directory enumeration, never an atomic tree snapshot."""
    result = ProcessInventory()
    try:
        for index, entry in enumerate(proc.iterdir()):
            if index >= limit:
                result.incomplete('entry_limit')
                break
            result.scanned += 1
            if not entry.name.isdigit():
                continue
            try:
                result[int(entry.name)] = read_process(int(entry.name), proc=proc)
            except OSError as exc:
                if exc.errno in (errno.ENOENT, errno.ESRCH):
                    result.vanished += 1
                else:
                    result.incomplete('process_read_unavailable')
            except (ValueError, IndexError):
                result.incomplete('invalid_process_record')
    except OSError:
        result.incomplete('inventory_unavailable')
    return result


def _error(exc: OSError) -> str:
    if exc.errno in (errno.ESRCH, errno.ENOENT):
        return 'exited'
    if exc.errno in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
        return 'unsupported'
    if exc.errno in (errno.EPERM, errno.EACCES):
        return 'denied'
    if exc.errno in (errno.EMFILE, errno.ENFILE):
        return 'resource_exhausted'
    return 'unavailable'


def pin_signal(pid: int, expected: dict, sig: int) -> dict:
    """Validate an already-owned observation across pidfd acquisition, then signal.

    Observable start stamps are not a standalone race-free custody oracle.
    flags=0 intentionally addresses one pinned process, never its descendants.
    """
    result = {'pid': pid, 'signal': sig, 'status': 'unsupported', 'delivery': None}
    if not callable(getattr(os, 'pidfd_open', None)) or not callable(getattr(signal, 'pidfd_send_signal', None)):
        return result
    fd = None
    try:
        before = read_process(pid)
        if before['start'] != expected.get('start') or before['uid'] != os.getuid():
            return {**result, 'status': 'identity_changed'}
        fd = os.pidfd_open(pid, 0)
        after = read_process(pid)
        if after['start'] != before['start'] or after['uid'] != before['uid']:
            return {**result, 'status': 'identity_changed'}
        signal.pidfd_send_signal(fd, sig, None, 0)
        return {**result, 'status': 'sent', 'delivery': 'pidfd'}
    except OSError as exc:
        return {**result, 'status': _error(exc), 'errno': exc.errno}
    except (ValueError, IndexError, KeyError):
        return {**result, 'status': 'invalid_identity'}
    finally:
        if fd is not None:
            os.close(fd)
