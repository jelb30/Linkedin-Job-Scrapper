import argparse
import time

from .job_runtime import error, info
from .ats_runner import ATS_CHECK_INTERVAL_SECONDS, ATS_MAX_AGE_HOURS, check_and_notify


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="ATS India job notifier.")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single cycle and exit.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    info(
        "🚀 ATS India Job Notifier starting "
        f"| interval={ATS_CHECK_INTERVAL_SECONDS}s | max_age_hours={ATS_MAX_AGE_HOURS} "
        f"| include_india=True"
    )
    while True:
        try:
            check_and_notify(include_india=True)
        except Exception as exc:
            error(f"Unhandled error in ATS India cycle. reason={exc}")
        if args.run_once:
            break
        time.sleep(ATS_CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
