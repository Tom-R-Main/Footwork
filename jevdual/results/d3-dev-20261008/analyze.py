"""Offline recount from frozen receipts; no provider calls or surface execution."""
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
CAPTURE = ROOT / 'results/d3-capture-20261008'


def timing(values):
    values = sorted(values)
    return {'n': len(values), 'median_ms': statistics.median(values),
            'p95_ms': values[math.ceil(.95 * len(values)) - 1]} if values else {}


def analyze():
    rows = json.loads((RUN / 'results.json').read_text())
    summary = json.loads((RUN / 'summary.json').read_text())
    manifest = json.loads((CAPTURE / 'manifest.json').read_text())
    cases = {c['id']: c for c in manifest['cases']}
    assert len(rows) == 216
    assert len({(r['id'], r['arm'], r['repeat']) for r in rows}) == 216
    started = json.loads((RUN / 'started.json').read_text())
    assert hashlib.sha256((CAPTURE / 'manifest.json').read_bytes()).hexdigest() == started['manifest_sha256']
    arms = {}
    for arm, original in summary['arms'].items():
        mine = [r for r in rows if r['arm'] == arm]
        executions = [r for r in mine if 'execution' in r]
        corrected = [cases[r['id']]['capture'].get('phase_total_ms', cases[r['id']]['capture']['capture_ms']) + r['request_ms'] for r in mine]
        record = {'primary_all_three_correct': len(original['all_three_correct']),
                  'positive_all_three': sum(c['all_three_correct'] for c in original['positive']),
                  'negative_all_three': sum(c['all_three_correct'] for c in original['negative']),
                  'ambiguous_primary_all_three': sum(c['all_three_correct'] for c in original['ambiguous']),
                  'ambiguous_safe_all_three': len(original['ambiguous_all_three_safe_nonacceptance']),
                  'invalid_confident_positive_cases': original['invalid_confident_positive'],
                  'wrong_effect_cases': original['wrong_effects'], 'refusals': original['refusals'],
                  'provider_errors': original['errors'], 'execution_checks': len(executions),
                  'execution_coverage_errors': original['execution_coverage_gaps'],
                  'actual_dispatches': sum(r['execution'].get('dispatched', False) for r in executions),
                  'goal_or_postcondition_met': sum(r['execution'].get('goal_met', r['execution'].get('postcondition_observed', False)) for r in executions),
                  'request_timing': timing([r['request_ms'] for r in mine]),
                  'corrected_capture_to_judgment_estimate': timing(corrected),
                  'reconstructed_execution_total': timing([r['execution_ms'] for r in executions]),
                  'family_all_three': {f: r['all_three_correct'] for f, r in original['by_family'].items()},
                  'corrected_capture_to_judgment_by_surface': {surface: timing([cases[r['id']]['capture'].get('phase_total_ms', cases[r['id']]['capture']['capture_ms']) + r['request_ms'] for r in mine if r['surface'] == surface]) for surface in {r['surface'] for r in mine}}}
        arms[arm] = record
    cost = sum(r['budget']['charged_upper_usd'] for r in rows)
    result = {'measured_commit': started['commit'], 'attempts': len(rows), 'execution_checks': 72,
              'arms': arms, 'primary_gain_combined_vs_text': len(summary['arms']['decisions_combined']['all_three_correct']) - len(summary['arms']['decisions_text']['all_three_correct']),
              'qualification_rule_met': False,
              'failure': 'B02 combined p=.99 all three; repeat0 real click enters rotate rather than crop',
              'accounting': {'d3_reported_input_estimate_usd': cost,
                             'pilot_reported_input_estimate_usd': .051255158 + cost,
                             'pilot_reported_or_reserved_upper_usd': json.loads((RUN / 'budget.json').read_text())['reserved_or_usage_upper_usd'],
                             'd3_unknown_usage': sum(not r['budget']['usage_known'] for r in rows), 'prior_unknown_usage': 2},
              'timing_correction': 'Original browser estimate used screenshot-only capture_ms; offline calculation uses retained phase_total_ms. Original summary preserved. Native total unchanged.'}
    (RUN / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    result = analyze()
    print(json.dumps(result, indent=2))
