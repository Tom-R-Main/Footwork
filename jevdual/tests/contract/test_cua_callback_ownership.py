"""Actual generated SDK callbacks on owned asyncio loops, without creating a Driver."""
import asyncio
import sys
import threading

import pytest
from cua_driver import _native as sdk


def test_foreign_thread_drop_cancels_on_owner_loop(monkeypatch):
    loop = asyncio.new_event_loop(); loop.set_debug(True)
    ready, cancelled = threading.Event(), threading.Event()
    errors = []
    def run():
        asyncio.set_event_loop(loop)
        loop.call_soon(ready.set)
        loop.run_forever()
    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert ready.wait(2)
        async def pending():
            await asyncio.Future()
        future = asyncio.run_coroutine_threadsafe(pending(), loop)
        future.add_done_callback(lambda _: cancelled.set())
        handle = sdk._UNIFFI_FOREIGN_FUTURE_HANDLE_MAP.insert((loop, future))
        monkeypatch.setattr(sys, 'unraisablehook', lambda event: errors.append(str(event.exc_value)))
        sdk._uniffi_future_dropped_callback(handle)
        observed = cancelled.wait(.5)
    finally:
        if 'future' in locals(): future.cancel()
        async def flush(): await asyncio.sleep(0)
        asyncio.run_coroutine_threadsafe(flush(), loop).result(2)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(2)
        assert not thread.is_alive()
        loop.close()
    assert observed, errors
    assert errors == []


@pytest.mark.parametrize('absent', [False, True])
def test_drop_handles_closed_or_absent_owner_loop(monkeypatch, absent):
    loop = asyncio.new_event_loop(); loop.close()
    errors = []
    handle = sdk._UNIFFI_FOREIGN_FUTURE_HANDLE_MAP.insert((None if absent else loop, None))
    monkeypatch.setattr(sys, 'unraisablehook', lambda event: errors.append(str(event.exc_value)))
    sdk._uniffi_future_dropped_callback(handle)
    assert errors == []


@pytest.mark.parametrize('name', ['ForeignDriverEnvelopeChannel', 'DriverServiceTransport'])
def test_remote_object_stays_bound_to_its_owner_loop(name):
    converter = getattr(sdk, '_UniffiFfiConverterType' + name)
    class Object: pass
    obj = Object()
    async def bind():
        h = converter.lower(obj)
        try:
            assert obj._uniffi_foreign_driver_event_loop is asyncio.get_running_loop()
        finally:
            converter._handle_map.remove(h)
    asyncio.run(bind())
    async def wrong_loop():
        with pytest.raises(RuntimeError, match='different asyncio event loop'):
            h = converter.lower(obj)
            # If the guard regresses, retain cleanup even though the assertion fails.
            converter._handle_map.remove(h)
    asyncio.run(wrong_loop())


def test_generation_overlay_reproduces_landed_callback_module(tmp_path):
    import hashlib
    import json
    import subprocess
    from pathlib import Path
    vendor = Path(__file__).resolve().parents[2] / 'vendor/cua-driver'
    manifest = json.loads((vendor / 'patches/python-callback-owner.json').read_text())
    patch = vendor / 'patches/python-callback-owner.patch'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(patch) == manifest['patch_sha256']
    target = tmp_path / manifest['file']
    target.parent.mkdir(parents=True)
    target.write_bytes((vendor / manifest['file']).read_bytes())
    assert digest(target) == digest(Path(sdk.__file__)) == manifest['patched_sha256']
    subprocess.run(['patch', '--batch', '--silent', '-R', '-p1', '-i', str(patch)], cwd=tmp_path, check=True)
    assert digest(target) == manifest['generated_sha256']
    subprocess.run(['patch', '--batch', '--silent', '-p1', '-i', str(patch)], cwd=tmp_path, check=True)
    assert digest(target) == manifest['patched_sha256']
