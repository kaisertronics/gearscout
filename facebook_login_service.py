#!/usr/bin/env python3
"""
Background worker for the dashboard's "Log in to Facebook" button.

Spawned as a subprocess by dashboard.py. Starts a virtual display, a VNC
server, and noVNC (a browser-based VNC client served over plain HTTP/WS —
no separate VNC app needed), then opens a real, visible Chromium window to
Facebook's login page. The human logs in there themselves — same reasoning
as fb_login_local.py and the original VNC flow: Facebook's bot detection
reliably blocks a scripted headless login (it serves a CAPTCHA instead), so
this hands the whole flow to a real person instead of automating it.

Completes automatically: it polls the browser's own cookies for Facebook's
auth cookies (c_user/xs) and saves the session the moment they appear — no
manual "I'm logged in" click needed once you've actually submitted the login
in the embedded browser. /data/.fb_login_signal still works as a manual
override (e.g. if a slow network delays the cookies) but isn't required.

Communicates with dashboard.py entirely through files in /data, since it's a
separate process:
  - writes  /data/fb_login_status.json   (state machine for the UI to poll)
  - reads   /data/.fb_login_signal        (optional manual override)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scrapers.facebook_scraper import FB_LOGIN_URL, _save_session, _start_vnc_display

STATUS_PATH = Path("/data/fb_login_status.json")
SIGNAL_PATH = Path("/data/.fb_login_signal")
LOGIN_TIMEOUT_SECONDS = 15 * 60


def write_status(**kwargs):
    STATUS_PATH.write_text(json.dumps(kwargs))


def main():
    SIGNAL_PATH.unlink(missing_ok=True)
    write_status(state="starting")

    # dashboard.py's own /vnc-ws route proxies to the x11vnc server this
    # starts (localhost:5900) — no separate websockify process/port needed;
    # that's what left the viewer blank when accessed through a single-port
    # tunnel like ngrok, which can't reach a second port at all.
    xvfb, fluxbox, x11vnc = _start_vnc_display()

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"],
            )
            context = browser.new_context(viewport=None, locale="en-US")
            page = context.new_page()
            page.goto(FB_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)

            write_status(state="waiting_for_login")

            deadline = time.time() + LOGIN_TIMEOUT_SECONDS
            logged_in = False
            while time.time() < deadline:
                cookie_names = {c["name"] for c in context.cookies()}
                if {"c_user", "xs"} <= cookie_names:
                    logged_in = True
                    break
                if SIGNAL_PATH.exists():
                    # Manual override — proceed to the same cookie check
                    # below even though auto-detection hasn't fired yet.
                    SIGNAL_PATH.unlink(missing_ok=True)
                    break
                time.sleep(2)

            if not logged_in:
                cookie_names = {c["name"] for c in context.cookies()}
                logged_in = {"c_user", "xs"} <= cookie_names

            if not logged_in:
                if time.time() >= deadline:
                    write_status(state="timed_out")
                else:
                    write_status(
                        state="failed",
                        reason="No authenticated session cookies found — login likely incomplete.",
                    )
                browser.close()
                return

            write_status(state="verifying")
            _save_session(context)
            browser.close()
            write_status(state="success")

    except Exception as e:
        write_status(state="failed", reason=str(e))

    finally:
        x11vnc.terminate()
        fluxbox.terminate()
        xvfb.terminate()


if __name__ == "__main__":
    main()
