"""Seven independent SIM5 API/adapter/native diagnostics after an explicit source freeze.

Uses identified backend fixture transport helpers, never calls unit-test methods.
Planning uses public RGB only. SQLite scoring is separately labelled and read-only.
Actual browser read/bind/fulfill is separately driven by the parent.
"""
import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import traceback
import urllib.parse
from pathlib import Path

import order_protocol as protocol
from test_order_app import BASE, CONTROLLER, OrderApplicationTests, encoded, sha

HANDOFF = BASE / 'app_handoff.py'
SOURCE_FILES = ('qualify_order_handoff.py', 'test_order_app.py', 'order_app.py', 'order_protocol.py',
                'order_app.html', 'app_handoff.py', 'controller.py', 'episode_runner.py',
                'workcell.py', 'image_guided.py', 'episode_cases.py', 'proposal.schema.json', 'scene.xml')


def freeze(commit):
    """Bind the named SOURCE_FILES only; no transitive or live qualification claim."""
    repo = BASE.parents[1]
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() != commit:
        raise ValueError('requested source freeze differs from current HEAD')
    sources = {}
    for name in SOURCE_FILES:
        path = BASE / name
        content = protocol.read_bytes(path)
        relative = path.relative_to(repo).as_posix()
        if subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=repo) != content:
            raise ValueError('source differs from named commit: ' + relative)
        sources[name] = sha(content)
    return sources


def expected_socket_path(control):
    import controller

    return controller.socket_path(control)


def bound_socket_path(control):
    import controller

    control = protocol.directory(control)
    binding = protocol.decode(protocol.read_bytes(control / 'controller-binding.json'))
    expected = expected_socket_path(control)
    if (not isinstance(binding, dict) or type(binding.get('version')) is not int or binding.get('version') != 1
            or binding.get('source_kind') != controller.body.SOURCE_KIND
            or binding.get('controller_sha256') != protocol.sha(protocol.read_bytes(CONTROLLER))
            or binding.get('controller_dir') != str(control) or binding.get('socket_path') != str(expected)):
        raise ValueError('controller/socket binding is invalid')
    return expected


