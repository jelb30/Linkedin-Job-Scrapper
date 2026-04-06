import argparse
import os
import time

from .job_runtime import (
    LocalFileStateStore,
    build_session,
    dedupe_jobs,
    error,
    info,
    parse_int,
    parse_bool,
    send_market_emails,
    warn,
)
from .job_sources import scrape_linkedin_jobs


PAGES_TO_SCRAPE = parse_int(os.getenv("LINKEDIN_PAGES_TO_SCRAPE"), 5)
CHECK_INTERVAL_SECONDS = parse_int(os.getenv("CHECK_INTERVAL_SECONDS"), 180)


def check_and_notify(include_india=False):
    info("Cycle start.")
    session = build_session()
    state = LocalFileStateStore()
    scraped_jobs = dedupe_jobs(
        scrape_linkedin_jobs(
            session=session,
            pages_to_scrape=PAGES_TO_SCRAPE,
            include_india=include_india,
        )
    )

    new_jobs = [job for job in scraped_jobs if not state.contains(job)]
    info(f"LinkedIn cycle summary | scraped={len(scraped_jobs)} | new={len(new_jobs)}")

    if not new_jobs:
        info("No new LinkedIn matches this cycle.")
        info("Cycle end.\n")
        return

    delivered_jobs = send_market_emails("LinkedIn", new_jobs)
    if delivered_jobs:
        state.mark_many(delivered_jobs)
        info(f"📬 Email sent | delivered_jobs={len(delivered_jobs)}")
    else:
        warn("Email did not send; new LinkedIn jobs will remain eligible next cycle.")

    info("Cycle end.\n")


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="LinkedIn job notifier.")
    parser.add_argument(
        "--include-india",
        action="store_true",
        help="Also include India jobs. US/North America remains enabled by default.",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single cycle and exit.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    include_india = args.include_india or parse_bool(os.getenv("JOBBOT_INCLUDE_INDIA"), False)
    info(
        "🚀 LinkedIn Job Notifier starting "
        f"| interval={CHECK_INTERVAL_SECONDS}s | pages={PAGES_TO_SCRAPE} "
        f"| include_india={include_india}"
    )
    while True:
        try:
            check_and_notify(include_india=include_india)
        except Exception as exc:
            error(f"Unhandled error in LinkedIn cycle. reason={exc}")
        if args.run_once:
            break
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
