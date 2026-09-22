# User Guide

Once it's running (see [INSTALL.md](INSTALL.md)), everything happens
through the dashboard at **http://localhost:8420**, plus the scheduled
email if you set one up.

## Dashboard tab

The landing page. At a glance:

- **Last run** / **Next scheduled run**
- **Sources OK** — how many sources came back successfully (or are a known
  "manual check only" site — see below) out of the total
- **Total listings seen**
- **Facebook session** status (active / not logged in)

Below that, a **Source status** table for the most recent run, and then
every recent listing, grouped by source, with images where the source
provides them.

### Reading the source status table

- **✓ green** — worked, here's how many new listings it found
- **🔗 blue "manual check only"** — the site blocks automated scraping
  outright (Guitar Center, Sweetwater, and eBay all do this via Akamai bot
  protection, confirmed by the site serving a reCAPTCHA/error page instead
  of results). This isn't a bug and won't fix itself — click the **"Open
  ... in browser"** button to run the same search yourself instead.
- **✗ red "failed"** — something actually broke (a site changed its page
  layout, a feed URL moved, etc.) — the error message includes a "How to
  fix" note, usually pointing at the exact function in
  `scrapers/html_scraper.py` to update if you're comfortable editing
  Python. If not, just disable that source from the Sources tab.

## Search

Two ways to search, both from the search box in the top bar or the
dedicated **Search** page:

- **Regular search** — instant, searches title/description/tags across
  every listing Gear Scout has already collected from past runs. Same
  whole-word matching as your keyword list (see below).
- **"Search live now"** — re-scrapes every enabled source right now,
  filtered by your search phrase instead of your standing keyword list.
  Useful for "has anyone posted a X in the last few minutes" instead of
  waiting for the next scheduled run. This takes a minute or two (it's
  hitting ~20+ real sites), and shows a live progress banner while it
  works. Results are saved the same way a scheduled run's results are, so
  they show up in regular search afterward too and won't trigger a
  duplicate in your next email digest.

## Favorites & tags

Click the star (★) on any listing card to save it to the **Favorites**
page. Click "edit tags" on any card to add your own freeform labels
(comma-separated) — tags are searchable too, so you can tag things like
"want", "too far", or "follow up" and find them again later.

## Sources tab

Add a source without hand-editing YAML: name, type, URL, and (for RSS
sources) a feed URL. Toggle any source on/off, or remove it — changes save
straight to `config.yaml` (comments and formatting preserved) and take
effect on the next run, no rebuild needed.

**Source types:**

