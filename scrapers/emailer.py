"""
Builds and sends the HTML email digest.
"""
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from .base import Listing, ScrapeResult

logger = logging.getLogger(__name__)


def _source_status_color(result: ScrapeResult) -> str:
    if result.success and result.listings:
        return "#22c55e"   # green
    if result.success and not result.listings:
        return "#94a3b8"   # slate — ok but nothing matched
    if result.blocked:
        return "#1d4ed8"   # blue — expected, has a manual link, not a bug
    return "#ef4444"       # red — failed


def build_email_html(
    new_listings: list[Listing],
    results: list[ScrapeResult],
    run_time: datetime,
    run_number: int,
    max_listings_per_source: int = 8,
    max_total_listings: int = 40,
    dashboard_url: str = "http://localhost:8420",
) -> str:
    """
    Build a full HTML email.
    - Top section: new listings (only sent when there are some)
    - Bottom section: source status report (always included)
    """

    # --- Source status tiles ---
    # Blocked sources (Guitar Center/Sweetwater/eBay behind Akamai) aren't
    # bugs needing attention — they're expected and have a working manual
    # link — so they're excluded from the "failed" alert/tally below.
    failed_sources = [r for r in results if not r.success and not r.blocked]
    ok_sources = [r for r in results if r.success or r.blocked]

    # Tiled instead of a row-per-source table — 3 per row, wrapped in a
    # plain <table> (not CSS flex/grid) since that's what renders reliably
    # across email clients. Only blocked/failed tiles link the source name
    # to its raw page — that link is the deliberate "check this yourself"
    # fallback for sources the app can't scrape or search. A successful
    # source's name used to link there too, but that's the same unfiltered
    # browse URL, and sitting next to "X new" it read like a shortcut to
    # those matches, which it never was — the real matches are the listing
    # cards above. Dropping the link there removes the false affordance.
    status_tiles = []
    for r in results:
        color = _source_status_color(r)
        icon = "✓" if r.success else ("🔗" if r.blocked else "✗")
        if r.success:
            count = f"{len(r.listings)} new"
        elif r.blocked:
            count = "manual check only"
        else:
            count = "FAILED"
        duration = f"{r.duration_seconds:.1f}s"

        if r.success:
            name_html = f'<span style="color:#1e293b;">{r.source_name}</span>'
        else:
            name_html = f'<a href="{r.source_url}" style="color:#1e40af;text-decoration:none;">{r.source_name}</a>'

        fix_html = ""
        if not r.success and r.fix_hint:
            manual_link = ""
            if r.source_url:
                manual_link = f"""
                <div style="margin-top:8px;">
                  <a href="{r.source_url}" target="_blank" rel="noopener"
                     style="display:inline-block;padding:5px 12px;background:#1e3a5f;
                         color:#ffffff;text-decoration:none;border-radius:6px;
                         font-size:11px;font-weight:600;">
                    Open in browser &rarr;
                  </a>
                </div>"""
            box_bg, box_border, box_text = (
                ("#eff6ff", "#bfdbfe", "#1d4ed8") if r.blocked
                else ("#fffbeb", "#fde68a", "#b45309")
            )
            label = "Heads up:" if r.blocked else "How to fix:"
            fix_html = f"""
            <div style="margin-top:8px;padding:8px 10px;font-size:11px;
                color:{box_text};background:{box_bg};border:1px solid {box_border};
                border-radius:6px;">
              <strong>{label}</strong> {r.fix_hint}
              {manual_link}
            </div>"""
        error_html = ""
        if not r.success and not r.blocked and r.error:
            error_html = f'<div style="margin-top:6px;font-size:11px;color:#ef4444;">{r.error}</div>'

        status_tiles.append(f"""
        <td width="33%" valign="top" style="padding:6px;">
          <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;
              padding:12px 14px;height:100%;">
            <div style="font-size:13px;font-weight:600;">
              <span style="color:{color};">{icon}</span> {name_html}
            </div>
            <div style="margin-top:4px;font-size:12px;color:#64748b;">
              {count} &middot; {duration}
            </div>
            {error_html}
            {fix_html}
          </div>
        </td>""")

    # Group tiles 3-per-row, padding the last row so cells stay evenly sized.
    status_rows = ""
    for i in range(0, len(status_tiles), 3):
        row_tiles = status_tiles[i:i + 3]
        while len(row_tiles) < 3:
            row_tiles.append('<td width="33%" style="padding:6px;"></td>')
        status_rows += f"<tr>{''.join(row_tiles)}</tr>"

    # --- Listing cards ---
    # Capped both per-source AND overall — with enough sources actually
    # finding real matches, an uncapped email can easily exceed Gmail's
    # ~102KB clipping threshold (confirmed: 148 listings across 25 sources
    # produced a 213KB email; even an 8-per-source cap alone still hit
    # 194KB with 23 active sources — the per-source cap isn't enough on its
    # own once enough sources are each contributing). Gmail truncates
    # mid-HTML past its limit, breaking the layout for everything after
    # the cut. The dashboard has no such limit and always shows everything,
    # so it's the actual place to see the rest.
    MAX_LISTINGS_PER_SOURCE = max_listings_per_source
    MAX_TOTAL_LISTINGS_SHOWN = max_total_listings

    listing_cards = ""
    by_source: dict[str, list[Listing]] = {}
    for l in new_listings:
        by_source.setdefault(l.source_name, []).append(l)

    shown_total = 0
    skipped_sources: list[str] = []
    for source_name, items in by_source.items():
        budget = MAX_TOTAL_LISTINGS_SHOWN - shown_total
        if budget <= 0:
            skipped_sources.append(source_name)
            continue
        shown = items[:min(MAX_LISTINGS_PER_SOURCE, budget)]
        shown_total += len(shown)
        remaining = len(items) - len(shown)
        listing_cards += f"""
        <h3 style="margin:28px 0 10px;font-size:14px;font-weight:600;
            color:#475569;text-transform:uppercase;letter-spacing:.05em;">
          {source_name} &mdash; {len(items)} listing{'s' if len(items) != 1 else ''}
        </h3>"""
        for item in shown:
            img_html = ""
            if item.image_url:
                img_html = f"""
                <img src="{item.image_url}" alt="" width="80" height="80"
                     style="width:80px;height:80px;object-fit:cover;
                            border-radius:6px;flex-shrink:0;" />"""
            price_html = ""
            if item.price:
                price_html = f"""
                <span style="display:inline-block;margin-top:6px;padding:2px 10px;
                    background:#dcfce7;color:#166534;border-radius:12px;
                    font-size:13px;font-weight:600;">{item.price}</span>"""
            desc_html = ""
            if item.description:
                desc_html = f"""
                <p style="margin:6px 0 0;font-size:13px;color:#64748b;line-height:1.5;">
                  {item.description}
                </p>"""
            posted_html = ""
            if item.posted_at:
                posted_html = f"""
                <span style="font-size:11px;color:#94a3b8;">
                  &nbsp;· {item.posted_at.strftime('%b %d, %I:%M %p UTC')}
                </span>"""

            listing_cards += f"""
            <div style="display:flex;gap:14px;padding:14px;margin-bottom:10px;
                background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;
                align-items:flex-start;">
              {img_html}
              <div style="flex:1;min-width:0;">
                <a href="{item.url}" style="font-size:15px;font-weight:600;
                    color:#1e3a5f;text-decoration:none;line-height:1.3;">
                  {item.title}
                </a>
                {posted_html}
                {price_html}
                {desc_html}
              </div>
            </div>"""

        if remaining > 0:
            listing_cards += f"""
            <p style="margin:4px 0 0;font-size:13px;color:#64748b;">
              + {remaining} more from {source_name} — see the full list on the dashboard.
            </p>"""

    total_new = len(new_listings)
    if skipped_sources or shown_total < total_new:
        hidden_count = total_new - shown_total
        skipped_note = f" ({len(skipped_sources)} source{'s' if len(skipped_sources) != 1 else ''} not shown at all: {', '.join(skipped_sources)})" if skipped_sources else ""
        listing_cards += f"""
        <div style="margin-top:20px;padding:14px 18px;background:#eff6ff;
            border:1px solid #bfdbfe;border-radius:8px;color:#1d4ed8;font-size:13px;">
          This email shows {shown_total} of {total_new} new listings found this run —
          the rest ({hidden_count}) are in the dashboard{skipped_note}. Capped to keep the
          email from growing large enough that some email clients (Gmail included) truncate it.
        </div>"""

    # --- Failed sources alert block ---
    failed_alert = ""
    if failed_sources:
        names = ", ".join(r.source_name for r in failed_sources)
        failed_alert = f"""
        <div style="margin-bottom:24px;padding:14px 18px;background:#fef2f2;
            border:1px solid #fecaca;border-radius:8px;color:#991b1b;">
          <strong>⚠️ {len(failed_sources)} source{'s' if len(failed_sources) != 1 else ''} failed:</strong>
          {names}<br/>
          <span style="font-size:13px;">See the Source Status section below for details and fix instructions.</span>
        </div>"""

    run_label = f"Run #{run_number} &middot; {run_time.strftime('%A %B %d, %Y at %I:%M %p UTC')}"
    total_ok = len(ok_sources)
    total_sources = len(results)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gear Scout Digest</title></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:20px;">

    <!-- Header -->
    <div style="background:#1e3a5f;color:#ffffff;padding:24px 28px;border-radius:12px 12px 0 0;">
      <div style="font-size:22px;font-weight:700;letter-spacing:-.02em;">🎛 Gear Scout</div>
      <div style="font-size:13px;color:#93c5fd;margin-top:4px;">{run_label}</div>
    </div>

    <!-- Body -->
    <div style="background:#f1f5f9;padding:24px 28px;border-radius:0 0 12px 12px;">

      <!-- This email is always a capped subset (see MAX_LISTINGS_PER_SOURCE/
      MAX_TOTAL_LISTINGS_SHOWN above) — this banner is unconditional, not
      just shown when this particular run happened to get truncated, so
      it's never a surprise that the dashboard has more. -->
      <div style="margin-bottom:20px;padding:14px 18px;background:#1e3a5f;
          border-radius:8px;display:flex;align-items:center;justify-content:space-between;
          flex-wrap:wrap;gap:10px;">
        <span style="color:#ffffff;font-size:13px;">
          This email never lists <strong>all</strong> your results — only a capped preview.
        </span>
        <a href="{dashboard_url}" target="_blank" rel="noopener"
           style="display:inline-block;padding:8px 18px;background:#ffffff;
               color:#1e3a5f;text-decoration:none;border-radius:6px;
               font-size:13px;font-weight:700;white-space:nowrap;">
          See everything on the dashboard &rarr;
        </a>
      </div>

      {failed_alert}

      <!-- New listings -->
      <div style="margin-bottom:32px;">
        <h2 style="margin:0 0 16px;font-size:18px;font-weight:700;color:#1e293b;">
          🆕 {len(new_listings)} New Listing{'s' if len(new_listings) != 1 else ''} Found
        </h2>
        {listing_cards if listing_cards else '<p style="color:#64748b;">No new matching listings this run.</p>'}
      </div>

      <!-- Source status -->
      <div>
        <h2 style="margin:0 0 12px;font-size:16px;font-weight:700;color:#1e293b;">
          📡 Source Status &mdash; {total_ok}/{total_sources} OK
        </h2>
        <table style="width:100%;border-collapse:collapse;table-layout:fixed;">
          <tbody>{status_rows}</tbody>
        </table>
      </div>

    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:16px;color:#94a3b8;font-size:12px;">
      Gear Scout &middot; Running in Docker &middot; Edit sources in config.yaml
    </div>
  </div>
</body>
</html>"""
    return html


def send_email(
    html: str,
    subject: str,
    cfg: dict,
    new_count: int,
    failed_count: int,
):
    """Send the digest via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    subject_line = f"{subject} — {new_count} new listing{'s' if new_count != 1 else ''}"
    if failed_count:
        subject_line += f" | ⚠️ {failed_count} source error{'s' if failed_count != 1 else ''}"
    msg["Subject"] = subject_line
    msg["From"] = cfg["from"]
    msg["To"] = cfg["to"]
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["from"], cfg["password"])
            server.sendmail(cfg["from"], [cfg["to"]], msg.as_string())
        logger.info("Email sent: %s", msg["Subject"])
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. "
            "Make sure you're using an App Password, not your regular password. "
            "Get one at: https://myaccount.google.com/apppasswords"
        )
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error: %s", e)
        return False
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False
