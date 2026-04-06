import argparse
import os
import time

from .job_runtime import (
    InvalidAtsTargetTracker,
    LocalFileStateStore,
    build_session,
    dedupe_jobs,
    error,
    info,
    load_ats_targets,
    parse_int,
    parse_bool,
    send_market_emails,
    warn,
)
from .job_sources import scrape_direct_ats_jobs


ATS_CHECK_INTERVAL_SECONDS = parse_int(os.getenv("ATS_CHECK_INTERVAL_SECONDS"), 1200)
ATS_MAX_AGE_HOURS = parse_int(os.getenv("ATS_MAX_AGE_HOURS"), 72)


def check_and_notify(include_india=False):
    info("ATS cycle start.")
    session = build_session()
    state = LocalFileStateStore()
    invalid_tracker = InvalidAtsTargetTracker(
        threshold=parse_int(os.getenv("ATS_INVALID_TARGET_THRESHOLD"), 3)
    )
    targets = load_ats_targets()
    if sum(len(values) for values in targets.values()) == 0:
        warn("ATS cycle skipped because no ATS boards/sites are configured.")
        info("ATS cycle end.\n")
        return

    scraped_jobs, scrape_stats = scrape_direct_ats_jobs(
        session=session,
        targets=targets,
        max_age_hours=ATS_MAX_AGE_HOURS,
        include_india=include_india,
        invalid_tracker=invalid_tracker,
    )
    scraped_jobs = dedupe_jobs(scraped_jobs)
    new_jobs = [job for job in scraped_jobs if not state.contains(job)]
    info(
        f"ATS cycle summary | total_available={scrape_stats['total_available']} "
        f"| scraped={len(scraped_jobs)} | new={len(new_jobs)}"
    )

    if not new_jobs:
        info("No new ATS matches this cycle.")
        info("ATS cycle end.\n")
        return

    delivered_jobs = send_market_emails("ATS", new_jobs)
    if delivered_jobs:
        state.mark_many(delivered_jobs)
        info(f"📬 ATS email sent | delivered_jobs={len(delivered_jobs)}")
    else:
        warn("Email did not send; new ATS jobs will remain eligible next cycle.")

    info("ATS cycle end.\n")


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="ATS job notifier.")
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
        "🚀 ATS Job Notifier starting "
        f"| interval={ATS_CHECK_INTERVAL_SECONDS}s | max_age_hours={ATS_MAX_AGE_HOURS} "
        f"| include_india={include_india}"
    )
    while True:
        try:
            check_and_notify(include_india=include_india)
        except Exception as exc:
            error(f"Unhandled error in ATS cycle. reason={exc}")
        if args.run_once:
            break
        time.sleep(ATS_CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
