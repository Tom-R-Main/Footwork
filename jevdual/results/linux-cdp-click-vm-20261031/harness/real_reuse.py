"""Four preregistered actual-ID challenges; no protocol response/parameter substitution."""
import asyncio
import ctypes
import importlib.util
import json
import os
import signal
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/workspace/scratch/footwork-cdp-click-c1496ca')
OUT = ROOT / 'real-reuse'
sys.path.insert(0, str(ROOT / 'tests'))  # unchanged test fixture, outside either checkout
from jevdual.effectors.cdp import launch
from jevdual.effectors.cdp.click import ACTIVATE, MARK_DOCUMENT
from jevdual.effectors.cdp.snapshot import STYLES
from test_cdp_click import Fixture, ingress

spec = importlib.util.spec_from_file_location('custody', Path(__file__).with_name('candidate.py'))
custody = importlib.util.module_from_spec(spec)
spec.loader.exec_module(custody)


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def reap():
    rows = []
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
        rows.append({'pid': pid, 'raw_wait_status': status, 'returncode': os.waitstatus_to_exitcode(status)})
    return rows


def cleanup():
    before = custody.descendants()
    signals, waits = [], []
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for row in custody.descendants():
            if row['status'] != 'zombie':
                signals.append({**row, 'signal': sig.value, 'delivery': custody.pinned_signal(row, sig)})
        end = time.monotonic() + 3
        while custody.descendants() and time.monotonic() < end:
            waits.extend(reap())
            time.sleep(.02)
        waits.extend(reap())
        if not custody.descendants():
            break
    return {'before_wrapper_cleanup': before, 'signals': signals, 'adopted_waits': waits,
            'final_owned_descendants': custody.descendants()}


def find_button(node):
    if dict(zip((node.get('attributes') or [])[::2], (node.get('attributes') or [])[1::2])).get('id') == 'intended':
        return node
    for child in node.get('children') or []:
        found = find_button(child)
        if found:
            return found
    return None


def drain(queue):
    rows = []
    while not queue.empty():
        rows.append(queue.get_nowait())
    return rows


async def challenge(chrome, url, records, row):
    async with await Fixture.open(chrome, url) as f:
        contexts = f.setup.listen('Runtime.executionContextCreated', session_id=f.session)
        await f.setup.send('Runtime.enable', session_id=f.session)
        frame = (await f.setup.send('Page.getFrameTree', session_id=f.session))['frameTree']['frame']
        for n in range(row['initial_setup_worlds']):
            await f.setup.send('Page.createIsolatedWorld', {'frameId': frame['id'], 'worldName': f'initial-padding-{n}'},
                               session_id=f.session)
        nm, candidate = await f.observe()
        binding = f.ops._refs[nm.refs[candidate]]
        row['before'] = {
            'execution_context_id': binding.execution_context_id, 'backend_node_id': binding.backend_node_id,
            'frame_id': binding.frame_id, 'loader_id': binding.loader_id,
            'isolate': await f.setup.send('Runtime.getIsolateId', session_id=f.session),
            'renderer_processes': [p for p in (await f.setup.send('SystemInfo.getProcessInfo'))['processInfo']
                                   if p['type'] == 'renderer'],
            'context_events': drain(contexts),
        }
        original = f.ops.conn.send
        row['action_marker_calls'] = 0
        row['resolution_intercepted'] = False

        async def send(method, params=None, **kwargs):
            if method == 'Runtime.callFunctionOn' and (params or {}).get('functionDeclaration') == MARK_DOCUMENT:
                row['action_marker_calls'] += 1
            if method == 'DOM.resolveNode' and not row['resolution_intercepted']:
                row['resolution_intercepted'] = True
                row['unchanged_resolution_request'] = {'method': method, 'params': params, 'kwargs': kwargs}
                loaded = f.setup.listen('Page.loadEventFired', session_id=f.session)
                try:
                    await f.setup.send('Page.navigate', {'url': url.replace('127.0.0.1', 'localhost')},
                                       session_id=f.session)
                    await asyncio.wait_for(loaded.get(), 10)
                finally:
                    f.setup.unlisten(loaded)
                frame = (await f.setup.send('Page.getFrameTree', session_id=f.session))['frameTree']['frame']
                worlds = []
                for n in range(12):
                    world = await f.setup.send('Page.createIsolatedWorld', {
                        'frameId': frame['id'], 'worldName': f'unmarked-collision-{n}'}, session_id=f.session)
                    worlds.append(world['executionContextId'])
                    if worlds[-1] >= binding.execution_context_id:
                        break
                document = None
                for stage in row['allocation_order']:
                    if stage == 'AX':
                        await f.setup.send('Accessibility.getFullAXTree', session_id=f.session)
                    else:
                        document = await f.setup.send('DOM.getDocument', {'depth': -1, 'pierce': True},
                                                      session_id=f.session)
                await f.setup.send('DOMSnapshot.captureSnapshot', {'computedStyles': list(STYLES)},
                                   session_id=f.session)
                await f.setup.send('Page.getLayoutMetrics', session_id=f.session)
                button = find_button(document['root'])
                assert button is not None
                row['after'] = {
                    'world_allocations': worlds, 'execution_context_id': worlds[-1],
                    'backend_node_id': button['backendNodeId'], 'frame_id': frame['id'], 'loader_id': frame['loaderId'],
                    'url': frame['url'], 'isolate': await f.setup.send('Runtime.getIsolateId', session_id=f.session),
                    'renderer_processes': [p for p in (await f.setup.send('SystemInfo.getProcessInfo'))['processInfo']
                                           if p['type'] == 'renderer'], 'context_events': drain(contexts),
                }
                row['numeric_ids_match'] = (worlds[-1] == binding.execution_context_id
                                            and button['backendNodeId'] == binding.backend_node_id)
                row['loader_changed'] = frame['loaderId'] != binding.loader_id
                try:
                    # Forward the ORIGINAL request and return its ORIGINAL real Chrome response.
                    result = await original(method, params, **kwargs)
                except Exception as error:
                    row['original_resolution_error'] = {'type': type(error).__name__, 'message': str(error)}
                    raise
                row['original_resolution_response'] = result
                object_id = (result.get('object') or {}).get('objectId')
                if object_id:
                    inspection = await original('Runtime.callFunctionOn', {
                        'objectId': object_id,
                        'functionDeclaration': "function(key) { return {url:document.URL,id:this.id,type:this.type,text:this.textContent,markerPresent:!!Object.getOwnPropertyDescriptor(globalThis,key)?.value}; }",
                        'arguments': [{'value': f.ops._document_key}], 'returnByValue': True,
                    }, **kwargs)
                    row['actual_resolved_object_inspection'] = inspection
                return result
            result = await original(method, params, **kwargs)
            if method == 'Runtime.callFunctionOn' and (params or {}).get('functionDeclaration') == ACTIVATE:
                row['activation_response'] = result
            return result

        f.ops.conn.send = send
        try:
            effect = await f.bridge.act(nm, 'click', candidate)
            await f.settle()
            row['effect'] = {key: getattr(effect, key) for key in
                             ['effect', 'dispatched', 'delivery', 'retryable', 'error_code', 'route']}
            row['ingress'] = records()
            inspected = row.get('actual_resolved_object_inspection', {}).get('result', {}).get('value', {})
            row['actual_reused_resolution'] = bool(row.get('numeric_ids_match') and row.get('loader_changed')
                                                  and inspected.get('id') == 'intended'
                                                  and inspected.get('url') == url.replace('127.0.0.1', 'localhost'))
            assert row['resolution_intercepted'] and row['action_marker_calls'] == 0
            assert row['ingress'] == [] and effect.effect == 'refused' and effect.dispatched is False
            if row['actual_reused_resolution']:
                assert inspected.get('markerPresent') is False
                assert effect.error_code == 'document_changed'
            row['status'] = 'refused_actual_reuse' if row['actual_reused_resolution'] else 'refused_with_reproduction_gap'
        finally:
            f.ops.conn.send = original
            f.setup.unlisten(contexts)


