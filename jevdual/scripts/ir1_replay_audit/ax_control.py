"""Real single-write owner/private bus; identity/writability checks stubbed.

This is NOT X11 binding or current product runtime qualification.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import time

from jevdual import linux_ax as ax


@contextlib.contextmanager
def fixture_binding(_element):
    with ax._Bus() as bus:
        yield bus


class Element:
    ref = (os.environ['IR1_TARGET_BUS'], '/org/a11y/atspi/accessible/1')


ax._bound = fixture_binding
ax._validate = lambda *_: None
ax._writable = lambda *_: True
start = time.monotonic()
try:
    ax.set_value_ack(Element(), 'TOKEN')
    outcome = {'ok':True}
except Exception as error:
    outcome = {'ok':False, 'type':type(error).__name__, 'error':str(error), 'code':getattr(error,'code',None)}
print(json.dumps({'boundary':'linux_ax.set_value_ack; binding and writability stubbed; actual private-bus call',
                  'source_sha256':hashlib.sha256(Path(ax.__file__).read_bytes()).hexdigest(),
                  'timeout_seconds':ax._TIMEOUT, 'elapsed_seconds':time.monotonic()-start, **outcome}))
