window.TACTICAL_FEED_DATA = {
  "schemaVersion": 2,
  "updatedAt": "2026-10-28T18:26:14.777243Z",
  "lastAttemptAt": "2026-10-28T18:25:58.142496Z",
  "lastSuccessfulScanAt": "2026-10-28T18:25:58.142496Z",
  "scanStatus": "ok",
  "sourceHealth": [
    {
      "source": "news:UEFA Champions League",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z",
      "count": 0
    },
    {
      "source": "news:Premier League",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z",
      "count": 0
    },
    {
      "source": "news:MLS",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z",
      "count": 0
    },
    {
      "source": "news:Bundesliga",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z",
      "count": 0
    },
    {
      "source": "news:Serie A",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z",
      "count": 0
    },
    {
      "source": "bundesliga:production",
      "ok": true,
      "checkedAt": "2026-10-28T18:25:58.142496Z"
    },
    {
      "source": "amazon:prime-vision",
      "ok": false,
      "checkedAt": "2026-10-28T18:26:00.952118Z",
      "count": 2,
      "pagesChecked": 2,
      "error": "ValueError"
    },
    {
      "source": "sky:bundesliga-tactical",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:02.811093Z",
      "count": 0,
      "exportsChecked": 11,
      "englishAudioVerified": false
    },
    {
      "source": "cbs:golazo-tactical",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "count": 0
    },
    {
      "source": "mls:alternate-cameras",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "count": 1
    },
    {
      "source": "premierleague:alternate-cameras",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "count": 0
    },
    {
      "source": "ligue1:expert-mode",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "count": 1
    },
    {
      "source": "global:camera-feed-discovery",
      "ok": true,
      "checkedAt": "2026-10-28T18:26:14.777243Z",
      "count": 1,
      "queriesChecked": 3
    }
  ],
  "feeds": [
    {
      "id": "bundesliga-bayern-dortmund-2026-10-31-tactical",
      "match": "FC Bayern München vs Borussia Dortmund",
      "competition": "Bundesliga",
      "kickoff": "2026-10-31T17:30:00Z",
      "type": "tactical",
      "status": "production",
      "platform": "Bundesliga production — consumer carrier unverified",
      "language": "English",
      "commentary": "DFL Tactical Feed includes expert English-language analysis; public carrier unverified",
      "usAvailability": null,
      "access": "unknown",
      "notes": "Official fixture page lists Extra Feeds → Tactical Feed and Extra Cams → Coach Cam. This verifies production for the match, not a public viewing route. Public territory, carrier and price still require verification.",
      "sourceUrl": "https://products.bundesliga.com/fixtures",
      "secondarySourceUrl": "https://products.bundesliga.com/matchdays",
      "checkedAt": "2026-10-28T18:05:00Z",
      "verifiedAt": "2026-10-28T18:05:00Z",
      "exactFixtureVerified": true,
      "publicAccessConfirmed": false
    },
    {
      "id": "mls-yahoo-miami-cincinnati-2026-10-28",
      "match": "Inter Miami CF vs FC Cincinnati",
      "competition": "MLS",
      "kickoff": "2026-10-28T23:30:00Z",
      "type": "alternate",
      "status": "confirmed",
      "platform": "Yahoo Sports / Apple TV altcast",
      "language": "English",
      "commentary": "English — The Cooligans with Calen Carr",
      "usAvailability": true,
      "access": "free",
      "territories": [
        "United States"
      ],
      "notes": "Full-match Yahoo Sports alternate broadcast with multiple Apple/MLS camera angles, including Ref Cam and a dedicated iPhone feed. The confirmed public territory here is the U.S.; do not infer Yahoo availability elsewhere without a regional source.",
      "sourceUrl": "https://bracket.mlssoccer.com/news/yahoo-sports-and-apple-tv-team-up-to-bring-the-cooligans-to-a-live-mls-alternate-broadcast",
      "fixtureSourceUrl": "https://www.intermiamicf.com/news/match-preview-inter-miami-cf-hosts-fc-cincinnati-on-wednesday",
      "watchUrl": "https://sports.yahoo.com/videos/watch-live-mls-apple-tv-185918425.html",
      "checkedAt": "2026-10-28T18:05:00Z",
      "verifiedAt": "2026-10-28T18:05:00Z",
      "exactFixtureVerified": true,
      "publicAccessConfirmed": true
    },
    {
      "id": "prime-vision-5d9fbd950af80a60",
      "match": "Manchester United vs Roma",
      "competition": "UEFA Champions League",
      "kickoff": "2026-11-03T20:00:00Z",
      "type": "alternate",
      "status": "candidate",
      "platform": "Prime Video — Prime Vision",
      "language": "Unknown",
      "commentary": "English audio not yet verified",
      "usAvailability": null,
      "access": "unknown",
      "territories": [],
      "notes": "Amazon's monthly schedule confirms the exact UCL top-pick fixture. Prime Video's UCL help confirms Prime Vision, English default commentary, and UK/Republic of Ireland public access. Prime Vision is data-enhanced alternate coverage, not a persistent full-pitch wide camera.",
      "sourceUrl": "https://www.aboutamazon.co.uk/news/entertainment/whats-on-prime-video-uk-november-2026",
      "watchUrl": null,
      "sourceKey": "amazon:prime-vision",
      "checkedAt": "2026-10-28T18:26:00.952118Z",
      "verifiedAt": null,
      "exactFixtureVerified": true,
      "publicAccessConfirmed": false,
      "secondarySourceUrl": "https://www.primevideo.com/salp/ucl-help/?content-id=amzn1.sym.c83a5986-c17a-49df-8a90-4c35387dfd80",
      "policySourceUrl": "https://www.aboutamazon.co.uk/news/entertainment/champions-league-prime-video-uk-renewal"
    },
    {
      "id": "prime-vision-ba82a33d35939a68",
      "match": "Arsenal vs Dortmund",
      "competition": "UEFA Champions League",
      "kickoff": "2026-11-24T20:00:00Z",
      "type": "alternate",
      "status": "candidate",
      "platform": "Prime Video — Prime Vision",
      "language": "Unknown",
      "commentary": "English audio not yet verified",
      "usAvailability": null,
      "access": "unknown",
      "territories": [],
      "notes": "Amazon's monthly schedule confirms the exact UCL top-pick fixture. Prime Video's UCL help confirms Prime Vision, English default commentary, and UK/Republic of Ireland public access. Prime Vision is data-enhanced alternate coverage, not a persistent full-pitch wide camera.",
      "sourceUrl": "https://www.aboutamazon.co.uk/news/entertainment/whats-on-prime-video-uk-november-2026",
      "watchUrl": null,
      "sourceKey": "amazon:prime-vision",
      "checkedAt": "2026-10-28T18:26:00.952118Z",
      "verifiedAt": null,
      "exactFixtureVerified": true,
      "publicAccessConfirmed": false,
      "secondarySourceUrl": "https://www.primevideo.com/salp/ucl-help/?content-id=amzn1.sym.c83a5986-c17a-49df-8a90-4c35387dfd80",
      "policySourceUrl": "https://www.aboutamazon.co.uk/news/entertainment/champions-league-prime-video-uk-renewal"
    },
    {
      "id": "brand-monitor-764f126459acee0a",
      "match": "Yahoo Sports and Apple TV Team Up to Bring “The Cooligans” to a Live MLS Alternate Broadcast - MLSsoccer.com",
      "competition": "MLS",
      "kickoff": null,
      "type": "alternate",
      "status": "candidate",
      "platform": "MLS / Apple TV alternate cameras",
      "language": "English",
      "commentary": "English",
      "usAvailability": null,
      "access": "unknown",
      "territories": [],
      "notes": "Branded-product lead. Exact fixture, public viewing route, territory and kickoff must be verified before confirmation.",
      "sourceUrl": "https://news.google.com/rss/articles/CBMivgFBVV95cUxNdVBEcVRKREY1cGhNRGRUSWVraEc2cjNmblAxSHJtZFBoSkxHOHZGRzN6Q2g4XzdkSzlyUm96T2VYVWxHS0trU1o3MWUyLUwzVF8zY0tQM3NDcEc3eUt6Y0loRU9YNmFCNlg3NzJGdWppNlhQYnZQQVhYbmh3eE5fVUZnLVVnRl9Pci0yV0VjM3dwX3RWRXZtZUNXV0tMYlU5U1l6Ykg4Rktic0VLekJYSUJmTlNvWkphMmJUM3Nn?oc=5",
      "sourcePublishedAt": "2026-09-02T07:00:00Z",
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "sourceKey": "mls:alternate-cameras",
      "exactFixtureVerified": false,
      "publicAccessConfirmed": false
    },
    {
      "id": "brand-monitor-263fc464a21d3d4d",
      "match": "LFP brings automated data ‘Moments’ to Ligue 1+ Expert Mode - SVG Europe",
      "competition": "Ligue 1",
      "kickoff": null,
      "type": "alternate",
      "status": "candidate",
      "platform": "Ligue 1+ — Expert Mode",
      "language": "Unknown",
      "commentary": "English audio not yet verified",
      "usAvailability": null,
      "access": "unknown",
      "territories": [],
      "notes": "Branded-product lead. Exact fixture, public viewing route, territory and kickoff must be verified before confirmation.",
      "sourceUrl": "https://news.google.com/rss/articles/CBMinwFBVV95cUxOcFlad29wOHpMQzhNMFlUaGMzd0dsMkRPcXU5YTdNMVptY3UwVVh0Mk1POXY3TUZIcXBObXNfY3ZPVjdReHZ3cDFfVHlJQ2FFdEJOaXhnel9GY1F5c0tWSXRUWnRMcHJqdFh3SklER0lCcDBMRTJYMXpTcm9MZjlkMV9rTnRYU2xId0ZNQ0dvY3d4b292YWE4ZDlkaUVqb2M?oc=5",
      "sourcePublishedAt": "2026-09-08T07:00:00Z",
      "checkedAt": "2026-10-28T18:26:13.986827Z",
      "sourceKey": "ligue1:expert-mode",
      "exactFixtureVerified": false,
      "publicAccessConfirmed": false
    },
    {
      "id": "global-lead-3349180fd1b8fa62",
      "match": "Underdog & Co. makes another move in adding Wide Angle Group - Sports Business Journal",
      "competition": "Other / global",
      "kickoff": null,
      "type": "tactical",
      "status": "candidate",
      "platform": "Global discovery — carrier unverified",
      "language": "Unknown",
      "commentary": "English audio not yet verified",
      "usAvailability": null,
      "access": "unknown",
      "territories": [],
      "notes": "Worldwide discovery lead. Exact fixture, English audio/commentary, public territory and viewing route must be verified before confirmation.",
      "sourceUrl": "https://news.google.com/rss/articles/CBMitwFBVV95cUxNNWxUNXZwMTR0VURaUms5WW1WcHNsTzNqWFAxV3dPMEFOYUV5T21pZDBJU0txNVgtZktCcUFmN1RqZ0VWdU9zSll5QXhfOVItUWhuX0hWdXhRNVJsZjcwMXBsSlZlaDEwaUdUUnJ0eFdXNElPc0tyZVJnZXlaNm9TajQ4V3d2RDl0NUdKaFZyWjZ5WEpTV1FBcTVvcFZxdENQWEpkbWkyeFY5aXVkMnV1N2k5Sm1xa00?oc=5",
      "sourcePublishedAt": "2026-09-28T07:00:00Z",
      "checkedAt": "2026-10-28T18:26:14.777243Z",
      "sourceKey": "global:camera-feed-discovery",
      "exactFixtureVerified": false,
      "publicAccessConfirmed": false
    }
  ]
};