class Fixture(OrderApplicationTests):
    def initialize(self, directory, name):
        self.setUp()
        self.directory.rename(directory)
        self.directory = directory
        self.app = directory / 'app'
        self.order_id = 'qualification-' + name
        self.work_order['order_id'] = self.order_id
        self.work_order['project'] = {'namespace': 'diagnostic', 'project_id': 'sim5-independent'}
        self.work_order['target_zone'] = {'x_min': .12, 'x_max': .20, 'y_min': -.035, 'y_max': .035}
        self.seed = {**self.work_order, 'revision': 3, 'state': 'open'}
        self.expected_native_pid = None
        self.adapter_stopped = False

    def bind(self):
        code, reply = self.http('POST', self.order_path('bind'), {
            'expected_revision': 3, 'binding_operation_id': 'bind-' + self.order_id})
        self.assertEqual(code, 200, reply)
        self.lease = reply['lease']
        self.assertEqual(self.lease['app_id'], self.app_id)
        self.assertEqual(self.lease['work_order'], self.work_order)
        return self.lease

    def handoff(self, command, *args):
        return self.command([str(BASE / '.venv/bin/python'), HANDOFF, command,
                             '--handoff-dir', self.lease['handoff_dir'], *args])

    def prepare(self, *, placed=False, pace=0):
        scene = {'block_xy': [.163, .004] if placed else [-.117, .004],
                 'illumination_scale': 1, 'occlusion_fraction': 0, 'camera_offset_x_m': 0}
        path = self.retain(self.directory / 'scene.json', scene)
        prepared = self.command([str(BASE / '.venv/bin/python'), HANDOFF, 'prepare', '--app-url', self.origin,
            '--expected-app-id', self.app_id, '--lease-id', self.lease['lease_id'], '--scene-file', path,
            '--scene-sha256', sha(path.read_bytes()), '--pace-s', pace])
        self.assertEqual(prepared['phase'], 'prepared', prepared)
        self.assertEqual(prepared['ownership'], 'owned')
        self.control = Path(self.lease['controller_dir'])
        self.incarnation = prepared['controller']['current_incarnation']
        self.expected_native_pid = prepared['controller']['pid']
        return prepared

    def observe(self):
        reply = self.handoff('observe')
        self.assertEqual(reply['phase'], 'ready', reply)
        packet = reply['observation']
        self.event({'kind': 'public_rgb_planning_basis', 'generation': packet['generation'],
                    'image_sha256': packet['image_sha256'], 'image_path': packet['image_path'],
                    'state_sha256': packet['state_sha256'], 'task_intent': packet['task_intent']})
        return packet

    def submit(self, ident, proposal):
        reply = self.handoff('submit', '--operation-id', ident, '--proposal-file', proposal[0],
                             '--proposal-sha256', proposal[1])
        self.assertIn(reply['phase'], {'accepted', 'running', 'executed', 'staged'}, reply)
        return reply

    def stop_adapter(self):
        stopped = self.handoff('stop')
        self.assertTrue(stopped['process_termination_observed'], stopped)
        self.adapter_stopped = True
        return stopped

    def scoring(self):
        # Scorer role begins here. No native poses or private controller journals are read.
        order, count = self.db_rows()
        database = self.app / 'orders.sqlite3'
        with sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True) as connection:
            binding = json.loads(connection.execute("SELECT value FROM meta WHERE key='binding'").fetchone()[0])
            receipts = [dict(zip(('operation_id', 'order_id', 'lease_id', 'receipt_json'), row, strict=True))
                        for row in connection.execute("SELECT operation_id,order_id,lease_id,receipt_json FROM operations WHERE kind='fulfill'")]
        self.assertEqual(binding['app_id'], self.app_id)
        self.assertEqual(binding['app_dir'], str(self.app))
        self.assertEqual(binding['database_identity'], [database.stat().st_dev, database.stat().st_ino])
        score = {'role': 'read_only_sqlite_scorer', 'order_row': order, 'fulfillment_count': count,
                 'app_id': binding['app_id'], 'store_id': binding['store_id'],
                 'database_identity': binding['database_identity'], 'source_fingerprints': binding['source_fingerprints'],
                 'fulfillment_receipts': receipts}
        self.event({'kind': 'separate_persisted_application_score', **score})
        return score

    def cleanup(self):
        errors = []
        if self.expected_native_pid is not None and not self.adapter_stopped:
            try:
                self.stop_adapter()
            except (AssertionError, KeyError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(str(exc))
                self.event({'kind': 'adapter_cleanup_unconfirmed', 'expected_owned_pid': self.expected_native_pid,
                            'reason': str(exc), 'unconfirmed_process_not_blindly_signalled': True})
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=4)
        for handle in self.handles:
            handle.close()
        bound, socket_exists = None, None
        if self.control is not None:
            try:
                bound = bound_socket_path(self.control)
                try:
                    bound.lstat()
                    socket_exists = True
                except FileNotFoundError:
                    socket_exists = False
                if socket_exists:
                    errors.append('bound controller socket remains after cleanup')
            except (OSError, ValueError) as exc:
                errors.append('controller socket cleanup unconfirmed: ' + str(exc))
        self.event({'kind': 'owned_process_cleanup',
                    'processes': [{'pid': p.pid, 'exit_code': p.poll()} for p in self.processes],
                    'all_parent_handles_exited': all(p.poll() is not None for p in self.processes),
                    'adapter_stop_observed': self.adapter_stopped,
                    'socket_path': str(bound) if bound is not None else None,
                    'socket_exists': socket_exists,
                    'socket_absence_verified': bound is not None and socket_exists is False})
        if errors:
            raise RuntimeError('adapter cleanup unconfirmed: ' + '; '.join(errors))


def normal(f):
    f.start()
    f.bind()
    f.prepare()
    staged, contacts = f.stage()
    f.assertGreater(contacts, 0)
    code, fulfilled = f.fulfill()
    f.assertEqual(code, 200, fulfilled)
    reconciled = f.handoff('reconcile')
    f.assertEqual(reconciled['phase'], 'fulfilled', reconciled)
    f.assertEqual(reconciled['receipt'], fulfilled['receipt'])
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['order_row'][2], score['fulfillment_count']), (4, 'fulfilled', 1))
    return {'expected_outcome': 'fulfilled', 'contact_samples': contacts, 'physical_receipt': staged,
            'application_receipt': fulfilled, 'sqlite_score': score, 'browser_scope': 'HTTP-only; parent owns actual browser case'}


