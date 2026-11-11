"""Real OS-lock/SQLite counterexample; no native driver or synthetic Coordinator."""
import asyncio
import json
import sys
import time
from pathlib import Path

from jevdual.coordination import CoordinationError, Coordinator


async def main(root):
    root.mkdir(parents=True, exist_ok=False)
    store = Coordinator(root / 'coordination.sqlite')
    result = {'target': 'ac892a75211900ca6e252a46bca4f0da2362af6b',
              'platform': sys.platform, 'registry': str(store.path), 'checks': {}}
    async with store.claim('film', ['desktop', 'app/fixture']) as claim:
        reservation = store.reserve(claim, claim.resources)
    async with store.claim('film', ['desktop', 'app/fixture'], reservation=reservation, timeout=.3):
        result['checks']['owner_without_waiter'] = True
    async with store.claim('independent', ['app/other'], timeout=.3):
        result['checks']['independent_background'] = True
    competitor = asyncio.create_task(store.claim('competitor', ['desktop'], timeout=5).__aenter__())
    for _ in range(100):
        if any(r['owner'] == 'competitor' and r['state'] == 'waiting' for r in store.status()['requests']):
            break
        await asyncio.sleep(.01)
    else:
        raise AssertionError('counterexample setup failed: no earlier waiter')
    before = time.monotonic()
    try:
        async with store.claim('film', ['desktop', 'app/fixture'], reservation=reservation, timeout=.3):
            result['checks']['owner_continues_with_waiter'] = True
    except CoordinationError as exc:
        result['checks']['owner_continues_with_waiter'] = False
        result['owner_error'] = str(exc)
    finally:
        result['owner_wait_seconds'] = round(time.monotonic() - before, 3)
        competitor.cancel()
        try:
            await competitor
        except asyncio.CancelledError:
            pass
    async with store.claim('film', ['desktop', 'app/fixture'], reservation=reservation, timeout=.3):
        result['checks']['owner_after_competitor_cancel'] = True
    store.revoke(reservation)
    result['cleanup'] = store.status()
    print(json.dumps(result, indent=2))
    return 0 if all(result['checks'].values()) else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main(Path(sys.argv[1]))))
