# Gear Scout

Gear Scout watches marketplaces, forums, Craigslist, Reddit, and Facebook
groups for used musical gear and emails you a digest when something new
shows up — plus a live web dashboard you can check any time in between.

It's not tied to any one instrument or category. **You tell it what to look
for** by editing a keyword list — guitars, drums, synths, DJ gear, studio
gear, orchestral instruments, whatever you're after — and it only ever
surfaces listings that match your own words.

Runs entirely in Docker, on your own machine or a small server. Nothing
about your search leaves your own setup except the sites it reads from.

## Features

- **Multi-source scraping** — Reverb, eBay, Guitar Center, Sweetwater,
  Craigslist (any city), Reddit, Facebook groups, and any forum with an RSS
  feed, all in one place.
- **Your own keywords** — nothing is hardcoded to a genre or instrument;
  matching is whole-word and case-insensitive, so short keywords like "eq"
  or "amp" won't misfire on unrelated text.
- **Scheduled email digest** — runs on whatever cron schedule you set, in
  your own timezone. Only emails when there's something new to report.
- **Live dashboard** (`http://localhost:8420`) — source status at a glance,
  keyword search across everything already collected, an on-demand "search
  live now" that re-checks every site immediately, and favorites/tags for
  listings you want to track.
- **Facebook login, done properly** — logging in happens in a real browser
  window streamed to you in the dashboard, not a scripted headless login
  (which gets flagged and CAPTCHA'd). You do the actual typing; Gear Scout
  just remembers the session afterward.
- **Honest about bot-blocked sites** — Guitar Center, Sweetwater, and eBay
  all sit behind bot detection that blocks automated scraping outright.
  Rather than pretend to fix that, those sources show as "manual check
  only" with a one-click link to the same search in your own browser.
- **Optional remote access** — an included ngrok service can expose the
  dashboard to a public URL, so you can check it from your phone.

## Getting started

1. **[INSTALL.md](INSTALL.md)** — prerequisites, first-time setup, and
   getting it running.
2. **[USER_GUIDE.md](USER_GUIDE.md)** — using the dashboard, adding
   sources, Facebook login, remote access, and troubleshooting.

## A note on scraping

Gear Scout reads public listing pages the same way a browser would — it
doesn't create accounts, bypass logins, or defeat bot-detection/CAPTCHAs on
sites that use them (a few sources are marked "manual check only" for
exactly that reason, by design). Scraping is subject to each site's own
terms of service; use this for your own personal gear search and be
reasonable about how often you run it.
