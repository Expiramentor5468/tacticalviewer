import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_feeds as base
import enrich_prime_vision as prime
import enrich_sky_bundesliga as sky
import enrich_branded_monitors as brands
import enrich_global_discovery as worldwide
import run_update as runner

NOW = datetime(2026, 10, 30, 14, tzinfo=timezone.utc)
RSS = '<rss><channel/></rss>'


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for module in (base, prime, sky, brands, worldwide):
            self.stack.enter_context(patch.object(module, 'ROOT', root))
            self.stack.enter_context(patch.object(module, 'DATA', root / 'data'))
            self.stack.enter_context(patch.object(module, 'datetime', Clock))
        self.stack.enter_context(patch.object(runner, 'datetime', Clock))
        keys = ['amazon:prime-vision', 'sky:bundesliga-tactical', 'mls:alternate-cameras', worldwide.SOURCE]
        self.old = [self.row(key) for key in keys]
        self.previous = dict(schemaVersion=2, updatedAt='2026-10-29T12:00:00Z',
                             lastSuccessfulScanAt='2026-10-29T12:00:00Z', scanStatus='ok',
                             sourceHealth=[], feeds=self.old)
        base.write_payload(self.previous)
        self.stack.enter_context(patch.object(base, 'get', side_effect=lambda url: RSS if 'rss' in url else '<html>' + 'x' * 150 + '</html>'))

    def row(self, key):
        return dict(id=key, sourceKey=key, match='A vs B', competition='MLS', type='alternate',
                    status='confirmed', kickoff='2026-11-20T20:00:00Z', platform=key,
                    sourceUrl='https://example.com/evidence', watchUrl='https://example.com/watch',
                    territories=['United States'], access='free', exactFixtureVerified=True,
                    publicAccessConfirmed=True, verifiedAt='2026-10-29T12:00:00Z',
                    checkedAt='2026-10-29T12:00:00Z', sourcePublishedAt='2026-10-29T12:00:00Z')

    def read(self):
        return base.read_json(base.DATA / 'feeds.json', {})

    def successful_sources(self):
        def amazon(url):
            if url == prime.PRIME_POLICY:
                return '<p>Prime Vision top-pick Tuesday match 2030/31</p>'
            return '<html>' + 'x' * 150 + '</html>'

        def sky_text(url):
            if url == sky.FIXTURES:
                return 'league[0]=bl&matchday[0]=9&season=2026'
            return 'Tactical Feed Sky Sport Bundesliga 3 Topspiel'

        self.stack.enter_context(patch.object(prime, 'get', side_effect=amazon))
        self.stack.enter_context(patch.object(sky, 'get_text', side_effect=sky_text))
        self.stack.enter_context(patch.object(sky, 'get_bytes', return_value=b'export'))
        self.stack.enter_context(patch.object(sky, 'top_spiele_from_export', return_value=[]))
        self.stack.enter_context(patch.object(brands, 'get', return_value=RSS))
        self.stack.enter_context(patch.object(worldwide, 'get', return_value=RSS))

    def test_full_pipeline_outages_retain_evidence_and_report_partial(self):
        for module, method in ((prime, 'get'), (sky, 'get_text'), (brands, 'get'), (worldwide, 'get')):
            self.stack.enter_context(patch.object(module, method, side_effect=TimeoutError))
        self.assertEqual(runner.main(), 2)
        p = self.read()
        self.assertEqual(p['scanStatus'], 'partial')
        self.assertEqual(p['lastSuccessfulScanAt'], self.previous['lastSuccessfulScanAt'])
        self.assertEqual({f['id'] for f in p['feeds']}, {f['id'] for f in self.old})
        for f in p['feeds']:
            self.assertEqual(f['checkedAt'], '2026-10-29T12:00:00Z')
            self.assertEqual(f['verifiedAt'], '2026-10-29T12:00:00Z')
        self.assertTrue(any(h['ok'] for h in p['sourceHealth']))
        self.assertTrue(any(not h['ok'] for h in p['sourceHealth']))
        bundled = (base.ROOT / 'data.js').read_text()
        self.assertEqual(bundled, 'window.TACTICAL_FEED_DATA = ' + __import__('json').dumps(p, indent=2, ensure_ascii=False) + ';\n')

    def test_complete_empty_sources_replace_previous_results(self):
        self.successful_sources()
        self.assertEqual(runner.main(), 0)
        p = self.read()
        self.assertEqual(p['scanStatus'], 'ok')
        self.assertEqual(p['lastSuccessfulScanAt'], base.stamp(NOW))
        self.assertTrue(all(h['ok'] for h in p['sourceHealth']))
        self.assertFalse(any(f.get('sourceKey') in {r['sourceKey'] for r in self.old} for f in p['feeds']))

    def test_partial_global_search_is_not_success_and_keeps_old_leads(self):
        self.stack.enter_context(patch.object(worldwide, 'get', side_effect=[RSS, TimeoutError(), TimeoutError()]))
        self.assertEqual(worldwide.main(), 2)
        p = self.read()
        h = p['sourceHealth'][-1]
        self.assertFalse(h['ok'])
        self.assertEqual((h['queriesChecked'], h['queriesExpected']), (1, 3))
        self.assertTrue(any(f['id'] == worldwide.SOURCE for f in p['feeds']))

    def test_partial_sky_exports_are_not_success_and_keep_old_rows(self):
        self.successful_sources()
        with patch.object(sky, 'get_bytes', side_effect=[b'export'] + [TimeoutError()] * 10):
            self.assertEqual(sky.main(), 2)
        p = self.read()
        h = p['sourceHealth'][-1]
        self.assertFalse(h['ok'])
        self.assertEqual((h['exportsChecked'], h['exportsExpected']), (1, 11))
        self.assertTrue(any(f['id'] == 'sky:bundesliga-tactical' for f in p['feeds']))

    def test_stage_crash_cannot_reuse_old_success_health(self):
        p = self.read()
        p['sourceHealth'] = [dict(source='amazon:prime-vision', ok=True, checkedAt=p['updatedAt'])]
        base.write_payload(p)

        def crash():
            raise RuntimeError('simulated')

        self.assertEqual(runner.main([(crash, {'amazon:prime-vision'})]), 2)
        p = self.read()
        self.assertEqual(p['scanStatus'], 'failed')
        self.assertFalse(p['sourceHealth'][0]['ok'])
        self.assertEqual(p['lastSuccessfulScanAt'], self.previous['lastSuccessfulScanAt'])

    def test_policy_review_is_not_renewed_by_successful_fetch(self):
        self.successful_sources()
        fixture = dict(match='A vs B', kickoff=datetime(2026, 11, 20, 20, tzinfo=timezone.utc))
        with patch.object(prime, 'parse_month_page', return_value=[fixture]):
            self.assertEqual(prime.main(), 0)
        row = next(f for f in self.read()['feeds'] if f.get('sourceKey') == 'amazon:prime-vision')
        self.assertEqual(row['status'], 'confirmed')
        self.assertEqual(row['verifiedAt'], prime.POLICY_REVIEWED_AT)
        self.assertEqual(row['checkedAt'], base.stamp(NOW))
        with patch.object(prime, 'POLICY_REVIEWED_AT', '2026-10-01T00:00:00Z'), patch.object(prime, 'parse_month_page', return_value=[fixture]):
            self.assertEqual(prime.main(), 0)
        row = next(f for f in self.read()['feeds'] if f.get('sourceKey') == 'amazon:prime-vision')
        self.assertEqual(row['status'], 'candidate')
        self.assertNotIn('watchUrl', row)
        self.assertTrue(self.read()['sourceHealth'][-1]['policyReviewExpired'])

    def test_retained_evidence_still_expires(self):
        row = self.row(worldwide.SOURCE)
        row['sourcePublishedAt'] = '2026-08-01T00:00:00Z'
        self.assertEqual(base.retain_evidence([row], NOW), [])
        row = self.row('sky:bundesliga-tactical')
        row['verifiedAt'] = '2026-10-01T00:00:00Z'
        retained = base.retain_evidence([row], NOW)[0]
        self.assertEqual(retained['status'], 'candidate')
        self.assertNotIn('watchUrl', retained)

    def test_html_error_page_is_not_an_empty_successful_search(self):
        for parse in (lambda xml: brands.parse(xml, brands.MONITORS[0], NOW), lambda xml: worldwide.parse(xml, NOW)):
            with self.assertRaises(ValueError):
                parse('<html>Rate limited</html>')


if __name__ == '__main__':
    unittest.main()
