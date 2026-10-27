import importlib.util
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

spec = importlib.util.spec_from_file_location('updater', Path(__file__).resolve().parents[1] / 'scripts/update_feeds.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
NOW = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)

class FeedTests(unittest.TestCase):
    def fixture(self, **changes):
        row = dict(id='match', match='A vs B', competition='Premier League', kickoff='2026-10-31T17:30:00Z', type='tactical', status='confirmed', exactFixtureVerified=True, publicAccessConfirmed=True, platform='Example', territories=['US'], sourceUrl='https://example.com/news', watchUrl='https://example.com/watch', verifiedAt='2026-10-27T10:00:00Z')
        row.update(changes)
        return row

    def test_public_route_required(self):
        self.assertEqual(u.normalize(self.fixture(watchUrl=None), NOW)['status'], 'candidate')
        self.assertEqual(u.normalize(self.fixture(publicAccessConfirmed=False), NOW)['status'], 'candidate')

    def test_production_never_infers_access(self):
        row = u.normalize(self.fixture(status='production', usAvailability=True, access='subscription'), NOW)
        self.assertIsNone(row['usAvailability'])
        self.assertEqual(row['access'], 'unknown')
        self.assertNotIn('watchUrl', row)

    def test_recent_exact_public_evidence_can_confirm(self):
        self.assertEqual(u.normalize(self.fixture(), NOW)['status'], 'confirmed')

    def test_expired_or_future_evidence_downgrades(self):
        for date in ['2026-10-01T10:00:00Z', '2026-10-28T10:00:00Z', 'invalid']:
            self.assertEqual(u.normalize(self.fixture(verifiedAt=date), NOW)['status'], 'candidate')

    def test_expired_fixture_removed(self):
        self.assertIsNone(u.normalize(self.fixture(kickoff='2026-10-25T10:00:00Z'), NOW))

    def test_unsafe_links_and_naive_dates_fail_validation(self):
        self.assertFalse(u.safe_url('javascript:alert(1)'))
        self.assertIsNone(u.parse_date('2026-10-27T12:00:00'))
        self.assertEqual(u.normalize(self.fixture(sourceUrl='javascript:alert(1)'), NOW)['status'], 'candidate')

    def test_rss_requires_recent_publication(self):
        def rss(date):
            return f'<rss><channel><item><title>Tactical cam announced</title><pubDate>{date}</pubDate><link>https://example.com/a</link></item></channel></rss>'
        self.assertEqual(len(u.news_candidates(rss('Tue, 27 Oct 2026 10:00:00 GMT'), 'MLS', 'news:MLS', NOW)), 1)
        for date in ['', 'Thu, 01 Oct 2026 10:00:00 GMT', 'Wed, 28 Oct 2026 10:00:00 GMT']:
            self.assertEqual(u.news_candidates(rss(date), 'MLS', 'news:MLS', NOW), [])

    def test_html_is_not_successful_rss(self):
        with self.assertRaises(ValueError):
            u.news_candidates('<html>Rate limited</html>', 'MLS', 'news:MLS', NOW)

    def test_failure_preserves_old_evidence_date_and_scan_time(self):
        old = self.fixture(status='candidate', id='lead', kickoff=None, sourceKey='news:MLS', sourcePublishedAt='2026-10-26T12:00:00Z', checkedAt='2026-10-26T13:00:00Z')
        def fail(_): raise TimeoutError()
        result = u.build_payload([], {'feeds': [old], 'lastSuccessfulScanAt': '2026-10-26T13:00:00Z'}, fetch=fail, now=NOW)
        self.assertEqual(result['scanStatus'], 'failed')
        self.assertEqual(result['feeds'][0]['checkedAt'], old['checkedAt'])
        self.assertEqual(result['lastSuccessfulScanAt'], '2026-10-26T13:00:00Z')

    def test_fixture_parser_keeps_tooltip_in_row_and_uses_utc(self):
        html = '<table><tr>' + ''.join('<td>' + value + '</td>' for value in ['9', 'Sat | 31-Oct-2026', '18:30', '17:30', 'Bayern München', 'Borussia Dortmund', 'Platinum', '<template><p>Extra Feeds</p><li>Tactical Feed</li></template>']) + '</tr></table>'
        rows = u.production_fixtures(html, NOW)
        self.assertEqual(rows[0]['kickoff'], '2026-10-31T17:30:00Z')
        self.assertEqual(rows[0]['status'], 'production')
        self.assertFalse(rows[0]['publicAccessConfirmed'])
        self.assertEqual(u.production_fixtures(html.replace('Tactical Feed', 'Coach Cam'), NOW), [])

    def test_manual_and_discovered_fixture_deduplicate(self):
        a = self.fixture(status='production')
        self.assertEqual(len(u.dedupe([a, dict(a, id='other')])), 1)

if __name__ == '__main__': unittest.main()