def changed(f, *, cancelled=False):
    f.start()
    f.bind()
    f.prepare(pace=.003)
    packet = f.observe()
    ident = 'admitted-before-app-change'
    f.submit(ident, f.proposal(packet, ident))
    f.until(ident, {'running'})
    time.sleep(.4)
    action = 'cancel' if cancelled else 'edit'
    mutation = {'expected_revision': 3}
    if not cancelled:
        mutation['target_zone'] = {'x_min': .15, 'x_max': .23, 'y_min': -.035, 'y_max': .035}
    code, app = f.http('POST', f.order_path(action), mutation)
    f.assertEqual(code, 200, app)
    guard = f.handoff('guard')
    f.assertFalse(guard['guard_current'])
    f.assertTrue(guard['physical_effects_may_be_partial'])
    f.assertFalse(guard['rollback_claim'])
    stopped = f.until(ident)
    f.assertEqual(stopped['phase'], 'cancelled', stopped)
    f.assertTrue(stopped['stop_evidence']['stop_verified'])
    f.assertTrue(stopped['stop_evidence']['state_retained'])
    f.assertGreater(stopped['stop_evidence']['native_steps_before_cancel'], 0)
    current_packet = f.controller('observe')['observation']
    f.assertEqual(stopped['stop_evidence']['retained_generation'], current_packet['generation'])
    f.assertEqual(stopped['stop_evidence']['retained_state_sha256'], current_packet['state_sha256'])
    f.event({'kind': 'read_only_cancel_stop_scoring', 'generation': current_packet['generation'],
             'state_sha256': current_packet['state_sha256'], 'after_application_guard': 'withheld'})
    blocked = f.handoff('submit', '--operation-id', 'after-change', '--proposal-file',
                        f.proposal(packet, 'after-change')[0], '--proposal-sha256',
                        sha((f.directory / 'proposal-after-change.json').read_bytes()))
    f.assertTrue(blocked['new_submissions_withheld'], blocked)
    f.assertNotEqual(f.fulfill()[0], 200)
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['order_row'][2], score['fulfillment_count']),
                  (4, 'cancelled' if cancelled else 'open', 0))
    return {'expected_outcome': 'stale_fulfillment_refused', 'app_mutation': app,
            'guard': guard, 'retained_cancelled_receipt': stopped, 'sqlite_score': score}


def lost_reply(f):
    f.start()
    f.bind()
    f.prepare(placed=True)
    f.stage()
    content = encoded({'lease_id': f.lease['lease_id'], 'completion_operation_id': f.lease['completion_operation_id']})
    port = urllib.parse.urlsplit(f.origin).port
    request = (f'POST {f.order_path("fulfill")} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nOrigin: {f.origin}\r\n'
               f'X-Footwork-App-ID: {f.app_id}\r\nContent-Type: application/json\r\nContent-Length: {len(content)}\r\n'
               'Connection: close\r\n\r\n').encode() + content
    with socket.create_connection(('127.0.0.1', port), timeout=5) as caller:
        caller.sendall(request)
    f.event({'kind': 'actual_http_socket_closed_before_reply', 'reply_consumed': False,
             'app_id': f.app_id, 'completion_operation_id': f.lease['completion_operation_id']})
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        code, saved = f.http('GET', '/api/operations/' + f.lease['completion_operation_id'])
        if code == 200:
            break
        time.sleep(.05)
    f.assertEqual(code, 200, saved)
    f.stop_adapter()
    code, repeated = f.fulfill()
    f.assertEqual(code, 200, repeated)
    f.assertEqual(saved['receipt'], repeated['receipt'])
    f.assertEqual(f.handoff('reconcile')['receipt'], saved['receipt'])
    conflicting_code, conflicting = f.fulfill(lease_id='0' * 32)
    f.assertNotEqual(conflicting_code, 200, conflicting)
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['fulfillment_count']), (4, 1))
    return {'expected_outcome': 'one_effect_historical_reconciliation', 'readback': saved,
            'repeat_after_controller_stop': repeated, 'sqlite_score': score}


def identities(f):
    f.start()
    f.bind()
    f.assertNotEqual(f.fulfill()[0], 200)  # No physical controller/evidence exists.
    f.prepare(placed=True)
    f.stage()
    original = f.app, f.origin, f.app_id, f.lease
    f.app = f.directory / 'foreign-app'
    f.initialize_app()
    f.serve_app()
    foreign = f.bind()
    foreign_app_id = f.app_id
    f.app, f.origin, f.app_id, f.lease = original
    f.assertNotEqual(f.fulfill(lease_id=foreign['lease_id'])[0], 200)
    for fields in ({'success': True}, {'receipt_path': '/tmp/unassigned-receipt'},
                   {'completion_operation_id': f.lease['binding_operation_id']},
                   {'completion_operation_id': 'wrong-assigned-operation'}):
        f.assertNotEqual(f.fulfill(**fields)[0], 200)
    for identity in ('', foreign_app_id):
        code, _ = f.http('POST', f.order_path('fulfill'), {
            'lease_id': f.lease['lease_id'], 'completion_operation_id': f.lease['completion_operation_id']},
            extra_headers={'X-Footwork-App-ID': identity})
        f.assertNotEqual(code, 200)
    wrong_order, _ = f.http('POST', f.order_path().replace(f.order_id, f.order_id + '-other') + '/fulfill', {
        'lease_id': f.lease['lease_id'], 'completion_operation_id': f.lease['completion_operation_id']})
    f.assertNotEqual(wrong_order, 200)
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['order_row'][2], score['fulfillment_count']), (3, 'open', 0))
    return {'expected_outcome': 'wrong_identity_flags_paths_and_unsupported_evidence_refused', 'sqlite_score': score}