| Type | What it's for |
|---|---|
| `html` | Scraped as a regular web page (most marketplaces/forums) |
| `rss` | A forum or feed with its own RSS/Atom URL |
| `craigslist` | Craigslist's own search format, one specific city — `https://{city}.craigslist.org/search/msa` (find city subdomains at https://www.craigslist.org/about/sites) |
| `craigslist_region` | One broad ~1000-mile-radius Craigslist search — see [Craigslist coverage](#craigslist-coverage) below |
| `facebook` | A Facebook group — needs a login first, see below |
| `facebook_marketplace_region` | One US region's Facebook Marketplace feed — see [Facebook Marketplace](#facebook-marketplace) below |
| `reddit` | A subreddit — needs `reddit_oauth` filled in in `config.yaml` |

### Craigslist coverage

The default config ships with **3 `craigslist_region` sources** — "Craigslist
— US West", "US Central", and "US East" — enabled out of the box, covering
the whole continental US. There's no single URL that searches all of
Craigslist at once (each city is its own subdomain), so instead each region
uses Craigslist's own "search distance" filter set to ~1000 miles from a
central point — confirmed live to genuinely span that far (e.g. a
Seattle-area search with a Miami postal code returns results from
Cincinnati, Tampa, Nashville, and everywhere between). The three regions'
circles overlap enough to jointly cover the country in just 3 requests,
instead of iterating hundreds of individual city subdomains.

Every listing found still shows/searches under **its own actual posted
city** (e.g. "Craigslist — Sherman Oaks"), parsed from that specific
listing, not a generic "US West" label — so it displays exactly like any
other source everywhere in the dashboard. Each region is its own row in the
source status table, and can be toggled off individually from the Sources
page if you only care about part of the country.

Want a specific city covered on its own instead (or a city outside the
US)? Add a `craigslist` type source with that city's own
`{city}.craigslist.org/search/msa` URL. Just know that a listing which falls
within both a region search and a separately-added city can occasionally
show up twice, tagged slightly differently (e.g. "Seattle" vs. the
listing's actual neighborhood) — a broad radius search can't practically
exclude one specific city out of thousands of postings the way per-city
scraping can. In practice this is uncommon and harmless (just a duplicate
card).

This is meaningfully more load on Craigslist than scraping a handful of
cities — only enable it if you actually want nationwide coverage. Also
consider that a run this broad may surface a lot more listings per cycle,
which means a longer email digest.

### Facebook groups

Facebook sources need an active login before they'll return anything.

1. Go to **Sources** and click **"Log in to Facebook."**
2. A real (non-headless) browser opens right inside the dashboard page,
   streamed to you live — this isn't a scripted login. A fully automated
   headless login gets flagged by Facebook's own bot detection (it serves a
   CAPTCHA instead of letting you in), so this hands the whole thing to
   you instead.
3. Log in exactly as you would in any browser — email, password, 2FA, any
   "I'm not a robot" check.
4. This finishes on its own the moment you're logged in — it's watching for
   your session to appear, no button to click. (If it doesn't pick it up
   automatically, there's an "Already logged in? Check now" button.)
5. Your session is saved and reused by every Facebook source on future
   runs, until it eventually expires — if a Facebook source starts failing
   with a session/login error, just repeat this flow.

Add a group by pasting its URL into the Sources form with type `facebook`.

### Facebook Marketplace

Two separate ways to cover Facebook Marketplace, for two different needs:

**1. Manual — search anything, right now, in your own browser.** Right on
the **Dashboard** tab, there's a "Facebook Marketplace — search all
regions" box — type a search term and click **"Open all 8 regions"** — it
opens Facebook's own Marketplace search for that term in 8
new tabs (Pacific Northwest, Southwest, Rocky Mountains, Texas, The South,
Midwest, Mid-Atlantic, Southeast), using *your own* logged-in Facebook
session. Nothing is scraped, stored, or sent to Gear Scout at all — this is
just a shortcut for opening 8 searches you could otherwise type by hand.
One-time setup: open Facebook Marketplace yourself and set your search
radius under Filters — Facebook remembers that per-account, so it applies
automatically to every region search from here on.

**2. Automated — background monitoring, same as every other source.** The
template ships 8 `facebook_marketplace_region` sources (one per region
above), commented out by default. These need the same Facebook login as
groups do (see above). Unlike the manual search, these don't send Facebook
a keyword query at all — Facebook's own search box requires every word in
a query to match (same limitation as Craigslist and eBay's search), so
instead each region fetches its general Marketplace browse feed once and
filters the results locally against your whole keyword list — **8
automated requests per run, not one per keyword.** Matches show up exactly
like any other source: dashboard, email digest, search, favorites.

Worth knowing before enabling all 8: this uses the same saved-session
automation as your Facebook groups, just applied more broadly (8 requests
instead of a few) — meaningfully more automated traffic against your
account than groups alone, though nowhere near what a per-keyword search
sweep would be. If you'd rather not run that much automated Facebook
traffic on a schedule, the manual search above covers the same ground
without any of that risk, just with you doing the actual browsing.

## Email digest

Only sent when there's something to report:

| Situation | Email sent? |
|---|---|
| New listings found | ✅ Yes |
| No new listings, everything OK | ❌ No |
| No new listings, but a source actually failed | ✅ Yes (with the error + fix instructions) |

"Manual check only" sources (see above) don't count as failures and won't
trigger an email by themselves.

## How keyword matching works

Matching is **whole-word and case-insensitive**, with optional plurals
(`amps` also matches `amp`) — a keyword like `neve` matches "Neve 1073" but
*not* "never used", since word-boundary matching requires it to appear as
its own word, not just a substring. This applies everywhere: the scheduled
scrape, the email digest, and both search modes in the dashboard.

Add or remove keywords any time in `config.yaml` (or send yourself a
reminder — there's no dashboard editor for the keyword list itself, just
sources). No rebuild needed; keywords reload on every run.

## Remote access (ngrok)

To reach the dashboard from your phone or another computer:

1. Sign up free at [ngrok.com](https://ngrok.com/) and grab your authtoken
   from https://dashboard.ngrok.com/get-started/your-authtoken.
2. Put it in `.env`:
   ```
   NGROK_AUTHTOKEN=your_token_here
   ```
3. `docker compose up -d` (the `ngrok` service only does anything once this
   is set).
4. Find your public URL at **http://localhost:4041** (ngrok's own local
   inspector) or via `docker compose logs ngrok`. On the free tier this URL
   changes every time the tunnel restarts, unless you've reserved a static
   domain on a paid plan.

### ⚠️ Security note

**The dashboard has no login by default.** That means once you turn on
ngrok, *anyone* with the public URL can view your listings, add/remove
sources, edit `config.yaml` through the Sources page, and trigger the
Facebook-login browser — there's no separate gate on any of it. This is
fine if you're the only one who'll ever have that URL, but treat the URL
itself as the only thing standing between a stranger and your dashboard.

If you want a login screen back, open `dashboard.py` and find this block
near the top:

```python
@app.before_request
def require_login():
    # Disabled at the user's explicit request ...
    return None
    if request.endpoint in ("login", "static"):
        return None
    if not session.get("authenticated"):
        return redirect(url_for("login", next=request.path))
    return None
```

Delete the `return None` line right after the comment (the login route and
page already exist, just gated off), then rebuild:

```bash
docker compose build dashboard
docker compose up -d dashboard
```

The login screen will ask for the `from` address and `password` from
`config.yaml`'s `email:` section — the same Gmail App Password used to send
your digest doubles as your dashboard login, so there's nothing extra to
set up.

## Troubleshooting

### A source shows "manual check only"

Not a bug — see [Reading the source status table](#reading-the-source-status-table)
above. Use the button, or disable the source from the Sources tab if you'd
rather not see it.

### A source shows "failed" (red)

The error includes a "How to fix" note. Most often this means the site
changed its page layout and a CSS selector in
`scrapers/html_scraper.py` needs updating — open the URL in a browser,
inspect a listing card, and update the selector the fix hint points at, then:

```bash
docker compose build scout dashboard
docker compose up -d scout dashboard
```

If you're not comfortable editing the scraper, just disable that source.

### A Facebook source fails with a login/session error

Sessions eventually expire. Repeat the [Facebook login](#facebook-groups)
flow from the Sources page.

### Start completely fresh

See "Starting over" in [INSTALL.md](INSTALL.md#starting-over).

## File structure

```
gear-scout/
├── config.yaml.example   ← template — copy to config.yaml and fill in
├── config.yaml           ← your real config: keywords, sources, email, schedule (git-ignored)
├── .env.example          ← template — copy to .env for the ngrok token
├── .env                  ← your real secrets (git-ignored)
├── docker-compose.yml    ← scout (scraper) + dashboard + ngrok services
├── Dockerfile
├── requirements.txt
├── main.py               ← scraper entry point and scheduler
├── dashboard.py          ← the web dashboard (localhost:8420)
├── facebook_login_service.py ← spawned by the dashboard's "Log in to Facebook" button
├── fb_login_local.py     ← alternative: run on your own Mac to log in via your real Chrome
├── templates/            ← dashboard HTML (Flask/Jinja)
├── static/style.css      ← dashboard styling
├── scrapers/
│   ├── base.py           ← Listing/ScrapeResult dataclasses, keyword matching
│   ├── dispatch.py        ← routes each source to the right scraper function
│   ├── rss_scraper.py     ← RSS/Atom feeds
│   ├── html_scraper.py    ← Guitar Center, Sweetwater, Reverb, eBay, Craigslist, etc.
│   ├── facebook_scraper.py ← Playwright FB scraper + in-browser login flow
│   ├── facebook_marketplace_regions.py ← the 8 region location IDs, shared by the
│   │                       manual search page and the automated region sources
│   ├── manual_scrape.py   ← the dashboard's "Scrape now" button (no email)
│   ├── run_status.py      ← shared last-run-status writer (scheduled + manual)
│   ├── live_search.py     ← the dashboard's on-demand "search live now"
│   ├── store.py           ← SQLite storage (dedup, favorites, tags, search)
│   └── emailer.py         ← HTML email builder and SMTP sender
├── README.md
├── INSTALL.md
└── USER_GUIDE.md
```

Collected data lives in a Docker volume (`gear_scout_data`), shared by both
services — not in this folder, so it survives rebuilds:
- `/data/seen_listings.db` — SQLite database (dedup, favorites, tags)
- `/data/last_run.json` — snapshot of the most recent run's per-source status
- `/data/fb_session.json` — saved Facebook session cookies
