"""Supplemental post-run, read-only evidence audit; writes only its own result.

This audit is not the preregistered frozen qualifier. It checks causal coverage
that the frozen qualifier's aggregate delay counter alone cannot establish.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT.parents[1]
REPO = SOURCE_DIR.parents[1]
sys.path.insert(0, str(SOURCE_DIR))


def read(path):
    return json.loads(path.read_bytes())


def sha(content):
    return hashlib.sha256(content).hexdigest()


def overlap(left_start, left_end, right_start, right_end):
    return max(0.0, min(left_end, right_end) - max(left_start, right_start))


def audit():
    frozen = read(ROOT / 'source-freeze.json')
    unchanged = all(sha((REPO / name).read_bytes()) == digest for name, digest in frozen['files'].items())
    if not unchanged:
        raise RuntimeError('Frozen evidence helpers changed; do not run a changed scorer against this trial')
    import score_workbench_health as scorer
    # Invoke only the helper functions with no persistence, dispatch or native-state access.
    process = read(ROOT / 'process-ledger.json')
    final = read(ROOT / 'final-public.json')
    identity = read(ROOT / 'identity.json')
    records, relay_valid = scorer.relay_records(ROOT)
    final_sequence = max(event['seq'] for event in final['activity'])
    final_wall = max(event['time'] for event in final['activity'])
    all_events = [read(path) for path in sorted((ROOT / 'operator' / 'events').glob('*.json'))]
    events = [event for event in all_events if event['seq'] <= final_sequence]
    posttrial_events = [event for event in all_events if event['seq'] > final_sequence]
    measured_request_count = read(ROOT / 'health-relay' / 'cleanup.json')['request_count']
    records = [record for record in records if record['request']['sequence'] <= measured_request_count]
    proofs = scorer.fresh_admissions(records, events, identity)
    measured_calls = {job['job_id']: job['call_count'] for job in final['jobs']}
    calls = []
    for directory in sorted((ROOT / 'operator' / 'calls').iterdir()):
        if not directory.is_dir():
            continue
        reservation = read(directory / 'reservation.json')
        result = read(directory / 'outcome.json')
        if reservation['job_id'] not in measured_calls or reservation['call'] > measured_calls[reservation['job_id']]:
            continue
        calls.append({'job_id': reservation['job_id'], 'call': reservation['call'],
                      'started_wall': result['started_at'], 'finished_wall': result['started_at'] + result['elapsed_s'],
                      'elapsed_s': result['elapsed_s'], 'outcome': result['outcome'],
                      'process_exit_observed': result['process_exit_observed']})
    delays = []
    for record in records:
        request, upstream, result = record['request'], record['upstream'], record['result']
        if not (request['tagged_health'] and request['injected_delay_s'] == 1.2 and upstream and
                upstream['http_status'] == 200 and result.get('completed') and result.get('delivered') and
                not result.get('delay_interrupted') and result.get('delay_elapsed_s', 0) >= 1.2):
            continue
        remote = json.loads(record['content'])
        healthy = remote == identity if request['path'] == '/identity' else remote.get('identity') == identity and remote.get('state') == 'ready'
        if not healthy:
            continue
        # The delay ends immediately before send/record. Subtracting the measured
        # monotonic duration maps the real wait into the recorded wall interval.
        ended = result['finished_wall']
        started = ended - result['delay_elapsed_s']
        matches = [{'job_id': call['job_id'], 'call': call['call'],
                    'overlap_s': overlap(started, ended, call['started_wall'], call['finished_wall'])}
                   for call in calls if overlap(started, ended, call['started_wall'], call['finished_wall']) > 0]
        offsets = [request['started_wall'] - request['started_monotonic'],
                   upstream['wall'] - upstream['finished_monotonic'],
                   result['finished_wall'] - result['finished_monotonic']]
        delays.append({'sequence': request['sequence'], 'path': request['path'],
                       'delay_started_wall': started, 'delay_finished_wall': ended,
                       'injected_elapsed_s': result['delay_elapsed_s'],
                       'genuine_upstream_elapsed_s': upstream['upstream_elapsed_s'],
                       'wall_monotonic_offset_range_s': max(offsets) - min(offsets), 'model_overlaps': matches})
    jobs = []
    for job in final['jobs']:
        per_path = {}
        for path in ('/identity', '/state'):
            matches = [delay for delay in delays if delay['path'] == path and
                       any(match['job_id'] == job['job_id'] for match in delay['model_overlaps'])]
            per_path[path] = {'healthy_injected_reads_overlapping_model': len(matches),
                              'relay_sequences': [delay['sequence'] for delay in matches],
                              'model_calls': sorted({match['call'] for delay in matches for match in delay['model_overlaps']
                                                     if match['job_id'] == job['job_id']})}
        jobs.append({'job_id': job['job_id'], 'label': job['label'], 'final_status': job['status'],
                     'path_coverage': per_path, 'both_paths_overlap_model': all(value['healthy_injected_reads_overlapping_model'] for value in per_path.values())})
    selected_proofs = [proof['proof_event'] for proof in proofs]
    selected_reads = [proof['state_read_sequence'] for proof in proofs]
    admission_events = [event for event in events if event['kind'] == 'admission_proof']
    unique_proofs = (bool(proofs) and all(proof['passed'] for proof in proofs) and
                     len(selected_proofs) == len(set(selected_proofs)) and len(selected_reads) == len(set(selected_reads)))
    # Tighten the trace check beyond merely finding a matching ready digest:
    # each chosen full-state reply must complete, reach its caller, and bind the
    # relay request/lease/command identity to the same immutable body.
    by_sequence = {record['request']['sequence']: record for record in records}
    strengthened = []
    expected_headers = {'x-body-id': identity['body_id'], 'x-adapter-id': identity['adapter_id'],
                        'x-source-sha256': identity['source_sha256']}
    for proof in proofs:
        state = by_sequence.get(proof['state_read_sequence'])
        lease = by_sequence.get(proof['lease_sequence'])
        command = by_sequence.get(proof['command_sequence'])
        ok = bool(proof['passed'] and state and lease and command)
        if ok:
            command_payload, lease_payload = json.loads(command['payload']), json.loads(lease['payload'])
            state_headers = {key.lower(): value for key, value in state['request']['headers'].items()}
            command_headers = {key.lower(): value for key, value in command['request']['headers'].items()}
            lease_result = json.loads(lease['content'])
            ok = bool(state['result'].get('completed') and state['result'].get('delivered') and
                      lease['result'].get('completed') and lease['result'].get('delivered') and
                      all(state_headers.get(key) == command_headers.get(key) == value for key, value in expected_headers.items()) and
                      all(command_payload[key] == identity[key] for key in ('body_id', 'adapter_id', 'source_sha256', 'epoch')) and
                      command_payload['client_id'] == lease_payload['client_id'] == lease_result['client_id'])
        strengthened.append({'command_id': proof['command_id'], 'passed': ok})
    cancelled = [call for call in calls if call['outcome'] == 'cancelled']
    control_kinds = ('pause', 'disconnect', 'reconnect', 'halt', 'resume')
    control_events = [event for event in events if event['kind'] in control_kinds]
    posttrial_controls = [event for event in posttrial_events if event['kind'] in control_kinds]
    steps = {step['name']:step for step in read(ROOT / 'ui-ledger.json')['steps']}
    expected_unknown_reason = steps['uncertain']['state']['recovery']['reason']
    unexpected_halts = [event for event in control_events if event['kind'] == 'halt' and event['outcome'] != expected_unknown_reason]
    checking = next((step for step in read(ROOT / 'ui-ledger.json')['steps'] if step['name'] == 'healthy_checking'), None)
    checking_same_identity = bool(checking and checking['state']['app_id'] == final['app_id'] and
                                  checking['state']['connection']['body_id'] == identity['body_id'] and
                                  checking['state']['active_job_id'] in {job['job_id'] for job in final['jobs']})
    coverage = len(jobs) == 2 and all(job['both_paths_overlap_model'] for job in jobs)
    result = {'audit_kind': 'supplemental_post_run_read_only_review', 'frozen_source_commit': frozen['commit'],
              'audit_source_sha256': sha(Path(__file__).read_bytes()), 'frozen_source_unchanged': unchanged,
              'passed': bool(coverage and not cancelled and unique_proofs and all(value['passed'] for value in strengthened) and
                             checking_same_identity and relay_valid and process['owned_processes_exited'] and not unexpected_halts),
              'both_jobs_both_paths_overlap_actual_model': coverage, 'jobs': jobs,
              'healthy_delayed_reads': delays, 'model_calls': calls, 'cancelled_calls': cancelled,
              'proof_count': len(proofs), 'proof_events_unique': unique_proofs,
              'strengthened_admission_bindings': strengthened,
              'unused_admission_proof_events': [event['seq'] for event in admission_events if event['seq'] not in selected_proofs],
              'healthy_checking_same_application_and_body': checking_same_identity,
              'measured_control_events': control_events, 'measured_unexpected_halts': unexpected_halts,
              'posttrial_handoff_control_events': posttrial_controls,
              'measured_cutoff_event_seq': final_sequence, 'measured_cutoff_wall': final_wall,
              'trace_scope_note': 'Append-only journals include later paused handoff administration. Events through the retained final-public snapshot are measured; subsequent events are reported separately.',
              'limits': ['This supplementary audit was authored after source freeze; it does not replace the frozen qualifier.',
                         'Model intervals use provider started_at plus monotonic elapsed_s; delay windows use recorded send time minus measured wait.',
                         'Wall/monotonic offset spread is retained to expose timing precision limits.',
                         'Overlap establishes exposure during model planning; it does not prove the cause of the historical SIM11 timeout.']}
    destination = ROOT / 'review-audit.json'
    original = ROOT / 'review-audit-unscoped.json'
    if destination.exists() and not original.exists():
        original_fd = os.open(original, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(original_fd, 'wb') as output:
            output.write(destination.read_bytes())
    staged = ROOT / 'review-audit-scoped.json'
    fd = os.open(staged, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(result, output, sort_keys=True, indent=2, allow_nan=False)
        output.write('\n')
    os.replace(staged, destination)
    print(json.dumps({key: result[key] for key in ('passed', 'both_jobs_both_paths_overlap_actual_model',
                                                  'proof_count', 'proof_events_unique', 'healthy_checking_same_application_and_body')}))


if __name__ == '__main__':
    audit()