def main():
    assert sys.prefix == str(ROOT / 'consumer')
    assert not importlib.util.find_spec('cua_driver') and not importlib.util.find_spec('browser_use')
    assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
    OUT.mkdir(mode=0o700)
    plans = [(padding, order) for padding in (0, 1) for order in (['AX', 'DOM'], ['DOM', 'AX'])]
    rows = []
    for number, (padding, order) in enumerate(plans, 1):
        path = OUT / f'attempt-{number:02}'
        path.mkdir(mode=0o700)
        row = {'attempt': number, 'initial_setup_worlds': padding, 'allocation_order': order,
               'source': custody.BASE, 'wheel_sha256': custody.sha(next((ROOT / 'wheel').glob('*.whl'))),
               'harness_sha256': custody.sha(Path(__file__)), 'utc_started': datetime.now(UTC).isoformat()}
        try:
            with contextmanager(ingress.__wrapped__)(path) as (url, records):
                chrome = launch.launch(custody.CHROME, path / 'profile')
                row['browser_identity'] = {'pid': chrome.pid, 'start': chrome.incarnation}
                try:
                    asyncio.run(asyncio.wait_for(challenge(chrome, url, records, row), 45))
                finally:
                    row['before_module_stop'] = custody.descendants()
                    launch.stop(chrome)
                row['saved_ingress'] = records()
        except Exception as error:  # noqa: BLE001 - record failures and finish the fixed batch
            row['status'] = 'failed'
            row['error'] = {'type': type(error).__name__, 'message': str(error)}
        finally:
            row['cleanup'] = cleanup()
            row['utc_finished'] = datetime.now(UTC).isoformat()
            write(path / 'receipt.json', row)
            rows.append(row)
            write(OUT / 'attempts.json', rows)
    summary = {'attempted': len(rows), 'actual_reuse': sum(bool(r.get('actual_reused_resolution')) for r in rows),
               'failed': sum(r['status'] == 'failed' or bool(r['cleanup']['final_owned_descendants']) for r in rows),
               'no_protocol_substitution': True}
    write(OUT / 'summary.json', summary)
    print(json.dumps(summary))
    return 1 if summary['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
