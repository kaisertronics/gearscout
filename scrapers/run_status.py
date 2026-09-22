"""
Shared "snapshot the last run's per-source status" writer, used by both the
scheduled run (main.py) and the dashboard's manual "Scrape now" button, so
the Dashboard tab's status table looks identical either way.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

RUN_STATUS_PATH = Path("/data/last_run.json")


def write_run_status(
    run_number: int,
    run_time: datetime,
    results: list,
    new_listings: list,
    manual: bool = False,
):
    """Snapshot the last run's per-source status so the dashboard can show
    it without needing to trigger a scrape of its own."""
    status = {
        "run_number": run_number,
        "manual": manual,
        "run_time": run_time.isoformat(),
        "new_listings_count": len(new_listings),
        "total_sources": len(results),
        "ok_sources": sum(1 for r in results if r.success or r.blocked),
        "sources": [
            {
                "name": r.source_name,
                "url": r.source_url,
                "success": r.success,
                "blocked": r.blocked,
                "count": len(r.listings),
                "duration_seconds": round(r.duration_seconds, 1),
                "error": r.error,
                "fix_hint": r.fix_hint,
            }
            for r in results
        ],
    }
    try:
        RUN_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUN_STATUS_PATH.write_text(json.dumps(status, indent=2))
    except Exception:
        logger.exception("Could not write run status snapshot")
