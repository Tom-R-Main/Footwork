"""SIM5 actual HTTP/SQLite/native-controller backend conformance.

Private application cases and owned processes are retained under output.
Public controller RGB supplies targets; server verifies real staged evidence.
"""
import hashlib
import json
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.client import HTTPConnection
from pathlib import Path

BASE = Path(__file__).resolve().parent
APP = BASE / 'order_app.py'
CONTROLLER = BASE / 'controller.py'
TERMINAL = {'executed', 'staged', 'cancelled', 'refused', 'unknown'}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(content):
    return hashlib.sha256(content).hexdigest()


class OrderApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = BASE / 'output' / ('a5' + uuid.uuid4().hex[:7])
        self.directory.mkdir(mode=0o700)
        self.app = self.directory / 'app'
        self.processes = []
        self.handles = []
        self.events = []
        self.origin = None
        self.app_id = None
        self.order_id = 'order-' + uuid.uuid4().hex[:8]
        self.work_order = {'version': 1, 'order_id': self.order_id,
            'project': {'namespace': 'test', 'project_id': 'application-conformance'},
            'part_id': 'block', 'target_zone': {'x_min': .14, 'x_max': .22, 'y_min': -.04, 'y_max': .04}}
        self.seed = {**self.work_order, 'revision': 1, 'state': 'open'}
        self.native = None
        self.control = None
        self.incarnation = None
        self.lease = None

    def tearDown(self):
        cleanup = []
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=4)
            cleanup.append({'pid': process.pid, 'exit_code': process.poll()})
        for handle in self.handles:
            handle.close()
        failed = any(test is self or getattr(test, 'test_case', None) is self
                     for test, _ in (*self._outcome.result.failures, *self._outcome.result.errors))
        self.retain(self.directory / 'conformance.json', {'test_id': self.id(), 'passed': not failed,
            'events': self.events, 'owned_process_cleanup': cleanup,
            'classification': 'actual HTTP/SQLite/native controller diagnostic, not browser or AI benchmark'})

    def retain(self, path, value):
        path.write_bytes(encoded(value))
        path.chmod(0o600)
        return path

    def event(self, value):
        self.events.append({'time_unix': time.time(), **value})

    def command(self, argv):
        argv = list(map(str, argv))
        result = subprocess.run(argv, capture_output=True, text=True, timeout=12, check=False)
        try:
            body = json.loads(result.stdout)
        except ValueError:
            self.fail(f'non-JSON CLI reply {result.stdout!r} stderr={result.stderr!r}; retained {self.directory}')
        self.event({'kind': 'public_cli', 'command': argv, 'exit_code': result.returncode,
                    'reply': body, 'stderr': result.stderr})
        return body

    def spawn(self, argv, name):
        path = self.directory / (name + '.log')
        handle = path.open('xb')
        path.chmod(0o600)
        self.handles.append(handle)
        argv = list(map(str, argv))
        process = subprocess.Popen(argv, stdout=handle, stderr=subprocess.STDOUT)
        self.processes.append(process)
        self.event({'kind': 'owned_process', 'command': argv, 'pid': process.pid, 'log': str(path)})
        return process

    def initialize_app(self):
        path = self.retain(self.directory / 'seed.json', self.seed)
        result = self.command([sys.executable, APP, 'init', '--app-dir', self.app,
                               '--order-file', path, '--order-sha256', sha(path.read_bytes())])
        self.assertNotEqual(result.get('phase'), 'refused', result)

    def serve_app(self, *, restart=False, fault_script=None):
        port = urllib.parse.urlsplit(self.origin).port if restart else 0
        process = self.spawn([sys.executable, fault_script or APP, 'serve', '--app-dir', self.app,
                              '--port', port], 'app-' + str(len(self.processes)))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if process.poll() is not None:
                self.fail(f'app startup failed {process.returncode}; retained {self.directory}')
            readiness = self.app / 'readiness.json'
            if readiness.exists():
                info = json.loads(readiness.read_bytes())
                if info.get('pid') == process.pid:
                    self.origin = info['origin']
                    code, health = self.http('GET', '/api/health')
                    if code == 200:
                        self.app_id = health['app_id']
                        return process, health
            time.sleep(.04)
        self.fail(f'app readiness timed out; retained {self.directory}')

    def http(self, method, path, body=None, *, origin=True, extra_headers=None):
        headers = {'Accept': 'application/json'}
        content = None if body is None else encoded(body)
        if content is not None:
            headers['Content-Type'] = 'application/json'
        if method == 'POST':
            headers['X-Footwork-App-ID'] = self.app_id
        if origin:
            headers['Origin'] = self.origin
        headers.update(extra_headers or {})
        request = urllib.request.Request(self.origin + path, data=content, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.status
            value = json.loads(response.read())
        self.event({'kind': 'http', 'method': method, 'path': path, 'request': body,
                    'headers': headers, 'status': status, 'reply': value})
        return status, value

    def order_path(self, action=''):
        return '/api/orders/' + self.order_id + (('/' + action) if action else '')

    def start(self):
        self.initialize_app()
        return self.serve_app()

    def bind(self):
        code, reply = self.http('POST', self.order_path('bind'),
                                {'expected_revision': 1, 'binding_operation_id': 'bind-' + uuid.uuid4().hex})
        self.assertEqual(code, 200, reply)
        self.assertEqual(reply['app_id'], self.app_id)
        self.lease = reply['lease']
        self.assertEqual(self.lease['work_order'], self.work_order)
        self.assertEqual(self.lease['expected_revision'], 1)
        return self.lease

    def start_native(self, *, pace=0, placed=False, altered_order=None):
        lease = self.lease
        self.control = Path(lease['controller_dir'])
        case = {'version': 1, 'case_id': lease['lease_id'], 'max_actions': 8,
                'scene': {'block_xy': [.175, .004] if placed else [-.138, .004],
                          'illumination_scale': 1, 'occlusion_fraction': 0, 'camera_offset_x_m': 0},
                'work_order': altered_order or lease['work_order']}
        path = self.retain(self.directory / ('case-' + lease['lease_id'] + '.json'), case)
        result = self.command([sys.executable, BASE / 'episode_runner.py', 'init', '--case-file', path,
                              '--case-sha256', sha(path.read_bytes()), '--run-dir', lease['run_dir']])
        self.assertEqual(result['phase'], 'active', result)
        self.native = self.spawn([sys.executable, CONTROLLER, 'serve', '--run-dir', lease['run_dir'],
                                  '--controller-dir', self.control, '--pace-s', pace],
                                 'native-' + str(len(self.processes)))
        return self.native_ready()

    def native_ready(self):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.native.poll() is not None:
                self.fail(f'native startup failed; retained {self.directory}')
            result = self.controller('health')
            if result.get('phase') != 'refused' and result.get('current_incarnation'):
                self.incarnation = result['current_incarnation']
                return result
            time.sleep(.04)
        self.fail('native readiness timed out')

    def controller(self, command, *args):
        return self.command([sys.executable, CONTROLLER, command, '--controller-dir', self.control, *args])

    def observe(self):
        result = self.controller('observe')
        self.assertEqual(result['phase'], 'ready', result)
        return result['observation']

    def proposal(self, packet, token, *, complete=False, advance=.105):
        value = {'version': 1, 'run_dir': self.lease['run_dir'], 'generation': packet['generation'],
                 'image_sha256': packet['image_sha256'], 'token': token,
                 'block_box': packet['perception']['block_box'], 'decision': 'complete' if complete else 'move'}
        if not complete:
            value['target'] = {'x': packet['perception']['pusher_center_xy'][0] + advance, 'y': .004}
        path = self.retain(self.directory / ('proposal-' + token + '.json'), value)
        return path, sha(path.read_bytes())

    def submit(self, ident, proposal):
        result = self.controller('submit', '--operation-id', ident, '--proposal-file', proposal[0],
                                 '--proposal-sha256', proposal[1], '--expected-incarnation', self.incarnation)
        self.assertIn(result['phase'], {'accepted', 'running', 'executed', 'staged'}, result)
        return result

    def until(self, ident, phases=TERMINAL):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            result = self.controller('status', '--operation-id', ident)
            if result.get('phase') in phases:
                return result
            time.sleep(.05)
        self.fail(f'controller status timed out for {ident}')

    def stage(self):
        contacts = 0
        for index in range(7):
            packet = self.observe()
            zone = packet['task_intent']['target_zone']
            block = packet['perception']['block_center_xy']
            pusher = packet['perception']['pusher_center_xy']
            inside = (zone['x_min'] + .005 <= block[0] <= zone['x_max'] - .005 and
                      zone['y_min'] + .005 <= block[1] <= zone['y_max'] - .005)
            ident = self.lease['physical_completion_id'] if inside else 'move-' + str(index)
            gap = max(0, block[0] - pusher[0] - .055)
            advance = min(.105, max(.015, gap + (zone['x_min'] + zone['x_max']) / 2 - block[0]))
            self.submit(ident, self.proposal(packet, ident, complete=inside, advance=advance))
            final = self.until(ident)
            if inside:
                self.assertEqual(final['phase'], 'staged', final)
                return final, contacts
            self.assertEqual(final['phase'], 'executed', final)
            contacts += final['receipt']['contact_statistics']['pusher_block_contact_samples']
        self.fail('RGB feedback did not stage with completion slot reserved')

    def fulfill(self, **changes):
        value = {'lease_id': self.lease['lease_id'],
                 'completion_operation_id': self.lease['completion_operation_id'], **changes}
        return self.http('POST', self.order_path('fulfill'), value)

    def db_rows(self):
        db = sqlite3.connect('file:' + str(self.app / 'orders.sqlite3') + '?mode=ro', uri=True)
        try:
            order = db.execute('SELECT order_id,revision,state,work_order_json FROM orders WHERE order_id=?',
                               (self.order_id,)).fetchone()
            count = db.execute("SELECT COUNT(*) FROM operations WHERE kind='fulfill'").fetchone()[0]
        finally:
            db.close()
        self.event({'kind': 'independent_sqlite_readback', 'order_row': order, 'fulfillment_effect_count': count})
        return order, count

    def test_real_contact_fulfillment_commits_exact_version_and_receipt(self):
        self.start()
        code, order = self.http('GET', self.order_path())
        self.assertEqual(code, 200)
        self.assertEqual(order['order']['revision'], 1)
        self.bind()
        self.start_native()
        physical, contacts = self.stage()
        self.assertGreater(contacts, 0)
        code, receipt = self.fulfill()
        self.assertEqual(code, 200, receipt)
        saved, count = self.db_rows()
        self.assertEqual((saved[1], saved[2], count), (2, 'fulfilled', 1))
        read_code, readback = self.http('GET', '/api/operations/' + self.lease['completion_operation_id'])
        self.assertEqual(read_code, 200)
        self.assertEqual(readback['receipt'], receipt['receipt'])
        self.assertEqual(physical['receipt']['token'], self.lease['physical_completion_id'])

    def test_concurrent_bind_allocates_one_workspace_per_order_revision(self):
        self.start()
        barrier = threading.Barrier(3)
        replies = []
        errors = []
        requests = [{'expected_revision': 1, 'binding_operation_id': 'parallel-' + uuid.uuid4().hex}
                    for _ in range(2)]

        def bind_in_parallel(payload):
            try:
                barrier.wait(timeout=5)
                code, reply = self.http('POST', self.order_path('bind'), payload)
                replies.append((payload, code, reply))
            except (OSError, ValueError, threading.BrokenBarrierError) as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=bind_in_parallel, args=(payload,)) for payload in requests]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=8)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertFalse(errors, errors)
        self.assertEqual(len(replies), 2)
        accepted = [reply for reply in replies if reply[1] == 200]
        self.assertEqual(len(accepted), 1, replies)
        payload, _, winner = accepted[0]
        repeated_code, repeated = self.http('POST', self.order_path('bind'), payload)
        self.assertEqual(repeated_code, 200, repeated)
        self.assertEqual(repeated['lease'], winner['lease'])
        self.assertTrue(repeated['historical'])
        conflicting_code, _ = self.http('POST', self.order_path('bind'), {**payload, 'expected_revision': 2})
        self.assertNotEqual(conflicting_code, 200)
        extra_code, _ = self.http('POST', self.order_path('bind'), {
            'expected_revision': 1, 'binding_operation_id': 'client-path-' + uuid.uuid4().hex,
            'run_dir': str(self.directory / 'client-picked-workspace')})
        self.assertNotEqual(extra_code, 200)
        db = sqlite3.connect('file:' + str(self.app / 'orders.sqlite3') + '?mode=ro', uri=True)
        try:
            count = db.execute('SELECT COUNT(*) FROM leases WHERE order_id=? AND revision=1',
                               (self.order_id,)).fetchone()[0]
            bind_count = db.execute("SELECT COUNT(*) FROM operations WHERE kind='bind'").fetchone()[0]
        finally:
            db.close()
        self.assertEqual((count, bind_count), (1, 1))
        self.event({'kind': 'independent_sqlite_lease_allocation_readback',
                    'lease_count_at_revision': count, 'binding_effect_count': bind_count,
                    'server_assigned_workspace': winner['lease']['workspace_dir']})

    def test_edit_during_actual_motion_refuses_stale_fulfillment(self):
        self.changed_during_motion(cancelled=False)

    def test_cancel_during_actual_motion_keeps_cancelled_app_truth(self):
        self.changed_during_motion(cancelled=True)

    def changed_during_motion(self, *, cancelled):
        self.start()
        self.bind()
        self.start_native(pace=.003)
        ident = 'active-before-order-change'
        self.submit(ident, self.proposal(self.observe(), ident))
        self.until(ident, {'running'})
        time.sleep(.3)
        action = 'cancel' if cancelled else 'edit'
        change = {'expected_revision': 1}
        if not cancelled:
            change['target_zone'] = {'x_min': .16, 'x_max': .24, 'y_min': -.04, 'y_max': .04}
        code, changed = self.http('POST', self.order_path(action), change)
        self.assertEqual(code, 200, changed)
        self.controller('cancel', '--operation-id', ident, '--expected-incarnation', self.incarnation)
        stopped = self.until(ident)
        self.assertIn(stopped['phase'], {'cancelled', 'unknown'})
        code, refused = self.fulfill()
        self.assertNotEqual(code, 200, refused)
        saved, count = self.db_rows()
        self.assertEqual(saved[1], 2)
        self.assertEqual(saved[2], 'cancelled' if cancelled else 'open')
        self.assertEqual(count, 0)

    def test_actual_lost_http_reply_has_one_sqlite_effect_and_historical_repeat(self):
        self.start()
        self.bind()
        self.start_native(placed=True)
        self.stage()
        content = encoded({'lease_id': self.lease['lease_id'],
                           'completion_operation_id': self.lease['completion_operation_id']})
        parsed = urllib.parse.urlsplit(self.origin)
        request = (f'POST {self.order_path("fulfill")} HTTP/1.1\r\nHost: 127.0.0.1:{parsed.port}\r\n'
                   f'Origin: {self.origin}\r\nX-Footwork-App-ID: {self.app_id}\r\n'
                   f'Content-Type: application/json\r\nContent-Length: {len(content)}\r\n'
                   'Connection: close\r\n\r\n').encode() + content
        with socket.create_connection(('127.0.0.1', parsed.port), timeout=5) as caller:
            caller.sendall(request)
        self.event({'kind': 'actual_http_socket_closed_before_reply', 'path': self.order_path('fulfill'),
                    'reply_consumed': False, 'body_sha256': sha(content)})
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            code, original = self.http('GET', '/api/operations/' + self.lease['completion_operation_id'])
            if code == 200:
                break
            time.sleep(.05)
        self.assertEqual(code, 200, original)
        self.native.terminate()
        self.native.wait(timeout=8)
        repeated_code, repeated = self.fulfill()
        self.assertEqual(repeated_code, 200, repeated)
        self.assertEqual(repeated['receipt'], original['receipt'])
        self.assertTrue(repeated['historical'])
        saved, count = self.db_rows()
        self.assertEqual((saved[1], saved[2], count), (2, 'fulfilled', 1))
        wrong_code, _ = self.fulfill(lease_id=uuid.uuid4().hex)
        self.assertNotEqual(wrong_code, 200)
        self.assertEqual(self.db_rows()[1], 1)

    def test_client_flags_paths_wrong_ids_and_missing_physical_evidence_refuse(self):
        self.start()
        self.bind()
        for extra in ({'success': True}, {'receipt_path': '/tmp/fake.json'},
                      {'app_id': uuid.uuid4().hex}, {'lease_id': uuid.uuid4().hex},
                      {'completion_operation_id': 'fulfill-' + uuid.uuid4().hex}):
            with self.subTest(extra=extra):
                self.assertNotEqual(self.fulfill(**extra)[0], 200)
        self.assertNotEqual(self.fulfill()[0], 200)
        saved, count = self.db_rows()
        self.assertEqual((saved[1], saved[2], count), (1, 'open', 0))

    def test_other_application_lease_cannot_alias_same_order_and_real_physical_proof(self):
        self.start()
        self.bind()
        self.start_native(placed=True)
        self.stage()
        original = self.app, self.origin, self.app_id, self.lease
        self.app = self.directory / 'other-app'
        self.initialize_app()
        self.serve_app()
        other = self.bind()
        self.assertNotEqual(self.app_id, original[2])
        self.assertEqual(other['work_order'], original[3]['work_order'])
        self.app, self.origin, self.app_id, self.lease = original
        foreign_code, foreign = self.fulfill(lease_id=other['lease_id'])
        self.assertNotEqual(foreign_code, 200, foreign)
        missing, _ = self.http('GET', '/api/leases/' + other['lease_id'])
        self.assertNotEqual(missing, 200)
        self.assertEqual(self.db_rows()[1], 0)
        own_code, own = self.fulfill()
        self.assertEqual(own_code, 200, own)
        self.assertEqual(self.db_rows()[1], 1)

    def test_valid_staging_for_wrong_task_cannot_fulfill_lease(self):
        self.start()
        self.bind()
        altered = {**self.work_order, 'target_zone': {'x_min': .16, 'x_max': .24, 'y_min': -.04, 'y_max': .04}}
        self.start_native(placed=True, altered_order=altered)
        self.assertEqual(self.stage()[0]['phase'], 'staged')
        self.assertNotEqual(self.fulfill()[0], 200)
        self.assertEqual(self.db_rows()[1], 0)

    def test_valid_staging_for_wrong_order_identity_cannot_fulfill_lease(self):
        self.start()
        self.bind()
        self.start_native(placed=True, altered_order={**self.work_order, 'order_id': self.order_id + '-different'})
        self.assertEqual(self.stage()[0]['phase'], 'staged')
        self.assertNotEqual(self.fulfill()[0], 200)
        self.assertEqual(self.db_rows()[1], 0)

    def test_executed_motion_under_completion_id_does_not_invent_staging(self):
        self.start()
        self.bind()
        self.start_native()
        ident = self.lease['physical_completion_id']
        self.submit(ident, self.proposal(self.observe(), ident))
        moved = self.until(ident)
        self.assertEqual(moved['phase'], 'executed')
        self.assertGreater(moved['receipt']['contact_statistics']['native_steps'], 0)
        self.assertNotEqual(self.fulfill()[0], 200)
        self.assertEqual(self.db_rows()[1], 0)

    def test_changed_source_binding_and_exact_store_replacement_refuse_restart(self):
        process, _ = self.start()
        self.bind()
        process.terminate()
        process.wait(timeout=8)
        port = urllib.parse.urlsplit(self.origin).port
        binding = self.app / 'app-binding.json'
        original = binding.read_bytes()
        saved_binding = self.directory / 'original-app-binding.json'
        saved_binding.write_bytes(original)
        saved_binding.chmod(0o600)
        changed = json.loads(original)
        changed['source_fingerprints']['order_app.py'] = '0' * 64
        self.retain(binding, changed)
        refusal = self.command([sys.executable, APP, 'serve', '--app-dir', self.app, '--port', port])
        self.assertEqual(refusal['phase'], 'refused', refusal)
        self.event({'kind': 'controlled_retained_binding_fault', 'fault': 'changed_app_source_fingerprint',
                    'original_path': str(saved_binding), 'runtime_source_changed': False})
        binding.write_bytes(original)
        database = self.app / 'orders.sqlite3'
        original_database = self.directory / 'original-orders.sqlite3'
        old_identity = [database.stat().st_dev, database.stat().st_ino]
        database.rename(original_database)
        database.write_bytes(original_database.read_bytes())
        database.chmod(0o600)
        new_identity = [database.stat().st_dev, database.stat().st_ino]
        self.assertNotEqual(new_identity, old_identity)
        refusal = self.command([sys.executable, APP, 'serve', '--app-dir', self.app, '--port', port])
        self.assertEqual(refusal['phase'], 'refused', refusal)
        self.event({'kind': 'controlled_retained_store_fault', 'fault': 'byte_identical_store_new_file_identity',
                    'original_path': str(original_database), 'old_identity': old_identity, 'new_identity': new_identity})

    def test_staged_history_with_tampered_current_artifact_refuses_first_fulfillment(self):
        self.start()
        self.bind()
        self.start_native(placed=True)
        final, _ = self.stage()
        artifact = Path(self.lease['run_dir']) / 'order.json'
        original = artifact.read_bytes()
        saved = self.directory / 'original-physical-order.json'
        saved.write_bytes(original)
        saved.chmod(0o600)
        artifact.write_bytes(original + b' ')
        self.event({'kind': 'controlled_current_artifact_fault', 'path': str(artifact), 'original_path': str(saved),
                    'original_sha256': sha(original)})
        status = self.controller('status', '--operation-id', self.lease['physical_completion_id'])
        self.assertEqual(status['phase'], 'staged')
        self.assertEqual(status['current_health'], 'blocked')
        self.assertEqual(status['receipt'], final['receipt'])
        self.assertNotEqual(self.fulfill()[0], 200)
        self.assertEqual(self.db_rows()[1], 0)

    def test_application_controller_restart_retains_exact_store_and_no_redispatch(self):
        app_process, first = self.start()
        self.bind()
        self.start_native(placed=True)
        final, _ = self.stage()
        before = self.observe()
        old_incarnation = self.incarnation
        self.native.terminate()
        self.native.wait(timeout=8)
        app_process.terminate()
        app_process.wait(timeout=8)
        _, current = self.serve_app(restart=True)
        self.assertEqual(current['app_id'], first['app_id'])
        self.assertNotEqual(current['server_incarnation'], first['server_incarnation'])
        self.native = self.spawn([sys.executable, CONTROLLER, 'serve', '--run-dir', self.lease['run_dir'],
                                  '--controller-dir', self.control], 'native-restart')
        self.native_ready()
        self.assertNotEqual(self.incarnation, old_incarnation)
        retained = self.controller('status', '--operation-id', self.lease['physical_completion_id'])
        self.assertEqual(retained['receipt'], final['receipt'])
        after = self.observe()
        self.assertEqual((after['generation'], after['state_sha256']),
                         (before['generation'], before['state_sha256']))
        self.assertEqual(self.fulfill()[0], 200)
        self.assertEqual(self.db_rows()[1], 1)

    def test_loopback_browser_origin_and_exact_schema_protect_mutations(self):
        self.start()
        payload = {'expected_revision': 1, 'binding_operation_id': 'origin-' + uuid.uuid4().hex}
        for headers, origin in (({'Origin': 'http://example.com'}, True), ({}, False),
                                ({'Host': 'example.com'}, True)):
            with self.subTest(headers=headers, origin=origin):
                code, reply = self.http('POST', self.order_path('bind'), payload, origin=origin, extra_headers=headers)
                self.assertNotEqual(code, 200, reply)
        self.assertEqual(self.db_rows()[1], 0)

    def test_mutations_require_pre_effect_exact_application_identity(self):
        self.start()
        original = self.app, self.origin, self.app_id
        self.app = self.directory / 'foreign-app'
        self.initialize_app()
        self.serve_app()
        foreign_id = self.app_id
        self.assertNotEqual(foreign_id, original[2])
        self.app, self.origin, self.app_id = original
        for expected_id, action in ((None, 'edit'), (foreign_id, 'cancel')):
            with self.subTest(expected_id=expected_id, action=action):
                before, before_count = self.db_rows()
                payload = {'expected_revision': before[1]}
                if action == 'edit':
                    payload['target_zone'] = {'x_min': .16, 'x_max': .24, 'y_min': -.04, 'y_max': .04}
                headers = {'Origin': self.origin, 'Content-Type': 'application/json'}
                if expected_id is not None:
                    headers['X-Footwork-App-ID'] = expected_id
                parsed = urllib.parse.urlsplit(self.origin)
                connection = HTTPConnection('127.0.0.1', parsed.port, timeout=8)
                try:
                    connection.request('POST', self.order_path(action), body=encoded(payload), headers=headers)
                    response = connection.getresponse()
                    code, reply = response.status, json.loads(response.read())
                finally:
                    connection.close()
                after, after_count = self.db_rows()
                self.event({'kind': 'expected_app_identity_pre_effect_regression', 'action': action,
                            'headers': headers, 'valid_foreign_app_id': foreign_id,
                            'request': payload, 'status': code, 'reply': reply,
                            'before_row': before, 'after_row': after})
                self.assertNotEqual(code, 200, reply)
                self.assertEqual((after, after_count), (before, before_count))

    def test_real_verified_proof_then_concurrent_edit_loses_version_cas(self):
        self.initialize_app()
        marker = self.directory / 'real-proof-ready'
        release = self.directory / 'allow-cas'
        script = self.directory / 'after-real-verification-timing-fault.py'
        content = f'''import importlib.util
import sys
import time
from pathlib import Path
sys.path.insert(0, {str(BASE)!r})
spec = importlib.util.spec_from_file_location("order_app_real_cas_fault", {str(APP)!r})
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
original = app.verify_physical
marker = Path({str(marker)!r})
release = Path({str(release)!r})
def delayed(lease):
    proof = original(lease)
    marker.write_bytes(b"real native/controller/artifact proof obtained\\n")
    deadline = time.monotonic() + 5
    while not release.exists():
        if time.monotonic() > deadline:
            raise RuntimeError("bounded verification/CAS timing fault timed out")
        time.sleep(.02)
    return proof
app.verify_physical = delayed
sys.exit(app.main())
'''
        script.write_text(content)
        script.chmod(0o600)
        self.serve_app(fault_script=script)
        self.bind()
        self.start_native(placed=True)
        self.stage()
        replies = []
        failures = []

        def fulfill_in_parallel():
            try:
                replies.append(self.fulfill())
            except (OSError, ValueError) as exc:
                failures.append(str(exc))

        thread = threading.Thread(target=fulfill_in_parallel)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.03)
            self.assertTrue(marker.exists(), f'no real proof marker; retained {self.directory}')
            changed_zone = {'x_min': .16, 'x_max': .24, 'y_min': -.04, 'y_max': .04}
            code, changed = self.http('POST', self.order_path('edit'),
                                      {'expected_revision': 1, 'target_zone': changed_zone})
            self.assertEqual(code, 200, changed)
            self.event({'kind': 'actual_process_with_labeled_timing_fault',
                        'fault': 'real_physical_verification_complete_before_cas_release',
                        'verification_success_mocked': False, 'marker': str(marker), 'release': str(release)})
        finally:
            release.write_bytes(b'continue real CAS after actual edit\n')
            thread.join(timeout=8)
        self.assertFalse(thread.is_alive())
        self.assertFalse(failures, failures)
        self.assertEqual(len(replies), 1)
        self.assertNotEqual(replies[0][0], 200, replies)
        saved, count = self.db_rows()
        self.assertEqual((saved[1], saved[2], count), (2, 'open', 0))


if __name__ == '__main__':
    unittest.main()