def restart(f):
    app_process, initial_app = f.start()
    f.bind()
    prepared = f.prepare()
    staged, _ = f.stage()
    before = f.observe()
    f.stop_adapter()
    app_process.terminate()
    app_process.wait(timeout=8)
    _, current_app = f.serve_app(restart=True)
    f.assertEqual(initial_app['app_id'], current_app['app_id'])
    f.native = f.spawn([str(BASE / '.venv/bin/python'), CONTROLLER, 'serve', '--run-dir', f.lease['run_dir'],
                        '--controller-dir', f.control], 'independent-controller-restart')
    current = f.native_ready()
    f.assertNotEqual(current['current_incarnation'], prepared['controller']['current_incarnation'])
    retained = f.controller('status', '--operation-id', f.lease['physical_completion_id'])
    f.assertEqual(retained['receipt'], staged['receipt'])
    after = f.controller('observe')['observation']
    f.assertEqual((before['generation'], before['state_sha256']), (after['generation'], after['state_sha256']))
    code, fulfilled = f.fulfill()
    f.assertEqual(code, 200, fulfilled)
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['fulfillment_count']), (4, 1))
    return {'expected_outcome': 'same_identity_history_no_redispatch', 'before_packet': before,
            'after_packet': after, 'retained_physical': retained, 'app_receipt': fulfilled, 'sqlite_score': score}


def artifact(f):
    f.start()
    f.bind()
    f.prepare(placed=True)
    staged, _ = f.stage()
    current_file = Path(f.lease['run_dir']) / 'order.json'
    preserved = f.directory / 'original-physical-order.json'
    shutil.copyfile(current_file, preserved)
    preserved.chmod(0o600)
    with current_file.open('ab') as sink:
        sink.write(b' ')
    f.event({'kind': 'controlled_current_artifact_byte_fault', 'path': str(current_file),
             'preserved_original': str(preserved), 'native_state_not_modified': True})
    current = f.controller('status', '--operation-id', f.lease['physical_completion_id'])
    f.assertEqual(current['phase'], 'staged')
    f.assertEqual(current['receipt'], staged['receipt'])
    f.assertEqual(current['current_health'], 'blocked')
    f.assertNotEqual(f.fulfill()[0], 200)
    score = f.scoring()
    f.assertEqual((score['order_row'][1], score['order_row'][2], score['fulfillment_count']), (3, 'open', 0))
    return {'expected_outcome': 'historical_stage_current_artifact_refuses_new_fulfillment',
            'current_physical_status': current, 'sqlite_score': score}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    output = Path(os.path.abspath(args.output_dir))
    if BASE / 'output' not in output.parents or output.exists():
        raise ValueError('qualification needs a new owned output directory; no episode rerun')
    commit = args.source_commit
    sources = freeze(commit)
    output.mkdir(mode=0o700)
    result = {'source_commit': commit, 'source_sha256': sources, 'fixture_source': 'test_order_app.OrderApplicationTests transport helpers',
              'classification': 'independent public API/adapter/native integration diagnostics; no AI benchmark',
              'browser_scope': 'parent separately owns actual browser evidence', 'cases': []}
    scenarios = [('01-normal-http-native', normal), ('02-edit-during-motion', changed),
                 ('03-cancel-during-motion', lambda f: changed(f, cancelled=True)), ('04-lost-app-reply', lost_reply),
                 ('05-identity-and-authority', identities), ('06-restart-history', restart), ('07-current-artifact', artifact)]
    for name, scenario in scenarios:
        fixture = Fixture('test_real_contact_fulfillment_commits_exact_version_and_receipt')
        case = {'case_id': name, 'passed': False}
        try:
            fixture.initialize(output / name, name)
            case['evidence'] = scenario(fixture)
            case['passed'] = True
        except Exception as exc:  # noqa: BLE001 - retain each failed attempt, no effect retry
            case.update(error=str(exc), traceback=traceback.format_exc())
        finally:
            try:
                fixture.cleanup()
            except Exception as exc:  # noqa: BLE001 - retain owned-resource cleanup failure
                case.update(passed=False, cleanup_error=str(exc))
            case['events'] = fixture.events
            fixture.retain(output / name / 'case-result.json', case)
            result['cases'].append(case)
            result['passed'] = sum(item['passed'] for item in result['cases'])
            result['attempted'] = len(result['cases'])
            fixture.retain(output / 'qualification.json', result)
            print(json.dumps({'case_id': name, 'passed': case['passed'], 'error': case.get('error')}), flush=True)
    result['final_source_sha256'] = {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest() for name in SOURCE_FILES}
    result['source_unchanged'] = result['final_source_sha256'] == sources
    fixture.retain(output / 'qualification.json', result)
    return 0 if result['passed'] == 7 and result['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
