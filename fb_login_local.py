#!/usr/bin/env python3
"""
One-time Facebook login using your actual installed Chrome, running directly
on your Mac — no Docker, no VNC, just a normal Chrome window.

Setup (once):
    pip3 install playwright

Usage:
    python3 fb_login_local.py

A Chrome window opens to the Facebook login page. Log in there yourself —
email, password, 2FA code, any "I'm not a robot" check — all done by you,
nothing automated. Once you're on your actual News Feed, come back here and
press ENTER. The session is then copied into the running Docker container so
the scraper can reuse it.
"""
import json
import subprocess
import sys
from pathlib import Path

FB_LOGIN_URL = "https://www.facebook.com/login"
CONTAINER_NAME = "gear-scout"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed on your Mac yet. Run:")
        print("  pip3 install playwright")
        print("Then try this again.\n")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("FACEBOOK LOGIN — via your local Chrome")
    print("=" * 60)
    print("\nOpening Chrome...")

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chrome", headless=False)
        except Exception:
            print("Couldn't find an installed Chrome — falling back to Playwright's")
            print("bundled Chromium instead. If this also fails, run:")
            print("  playwright install chromium\n")
            browser = pw.chromium.launch(headless=False)

        context = browser.new_context()
        page = context.new_page()
        page.goto(FB_LOGIN_URL, wait_until="domcontentloaded")

        input(
            "\nLog in to Facebook in the window that opened, then come back "
            "here and press ENTER... "
        )

        cookie_names = {c["name"] for c in context.cookies()}
        if not {"c_user", "xs"} <= cookie_names:
            print("\nDoesn't look like you're logged in yet — no session cookies found.")
            input("Finish logging in, then press ENTER again (or Ctrl+C to abort)... ")
            cookie_names = {c["name"] for c in context.cookies()}

        if not {"c_user", "xs"} <= cookie_names:
            browser.close()
            print("\n❌ Still not logged in. Nothing was saved — try again.\n")
            sys.exit(1)

        cookies = context.cookies()
        browser.close()

    export_path = Path(__file__).parent / "fb_session_export.json"
    export_path.write_text(json.dumps(cookies, indent=2))

    print("\nLogin looks good. Copying the session into the running container...")
    try:
        subprocess.run(
            ["docker", "cp", str(export_path), f"{CONTAINER_NAME}:/data/fb_session.json"],
            check=True,
        )
    except subprocess.CalledProcessError:
        print(f"\n❌ Could not copy into container '{CONTAINER_NAME}'.")
        print(f"   Is it running? Check with: docker ps --filter name={CONTAINER_NAME}")
        print(f"   The exported session is still saved locally at: {export_path}")
        sys.exit(1)
    finally:
        # Don't leave a live session-cookie file sitting in plaintext longer
        # than necessary — it's as sensitive as a password.
        if export_path.exists():
            export_path.unlink()

    print("\n✅ Done. Facebook session is active for the scraper.")
    print("Set 'enabled: true' on your Facebook sources in config.yaml.")
    print("Sessions typically last 30–90 days — re-run this script if scraping stops working.\n")


if __name__ == "__main__":
    main()
