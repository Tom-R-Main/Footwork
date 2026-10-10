"""Actual local entry points, durable collection and frozen correspondence; no remote calls."""
import asyncio
import json

import httpx
import pytest

from evals.visual_qualification.__main__ import main
from evals.visual_qualification.corpus import load_corpus
from evals.visual_qualification.fixtures import save_json, seed_corpus
from evals.visual_qualification.runner import (
    checked_run,
    collect,
    default_protocol,
    freeze,
    mock_callers,
    prepare,
    read_json,
    score_run,
    sha,
    validate_protocol,
)


@pytest.fixture
def frozen(tmp_path):
    corpus = tmp_path / 'corpus'
    seed_corpus(corpus)
    manifest = read_json(corpus / 'manifest.json')
    ids = {'c001', 'c002', 'c003', 'c013', 'c014', 'c015'}
    manifest['cases'] = [c for c in manifest['cases'] if c['id'] in ids]
    labels = read_json(corpus / 'labels.json')
    labels['labels'] = {k: v for k, v in labels['labels'].items() if k in ids}
    save_json(corpus / 'labels.json', labels)
    import hashlib
    manifest['labels']['sha256'] = hashlib.sha256((corpus / 'labels.json').read_bytes()).hexdigest()
    save_json(corpus / 'manifest.json', manifest)
    protocol = corpus / 'protocol.json'
    save_json(protocol, default_protocol())
    run = tmp_path / 'run'
    freeze(corpus, protocol, run)
    return corpus, protocol, run


async def test_local_smoke_production_wire_and_recount(frozen, monkeypatch):
    corpus, _, run = frozen
    # MockTransport is the sole route; an accidental ordinary network request fails.
    async def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', forbidden)
    report = await collect(run, mock_callers(run))
    assert report['complete'] and report['observed_attempts'] == 24
    assert report['mode'] == 'mock' and report['execution_authority'] is False
    assert len(list((run / 'ledgers').glob('*.json'))) == 12
    assert all(not arm['qualified'] for family in report['families'].values() for arm in family.values())
    assert score_run(run) == report
    assert main(['score', '--run', str(run), '--out', str(run.parent / 'score')]) == 0
    assert main(['score', '--run', str(run), '--out', str(run.parent / 'score')]) == 4
    assert load_corpus(corpus).eligibility['eligible'] is False


async def test_reservation_before_call_unknown_usage_and_hard_cap(frozen):
    _, protocol, run = frozen
    p = read_json(protocol)
    p.update(max_calls=1, reservation_usd_per_attempt=.01, max_reserved_cost_usd=.01)
    save_json(protocol, p)
    # Start a fresh freeze; the old one remains historical and now refuses changed protocol.
    new = run.parent / 'capped'
    freeze(run.parent / 'corpus', protocol, new)
    called = []
    async def callback(prepared):
        budget = read_json(new / 'budget.json')
        assert budget['calls'] == 1 and not budget['entries'][0]['settled']
        called.append(prepared)
        return {'status': 'refusal', 'p': None, 'returned_model': prepared.model}
    report = await collect(new, dict.fromkeys(p['arms'], callback))
    assert len(called) == 1 and report['observed_attempts'] == 24
    assert report['cost']['unknown_usage_attempts'] == 1
    assert read_json(new / 'budget.json')['reserved_upper_usd'] == .01
    statuses = [json.loads(x)['status'] for x in (new / 'attempts.jsonl').read_text().splitlines()]
    assert statuses.count('not_run') == 23
    with pytest.raises(FileExistsError):
        await collect(new, dict.fromkeys(p['arms'], callback))
    with pytest.raises(ValueError, match='protocol_changed'):
        checked_run(run)


async def test_timeout_retains_reservation(frozen):
    _, protocol, run = frozen
    p = read_json(protocol)
    p.update(deadline_s=.001, max_calls=1)
    save_json(protocol, p)
    new = run.parent / 'timeout'
    freeze(run.parent / 'corpus', protocol, new)
    async def callback(prepared):
        await asyncio.sleep(.05)
        raise AssertionError('must be cancelled')
    result = await collect(new, dict.fromkeys(p['arms'], callback))
    assert result['cost']['unknown_usage_attempts'] == 1
    rows = [json.loads(x) for x in (new / 'attempts.jsonl').read_text().splitlines()]
    assert rows[0]['status'] == 'timeout' and rows[0]['p'] is None
    assert rows[0]['cost']['upper_usd'] == p['reservation_usd_per_attempt']


async def test_wrong_returned_model_stops_and_preserves_failure(frozen):
    _, protocol, run = frozen
    async def callback(prepared):
        return {'status': 'valid', 'p': .99, 'returned_model': 'different'}
    report = await collect(run, dict.fromkeys(read_json(protocol)['arms'], callback))
    rows = [json.loads(x) for x in (run / 'attempts.jsonl').read_text().splitlines()]
    assert rows[0]['status'] == 'invalid_response' and rows[0]['p'] is None
    assert all(r['status'] == 'not_run' for r in rows[1:])
    assert all(not a['quality']['qualified'] for f in report['families'].values() for a in f.values())


async def test_cancellation_records_interruption_without_reset(frozen):
    _, protocol, run = frozen
    async def callback(prepared):
        raise asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await collect(run, dict.fromkeys(read_json(protocol)['arms'], callback))
    rows = [json.loads(x) for x in (run / 'attempts.jsonl').read_text().splitlines()]
    assert rows[0]['status'] == 'interrupted'
    assert not score_run(run)['complete']
    assert read_json(run / 'budget.json')['reserved_upper_usd'] > 0


