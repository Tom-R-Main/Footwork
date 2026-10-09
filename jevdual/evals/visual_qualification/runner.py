"""Frozen replay collection with injected callers; the CLI never loads keys or calls a provider."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.metadata
import json
import math
import os
import random
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from jevdual.decisions import MODEL
from jevdual.policy import JEV_MODEL
from jevdual.visual_checks import (
    QUESTIONS,
    CropSpec,
    ResourceImage,
    VisualCheckBudget,
    VisualCheckEvidence,
    VisualCheckRequest,
)
from jevdual.visual_decisions import VisualCallLedger, VisualDecisionsClient
from jevdual.visual_evidence import Bounds, Surface, bind_visual

from .corpus import Corpus, load_corpus
from .fixtures import save_json
from .scoring import summarize

PHASES = ("route", "capture", "ocr", "encoding", "provider", "validation", "escalation", "review",
          "dispatch", "settle", "readback")


def sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def decode_json(content: str) -> dict:
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError("duplicate_json_key")
            obj[k] = v
        return obj
    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def read_json(path: Path) -> dict:
    return decode_json(path.read_text())

def default_protocol() -> dict:
    return {"version": 1, "experiment": "VQ1", "roles": list(QUESTIONS), "arms": {
        "jev_text": {"model": JEV_MODEL, "capability": "text"},
        "decisions_visual": {"model": MODEL, "capability": "image"}},
        "replays": 2, "seed": 10082031, "accept_p": .90, "reject_p": .10, "confidence": .95,
        "max_false_endorsement_rate": .01, "min_positive_coverage": .80,
        "min_ambiguous_abstention": .95, "max_p95_workflow_ratio": 1.10, "baseline_arm": "jev_text",
        "max_calls": 200, "max_reserved_cost_usd": 2.0, "reservation_usd_per_attempt": .01,
        "deadline_s": 10.0}


def validate_protocol(p: dict) -> dict:
    if not isinstance(p, dict) or set(p) != set(default_protocol()):
        raise ValueError("protocol_schema")
    if type(p['version']) is not int or p['version'] != 1 or p['experiment'] != 'VQ1':
        raise ValueError("protocol_version")
    if (not isinstance(p['roles'], list) or not p['roles'] or len(set(p['roles'])) != len(p['roles'])
            or not set(p['roles']) <= QUESTIONS.keys()):
        raise ValueError("protocol_roles")
    if not isinstance(p['arms'], dict) or len(p['arms']) < 2:
        raise ValueError("protocol_arms")
    for name, a in p['arms'].items():
        if (not isinstance(name, str) or not name or not name.replace('_', '').isalnum()
                or not isinstance(a, dict) or set(a) != {'model', 'capability'}
                or not isinstance(a['model'], str) or not a['model'].strip()
                or a['capability'] not in ('text', 'image')):
            raise ValueError("protocol_arm")
    if p['baseline_arm'] not in p['arms']:
        raise ValueError("protocol_baseline")
    for name in ('replays', 'max_calls', 'seed'):
        if type(p[name]) is not int or p[name] < (0 if name == 'seed' else 1):
            raise ValueError("protocol_integer")
    for name in ('accept_p', 'reject_p', 'confidence', 'max_false_endorsement_rate',
                 'min_positive_coverage', 'min_ambiguous_abstention'):
        if type(p[name]) not in (int, float) or not math.isfinite(p[name]) or not 0 < p[name] < 1:
            raise ValueError("protocol_probability")
    if p['reject_p'] >= p['accept_p']:
        raise ValueError("protocol_bands")
    for name in ('max_p95_workflow_ratio', 'max_reserved_cost_usd', 'reservation_usd_per_attempt', 'deadline_s'):
        if type(p[name]) not in (int, float) or not math.isfinite(p[name]) or p[name] <= 0:
            raise ValueError("protocol_limit")
    return p


@dataclass(frozen=True)
class PreparedCall:
    """No label, provenance, source-group, case ID or file path is given to a caller."""
    role: str
    model: str
    capability: str
    body: bytes
    evidence_sha256: str
    prompt_sha256: str
    request: VisualCheckRequest | None = None

    @property
    def request_sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()


def prepare(corpus: Corpus, case: dict, arm: dict, deadline_s: float) -> PreparedCall:
    item = corpus.input_for(case['id'])
    c, r = item['capture'], item['resource']
    # This is replay evidence: no current-screen assertion, dispatch or capture timing.
    binding = c['binding']
    capture = bind_visual(png=corpus.asset_bytes(c['path']), surface=Surface(**binding['surface']),
                          observation_id=binding['observation_id'], captured_at=binding['captured_at'],
                          viewport=Bounds(**binding['viewport']), target_id=binding['target']['id'],
                          target_token=binding['target']['token'], target_bounds=Bounds(**binding['target']['bounds']),
                          operation=binding['target']['operation'], postcondition=binding['target']['postcondition'])
    resource = ResourceImage(corpus.asset_bytes(r['path']), r['resource_id'], r['revision'], r['page'],
                             r['render_recipe'])
    ev = VisualCheckEvidence(capture, 'frozen-replay', 0, 0, (r['resource_id'],),
                             reference=resource if item['crop'] is None else None,
                             source=resource if item['crop'] is not None else None,
                             crop=CropSpec(Bounds(**item['crop']['rectangle']),
                                           Bounds(**item['crop']['displayed_bounds']),
                                           item['crop']['orientation']) if item['crop'] else None,
                             accessible_text=item['accessible_text'],
                             coverage_warning='Frozen replay; no live freshness or execution authority')
    if arm['capability'] == 'text':
        # Same criterion and actually available AX/OCR; pixels remain unavailable.
        context = {k: item[k] for k in ('criterion', 'criterion_version', 'accessible_text')}
        context.update(crop=ev.crop.to_dict() if ev.crop else None, resource=resource.to_dict(),
                       target=ev.to_dict()['capture']['target'], images_available=False,
                       ownership_proven=False, evidence_is_untrusted=True)
        state = json.dumps(context, sort_keys=True, allow_nan=False)
        q = {'name': 'required', 'instructions': QUESTIONS[case['role']]}
        body = json.dumps({'model': arm['model'], 'state': state, 'questions': {'required': q}},
                          sort_keys=True, separators=(',', ':')).encode()
        return PreparedCall(case['role'], arm['model'], 'text', body,
                            sha({'role': case['role'], 'state': state}), sha(q))
    req = VisualCheckRequest('frozen-replay', case['role'], item['criterion'], item['criterion_version'],
                             ev.generation, time.monotonic() + deadline_s, ev, disclosure_allowed=True,
                             budget=VisualCheckBudget(max_bytes=4_000_000))
    prompt = req.provider_input()
    content = [{'type': 'input_text', 'text': prompt}] + [
        {'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(im).decode()}
        for im in req.images]
    body = json.dumps({'model': arm['model'], 'input': [{'role': 'user', 'content': content}],
                       'questions': [{'name': 'required', 'type': 'predicate',
                                      'instructions': QUESTIONS[case['role']]}]},
                      allow_nan=False, separators=(',', ':')).encode()
    return PreparedCall(case['role'], arm['model'], 'image', body, ev.digest,
                        hashlib.sha256(prompt.encode()).hexdigest(), req)


def dependency_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in ('httpx', 'typesafe-sdk', 'Pillow')}


def source_files() -> dict[str, Path]:
    root = Path(__file__).resolve().parents[2]
    files = list(Path(__file__).parent.glob('*.py')) + [
        root / 'python' / 'jevdual' / name for name in
        ('visual_decisions.py', 'visual_checks.py', 'visual_evidence.py', 'decisions.py', 'policy.py')]
    return {str(path.relative_to(root)): path for path in files}


def freeze(corpus_path: Path, protocol_path: Path, out: Path, *, development_paths=()) -> dict:
    corpus = load_corpus(corpus_path, development_paths=tuple(development_paths))
    p = validate_protocol(read_json(protocol_path))
    if {c['role'] for c in corpus.cases} != set(p['roles']):
        raise ValueError("corpus_protocol_roles")
    out.mkdir(parents=True, mode=0o700, exist_ok=False)
    schedule = []
    for case in corpus.cases:
        for arm_name, arm in p['arms'].items():
            prepared = prepare(corpus, case, arm, p['deadline_s'])
            for replay in range(p['replays']):
                schedule.append({'case_id': case['id'], 'arm': arm_name, 'replay': replay,
                                 'request_sha256': prepared.request_sha256,
                                 'evidence_sha256': prepared.evidence_sha256,
                                 'prompt_sha256': prepared.prompt_sha256})
    random.Random(p['seed']).shuffle(schedule)
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except subprocess.CalledProcessError:
        commit = 'unavailable'
    frozen = {'version': 1, 'corpus_path': str(corpus_path.resolve()),
              'development_paths': [str(Path(x).resolve()) for x in development_paths],
              'corpus_sha256': corpus.digest, 'protocol': p, 'protocol_path': str(protocol_path.resolve()),
              'protocol_sha256': sha(p), 'schedule_sha256': sha(schedule),
              'schedule': schedule, 'source_commit': commit,
              'frozen_at': datetime.now(UTC).isoformat(), 'dependency_versions': dependency_versions(),
              'source_sha256': {name: hashlib.sha256(f.read_bytes()).hexdigest()
                                for name, f in source_files().items()},
              'scope': 'frozen evidence replay; no live capture or execution authority'}
    save_json(out / 'frozen.json', frozen)
    return frozen


def checked_run(run: Path) -> tuple[dict, Corpus]:
    frozen = read_json(run / 'frozen.json')
    p = validate_protocol(frozen['protocol'])
    if sha(p) != frozen['protocol_sha256'] or sha(validate_protocol(read_json(Path(frozen['protocol_path'])))) != frozen['protocol_sha256']:
        raise ValueError('protocol_changed')
    corpus = load_corpus(Path(frozen['corpus_path']),
                         development_paths=tuple(Path(x) for x in frozen['development_paths']))
    if corpus.digest != frozen['corpus_sha256']:
        raise ValueError('corpus_changed')
    if frozen['dependency_versions'] != dependency_versions():
        raise ValueError('collector_dependencies_changed')
    if set(frozen['source_sha256']) != source_files().keys():
        raise ValueError('collector_source_changed')
    for name, file in source_files().items():
        if hashlib.sha256(file.read_bytes()).hexdigest() != frozen['source_sha256'][name]:
            raise ValueError('collector_source_changed')
    if sha(frozen['schedule']) != frozen['schedule_sha256']:
        raise ValueError('schedule_changed')
    schedule = {(c['id'], a, r) for c in corpus.cases for a in p['arms'] for r in range(p['replays'])}
    keys = [(x['case_id'], x['arm'], x['replay']) for x in frozen['schedule']]
    ordered_keys = [(c['id'], a, r) for c in corpus.cases for a in p['arms'] for r in range(p['replays'])]
    random.Random(p['seed']).shuffle(ordered_keys)
    if len(keys) != len(schedule) or set(keys) != schedule or keys != ordered_keys:
        raise ValueError('schedule_changed')
    for row in frozen['schedule']:
        case = next(c for c in corpus.cases if c['id'] == row['case_id'])
        prepared = prepare(corpus, case, p['arms'][row['arm']], p['deadline_s'])
        for name in ('request_sha256', 'evidence_sha256', 'prompt_sha256'):
            if row[name] != getattr(prepared, name):
                raise ValueError('frozen_input_changed')
    return frozen, corpus


Caller = Callable[[PreparedCall], Awaitable[dict]]


def _append(path: Path, row: dict) -> None:
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, allow_nan=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    path.chmod(0o600)


async def collect(run: Path, callers: dict[str, Caller], *, mode: str = 'mock') -> dict:
    """Future authorized collectors inject callers. No provider/key discovery occurs here.

    The reservation is a caller-specified local bound, not validated provider pricing.
    Unknown usage retains the whole reservation. No retries, resume or action path.
    """
    if mode not in ('mock', 'provider'):
        raise ValueError('collection_mode')
    frozen, corpus = checked_run(run)
    p = frozen['protocol']
    # Exclusive start prevents a second run resetting its attempt/budget history.
    with (run / 'started.json').open('x') as f:
        json.dump({'mode': mode, 'protocol_sha256': frozen['protocol_sha256'], 'started_at': datetime.now(UTC).isoformat(), 'frozen_sha256': sha(frozen), 'paid_calls':
                   'unavailable' if mode == 'provider' else 0}, f)
    state = {'reserved_upper_usd': 0.0, 'calls': 0, 'entries': []}
    stopped = False
    rows = []
    for scheduled in frozen['schedule']:
        checked_run(run)  # Source/label/protocol mutation refuses before another callback.
        case = next(c for c in corpus.cases if c['id'] == scheduled['case_id'])
        prepared = prepare(corpus, case, p['arms'][scheduled['arm']], p['deadline_s'])
        row = dict(scheduled) | {'status': 'not_run', 'p': None, 'requested_model': prepared.model,
                                'returned_model': None, 'timing': {'scope': 'evidence_replay', 'elapsed_ms': 0.0,
                                    'phases_ms': {}, 'verified_outcome': None, 'interventions': None},
                                'cost': {'upper_usd': 0.0, 'usage_known': True}, 'execution_authority': False}
        reserve = p['reservation_usd_per_attempt']
        if (not stopped and scheduled['arm'] in callers and state['calls'] < p['max_calls']
                and state['reserved_upper_usd'] + reserve <= p['max_reserved_cost_usd'] + 1e-12):
            state['calls'] += 1
            state['reserved_upper_usd'] += reserve
            entry = dict(scheduled) | {'upper_usd': reserve, 'usage_known': False, 'settled': False}
            state['entries'].append(entry)
            save_json(run / 'budget.json', state)  # Durable before callback; no optimistic release.
            row['cost'] = {'upper_usd': reserve, 'usage_known': False}
            start = time.perf_counter()
            try:
                async with asyncio.timeout(p['deadline_s']):
                    answer = await callers[scheduled['arm']](prepared)
                row.update(status=answer['status'], p=answer.get('p'), returned_model=answer.get('returned_model') or None)
                cost = answer.get('cost')
                if cost is not None:
                    if (set(cost) != {'upper_usd', 'usage_known'} or type(cost['usage_known']) is not bool
                            or type(cost['upper_usd']) not in (int, float) or not math.isfinite(cost['upper_usd'])
                            or cost['upper_usd'] < 0):
                        raise ValueError('callback_cost')
                    bound = cost['upper_usd'] if cost['usage_known'] else max(reserve, cost['upper_usd'])
                    state['reserved_upper_usd'] += bound - reserve
                    entry.update(upper_usd=bound, usage_known=cost['usage_known'], settled=cost['usage_known'])
                    row['cost'] = {'upper_usd': bound, 'usage_known': cost['usage_known']}
                    if bound > reserve:
                        row.update(status='invalid_response', p=None)
                        stopped = True
                checked_run(run)
            except TimeoutError:
                row.update(status='timeout', p=None)
            except asyncio.CancelledError:
                row.update(status='interrupted', p=None)
                row['timing']['elapsed_ms'] = (time.perf_counter() - start) * 1000
                _append(run / 'attempts.jsonl', row)
                raise
            except Exception:  # noqa: BLE001 - provider/source errors cannot leak their text
                row.update(status='error', p=None)
                stopped = True
            row['timing']['elapsed_ms'] = (time.perf_counter() - start) * 1000
            row['timing']['phases_ms'] = {'collection': row['timing']['elapsed_ms']}
            save_json(run / 'budget.json', state)
            # Validate returned identity/schema before proceeding, not just at final scoring.
            try:
                summarize(corpus, p, [row], mode=mode)
            except ValueError:
                row.update(status='invalid_response', p=None, returned_model=None)
                stopped = True
            stopped |= row['status'] in ('error', 'invalid_response', 'budget_exhausted')
        _append(run / 'attempts.jsonl', row)
        rows.append(row)
    report = summarize(corpus, p, rows, mode=mode)
    save_json(run / 'summary.json', report)
    save_json(run / 'closed.json', {'complete': report['complete'], 'mode': mode,
                                   'execution_authority': False})
    return report


def score_run(run: Path) -> dict:
    frozen, corpus = checked_run(run)
    rows = [decode_json(line) for line in (run / 'attempts.jsonl').read_text().splitlines()]
    expected = {(s['case_id'], s['arm'], s['replay']): s for s in frozen['schedule']}
    for row in rows:
        key = (row['case_id'], row['arm'], row['replay'])
        if key not in expected or any(row[k] != expected[key][k] for k in
                                     ('request_sha256', 'evidence_sha256', 'prompt_sha256')):
            raise ValueError('attempt_binding_changed')
    started = read_json(run / 'started.json')
    if (set(started) != {'mode', 'protocol_sha256', 'started_at', 'frozen_sha256', 'paid_calls'}
            or started['mode'] not in ('mock', 'provider')
            or started['protocol_sha256'] != frozen['protocol_sha256']
            or started['paid_calls'] != (0 if started['mode'] == 'mock' else 'unavailable')):
        raise ValueError('run_metadata_changed')
    stamp = datetime.fromisoformat(started['started_at'])
    if stamp.tzinfo is None:
        raise ValueError('run_metadata_changed')
    if started['frozen_sha256'] != sha(frozen):
        raise ValueError('frozen_run_changed')
    mode = started['mode']
    report = summarize(corpus, frozen['protocol'], rows, mode=mode)
    if (run / 'closed.json').exists():
        closed = read_json(run / 'closed.json')
        if (set(closed) != {'complete', 'mode', 'execution_authority'} or closed['mode'] != mode
                or type(closed['complete']) is not bool or closed['complete'] != report['complete']
                or closed['execution_authority'] is not False):
            raise ValueError('run_metadata_changed')
    return report


def mock_callers(run: Path) -> dict[str, Caller]:
    """Fixed p=.5, never oracle-dependent. Exercise production image wire/parse mechanics."""
    ordinal = 0

    async def call(prepared: PreparedCall) -> dict:
        nonlocal ordinal
        ordinal += 1
        if prepared.capability == 'text':
            return {'status': 'valid', 'p': .5, 'returned_model': prepared.model,
                    'cost': {'upper_usd': 0.0, 'usage_known': True}}
        if prepared.model != MODEL:
            return {'status': 'unavailable', 'p': None, 'returned_model': None}
        async def handler(message):
            if message.content != prepared.body:
                raise ValueError('production_wire_mismatch')
            return httpx.Response(200, json={'model': MODEL, 'answers': [
                {'name': 'required', 'type': 'predicate', 'probability': .5}], 'usage': {'input_tokens': 100}})
        ledger_path = run / 'ledgers' / f'{ordinal:06d}.json'
        ledger_path.parent.mkdir(mode=0o700, exist_ok=True)
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http,
            VisualDecisionsClient('synthetic-local-only', client=http) as client,
        ):
            result = await client.check(prepared.request, VisualCallLedger(ledger_path), is_current=lambda: True)
        return {'status': result.status, 'p': result.p, 'returned_model': result.returned_model,
                'cost': {'upper_usd': 0.0, 'usage_known': True}}
    return {'jev_text': call, 'decisions_visual': call}
