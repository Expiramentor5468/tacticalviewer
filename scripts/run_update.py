#!/usr/bin/env python3
"""Run every source before publishing a single, honest scan result."""
from datetime import datetime, timezone

import update_feeds as base
import enrich_prime_vision as prime
import enrich_sky_bundesliga as sky
import enrich_branded_monitors as brands
import enrich_global_discovery as worldwide


STAGES = [
    (base.main, {'news:' + comp for comp, _ in base.SEARCHES} | {'bundesliga:production'}),
    (prime.main, {'amazon:prime-vision'}),
    (sky.main, {'sky:bundesliga-tactical'}),
    (brands.main, {m['key'] for m in brands.MONITORS}),
    (worldwide.main, {worldwide.SOURCE}),
]


def main(stages=None):
    stages = STAGES if stages is None else stages
    started = datetime.now(timezone.utc)
    previous = base.read_json(base.DATA / 'feeds.json', {})
    failed = set()
    for run, keys in stages:
        try:
            run()  # Per-source health distinguishes partial coverage from total failure.
        except Exception as exc:
            failed.update(keys)
            print(f'{run.__module__}: {type(exc).__name__}')

    payload = base.read_json(base.DATA / 'feeds.json', previous)
    health = {h['source']: h for h in payload.get('sourceHealth', [])}
    expected = set().union(*(keys for _, keys in stages))
    for key in sorted(expected):
        h = health.get(key)
        checked = base.parse_date((h or {}).get('checkedAt') or (h or {}).get('attemptedAt'))
        if not h or not checked or checked < started:
            health[key] = {'source': key, 'ok': False, 'attemptedAt': base.stamp(started), 'error': 'StageDidNotComplete'}
        elif key in failed and h.get('ok'):
            health[key] = dict(h, ok=False, error='StageDidNotComplete')
    successes = sum(health[k].get('ok') is True for k in expected)
    complete = bool(expected) and successes == len(expected)
    now = datetime.now(timezone.utc)
    payload.update(
        schemaVersion=2, updatedAt=base.stamp(now), lastAttemptAt=base.stamp(started),
        lastSuccessfulScanAt=base.stamp(now) if complete else previous.get('lastSuccessfulScanAt'),
        scanStatus='ok' if complete else 'partial' if successes else 'failed',
        sourceHealth=list(health.values()),
        feeds=base.retain_evidence(payload.get('feeds', []), now),
    )
    base.write_payload(payload)
    print(f"Full scan {payload['scanStatus']}: {successes}/{len(expected)} sources checked")
    return 0 if complete else 2


if __name__ == '__main__':
    raise SystemExit(main())