async def test_tampered_attempt_binding_refuses_scoring(frozen):
    _, _, run = frozen
    await collect(run, mock_callers(run))
    rows = [json.loads(x) for x in (run / 'attempts.jsonl').read_text().splitlines()]
    rows[0]['request_sha256'] = 'f' * 64
    (run / 'attempts.jsonl').write_text('\n'.join(json.dumps(x) for x in rows) + '\n')
    with pytest.raises(ValueError, match='attempt_binding_changed'):
        score_run(run)


def test_frozen_schedule_permutation_is_registered(frozen):
    _, _, run = frozen
    frozen_data = read_json(run / 'frozen.json')
    frozen_data['schedule'].reverse()
    frozen_data['schedule_sha256'] = sha(frozen_data['schedule'])
    save_json(run / 'frozen.json', frozen_data)
    with pytest.raises(ValueError, match='schedule_changed'):
        checked_run(run)


def test_projected_request_excludes_oracle_provenance_and_paths(frozen):
    corpus_path, protocol, _ = frozen
    corpus = load_corpus(corpus_path)
    for case in corpus.cases:
        for arm in read_json(protocol)['arms'].values():
            prepared = prepare(corpus, case, arm, 10)
            body = prepared.body.decode()
            assert 'authored_fixture' not in body and 'fixture-construction' not in body
            assert case['source_group'] not in body and case['id'] not in body
            assert case['input']['capture']['path'] not in body
            assert case['provenance']['source_record']['path'] not in body
            assert 'expected' not in body and 'labels.json' not in body


@pytest.mark.parametrize('change', [
    {'accept_p': True}, {'reject_p': .95}, {'replays': 0}, {'deadline_s': float('nan')},
    {'arms': {'single': {'model': 'm', 'capability': 'image'}}}, {'baseline_arm': 'missing'},
])
def test_invalid_protocol_refuses(change):
    with pytest.raises(ValueError):
        validate_protocol(default_protocol() | change)


def test_actual_seed_and_preflight_cli(tmp_path, capsys):
    out = tmp_path / 'seed'
    assert main(['seed', '--out', str(out)]) == 0
    assert main(['preflight', '--corpus', str(out)]) == 0
    printed = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert printed[0]['cases'] == printed[1]['cases'] == 24
    assert printed[1]['eligibility']['eligible'] is False
    assert main(['seed', '--out', str(out)]) == 4


def test_freeze_pins_production_interpretation_modules(frozen):
    _, _, run = frozen
    pins = read_json(run / 'frozen.json')['source_sha256']
    for path in ('python/jevdual/visual_decisions.py', 'python/jevdual/visual_checks.py',
                 'python/jevdual/visual_evidence.py', 'python/jevdual/decisions.py', 'python/jevdual/policy.py'):
        assert path in pins


def test_missing_frozen_source_pin_refuses(frozen):
    _, _, run = frozen
    data = read_json(run / 'frozen.json')
    data['source_sha256'].pop(next(iter(data['source_sha256'])))
    save_json(run / 'frozen.json', data)
    with pytest.raises(ValueError, match='collector_source_changed'):
        checked_run(run)


async def test_larger_unknown_usage_bound_never_disappears(frozen):
    _, protocol, run = frozen
    calls = []
    async def callback(prepared):
        calls.append(prepared)
        return {'status': 'valid', 'p': .5, 'returned_model': prepared.model,
                'cost': {'upper_usd': .5, 'usage_known': False}}
    result = await collect(run, dict.fromkeys(read_json(protocol)['arms'], callback))
    assert len(calls) == 1
    assert result['cost']['known_upper_usd_sum'] == .5
    assert read_json(run / 'budget.json')['reserved_upper_usd'] == .5
    first = json.loads((run / 'attempts.jsonl').read_text().splitlines()[0])
    assert first['status'] == 'invalid_response' and first['p'] is None
    assert first['cost'] == {'upper_usd': .5, 'usage_known': False}


def test_text_control_receives_explicit_crop_and_target_geometry(frozen):
    path, protocol, _ = frozen
    corpus = load_corpus(path)
    case = next(c for c in corpus.cases if c['role'] == 'crop_subject_containment')
    prepared = prepare(corpus, case, read_json(protocol)['arms']['jev_text'], 10)
    state = json.loads(json.loads(prepared.body)['state'])
    assert state['crop'] == case['input']['crop']
    assert state['target']['bounds'] == case['input']['capture']['binding']['target']['bounds']
    assert state['images_available'] is False and state['ownership_proven'] is False
    assert 'token' not in state['target'] and 'path' not in state['resource']


@pytest.mark.parametrize('artifact,field,value', [
    ('started.json', 'protocol_sha256', 'f' * 64),
    ('closed.json', 'mode', 'provider'),
    ('closed.json', 'complete', False),
])
async def test_contradictory_start_or_close_metadata_refuses(frozen, artifact, field, value):
    _, _, run = frozen
    await collect(run, mock_callers(run))
    data = read_json(run / artifact)
    data[field] = value
    save_json(run / artifact, data)
    with pytest.raises(ValueError, match='run_metadata_changed'):
        score_run(run)
