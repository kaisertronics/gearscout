# Installing Gear Scout

## Prerequisites

- **Docker Desktop** (Mac/Windows) or **Docker Engine + the Compose plugin**
  (Linux) — that's the only thing you need installed. Everything else
  (Python, Playwright, the browser it scrapes with) lives inside the
  container.
- A **Gmail account with 2FA enabled**, if you want the email digest.
  Optional — see step 3 below.

## 1. Get the files

Clone or download this repository, then open a terminal in that folder —
every command below is run from there.

## 2. Create your config files

Gear Scout ships with two templates. Copy them to their real names — the
real ones hold your own credentials/keywords and are already excluded from
git via `.gitignore`, so they're safe to edit without worrying about
accidentally sharing them:

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

## 3. Set up email (optional, but recommended)

The digest email needs a Gmail **App Password** (not your regular
password):

1. Go to https://myaccount.google.com/apppasswords (requires 2FA to be
   enabled on the account first).
2. Name it anything (e.g. "Gear Scout") and create it.
3. Copy the 16-character password it gives you.

Open `config.yaml` and fill in the `email:` section:

```yaml
email:
  from: "youraddress@gmail.com"
  to: "youraddress@gmail.com"      # can be a different address
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  password: "xxxx xxxx xxxx xxxx"  # the app password from above
  subject: "Gear Scout Digest"
```

If you skip this, the scraper and dashboard still work fine — you just
won't get emailed, and you'd check the dashboard for new listings instead.

## 4. Add your own keywords

This is the part that actually makes Gear Scout *yours*. Open `config.yaml`
and look at the `keywords:` section — it ships **empty on purpose**, with a
block of commented-out examples across different gear categories (guitars,
drums, keyboards, DJ gear, studio/pro audio, brass, strings, amps/pedals).
Uncomment the ones you want, or just write your own list:

```yaml
keywords:
  - stratocaster
  - jazz bass
  - drum kit
  - moog
```

Matching is whole-word and case-insensitive (plurals like "amps" also match
"amp"), so short keywords are safe to use without misfiring on unrelated
words.

## 5. Set your schedule and timezone

Also in `config.yaml`:

```yaml
schedule:
  timezone: "America/Chicago"   # any IANA timezone name — DST is automatic
  cron: "0 8 * * *"             # minute hour day month weekday, in that timezone
```

The default runs once a day at 8am. For multiple checks a day (still only
emails you when something's actually new), e.g. four times a day:

```yaml
cron: "0 7,12,17,21 * * *"
```

## 6. (Optional) Remote access via ngrok

If you want to check the dashboard from your phone or another computer, see
the "Remote access" section in [USER_GUIDE.md](USER_GUIDE.md#remote-access-ngrok)
for how to get a free ngrok token and set it in `.env`. Skip this if you
only need the dashboard on the machine it's running on.

## 7. Build and start

```bash
docker compose build
docker compose up -d
```

This starts three services: the scraper (`scout`), the dashboard
(`dashboard`), and the optional remote-access tunnel (`ngrok`). If you
didn't set up an ngrok token, that third one just fails/restarts on its own
without affecting the other two — or start only what you need:

```bash
docker compose up -d scout dashboard
```

Gear Scout runs an initial scrape immediately, then on your cron schedule.
Watch it work:

```bash
docker compose logs -f
```

## 8. Open the dashboard

**http://localhost:8420** — bound to `127.0.0.1` by default, so it's only
reachable from the machine it's running on (unless you set up ngrok in step
6). See [USER_GUIDE.md](USER_GUIDE.md) for a full tour.

## 9. (Optional) Log in to Facebook

Only needed if you added any `type: facebook` sources. Go to the
dashboard's **Sources** page and click **"Log in to Facebook"** — see
[USER_GUIDE.md](USER_GUIDE.md#facebook-groups) for how that works.

---

## Updating

```bash
git pull            # if you cloned via git
docker compose build
docker compose up -d
```

Your `config.yaml`, `.env`, and collected data (the SQLite database, saved
Facebook session) all live outside the image — in the current folder and a
Docker volume — so rebuilding never touches them.

## Starting over

To wipe the "already seen" listings database and Facebook session and start
completely fresh:

```bash
docker compose down
docker volume rm gear-scout_gear_scout_data
docker compose up -d
```

Your `config.yaml` and `.env` are untouched by this — only the collected
data goes away.

## Troubleshooting install issues

| Problem | Likely cause / fix |
|---|---|
| `docker compose build` fails | Make sure Docker Desktop/Engine is actually running |
| Port `8420` already in use | Something else is using it — change the host side of the port mapping in `docker-compose.yml` (`"127.0.0.1:8420:8420"`) to a free port |
| Port `4041` already in use | Same idea, for the ngrok inspector — change the host side of its mapping |
| Dashboard loads but says "never" for last run | The first scrape can take a few minutes across ~20+ sources — check `docker compose logs -f scout` |
| `NGROK_AUTHTOKEN` not set / ngrok container keeps restarting | Only matters if you want remote access — see step 6 above, or ignore it and use `docker compose up -d scout dashboard` |
