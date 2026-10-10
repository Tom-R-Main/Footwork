"""No-key local entry point: seed, preflight, freeze, smoke, score."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .corpus import load_corpus
from .fixtures import save_json, seed_corpus
from .runner import checked_run, collect, default_protocol, freeze, mock_callers, score_run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    seed = sub.add_parser('seed', help='create a fresh authored development corpus and example protocol')
    seed.add_argument('--out', type=Path, required=True)
    for name in ('preflight', 'freeze', 'smoke'):
        command = sub.add_parser(name)
        command.add_argument('--corpus', type=Path, required=True)
        command.add_argument('--development', type=Path, action='append', default=[])
        if name != 'preflight':
            command.add_argument('--protocol', type=Path, required=True)
            command.add_argument('--out', type=Path, required=True)
    score = sub.add_parser('score', help='read frozen attempts; never invoke a provider')
    score.add_argument('--run', type=Path, required=True)
    score.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'seed':
            path = seed_corpus(args.out)
            save_json(args.out / 'protocol.json', default_protocol())
            result = {'manifest': str(path), 'cases': 24, 'split': 'development', 'qualification_eligible': False}
        elif args.command == 'preflight':
            corpus = load_corpus(args.corpus, development_paths=tuple(args.development))
            result = {'cases': len(corpus.cases), 'corpus_sha256': corpus.digest, 'eligibility': corpus.eligibility}
        elif args.command in ('freeze', 'smoke'):
            freeze(args.corpus, args.protocol, args.out, development_paths=args.development)
            if args.command == 'smoke':
                report = asyncio.run(collect(args.out, mock_callers(args.out), mode='mock'))
                result = {'complete': report['complete'], 'attempts': report['observed_attempts'],
                          'mode': 'mock', 'paid_calls': 0, 'execution_authority': False}
            else:
                frozen, _ = checked_run(args.out)
                result = {'scheduled_attempts': len(frozen['schedule']), 'mode': 'not_started'}
        else:
            result = score_run(args.run)
            args.out.mkdir(mode=0o700, parents=True, exist_ok=False)
            save_json(args.out / 'summary.json', result)
            result = {'complete': result['complete'], 'attempts': result['observed_attempts'], 'mode': result['mode'],
                      'report': str(args.out / 'summary.json'), 'execution_authority': False}
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        # Corpus/provider contents and paths are not error messages.
        print(json.dumps({'status': 'refused', 'reason': getattr(exc, 'code', 'invalid_or_changed_qualification_artifact')}))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
